import os
import json
import cv2
import numpy as np
import pandas as pd
import torch
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from detectron2.engine import DefaultPredictor
from detectron2.config import get_cfg
from detectron2.data.datasets import register_coco_instances
from detectron2.data import MetadataCatalog
from detectron2.utils.visualizer import Visualizer, ColorMode
from detectron2.model_zoo import get_config_file
from detectron2.structures import Instances

# =====================================================
# CONSTANTES DE CALIBRACIÓN
# =====================================================
FRASCO_DIAMETER_MM = 90.0
FRASCO_HEIGHT_MM = 12.0

# =====================================================
# HELPER FUNCTIONS
# =====================================================
def find_highest_score_instance(instances, class_id):
    """Devuelve la instancia con mayor score de una clase específica."""
    if len(instances) == 0:
        return None
    scores = instances.scores
    classes = instances.pred_classes
    idxs = (classes == class_id).nonzero(as_tuple=True)[0]
    if len(idxs) == 0:
        return None
    best_idx = idxs[torch.argmax(scores[idxs])]
    inst = Instances(instances.image_size)
    inst.pred_masks = instances.pred_masks[best_idx:best_idx+1]
    inst.pred_classes = instances.pred_classes[best_idx:best_idx+1]
    inst.scores = instances.scores[best_idx:best_idx+1]
    return inst

# Configurar container_label
def resolve_container_category(image_name, category_names):
    """Devuelve el índice correcto para container_top / container_side"""
    name = image_name.lower()
    if "top" in name:
        target = "container_top"
    elif "side" in name:
        target = "container_side"
    else:
        target = "container"  # fallback seguro
    if target not in category_names:
        raise ValueError(f"Categoría {target} no encontrada en category_names")
    return category_names.index(target)

# =====================================================
# CONFIGURAR DATASET COCO
# =====================================================
def setup_dataset(json_path="annotations/coco_annotations.json", image_dir="images"):
    dataset_name = "callus_dataset"
    try:
        register_coco_instances(dataset_name, {}, json_path, image_dir)
    except AssertionError:
        pass
    with open(json_path, 'r') as f:
        coco = json.load(f)
    MetadataCatalog.get(dataset_name).thing_classes = [c["name"] for c in coco["categories"]]
    return dataset_name, coco

# =====================================================
# PROCESAR UNA MUESTRA (TOP y SIDE)
# =====================================================
def process_sample(sample_key, predictor, metadata, input_dir, output_dir, category_names):
    results = []

    # Rutas de imágenes
    top_path = os.path.join(input_dir, f"{sample_key}_TOP.jpeg")
    side_path = os.path.join(input_dir, f"{sample_key}_SIDE.jpeg")

    # Manejar extensiones alternativas
    if not os.path.exists(top_path):
        top_path = os.path.join(input_dir, f"{sample_key}_TOP.jpg")
    side_exists = True
    if not os.path.exists(side_path):
        side_path = os.path.join(input_dir, f"{sample_key}_SIDE.jpg")
        if not os.path.exists(side_path):
            side_exists = False

    if not os.path.exists(top_path):
        print(f"[SKIP] No hay TOP para {sample_key}")
        return results

    im_top = cv2.imread(top_path)
    im_side = cv2.imread(side_path) if side_exists else None

    # --- SIDE: Altura Z (si existe) ---
    height_mm = None
    if side_exists:
        outputs_side = predictor(im_side)
        instances_side = outputs_side["instances"].to("cpu")
        frasco_side = find_highest_score_instance(instances_side, resolve_container_category(os.path.basename(side_path), category_names)
        )
        cell_side = find_highest_score_instance(instances_side, category_names.index("cell_profile"))
        if frasco_side is not None and cell_side is not None:
            frasco_mask = frasco_side.pred_masks[0].cpu().numpy().astype(bool)
            y_coords = np.where(frasco_mask)[0]
            height_px = y_coords.max() - y_coords.min()
            factor_z = FRASCO_HEIGHT_MM / height_px

            cell_mask = cell_side.pred_masks[0].cpu().numpy().astype(bool)
            y_coords_cell = np.where(cell_mask)[0]
            height_mm = (y_coords_cell.max() - y_coords_cell.min()) * factor_z
        else:
            print(f"[INFO] SIDE detectado pero no se encontró container o cell_profile para {sample_key}")
            height_mm = None

    # --- TOP: Segmentación y área XY ---
    outputs_top = predictor(im_top)
    instances_top = outputs_top["instances"].to("cpu")
    frasco_top = find_highest_score_instance(instances_top, resolve_container_category(os.path.basename(top_path), category_names)
)
    if frasco_top is None:
        print(f"[SKIP] No se detecta container en TOP para {sample_key}")
        return results
    frasco_mask_top = frasco_top.pred_masks[0].cpu().numpy().astype(bool)
    x_coords = np.where(frasco_mask_top)[1]
    width_px = x_coords.max() - x_coords.min()
    factor_xy = (FRASCO_DIAMETER_MM / width_px) ** 2

    # Recorrer todas las instancias
    for idx in range(len(instances_top)):
        cls_id = instances_top.pred_classes[idx].item()
        cls_name = category_names[cls_id]
        if cls_name not in ["callus", "potato"]:
            continue
        mask = instances_top.pred_masks[idx].numpy().astype(bool)
        intersection = np.logical_and(frasco_mask_top, mask)
        if np.sum(intersection)/np.sum(mask) < 0.9:
            continue

        area_mm2 = np.sum(mask) * factor_xy
        volume_ml = area_mm2 * height_mm / 1000 if height_mm is not None else None
        y_c, x_c = np.where(mask)
        center = [int(np.mean(x_c)), int(np.mean(y_c))]

        results.append({
            "sample_key": sample_key,
            "cell_index": idx,
            "class_name": cls_name,
            "area_mm2": area_mm2,
            "height_mm": height_mm,
            "volume_ml": volume_ml,
            "center": center,
            "score": instances_top.scores[idx].item()
        })

    # --- Guardar imágenes con predicciones ---
    os.makedirs(output_dir, exist_ok=True)
    # TOP
    v_top = Visualizer(im_top[:, :, ::-1], metadata, scale=1.0, instance_mode=ColorMode.SEGMENTATION)
    final_top = cv2.cvtColor(v_top.draw_instance_predictions(instances_top).get_image(), cv2.COLOR_RGB2BGR)
    for r in results:
        text = f"{r['class_name']}"
        if r['volume_ml'] is not None:
            text += f": {r['volume_ml']:.3f} mL"
        cv2.putText(final_top, text, tuple(r['center']), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 1, cv2.LINE_AA)
    cv2.imwrite(os.path.join(output_dir, f"{sample_key}_TOP_predicted.jpg"), final_top)
    # SIDE
    if side_exists:
        v_side = Visualizer(im_side[:, :, ::-1], metadata, scale=1.0, instance_mode=ColorMode.SEGMENTATION)
        final_side = cv2.cvtColor(v_side.draw_instance_predictions(instances_side).get_image(), cv2.COLOR_RGB2BGR)
        cv2.imwrite(os.path.join(output_dir, f"{sample_key}_SIDE_predicted.jpg"), final_side)

    # --- Guardar CSV ---
    if results:
        csv_path = os.path.join(output_dir, f"{sample_key}_volumes.csv")
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
            writer.writeheader()
            writer.writerows(results)

    return results

# =====================================================
# CONSOLIDAR RESULTADOS
# =====================================================
def consolidate_results(output_dir, real_volume_map={}):
    all_files = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.endswith("_volumes.csv")]
    if not all_files:
        print("[INFO] No hay CSVs para consolidar")
        return
    all_data = []
    for f in all_files:
        try:
            df = pd.read_csv(f)
            sample_key = os.path.basename(f).replace("_volumes.csv","")
            df.insert(0,"sample_key",sample_key)
            all_data.append(df)
        except:
            continue
    if not all_data:
        return
    master_df = pd.concat(all_data, ignore_index=True)
    # Volumen real y métricas
    if real_volume_map:
        master_df['real_volume_ml'] = master_df['sample_key'].map(real_volume_map)
        master_df['error_abs_ml'] = np.abs(master_df['volume_ml'] - master_df['real_volume_ml'])
        master_df['precision_percent'] = (1 - (master_df['error_abs_ml']/master_df['real_volume_ml']))*100
    # Expandir center
    if 'center' in master_df.columns:
        master_df[['center_x','center_y']] = master_df['center'].str.strip('[]').str.split(', ',expand=True).astype(float)
        master_df = master_df.drop(columns=['center'])
    master_df.to_excel(os.path.join(output_dir,"all_volumes_summary.xlsx"), index=False)
    print("[DONE] Consolidación finalizada")

# =====================================================
# MAIN
# =====================================================
def main():
    input_dir = "testImages"
    output_dir = "output_predict"
    model_path = "output_train/model_final.pth"
    os.makedirs(output_dir, exist_ok=True)

    dataset_name, coco_data = setup_dataset()
    category_names = [c['name'] for c in coco_data['categories']]
    metadata = MetadataCatalog.get(dataset_name)

    # --- Predictor ---
    cfg = get_cfg()
    cfg.merge_from_file(get_config_file("COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"))
    cfg.MODEL.WEIGHTS = model_path
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = len(category_names)
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.4
    cfg.MODEL.DEVICE = "cpu"
    predictor = DefaultPredictor(cfg)

    # --- Extraer sample keys ---
    all_files = os.listdir(input_dir)
    sample_keys = set()
    for f in all_files:
        if f.lower().endswith(('_top.jpg','_top.jpeg','_side.jpg','_side.jpeg')):
            key = f.rsplit("_",1)[0]
            sample_keys.add(key)

    # --- Procesamiento paralelo ---
    results_all = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(process_sample, k, predictor, metadata, input_dir, output_dir, category_names): k for k in sample_keys}
        for future in as_completed(futures):
            results_all.extend(future.result())

    # --- Consolidar ---
    consolidate_results(output_dir)

if __name__ == "__main__":
    main()
