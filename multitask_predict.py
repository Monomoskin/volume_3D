import cv2
import numpy as np
import os
import json
import csv
import pandas as pd
import torch
from detectron2.engine import DefaultPredictor
from detectron2.config import get_cfg
from detectron2.data import MetadataCatalog
from detectron2.data.datasets import register_coco_instances
from detectron2.utils.visualizer import Visualizer, ColorMode
from detectron2.model_zoo import get_config_file

# --- CONSTANTES DE CALIBRACIÓN (DEBES VERIFICAR ESTOS VALORES REALES) ---
FRASCO_DIAMETER_MM = 90.0
FRASCO_HEIGHT_MM =12.0

# --- 1. Helper function (Sin cambios) ---
def find_highest_score_instance(instances, class_id):
    """
    Returns the instance with the highest score for a given class ID.
    """
    if len(instances) == 0:
        return None
    scores = instances.scores
    classes = instances.pred_classes
    class_indices = (classes == class_id).nonzero(as_tuple=True)[0]
    if len(class_indices) == 0:
        return None
    best_idx = class_indices[torch.argmax(scores[class_indices])]
    
    from detectron2.structures import Instances
    best_instance = Instances(instances.image_size)
    best_instance.pred_masks = instances.pred_masks[best_idx:best_idx+1]
    best_instance.pred_classes = instances.pred_classes[best_idx:best_idx+1]
    best_instance.scores = instances.scores[best_idx:best_idx+1]
    
    return best_instance

# --- 2. LÓGICA DE PREDICCIÓN CON DOBLE IMAGEN (Sin cambios mayores) ---
def process_sample_pair(predictor, metadata, sample_key, input_image_dir, output_base_dir, category_names):
    """
    Procesa una muestra: TOP siempre, SIDE opcional. Genera CSV con fila por célula
    incluyendo atributos species, embryogenic_potential y quality. 
    El volumen solo se calcula si SIDE está presente.
    """
    # --- Rutas de archivos ---
    top_name = f"{sample_key}_TOP.jpeg"
    side_name = f"{sample_key}_SIDE.jpeg"
    top_path = os.path.join(input_image_dir, top_name)
    side_path = os.path.join(input_image_dir, side_name)

    # Intentar .jpg si no existe .jpeg
    if not os.path.exists(top_path):
        top_name = top_name.replace(".jpeg", ".jpg")
        top_path = os.path.join(input_image_dir, top_name)
        if not os.path.exists(top_path):
            print(f"[SKIP] Faltan archivos TOP para {sample_key}")
            return

    has_side = os.path.exists(side_path)
    print(f"[PROCESS] Procesando {sample_key} (SIDE {'sí' if has_side else 'no'})")

    # --- IDs de clases ---
    frasco_id = category_names.index("container")
    cell_id = category_names.index("callus")  # o "cell" si así se llama en tu JSON
    try:
        cell_profile_id = category_names.index("cell_profile")
    except ValueError:
        cell_profile_id = cell_id

    # -------------------------------------------------------------
    # SIDE: Altura Z y calibración (opcional)
    # -------------------------------------------------------------
    height_mm = None
    if has_side:
        im_side = cv2.imread(side_path)
        outputs_side = predictor(im_side)
        instances_side = outputs_side["instances"].to("cpu")

        frasco_side = find_highest_score_instance(instances_side, frasco_id)
        if frasco_side is None:
            print("[ERROR] Frasco no detectado SIDE")
        else:
            frasco_side_mask = frasco_side.pred_masks[0].numpy().astype(bool)
            y_coords, _ = np.where(frasco_side_mask)
            factor_z_mm_per_pixel = FRASCO_HEIGHT_MM / (y_coords.max() - y_coords.min())

            cell_profile = find_highest_score_instance(instances_side, cell_profile_id)
            if cell_profile is None:
                print("[ERROR] Cell profile no detectada SIDE")
            else:
                mask_cell_profile = cell_profile.pred_masks[0].numpy().astype(bool)
                height_mm = mask_cell_profile.shape[0] * factor_z_mm_per_pixel

    # -------------------------------------------------------------
    # TOP: área XY y atributos
    # -------------------------------------------------------------
    im_top = cv2.imread(top_path)
    outputs_top = predictor(im_top)
    instances_top = outputs_top["instances"].to("cpu")

    frasco_top = find_highest_score_instance(instances_top, frasco_id)
    if frasco_top is None:
        print("[ERROR] Frasco no detectado TOP")
        return
    frasco_top_mask = frasco_top.pred_masks[0].numpy().astype(bool)
    y_coords_top, x_coords_top = np.where(frasco_top_mask)
    pixels_per_mm = (x_coords_top.max() - x_coords_top.min()) / FRASCO_DIAMETER_MM
    pixels_to_mm2 = 1 / (pixels_per_mm ** 2)

    # -------------------------------------------------------------
    # Separar instancias de callos y atributos
    # -------------------------------------------------------------
    cells = []
    attributes = []

    # -------------------------------------------------------------
# Extraer células y atributos multitarea del ROI head
# -------------------------------------------------------------
    cells = []

    for idx in range(len(instances_top)):
        cls_id = instances_top.pred_classes[idx].item()
        if cls_id != cell_id:
            continue

        mask = instances_top.pred_masks[idx].numpy().astype(bool)
        y_c, x_c = np.where(mask)
        center = [int(np.mean(x_c)), int(np.mean(y_c))]

        area_mm2 = np.sum(mask) * pixels_to_mm2
        volume_ml = area_mm2 * height_mm / 1000 if height_mm is not None else None

        inst = instances_top[idx]

        # Clases predichas por las cabezas multitarea (enteros 0,1,2,...)
        vol_cls = inst.pred_volume.item()
        qual_cls = inst.pred_quality.item()
        species_cls = inst.pred_species.item()
        stage_cls = inst.pred_stage.item()

        # Si quieres, puedes mapear a etiquetas legibles usando tus INV_*_MAP:
        # from train_callus_multitask import INV_VOL_MAP, INV_QUAL_MAP, INV_SPECIES_MAP, INV_STAGE_MAP
        # vol_label = INV_VOL_MAP[vol_cls]
        # qual_label = INV_QUAL_MAP[qual_cls]
        # species_label = INV_SPECIES_MAP[species_cls]
        # stage_label = INV_STAGE_MAP[stage_cls]

        cells.append({
            "cell_index": idx,
            "mask": mask,
            "center": center,
            "volume_ml": volume_ml,
            "area_mm2": area_mm2,
            "height_mm": height_mm,
            "score": inst.scores.item(),
            "volume_class": vol_cls,
            "quality_class": qual_cls,
            "species_class": species_cls,
            "stage_class": stage_cls,
        })

    # -------------------------------------------------------------
    # Asociar atributos a la célula más cercana
    # -------------------------------------------------------------
    for attr in attributes:
        min_dist = float("inf")
        nearest_cell = None
        for cell in cells:
            dist = np.linalg.norm(np.array(cell["center"]) - np.array(attr["center"]))
            if dist < min_dist:
                min_dist = dist
                nearest_cell = cell
        if nearest_cell is not None:
            if attr["class_name"] == "species":
                nearest_cell["species"] = attr["score"]
            elif attr["class_name"] == "embryogenic_potential":
                nearest_cell["embryogenic_potential"] = attr["score"]
            elif attr["class_name"] == "quality":
                nearest_cell["quality"] = attr["score"]

    # -------------------------------------------------------------
    # Guardar CSV
    # -------------------------------------------------------------
    output_csv_path = os.path.join(output_base_dir, f"{sample_key}_volumes.csv")
    fieldnames = [
    "cell_index","class_name","volume_ml","area_mm2","height_mm","center","score",
    "volume_class","quality_class","species_class","stage_class"
    ]

    with open(output_csv_path, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for cell in cells:
            writer.writerow({
            "cell_index": cell["cell_index"],
            "class_name": "callus",  # o "cell"
            "volume_ml": cell["volume_ml"],
            "area_mm2": cell["area_mm2"],
            "height_mm": cell["height_mm"],
            "center": cell["center"],
            "score": cell["score"],
            "volume_class": cell["volume_class"],
            "quality_class": cell["quality_class"],
            "species_class": cell["species_class"],
            "stage_class": cell["stage_class"],
        })

    print(f"[SAVE] CSV generado: {output_csv_path}")

# --- 3. FUNCIÓN MODIFICADA: Consolidación y Análisis ---
def consolidate_results(output_base_dir, real_volume_map):
    all_files = [os.path.join(output_base_dir, f) for f in os.listdir(output_base_dir) if f.endswith('_volumes.csv')]
    
    if not all_files:
        print("\nNo individual volume CSV files found to consolidate.")
        return

    all_data = []
    
    for f in all_files:
        try:
            df = pd.read_csv(f)
            # Extraer la clave de la muestra (ej: "Sample_039") del nombre del archivo CSV
            sample_key = os.path.basename(f).replace('_volumes.csv', '')
            df.insert(0, 'sample_key', sample_key)
            all_data.append(df)
        except Exception as e:
            print(f"Error reading file {f}: {e}")

    if not all_data:
        print("No data successfully read for consolidation.")
        return

    master_df = pd.concat(all_data, ignore_index=True)
    
    # --- LÓGICA DE CRUCE Y CÁLCULO DE PRECISIÓN ---
    
    # Mapear el volumen real (anotado) a cada fila del dataframe
    master_df['real_volume_ml'] = master_df['sample_key'].apply(lambda x: real_volume_map.get(x, np.nan))

    # Calcular la precisión / Error Absoluto Porcentual
    # Asegúrate de que el volumen real no sea cero antes de la división
    master_df['error_abs_ml'] = np.abs(master_df['volume_ml'] - master_df['real_volume_ml'])
    master_df['precision_percent'] = (1 - (master_df['error_abs_ml'] / master_df['real_volume_ml'])) * 100
    
    # Limpieza de la columna 'center' y reordenamiento
    if 'center' in master_df.columns:
        master_df['center'] = master_df['center'].astype(str)
        master_df[['center_x', 'center_y']] = master_df['center'].str.strip('[]').str.split(', ', expand=True).astype(float)
        master_df = master_df.drop(columns=['center'])

    cols = ['sample_key', 'class_name', 'volume_ml', 'real_volume_ml', 'error_abs_ml', 'precision_percent', 
            'score', 'cell_index', 'area_mm2', 'height_mm', 'center_x', 'center_y']
    master_df = master_df.reindex(columns=cols)

    master_csv_path = os.path.join(output_base_dir, 'all_volumes_summary.csv')
    
    # Guardar en Excel
    master_df.to_excel(master_csv_path.replace('.csv', '.xlsx'), index=False)
    
    # Imprimir métrica global de precisión (solo para muestras con volumen real)
    valid_precision = master_df.dropna(subset=['real_volume_ml', 'precision_percent'])
    
    if not valid_precision.empty:
        mean_precision = valid_precision['precision_percent'].mean()
        mean_error = valid_precision['error_abs_ml'].mean()
        
        print(f"\n==============================================")
        print(f"✅ CONSOLIDACIÓN Y ANÁLISIS EXITOSO")
        print(f"ERROR ABSOLUTO PROMEDIO: {mean_error:.3f} mL")
        print(f"PRECISIÓN PROMEDIO: {mean_precision:.2f}%")
        print(f"RESULTADOS GUARDADOS EN: {master_csv_path.replace('.csv', '.xlsx')}")
        print(f"==============================================")
    else:
        print("\nNo se pudo calcular la precisión. Revise si el volumen real está en el COCO JSON.")

# --- 4. Main prediction logic (MODIFICADA para cargar datos COCO) ---
def main():
    # --- Paths ---
    input_image_dir = "testImages"
    model_path = "output_callus/model_final.pth" 
    output_base_dir = "output_predict"
    os.makedirs(output_base_dir, exist_ok=True)

    # --- Dataset and Metadata Setup ---
    dataset_name = "celulas_frascos"
    json_path = os.path.join("annotations", "coco_annotations.json")
    image_dir = "images"
    try:
        register_coco_instances(dataset_name, {}, json_path, image_dir)
    except AssertionError:
        pass
        
    with open(json_path, 'r') as f:
        coco_data = json.load(f)

    category_names = [cat['name'] for cat in coco_data['categories']]
    MetadataCatalog.get(dataset_name).thing_classes = category_names
    metadata = MetadataCatalog.get(dataset_name)
    
    # ====================================================================
    # LÓGICA CLAVE AÑADIDA: CARGAR VOLUMEN REAL DE COCO (FINAL)
    # ====================================================================
    real_volume_map = {}

    # 1. Crear un mapa de Image ID a Sample Key (ej: {1: 'Sample_039'})
    #    Esto es necesario para cruzar las anotaciones con el nombre del archivo.
    image_id_to_sample_key = {}
    for img_info in coco_data['images']:
        file_name = img_info['file_name']
        sample_key = file_name.rsplit('_', 1)[0]
        
        # Solo necesitamos mapear una vez por muestra
        if sample_key not in image_id_to_sample_key.values():
            image_id_to_sample_key[img_info['id']] = sample_key


    # 2. Iterar sobre las Anotaciones y extraer el volumen
    for ann in coco_data['annotations']:
        
        # Asumimos que solo una anotación por imagen tendrá el volumen de la muestra
        # (por lo general, la máscara de la 'cell' o 'callus' que quieres medir).
        
        if 'attributes' in ann and 'volume' in ann['attributes']:
            image_id = ann['image_id']
            
            if image_id in image_id_to_sample_key:
                sample_key = image_id_to_sample_key[image_id]
                volume_value = ann['attributes']['volume']
                
                # Guardamos el volumen real solo si es numérico y no ha sido cargado aún
                if isinstance(volume_value, (int, float)) and sample_key not in real_volume_map:
                    real_volume_map[sample_key] = volume_value

    print(f"Volúmenes reales cargados para {len(real_volume_map)} muestras.")
    # ====================================================================

    # --- Predictor Configuration ---
    cfg = get_cfg()
    cfg.merge_from_file(
        get_config_file("COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml")
    )

    cfg.MODEL.WEIGHTS = model_path
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = len(category_names)  # ✅ SÍ, ESTO ES CORRECTO
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.7
    cfg.MODEL.DEVICE = "cpu"
    predictor = DefaultPredictor(cfg)
    # -------------------------------------------------------------
    # ITERAR POR MUESTRA ÚNICA
    # -------------------------------------------------------------
    all_files = os.listdir(input_image_dir)
    sample_keys = set()
    for name in all_files:
        if name.lower().endswith(('_top.jpg', '_top.jpeg', '_top.png', '_side.jpg', '_side.jpeg', '_side.png')):
            key = name.rsplit('_', 1)[0]
            sample_keys.add(key)
    
    if not sample_keys:
        print(f"No se encontraron pares de imágenes (TOP/SIDE) en el directorio: {input_image_dir}")
        return

    for key in sorted(list(sample_keys)):
        process_sample_pair(predictor, metadata, key, input_image_dir, output_base_dir, category_names)

    # --- Llamar a la función de consolidación con el mapa de volúmenes reales ---
    consolidate_results(output_base_dir, real_volume_map)

if __name__ == "__main__":
    main()