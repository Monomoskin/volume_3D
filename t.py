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
from detectron2.structures import Instances

# --- CONSTANTES DE CALIBRACIÓN ---
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
    
    best_instance = Instances(instances.image_size)
    best_instance.pred_masks = instances.pred_masks[best_idx:best_idx+1]
    best_instance.pred_classes = instances.pred_classes[best_idx:best_idx+1]
    best_instance.scores = instances.scores[best_idx:best_idx+1]
    
    return best_instance

# --- 2. Procesar par TOP/SIDE ---
def process_sample_pair(predictor, metadata, sample_key, input_image_dir, output_base_dir, category_names, predicted_attributes):

    # Buscar archivos
    top_path, side_path = None, None
    for ext in [".jpeg", ".jpg", ".png"]:
        tp = os.path.join(input_image_dir, f"{sample_key}_TOP{ext}")
        sp = os.path.join(input_image_dir, f"{sample_key}_SIDE{ext}")
        if os.path.exists(tp):
            top_path = tp
        if os.path.exists(sp):
            side_path = sp

    if top_path is None:
        print(f"[SKIP] Falta TOP para la muestra {sample_key}")
        return

    has_side = side_path is not None
    print(f"[PROCESS] {sample_key} | SIDE={'YES' if has_side else 'NO'}")

    # IDs de clases
    frasco_top_id = category_names.index("container_top")
    frasco_side_id = category_names.index("container_side")
    top_classes_of_interest = [category_names.index(n) for n in ["callus", "potato"] if n in category_names]
    cell_profile_id = category_names.index("cell_profile") if "cell_profile" in category_names else None
    defective_region_id = category_names.index("defective_region") if "defective_region" in category_names else None

    # SIDE → altura
    height_real_mm = None
    if has_side:
        im_side = cv2.imread(side_path)
        inst_side = predictor(im_side)["instances"].to("cpu")

        frasco_side = find_highest_score_instance(inst_side, frasco_side_id)
        if frasco_side is not None:
            m_f = frasco_side.pred_masks[0].numpy().astype(bool)
            ys = np.where(m_f)[0]
            if len(ys) > 0:
                factor_z = FRASCO_HEIGHT_MM / (ys.max() - ys.min() + 1e-6)
                if cell_profile_id is not None:
                    cp = find_highest_score_instance(inst_side, cell_profile_id)
                    if cp is not None:
                        m_cp = cp.pred_masks[0].numpy().astype(bool)
                        ys_cp = np.where(m_cp)[0]
                        if len(ys_cp) > 0:
                            height_real_mm = (ys_cp.max() - ys_cp.min()) * factor_z

        # Visualización SIDE
        v_side = Visualizer(im_side[:, :, ::-1], metadata, instance_mode=ColorMode.SEGMENTATION)
        for i in range(len(inst_side)):
            mask = inst_side.pred_masks[i].numpy()
            if mask.sum() > 0:
                v_side.draw_binary_mask(mask, alpha=0.35)
        cv2.imwrite(os.path.join(output_base_dir, f"{sample_key}_SIDE_predicted.jpg"), v_side.output.get_image()[:, :, ::-1])

    # TOP
    im_top = cv2.imread(top_path)
    inst_top = predictor(im_top)["instances"].to("cpu")

    frasco_top = find_highest_score_instance(inst_top, frasco_top_id)
    if frasco_top is None:
        print("[ERROR] Contenedor no detectado en TOP")
        return

    m_f = frasco_top.pred_masks[0].numpy().astype(bool)
    _, xs = np.where(m_f)
    if len(xs) == 0:
        print("[ERROR] Máscara del contenedor vacía")
        return
    px_per_mm = (xs.max() - xs.min()) / FRASCO_DIAMETER_MM
    px_to_mm2 = 1 / (px_per_mm ** 2)

    volume_calculable = has_side and height_real_mm is not None
    rows = []

    for i in range(len(inst_top)):
        cid = inst_top.pred_classes[i].item()
        if cid not in top_classes_of_interest:
            continue

        cell_mask = inst_top.pred_masks[i].numpy().astype(bool)
        if np.sum(cell_mask & m_f) / np.sum(cell_mask) < 0.9:
            continue

        score = inst_top.scores[i].item()
        best_class_name = category_names[cid]

        area_mm2 = np.sum(cell_mask) * px_to_mm2
        if area_mm2 <= 0:
            continue

        ys, xs = np.where(cell_mask)
        cx, cy = int(xs.mean()), int(ys.mean())

        volume_ml = (area_mm2 * height_real_mm) / 1000 if volume_calculable else None

        # DEFECTOS
        defective_percent = 0.0
        defective_area_mm2 = 0.0
        if defective_region_id is not None:
            defective_mask_total = np.zeros_like(cell_mask, dtype=bool)
            for j in range(len(inst_top)):
                if inst_top.pred_classes[j].item() != defective_region_id:
                    continue
                defect_mask = inst_top.pred_masks[j].numpy().astype(bool)
                if np.sum(defect_mask) == 0:
                    continue
                if np.sum(defect_mask & cell_mask) / np.sum(defect_mask) > 0.8:
                    defective_mask_total |= defect_mask
            if defective_mask_total.sum() > 0:
                defective_area_mm2 = np.sum(defective_mask_total) * px_to_mm2
                defective_percent = (defective_area_mm2 / area_mm2) * 100

        # CALIDAD COMBINADA
        base_score = 100.0
        quality_from_model = None
        if best_class_name == "callus":
            if hasattr(inst_top, "quality") and len(inst_top.quality) > i:
                q_idx = inst_top.quality[i].item()
                quality_from_model = metadata.quality_classes[q_idx]
                if quality_from_model == "good":
                    base_score = 100.0
                elif quality_from_model == "medium":
                    base_score = 50.0
                elif quality_from_model == "poor":
                    base_score = 0.0

        quality_from_defect = 100.0 - defective_percent
        final_quality_percent = (base_score + quality_from_defect) / 2
        final_quality_percent = max(0.0, min(100.0, final_quality_percent))

        # ATRIBUTOS RESTANTES
        species = stage = None
        if best_class_name == "callus":
            if hasattr(inst_top, "species") and len(inst_top.species) > i:
                species = metadata.species_classes[inst_top.species[i].item()]
            if hasattr(inst_top, "stage") and len(inst_top.stage) > i:
                stage = metadata.stage_classes[inst_top.stage[i].item()]

        # GUARDAR
        cell_key = f"{sample_key}_cell{i+1}"
        predicted_attributes[cell_key] = {
            "class": best_class_name,
            "species": species,
            "quality_from_model": quality_from_model,
            "stage": stage,
            "score": round(score, 3),
            "volume_ml": round(volume_ml, 4) if volume_ml else None,
            "area_mm2": round(area_mm2, 2),
            "height_mm": round(height_real_mm, 2) if height_real_mm else None,
            "defective_area_mm2": round(defective_area_mm2, 2),
            "defective_percent": round(defective_percent, 1),
            "final_quality_percent": round(final_quality_percent, 1)
        }

        rows.append({
            "sample_key": cell_key,
            "class_name": best_class_name,
            "species": species,
            "quality_from_model": quality_from_model,
            "stage": stage,
            "volume_ml": round(volume_ml, 4) if volume_ml else None,
            "area_mm2": round(area_mm2, 2),
            "height_mm": round(height_real_mm, 2) if height_real_mm else None,
            "center_x": cx,
            "center_y": cy,
            "score": round(score, 3),
            "defective_area_mm2": round(defective_area_mm2, 2),
            "defective_percent": round(defective_percent, 1),
            "final_quality_percent": round(final_quality_percent, 1)
        })

    # VISUALIZACIÓN TOP
    v = Visualizer(im_top[:, :, ::-1], metadata, instance_mode=ColorMode.SEGMENTATION)
    for i in range(len(inst_top)):
        mask = inst_top.pred_masks[i].numpy()
        class_name = category_names[inst_top.pred_classes[i].item()]
        if class_name == "defective_region":
            v.draw_binary_mask(mask, alpha=0.6, color=(255, 0, 0))
        else:
            v.draw_binary_mask(mask, alpha=0.35)

    for row in rows:
        text_lines = [
            row['class_name'],
            f"Vol: {row['volume_ml']:.3f} mL" if row['volume_ml'] else "Vol: N/A",
            f"Defect: {row['defective_percent']:.1f}%",
            f"Quality: {row['final_quality_percent']:.1f}%"
        ]
        v.draw_text("\n".join(text_lines), (row["center_x"], row["center_y"] - 40),
                    font_size=16, color="yellow", horizontal_alignment="center")

    cv2.imwrite(os.path.join(output_base_dir, f"{sample_key}_TOP_predicted.jpg"), v.output.get_image()[:, :, ::-1])

    # CSV
    if rows:
        df = pd.DataFrame(rows)
        df.to_csv(os.path.join(output_base_dir, f"{sample_key}_volumes.csv"), index=False)
        print(f"[SAVE] CSV guardado para {sample_key}")
    else:
        print(f"[WARN] No se detectaron calli válidos en {sample_key}")

# --- Consolidación corregida ---
def consolidate_results(output_base_dir, real_volume_map, predicted_attributes):
    all_rows = []
    for cell_key, attr in predicted_attributes.items():
        volume_ml = attr.get("volume_ml", np.nan)
        sample_key_only = cell_key.rsplit("_cell", 1)[0]
        real_volume = real_volume_map.get(sample_key_only, np.nan)

        if not np.isnan(volume_ml) and not np.isnan(real_volume):
            error_abs_ml = abs(volume_ml - real_volume)
            precision_percent = (1 - error_abs_ml / real_volume) * 100 if real_volume > 0 else np.nan
        else:
            error_abs_ml = np.nan
            precision_percent = np.nan

        all_rows.append({
            "sample_key": cell_key,
            "species": attr.get("species"),
            "quality_from_model": attr.get("quality_from_model"),
            "final_quality_percent": attr.get("final_quality_percent"),
            "stage": attr.get("stage"),
            "score": attr.get("score"),
            "volume_ml": volume_ml,
            "area_mm2": attr.get("area_mm2"),
            "height_mm": attr.get("height_mm"),
            "defective_percent": attr.get("defective_percent"),
            "real_volume_ml": real_volume,
            "error_abs_ml": error_abs_ml,
            "precision_percent": precision_percent
        })

    df = pd.DataFrame(all_rows)
    master_csv_path = os.path.join(output_base_dir, 'all_volumes_summary.xlsx')
    df.to_excel(master_csv_path, index=False)

    valid = df.dropna(subset=['error_abs_ml', 'precision_percent'])
    if not valid.empty:
        print(f"\n✅ CONSOLIDACIÓN | Error promedio: {valid['error_abs_ml'].mean():.3f} mL | Precisión promedio: {valid['precision_percent'].mean():.2f}%")
    print(f"Resultados en: {master_csv_path}")

# --- Main corregido ---
def main():
    input_image_dir = "testImages"
    model_path = "output_train_attr/model_final.pth"
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
    metadata = MetadataCatalog.get(dataset_name)
    metadata.thing_classes = category_names
    metadata.species_classes = ["moso", "other"]
    metadata.quality_classes = ["poor", "medium", "good"]
    metadata.stage_classes = ["non_embryogenic", "embryogenic"]

    # Volúmenes reales
    real_volume_map = {}
    image_id_to_key = {}
    for img in coco_data['images']:
        key = img['file_name'].rsplit('_', 1)[0]
        image_id_to_key[img['id']] = key
    for ann in coco_data['annotations']:
        if 'attributes' in ann and 'volume' in ann['attributes']:
            key = image_id_to_key.get(ann['image_id'])
            if key and key not in real_volume_map:
                real_volume_map[key] = ann['attributes']['volume']

    # Predictor (SIN cfg personalizadas inválidas)
    cfg = get_cfg()
    cfg.merge_from_file(get_config_file("COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"))
    cfg.MODEL.ROI_HEADS.NAME = "CallusROIHeads"  # ← Asegúrate de que esté definido en el entorno
    cfg.MODEL.WEIGHTS = model_path
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = len(category_names)
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.7  # Baja un poco para detectar defectos
    cfg.MODEL.DEVICE = "cpu"  # Cambia a "cuda" si tienes GPU
    predictor = DefaultPredictor(cfg)

    # Procesar muestras
    predicted_attributes = {}
    all_files = os.listdir(input_image_dir)
    sample_keys = {name.rsplit('_', 1)[0] for name in all_files 
                   if name.lower().endswith(('_top.jpg', '_top.jpeg', '_top.png', '_side.jpg', '_side.jpeg', '_side.png'))}

    for key in sorted(sample_keys):
        process_sample_pair(predictor, metadata, key, input_image_dir, output_base_dir, category_names, predicted_attributes)

    consolidate_results(output_base_dir, real_volume_map, predicted_attributes)

if __name__ == "__main__":
    main()