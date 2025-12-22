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
from detectron2.engine import DefaultPredictor
from roi_heads import CallusROIHeads 
# --- CONSTANTES DE CALIBRACIÓN (DEBES VERIFICAR ESTOS VALORES REALES) ---
FRASCO_DIAMETER_MM = 90.0
FRASCO_HEIGHT_MM = 12.0
predicted_attributes = {}
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

def process_sample_pair(predictor, metadata, sample_key, input_image_dir, output_base_dir, category_names):
    # --------------------------------------------------
    # 0. Buscar archivos (TOP obligatorio, SIDE opcional)
    # --------------------------------------------------
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

    frasco_top_id = category_names.index("container_top")
    frasco_side_id = category_names.index("container_side")
    top_classes_of_interest = [
        category_names.index(n) for n in ["callus", "potato"] if n in category_names
    ]
    cell_profile_id = category_names.index("cell_profile") if "cell_profile" in category_names else None

    # --------------------------------------------------
    # 1. SIDE → altura real (si existe)
    # --------------------------------------------------
    height_real_mm = None
    if has_side:
        im_side = cv2.imread(side_path)
        inst_side = predictor(im_side)["instances"].to("cpu")

        frasco_side = find_highest_score_instance(inst_side, frasco_side_id)
        if frasco_side is not None:
            m_f = frasco_side.pred_masks[0].numpy().astype(bool)
            ys = np.where(m_f)[0]
            factor_z = FRASCO_HEIGHT_MM / (ys.max() - ys.min())

            if cell_profile_id is not None:
                cp = find_highest_score_instance(inst_side, cell_profile_id)
                if cp is not None:
                    m_cp = cp.pred_masks[0].numpy().astype(bool)
                    ys = np.where(m_cp)[0]
                    height_real_mm = (ys.max() - ys.min()) * factor_z

    # --------------------------------------------------
    # 2. TOP → detección y selección de células
    # --------------------------------------------------
    im_top = cv2.imread(top_path)
    inst_top = predictor(im_top)["instances"].to("cpu")

    frasco_top = find_highest_score_instance(inst_top, frasco_top_id)
    if frasco_top is None:
        print("[ERROR] Contenedor no detectado en TOP")
        return

    m_f = frasco_top.pred_masks[0].numpy().astype(bool)
    _, xs = np.where(m_f)
    px_per_mm = (xs.max() - xs.min()) / FRASCO_DIAMETER_MM
    px_to_mm2 = 1 / (px_per_mm ** 2)

    # --------------------------------------------------
    # 3. Recorrer todas las células TOP
    # --------------------------------------------------
    volume_calculable = has_side and (len([i for i in range(len(inst_top)) if inst_top.pred_classes[i].item() in top_classes_of_interest]) == 1)
    volume_ml = None
    rows = []

    for i in range(len(inst_top)):
        cid = inst_top.pred_classes[i].item()
        if cid not in top_classes_of_interest:
            continue

        cell_mask = inst_top.pred_masks[i].numpy().astype(bool)
        # Asegurarse que esté dentro del frasco
        if np.sum(cell_mask & m_f) / np.sum(cell_mask) < 0.9:
            continue

        score = inst_top.scores[i].item()
        best_class_name = category_names[cid]

        area_mm2 = np.sum(cell_mask) * px_to_mm2
        ys, xs = np.where(cell_mask)
        cx, cy = int(xs.mean()), int(ys.mean())

        # Calcular volumen solo si hay SIDE y solo 1 célula
        if volume_calculable:
            volume_ml = (area_mm2 * height_real_mm) / 1000
        else:
            volume_ml = None

        # Atributos solo callus
        if best_class_name == "callus" and hasattr(inst_top, "pred_species"):
            species = metadata.species_classes[inst_top.pred_species[i].item()]
            quality = metadata.quality_classes[inst_top.pred_quality[i].item()]
            stage   = metadata.stage_classes[inst_top.pred_stage[i].item()]
        else:
            species = quality = stage = None

        # Guardar en predicted_attributes con key por célula
        cell_key = f"{sample_key}_cell{i+1}"
        predicted_attributes[cell_key] = {
            "class": best_class_name,
            "species": species,
            "quality": quality,
            "stage": stage,
            "score": round(score, 3),
            "volume_ml": volume_ml,
            "area_mm2": area_mm2,
            "height_mm": height_real_mm
        }

        rows.append({
            "sample_key": cell_key,
            "class_name": best_class_name,
            "species": species,
            "quality": quality,
            "stage": stage,
            "volume_ml": volume_ml,
            "area_mm2": area_mm2,
            "height_mm": height_real_mm,
            "center_x": cx,
            "center_y": cy,
            "score": score
        })

    # --------------------------------------------------
    # 4. Guardar imagen con texto para cada célula
    # --------------------------------------------------
    v = Visualizer(im_top[:, :, ::-1], metadata, instance_mode=ColorMode.SEGMENTATION)
    for i in range(len(inst_top)):
        v.draw_binary_mask(inst_top.pred_masks[i].numpy(), alpha=0.35)

    for idx, row in enumerate(rows):
        text_lines = [
            f"Class: {row['class_name']}",
            f"Species: {row['species']}",
            f"Quality: {row['quality']}",
            f"Stage: {row['stage']}",
            f"Score: {row['score']:.2f}",
            f"Volume: {row['volume_ml']:.2f} mL" if row['volume_ml'] else "Volume: N/A"
        ]
        ys, xs = np.where(inst_top.pred_masks[idx].numpy())
        cx, cy = int(xs.mean()), int(ys.mean())
        v.draw_text(
            "\n".join(text_lines),
            (cx, cy - 40),
            font_size=18,
            color="yellow",
            horizontal_alignment="center"
        )

    cv2.imwrite(os.path.join(output_base_dir, f"{sample_key}_TOP_predicted.jpg"), v.output.get_image()[:, :, ::-1])

    # --------------------------------------------------
    # 5. Guardar CSV
    # --------------------------------------------------
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(output_base_dir, f"{sample_key}_volumes.csv"), index=False)
    print(f"[SAVE] CSV guardado para {sample_key}")

# --- 3. Consolidación de resultados ---
def consolidate_results(output_base_dir, real_volume_map, predicted_attributes):
    all_rows = []

    for sample_key, attr in predicted_attributes.items():
        volume_ml = attr["volume_ml"] if attr["volume_ml"] is not None else np.nan
        real_volume = real_volume_map.get(sample_key, np.nan)

        # Calcular error absoluto de forma segura
        if not np.isnan(volume_ml) and not np.isnan(real_volume):
            error_abs_ml = abs(volume_ml - real_volume)
            precision_percent = (1 - error_abs_ml / real_volume) * 100
        else:
            error_abs_ml = np.nan
            precision_percent = np.nan

        row = {
            "sample_key": sample_key,
            "species": attr["species"],
            "quality": attr["quality"],
            "stage": attr["stage"],
            "score": attr["score"],
            "volume_ml": volume_ml,
            "area_mm2": attr["area_mm2"],
            "height_mm": attr["height_mm"],
            "real_volume_ml": real_volume,
            "error_abs_ml": error_abs_ml,
            "precision_percent": precision_percent
        }

        all_rows.append(row)

    df = pd.DataFrame(all_rows)
    master_csv_path = os.path.join(output_base_dir, 'all_volumes_summary.xlsx')
    df.to_excel(master_csv_path, index=False)

    # Estadísticas solo con datos válidos
    valid_precision = df.dropna(subset=['error_abs_ml', 'precision_percent'])
    if not valid_precision.empty:
        mean_precision = valid_precision['precision_percent'].mean()
        mean_error = valid_precision['error_abs_ml'].mean()
        print(f"\n✅ CONSOLIDACIÓN EXITOSA | ERROR ABSOLUTO PROMEDIO: {mean_error:.3f} mL | PRECISIÓN PROMEDIO: {mean_precision:.2f}%")
        print(f"RESULTADOS GUARDADOS EN: {master_csv_path}")
    else:
        print(f"\n⚠️ No hay datos válidos para calcular estadísticas. Resultados guardados en: {master_csv_path}")

def build_attribute_text(instances, idx, metadata):
    parts = []

    if hasattr(instances, "pred_species"):
        sp = instances.pred_species[idx].item()
        parts.append(metadata.species_classes[sp])

    if hasattr(instances, "pred_quality"):
        q = instances.pred_quality[idx].item()
        parts.append(metadata.quality_classes[q])

    if hasattr(instances, "pred_stage"):
        st = instances.pred_stage[idx].item()
        parts.append(metadata.stage_classes[st])

    return " | ".join(parts)

# --- 4. Main ---
def main():
    input_image_dir = "testImages_copy"
    model_path = "output_train/model_final.pth" 
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
    metadata.species_classes = ["moso", "other"]
    metadata.quality_classes = ["poor", "medium", "good"]
    metadata.stage_classes = ["non_embryogenic", "embryogenic"]

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

    # 🔥 USAR TU ROI HEADS CUSTOM
    cfg.MODEL.ROI_HEADS.NAME = "CallusROIHeads"

    # 🔥 ATRIBUTOS (IGUAL QUE ENTRENAMIENTO)
    cfg.MODEL.ROI_HEADS.NUM_SPECIES = 2
    cfg.MODEL.ROI_HEADS.NUM_QUALITY = 3
    cfg.MODEL.ROI_HEADS.NUM_STAGE = 2
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

    consolidate_results(output_base_dir, real_volume_map, predicted_attributes)

if __name__ == "__main__":
    main()
