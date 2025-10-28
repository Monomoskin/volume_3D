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
    Procesa el par de imágenes TOP y SIDE para una única muestra, realiza la
    doble calibración y calcula el volumen estimado 3D.
    """
    # ... [El cuerpo de process_sample_pair se mantiene como lo enviaste] ...
    # Nota: Tu función ya genera un CSV por muestra. Nos enfocaremos en consolidar
    # estos CSV y añadir la columna real.

    # -------------------------------------------------------------
    # 1. Definición de rutas de archivos
    # -------------------------------------------------------------
    top_name = f"{sample_key}_TOP.jpeg" # Asumimos la extensión .jpeg basada en tu error previo, ajústala si es necesario
    side_name = f"{sample_key}_SIDE.jpeg"
    
    top_path = os.path.join(input_image_dir, top_name)
    side_path = os.path.join(input_image_dir, side_name)
    
    # Verificar existencia de archivos
    if not os.path.exists(top_path) or not os.path.exists(side_path):
        # Intentar con .jpg si falla .jpeg
        top_name = f"{sample_key}_TOP.jpg"
        side_name = f"{sample_key}_SIDE.jpg"
        top_path = os.path.join(input_image_dir, top_name)
        side_path = os.path.join(input_image_dir, side_name)
        
        if not os.path.exists(top_path) or not os.path.exists(side_path):
            print(f"\n[SKIP] Faltan archivos para la muestra {sample_key}. Se esperan .jpeg o .jpg.")
            return

    print(f"\n[PROCESS] Procesando muestra: {sample_key}")

    # --- IDs de Clases ---
    frasco_id = category_names.index("container")
    cell_id = category_names.index("cell") # Clase para el área (vista TOP)
    
    try:
        cell_profile_id = category_names.index("cell_profile")
    except ValueError:
        cell_profile_id = cell_id 
        
    # -------------------------------------------------------------
    # 2. PROCESAMIENTO VISTA SIDE (Altura Z y Calibración Z)
    # -------------------------------------------------------------
    im_side = cv2.imread(side_path)
    outputs_side = predictor(im_side)
    instances_side = outputs_side["instances"].to("cpu")
    
    frasco_side_instance = find_highest_score_instance(instances_side, frasco_id)
    if frasco_side_instance is None:
        print("  [ERROR] Contenedor no detectado en vista SIDE. Imposible calibrar Z.")
        return
        
    frasco_side_mask = frasco_side_instance.pred_masks[0].cpu().numpy().astype(bool)
    y_coords_side, x_coords_side = np.where(frasco_side_mask)
    height_pixels_frasco = y_coords_side.max() - y_coords_side.min()
    factor_z_mm_per_pixel = FRASCO_HEIGHT_MM / height_pixels_frasco
    print(f"  [SIDE] Altura Frasco Detectada (px): {height_pixels_frasco} -> Factor Z: {factor_z_mm_per_pixel:.6f} mm/px")

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
    
    frasco_top_instance = find_highest_score_instance(instances_top, frasco_id)
    if frasco_top_instance is None:
        print("  [ERROR] Contenedor no detectado en vista TOP. Imposible calibrar XY.")
        return
        
    frasco_top_mask = frasco_top_instance.pred_masks[0].cpu().numpy().astype(bool)
    y_coords_top, x_coords_top = np.where(frasco_top_mask)
    width_pixels_frasco = x_coords_top.max() - x_coords_top.min()
    pixels_per_mm = width_pixels_frasco / FRASCO_DIAMETER_MM
    pixels_to_mm2 = 1 / (pixels_per_mm ** 2)
    print(f"  [TOP] Ancho Frasco Detectado (px): {width_pixels_frasco} -> Factor XY: {pixels_to_mm2:.6f} mm²/px²")

    # -------------------------------------------------------------
    # 4. CÁLCULO FINAL DEL VOLUMEN
    # -------------------------------------------------------------
    volume_results = []
    
    for idx in range(len(instances_top)):
        current_class_id = instances_top.pred_classes[idx].item()
        
        if current_class_id == cell_id: 
            cell_mask = instances_top.pred_masks[idx].numpy().astype(bool)
            
            # Validación de intersección (Mantener esta lógica es bueno)
            intersection = np.logical_and(frasco_top_mask, cell_mask)
            if np.sum(intersection) / np.sum(cell_mask) < 0.9: 
                continue

            area_mm2 = np.sum(cell_mask) * pixels_to_mm2
            volumen_ml = (area_mm2 * height_real_mm) / 1000 # mm³ a mL

            y_c, x_c = np.where(cell_mask)
            center_x, center_y = int(np.mean(x_c)), int(np.mean(y_c))
            
            class_name = category_names[current_class_id] 

            volume_results.append({
                "cell_index": idx,
                "class_name": class_name, 
                "volume_ml": volumen_ml, # Volumen estimado
                "area_mm2": area_mm2,
                "height_mm": height_real_mm,
                "center": [center_x, center_y],
                "score": instances_top.scores[idx].item()
            })

     # -------------------------------------------------------------
    # 5. VISUALIZACIÓN y GUARDADO
    # -------------------------------------------------------------
    
    # === A. VISUALIZACIÓN Y GUARDADO DE IMAGEN TOP ===
    
    # Guardar la imagen de predicción TOP
    output_image_top_path = os.path.join(output_base_dir, f"{sample_key}_TOP_predicted.jpg")
    v_top = Visualizer(im_top[:, :, ::-1], metadata, scale=1.0, instance_mode=ColorMode.SEGMENTATION)
    out_top = v_top.draw_instance_predictions(instances_top)
    final_image_top = cv2.cvtColor(out_top.get_image(), cv2.COLOR_RGB2BGR)
    
    # Dibujar resultados del volumen en la imagen TOP
    for v_res in volume_results:
        text = f"{v_res['class_name']}: {v_res['volume_ml']:.3f} mL"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        center_x, center_y = v_res['center']
        
        # Dibuja contorno negro y luego texto blanco
        cv2.putText(final_image_top, text, (center_x, center_y), font, font_scale, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(final_image_top, text, (center_x, center_y), font, font_scale, (255, 255, 255), 1, cv2.LINE_AA)

    cv2.imwrite(output_image_top_path, final_image_top)
    print(f"  [SAVE] Imagen TOP guardada con resultados en: {output_image_top_path}")

    # === B. VISUALIZACIÓN Y GUARDADO DE IMAGEN SIDE (NUEVO) ===
    
    output_image_side_path = os.path.join(output_base_dir, f"{sample_key}_SIDE_predicted.jpg")
    
    # 1. Crear el visualizador para la imagen SIDE
    v_side = Visualizer(im_side[:, :, ::-1], metadata, scale=1.0, instance_mode=ColorMode.SEGMENTATION)
    
    # 2. Dibujar las predicciones de la vista lateral
    # Usamos instances_side que contiene las detecciones de 'container' y 'cell_profile'
    out_side = v_side.draw_instance_predictions(instances_side)
    final_image_side = cv2.cvtColor(out_side.get_image(), cv2.COLOR_RGB2BGR)
    
    # 3. Guardar la imagen SIDE
    cv2.imwrite(output_image_side_path, final_image_side)
    print(f"  [SAVE] Imagen SIDE guardada con segmentación en: {output_image_side_path}")

    # Guardar resultados CSV
    output_csv_path = os.path.join(output_base_dir, f"{sample_key}_volumes.csv")
    with open(output_csv_path, "w", newline="") as csvfile:
        fieldnames=["cell_index", "class_name", "volume_ml", "area_mm2", "height_mm", "center", "score"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(volume_results)
    print("  [SAVE] Resultados de volumen guardados en CSV.")
    
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
    cfg.merge_from_file(get_config_file("COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"))
    cfg.MODEL.WEIGHTS = model_path
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = len(category_names)
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.70 
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