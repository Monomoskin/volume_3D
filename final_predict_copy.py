import cv2
import numpy as np
import os
import json
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
FRASCO_HEIGHT_MM = 12.0

# --- 1. Helper: Obtener la instancia con mayor score de una clase ---
def find_highest_score_instance(instances, class_id):
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

# --- 2. Procesamiento de cada muestra (TOP + SIDE) ---
def process_sample_pair(predictor, metadata, sample_key, input_image_dir, output_base_dir, category_names):
    top_name = f"{sample_key}_TOP.jpeg"
    side_name = f"{sample_key}_SIDE.jpeg"
    top_path = os.path.join(input_image_dir, top_name)
    side_path = os.path.join(input_image_dir, side_name)

    # Intentar con .jpg si no existe .jpeg
    if not os.path.exists(top_path) or not os.path.exists(side_path):
        top_name = f"{sample_key}_TOP.jpg"
        side_name = f"{sample_key}_SIDE.jpg"
        top_path = os.path.join(input_image_dir, top_name)
        side_path = os.path.join(input_image_dir, side_name)
        if not os.path.exists(top_path) or not os.path.exists(side_path):
            print(f"[SKIP] Faltan archivos para la muestra {sample_key}.")
            return

    print(f"[PROCESS] Procesando muestra: {sample_key}")

    frasco_top_id = category_names.index("container_top")
    frasco_side_id = category_names.index("container_side")
    top_classes_of_interest = [category_names.index(name) for name in ["callus", "potato"] if name in category_names]

    try:
        cell_profile_id = category_names.index("cell_profile")
    except ValueError:
        cell_profile_id = None

    # --- SIDE ---
    im_side = cv2.imread(side_path)
    outputs_side = predictor(im_side)
    instances_side = outputs_side["instances"].to("cpu")

    frasco_side_instance = find_highest_score_instance(instances_side, frasco_side_id)
    if frasco_side_instance is None:
        print("[ERROR] Contenedor no detectado en SIDE.")
        v_side = Visualizer(im_side[:, :, ::-1], metadata, scale=1.0, instance_mode=ColorMode.SEGMENTATION)
        out_side = v_side.draw_instance_predictions(instances_side)
        cv2.imwrite(os.path.join(output_base_dir, f"{sample_key}_SIDE_debug.jpg"), out_side.get_image()[:, :, ::-1])
        return

    frasco_side_mask = frasco_side_instance.pred_masks[0].cpu().numpy().astype(bool)
    y_coords_side, _ = np.where(frasco_side_mask)
    height_pixels_frasco = y_coords_side.max() - y_coords_side.min()
    factor_z_mm_per_pixel = FRASCO_HEIGHT_MM / height_pixels_frasco

    if cell_profile_id is not None:
        cell_profile_instance = find_highest_score_instance(instances_side, cell_profile_id)
        if cell_profile_instance is None:
            print("[ERROR] cell_profile no detectada en SIDE.")
            return
        cell_profile_mask = cell_profile_instance.pred_masks[0].cpu().numpy().astype(bool)
        y_coords_cell, _ = np.where(cell_profile_mask)
        height_real_mm = (y_coords_cell.max() - y_coords_cell.min()) * factor_z_mm_per_pixel
    else:
        height_real_mm = None

    # --- TOP ---
    im_top = cv2.imread(top_path)
    outputs_top = predictor(im_top)
    instances_top = outputs_top["instances"].to("cpu")

    frasco_top_instance = find_highest_score_instance(instances_top, frasco_top_id)
    if frasco_top_instance is None:
        print("[ERROR] Contenedor no detectado en TOP.")
        v_top = Visualizer(im_top[:, :, ::-1], metadata, scale=1.0, instance_mode=ColorMode.SEGMENTATION)
        out_top = v_top.draw_instance_predictions(instances_top)
        cv2.imwrite(os.path.join(output_base_dir, f"{sample_key}_TOP_debug.jpg"), out_top.get_image()[:, :, ::-1])
        return

    frasco_top_mask = frasco_top_instance.pred_masks[0].cpu().numpy().astype(bool)
    y_coords_top, x_coords_top = np.where(frasco_top_mask)
    width_pixels_frasco = x_coords_top.max() - x_coords_top.min()
    pixels_per_mm = width_pixels_frasco / FRASCO_DIAMETER_MM
    pixels_to_mm2 = 1 / (pixels_per_mm ** 2)

    # --- SELECCIONAR UNA SOLA CÉLULA ---
    best_cell = None
    best_score = -1
    for idx in range(len(instances_top)):
        class_id = instances_top.pred_classes[idx].item()
        if class_id not in top_classes_of_interest:
            continue

        cell_mask = instances_top.pred_masks[idx].numpy().astype(bool)
        intersection = np.logical_and(frasco_top_mask, cell_mask)
        if np.sum(intersection) / np.sum(cell_mask) < 0.9:
            continue

        score = instances_top.scores[idx].item()
        if score > best_score:
            best_score = score
            best_cell = idx

    if best_cell is None:
        print("[ERROR] No se encontró célula válida en TOP.")
        return

    # --- Cálculo de volumen ---
    cell_mask = instances_top.pred_masks[best_cell].numpy().astype(bool)
    area_mm2 = np.sum(cell_mask) * pixels_to_mm2
    if height_real_mm is None:
        print("[ERROR] Altura no disponible para volumen.")
        return
    volumen_ml = (area_mm2 * height_real_mm) / 1000

    y_c, x_c = np.where(cell_mask)
    center_x, center_y = int(np.mean(x_c)), int(np.mean(y_c))

    volume_results = [{
        "class_name": category_names[instances_top.pred_classes[best_cell].item()],
        "volume_ml": volumen_ml,
        "area_mm2": area_mm2,
        "height_mm": height_real_mm,
        "center_x": center_x,
        "center_y": center_y,
        "score": best_score
    }]

    # --- Guardar imágenes predichas ---
    for view, im, instances, fname in [("TOP", im_top, instances_top, f"{sample_key}_TOP_predicted.jpg"),
                                       ("SIDE", im_side, instances_side, f"{sample_key}_SIDE_predicted.jpg")]:
        v = Visualizer(im[:, :, ::-1], metadata, scale=1.0, instance_mode=ColorMode.SEGMENTATION)
        out = v.draw_instance_predictions(instances)
        cv2.imwrite(os.path.join(output_base_dir, fname), out.get_image()[:, :, ::-1])

    # --- Guardar CSV ---
    output_csv_path = os.path.join(output_base_dir, f"{sample_key}_volumes.csv")
    df = pd.DataFrame(volume_results)
    df.to_csv(output_csv_path, index=False)
    print(f"[SAVE] CSV guardado para {sample_key}")

# --- 3. Consolidación de resultados ---
def consolidate_results(output_base_dir, real_volume_map):
    all_files = [os.path.join(output_base_dir, f) for f in os.listdir(output_base_dir) if f.endswith('_volumes.csv')]
    if not all_files:
        print("No CSV files found.")
        return

    all_data = []
    for f in all_files:
        df = pd.read_csv(f)
        sample_key = os.path.basename(f).replace('_volumes.csv', '')
        df.insert(0, 'sample_key', sample_key)
        all_data.append(df)

    master_df = pd.concat(all_data, ignore_index=True)
    master_df['real_volume_ml'] = master_df['sample_key'].apply(lambda x: real_volume_map.get(x, np.nan))
    master_df['error_abs_ml'] = np.abs(master_df['volume_ml'] - master_df['real_volume_ml'])
    master_df['precision_percent'] = (1 - (master_df['error_abs_ml'] / master_df['real_volume_ml'])) * 100

    master_csv_path = os.path.join(output_base_dir, 'all_volumes_summary.xlsx')
    master_df.to_excel(master_csv_path, index=False)

    valid_precision = master_df.dropna(subset=['real_volume_ml', 'precision_percent'])
    if not valid_precision.empty:
        mean_precision = valid_precision['precision_percent'].mean()
        mean_error = valid_precision['error_abs_ml'].mean()
        print(f"\n✅ CONSOLIDACIÓN EXITOSA | ERROR ABSOLUTO PROMEDIO: {mean_error:.3f} mL | PRECISIÓN PROMEDIO: {mean_precision:.2f}%")
        print(f"RESULTADOS GUARDADOS EN: {master_csv_path}")

# --- 4. Main ---
def main():
    input_image_dir = "testImages"
    model_path = "output_train/model_0002999.pth" 
    output_base_dir = "output_predict"
    os.makedirs(output_base_dir, exist_ok=True)

    dataset_name = "celulas_frascos"
    json_path = os.path.join("annotations", "coco_annotations_multiattr.json")
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

    # --- Volumen real desde COCO ---
    real_volume_map = {}
    image_id_to_sample_key = {}
    for img_info in coco_data['images']:
        file_name = img_info['file_name']
        sample_key = file_name.rsplit('_', 1)[0]
        if sample_key not in image_id_to_sample_key.values():
            image_id_to_sample_key[img_info['id']] = sample_key

    for ann in coco_data['annotations']:
        if 'attributes' in ann and 'volume' in ann['attributes']:
            image_id = ann['image_id']
            if image_id in image_id_to_sample_key:
                sample_key = image_id_to_sample_key[image_id]
                volume_value = ann['attributes']['volume']
                if isinstance(volume_value, (int, float)) and sample_key not in real_volume_map:
                    real_volume_map[sample_key] = volume_value

    print(f"Volúmenes reales cargados para {len(real_volume_map)} muestras.")

    # --- Predictor ---
    cfg = get_cfg()
    cfg.merge_from_file(get_config_file("COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"))
    cfg.MODEL.WEIGHTS = model_path
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = len(category_names)
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.80 
    cfg.MODEL.DEVICE = "cpu"
    predictor = DefaultPredictor(cfg)

    # --- Iterar por muestras ---
    all_files = os.listdir(input_image_dir)
    sample_keys = set()
    for name in all_files:
        if name.lower().endswith(('_top.jpg', '_top.jpeg', '_top.png', '_side.jpg', '_side.jpeg', '_side.png')):
            key = name.rsplit('_', 1)[0]
            sample_keys.add(key)

    for key in sorted(list(sample_keys)):
        process_sample_pair(predictor, metadata, key, input_image_dir, output_base_dir, category_names)

    consolidate_results(output_base_dir, real_volume_map)

if __name__ == "__main__":
    main()
