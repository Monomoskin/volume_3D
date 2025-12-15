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
# Estos valores son la 'regla' que usaremos para medir.
FRASCO_DIAMETER_MM = 90.0  # Diámetro real del frasco de Petri.
FRASCO_HEIGHT_MM = 20.0    # Altura real del frasco de Petri (para la calibración Z).

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

# --- NUEVA LÓGICA DE PREDICCIÓN CON DOBLE IMAGEN ---
def process_sample_pair(predictor, metadata, sample_key, input_image_dir, output_base_dir, category_names):
    """
    Procesa el par de imágenes TOP y SIDE para una única muestra, realiza la
    doble calibración y calcula el volumen real 3D.
    """
    # -------------------------------------------------------------
    # 1. Definición de rutas de archivos
    # -------------------------------------------------------------
    top_name = f"{sample_key}_TOP.jpg"
    side_name = f"{sample_key}_SIDE.jpg"
    
    top_path = os.path.join(input_image_dir, top_name)
    side_path = os.path.join(input_image_dir, side_name)
    
    # Verificar existencia de archivos
    if not os.path.exists(top_path) or not os.path.exists(side_path):
        print(f"\n[SKIP] Faltan archivos para la muestra {sample_key}. Se esperan {top_name} y {side_name}.")
        return

    print(f"\n[PROCESS] Procesando muestra: {sample_key}")

    # --- IDs de Clases ---
    frasco_id = category_names.index("container")
    cell_id = category_names.index("cell") # Clase para el área (vista TOP)
    
    # Usamos "cell_profile" si fue creada, o "cell" si se usa la misma clase para la altura.
    # Asumiremos la clase 'cell_profile' para mayor claridad:
    try:
        cell_profile_id = category_names.index("cell_profile")
    except ValueError:
        # Si no existe 'cell_profile', asumimos que se usa 'cell' para ambos, lo cual NO es óptimo
        print("[WARNING] Usando 'cell' para la detección de altura. Asegúrese de que la anotación es clara.")
        cell_profile_id = cell_id 
        
    cell_class_ids = [cell_id, cell_profile_id] # Aquí se incluirían 'callus' si se usara


    # -------------------------------------------------------------
    # 2. PROCESAMIENTO VISTA SIDE (Altura Z y Calibración Z)
    # -------------------------------------------------------------
    im_side = cv2.imread(side_path)
    outputs_side = predictor(im_side)
    instances_side = outputs_side["instances"].to("cpu")
    
    # Detección y Calibración del Frasco (Z)
    frasco_side_instance = find_highest_score_instance(instances_side, frasco_id)
    if frasco_side_instance is None:
        print("  [ERROR] Contenedor no detectado en vista SIDE. Imposible calibrar Z.")
        return
        
    frasco_side_mask = frasco_side_instance.pred_masks[0].cpu().numpy().astype(bool)
    
    # Medir Altura del Frasco en píxeles (Z)
    y_coords_side, x_coords_side = np.where(frasco_side_mask)
    height_pixels_frasco = y_coords_side.max() - y_coords_side.min()
    
    # Factor de Conversión Z: mm por píxel
    factor_z_mm_per_pixel = FRASCO_HEIGHT_MM / height_pixels_frasco
    print(f"  [SIDE] Altura Frasco Detectada (px): {height_pixels_frasco} -> Factor Z: {factor_z_mm_per_pixel:.6f} mm/px")

    # Detección y Medición de Altura de la Muestra (Z)
    cell_profile_instance = find_highest_score_instance(instances_side, cell_profile_id)
    if cell_profile_instance is None:
        print("  [ERROR] Muestra (cell_profile) no detectada en vista SIDE. Imposible calcular volumen.")
        return
        
    cell_profile_mask = cell_profile_instance.pred_masks[0].cpu().numpy().astype(bool)
    y_coords_cell_profile, _ = np.where(cell_profile_mask)
    
    height_pixels_cell = y_coords_cell_profile.max() - y_coords_cell_profile.min()
    height_real_mm = height_pixels_cell * factor_z_mm_per_pixel
    print(f"  [SIDE] Altura Muestra Detectada (px): {height_pixels_cell} -> Altura Real Z: {height_real_mm:.3f} mm")


    # -------------------------------------------------------------
    # 3. PROCESAMIENTO VISTA TOP (Área XY y Calibración XY)
    # -------------------------------------------------------------
    im_top = cv2.imread(top_path)
    outputs_top = predictor(im_top)
    instances_top = outputs_top["instances"].to("cpu")
    
    # Detección y Calibración del Frasco (XY)
    frasco_top_instance = find_highest_score_instance(instances_top, frasco_id)
    if frasco_top_instance is None:
        print("  [ERROR] Contenedor no detectado en vista TOP. Imposible calibrar XY.")
        return
        
    frasco_top_mask = frasco_top_instance.pred_masks[0].cpu().numpy().astype(bool)
    
    # Medir Ancho del Frasco en píxeles (XY)
    y_coords_top, x_coords_top = np.where(frasco_top_mask)
    width_pixels_frasco = x_coords_top.max() - x_coords_top.min()
    
    # Factor de Conversión XY: mm² por píxel cuadrado
    pixels_per_mm = width_pixels_frasco / FRASCO_DIAMETER_MM
    pixels_to_mm2 = 1 / (pixels_per_mm ** 2)
    print(f"  [TOP] Ancho Frasco Detectado (px): {width_pixels_frasco} -> Factor XY: {pixels_to_mm2:.6f} mm²/px²")

    # -------------------------------------------------------------
    # 4. CÁLCULO FINAL DEL VOLUMEN
    # -------------------------------------------------------------
    volume_results = []
    
    # Itera sobre TODAS las detecciones de CÉLULAS en la vista TOP
    for idx in range(len(instances_top)):
        current_class_id = instances_top.pred_classes[idx].item()
        
        # Asumimos que la clase "cell" o "callus" es la que tiene el área base
        if current_class_id == cell_id: # Se podría expandir a otras clases de células aquí
            
            cell_mask = instances_top.pred_masks[idx].numpy().astype(bool)
            
            # Validación: asegurar que la célula esté dentro del frasco
            intersection = np.logical_and(frasco_top_mask, cell_mask)
            if np.sum(intersection) / np.sum(cell_mask) < 0.9: 
                continue

            # Cálculo: Área (del TOP) x Altura (del SIDE)
            area_mm2 = np.sum(cell_mask) * pixels_to_mm2
            volumen_ml = (area_mm2 * height_real_mm) / 1000 # Dividido por 1000 para pasar mm³ a mL

            # Obtener el centro para la visualización
            y_c, x_c = np.where(cell_mask)
            center_x, center_y = int(np.mean(x_c)), int(np.mean(y_c))
            
            class_name = category_names[current_class_id] 

            volume_results.append({
                "cell_index": idx,
                "class_name": class_name, 
                "volume_ml": volumen_ml,
                "area_mm2": area_mm2,
                "height_mm": height_real_mm,
                "center": [center_x, center_y],
                "score": instances_top.scores[idx].item()
            })

    # -------------------------------------------------------------
    # 5. VISUALIZACIÓN y GUARDADO (Solo de la imagen TOP)
    # -------------------------------------------------------------
    
    # Guardar la imagen de predicción TOP
    output_image_path = os.path.join(output_base_dir, f"{sample_key}_TOP_predicted.jpg")
    v = Visualizer(im_top[:, :, ::-1], metadata, scale=1.0, instance_mode=ColorMode.SEGMENTATION)
    out = v.draw_instance_predictions(instances_top)
    final_image = cv2.cvtColor(out.get_image(), cv2.COLOR_RGB2BGR)
    
    # Dibujar resultados del volumen en la imagen TOP
    for v in volume_results:
        text = f"{v['class_name']}: {v['volume_ml']:.3f} mL"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        center_x, center_y = v['center']
        
        # Dibuja contorno negro y luego texto blanco
        cv2.putText(final_image, text, (center_x, center_y), font, font_scale, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(final_image, text, (center_x, center_y), font, font_scale, (255, 255, 255), 1, cv2.LINE_AA)

    cv2.imwrite(output_image_path, final_image)
    print(f"  [SAVE] Imagen TOP guardada con resultados en: {output_image_path}")

    # Guardar resultados CSV
    output_csv_path = os.path.join(output_base_dir, f"{sample_key}_volumes.csv")
    with open(output_csv_path, "w", newline="") as csvfile:
        fieldnames=["cell_index", "class_name", "volume_ml", "area_mm2", "height_mm", "center", "score"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(volume_results)
    print("  [SAVE] Resultados de volumen guardados en CSV.")

# --- NUEVA FUNCIÓN: Consolida todos los resultados en un único CSV (sin cambios) ---
def consolidate_results(output_base_dir):
    all_files = [os.path.join(output_base_dir, f) for f in os.listdir(output_base_dir) if f.endswith('_volumes.csv')]
    
    if not all_files:
        print("\nNo individual volume CSV files found to consolidate.")
        return

    all_data = []
    
    for f in all_files:
        try:
            df = pd.read_csv(f)
            image_name = os.path.basename(f).replace('_volumes.csv', '')
            df.insert(0, 'image_name', image_name)
            all_data.append(df)
        except Exception as e:
            print(f"Error reading file {f}: {e}")

    if not all_data:
        print("No data successfully read for consolidation.")
        return

    master_df = pd.concat(all_data, ignore_index=True)
    
    if 'center' in master_df.columns:
        master_df['center'] = master_df['center'].astype(str)
        master_df[['center_x', 'center_y']] = master_df['center'].str.strip('[]').str.split(', ', expand=True).astype(float)
        master_df = master_df.drop(columns=['center'])

    master_df['real_volume_ml'] = np.nan 

    cols = ['image_name', 'class_name', 'volume_ml', 'real_volume_ml', 'score', 'cell_index', 'area_mm2', 'height_mm', 'center_x', 'center_y']
    master_df = master_df.reindex(columns=cols)

    master_csv_path = os.path.join(output_base_dir, 'all_volumes_summary.csv')
    master_df.to_csv(master_csv_path, index=False)
    
    print(f"\n==============================================")
    print(f"✅ CONSOLIDACIÓN EXITOSA: {master_csv_path}")
    print(f"==============================================")

# --- 2. Main prediction logic ---
def main():
    # --- Paths ---
    input_image_dir = "testImages"
    model_path = "output_train/model_final.pth" 
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

    # --- Predictor Configuration ---
    cfg = get_cfg()
    cfg.merge_from_file(get_config_file("COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"))
    cfg.MODEL.WEIGHTS = model_path
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = len(category_names)
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.70 
    cfg.MODEL.DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"
    predictor = DefaultPredictor(cfg)

    # -------------------------------------------------------------
    # ADAPTACIÓN CLAVE: ITERAR POR MUESTRA ÚNICA
    # -------------------------------------------------------------
    
    # 1. Obtener la lista de nombres de archivos
    all_files = os.listdir(input_image_dir)
    
    # 2. Extraer las claves de muestra únicas (ej: "Muestra_001")
    sample_keys = set()
    for name in all_files:
        if name.lower().endswith(('_top.jpg', '_top.jpeg', '_top.png', '_side.jpg', '_side.jpeg', '_side.png')):
            # Extraer la parte antes de _TOP o _SIDE
            key = name.rsplit('_', 1)[0]
            sample_keys.add(key)
    
    # 3. Procesar cada muestra única
    if not sample_keys:
        print(f"No se encontraron pares de imágenes (TOP/SIDE) en el directorio: {input_image_dir}")
        return

    for key in sorted(list(sample_keys)):
        process_sample_pair(predictor, metadata, key, input_image_dir, output_base_dir, category_names)

    # --- Llamar a la función de consolidación al final de main ---
    consolidate_results(output_base_dir)

if __name__ == "__main__":
    main()