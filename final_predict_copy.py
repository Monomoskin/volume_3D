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

# --- 2. Procesamiento de cada muestra (TOP + SIDE) ---
def process_sample_pair(predictor, metadata, sample_key, input_image_dir, output_base_dir, category_names):
    # --------------------------------------------------
    # 0. Cargar paths
    # --------------------------------------------------
    for ext in [".jpeg", ".jpg"]:
        top_path = os.path.join(input_image_dir, f"{sample_key}_TOP{ext}")
        side_path = os.path.join(input_image_dir, f"{sample_key}_SIDE{ext}")
        if os.path.exists(top_path) and os.path.exists(side_path):
            break
    else:
        print(f"[SKIP] Faltan archivos para la muestra {sample_key}.")
        return

    print(f"[PROCESS] Procesando muestra: {sample_key}")

    frasco_top_id = category_names.index("container_top")
    frasco_side_id = category_names.index("container_side")
    top_classes_of_interest = [
        category_names.index(n) for n in ["callus", "potato"] if n in category_names
    ]

    cell_profile_id = category_names.index("cell_profile") if "cell_profile" in category_names else None

    # --------------------------------------------------
    # 1. SIDE → altura real
    # --------------------------------------------------
    im_side = cv2.imread(side_path)
    instances_side = predictor(im_side)["instances"].to("cpu")

    frasco_side = find_highest_score_instance(instances_side, frasco_side_id)
    if frasco_side is None:
        print("[ERROR] Contenedor no detectado en SIDE.")
        return

    frasco_mask = frasco_side.pred_masks[0].numpy().astype(bool)
    y = np.where(frasco_mask)[0]
    factor_z = FRASCO_HEIGHT_MM / (y.max() - y.min())

    if cell_profile_id is not None:
        cell_prof = find_highest_score_instance(instances_side, cell_profile_id)
        if cell_prof is None:
            print("[ERROR] cell_profile no detectada en SIDE.")
            return
        m = cell_prof.pred_masks[0].numpy().astype(bool)
        y = np.where(m)[0]
        height_real_mm = (y.max() - y.min()) * factor_z
    else:
        height_real_mm = None

    # --------------------------------------------------
    # 2. TOP → área y selección de mejor célula
    # --------------------------------------------------
    im_top = cv2.imread(top_path)
    instances_top = predictor(im_top)["instances"].to("cpu")

    frasco_top = find_highest_score_instance(instances_top, frasco_top_id)
    if frasco_top is None:
        print("[ERROR] Contenedor no detectado en TOP.")
        return

    mask_f = frasco_top.pred_masks[0].numpy().astype(bool)
    _, x = np.where(mask_f)
    px_per_mm = (x.max() - x.min()) / FRASCO_DIAMETER_MM
    px_to_mm2 = 1 / (px_per_mm ** 2)

    best_cell, best_score = None, -1
    for i in range(len(instances_top)):
        cid = instances_top.pred_classes[i].item()
        if cid not in top_classes_of_interest:
            continue
        m = instances_top.pred_masks[i].numpy().astype(bool)
        if np.sum(m & mask_f) / np.sum(m) < 0.9:
            continue
        s = instances_top.scores[i].item()
        if s > best_score:
            best_score, best_cell = s, i

    if best_cell is None:
        print("[ERROR] No se encontró célula válida.")
        return

    # --------------------------------------------------
    # 3. Datos finales de la mejor instancia
    # --------------------------------------------------
    best_class_id = instances_top.pred_classes[best_cell].item()
    best_class_name = category_names[best_class_id]

    cell_mask = instances_top.pred_masks[best_cell].numpy().astype(bool)
    area_mm2 = np.sum(cell_mask) * px_to_mm2

    if height_real_mm is None:
        print("[ERROR] Altura no disponible.")
        return

    volumen_ml = (area_mm2 * height_real_mm) / 1000
    ys, xs = np.where(cell_mask)
    cx, cy = int(xs.mean()), int(ys.mean())

    # --------------------------------------------------
    # 4. Atributos (SOLO si es callus)
    # --------------------------------------------------
    if best_class_name == "callus":
        species = metadata.species_classes[instances_top.pred_species[best_cell].item()]
        quality = metadata.quality_classes[instances_top.pred_quality[best_cell].item()]
        stage   = metadata.stage_classes[instances_top.pred_stage[best_cell].item()]
    else:
        species = quality = stage = None

    predicted_attributes[sample_key] = {
        "class": best_class_name,
        "species": species,
        "quality": quality,
        "stage": stage,
        "score": round(best_score, 3),
        "volume_ml": volumen_ml,
        "area_mm2": area_mm2,
        "height_mm": height_real_mm
    }

    # --------------------------------------------------
    # 5. Guardar imágenes
    # --------------------------------------------------
    for view, im, inst, name in [
        ("TOP", im_top, instances_top, f"{sample_key}_TOP_predicted.jpg"),
        ("SIDE", im_side, instances_side, f"{sample_key}_SIDE_predicted.jpg")
    ]:
        v = Visualizer(im[:, :, ::-1], metadata, instance_mode=ColorMode.SEGMENTATION)

        for i in range(len(inst)):
            v.draw_binary_mask(inst.pred_masks[i].numpy(), alpha=0.4)

        if view == "TOP":
            a = predicted_attributes[sample_key]
            text = (
                f"Class: {a['class']}\n"
                f"Species: {a['species']}\n"
                f"Quality: {a['quality']}\n"
                f"Stage: {a['stage']}\n"
                f"Score: {a['score']:.2f}\n"
                f"Volume: {a['volume_ml']:.2f} mL"
            )
            v.draw_text(text, (cx, cy), font_size=14, color="yellow", horizontal_alignment="center")

        cv2.imwrite(os.path.join(output_base_dir, name), v.output.get_image()[:, :, ::-1])

    # --------------------------------------------------
    # 6. CSV
    # --------------------------------------------------
    df = pd.DataFrame([{
        "sample_key": sample_key,
        "class_name": best_class_name,
        "species": species,
        "quality": quality,
        "stage": stage,
        "volume_ml": volumen_ml,
        "area_mm2": area_mm2,
        "height_mm": height_real_mm,
        "center_x": cx,
        "center_y": cy,
        "score": best_score
    }])

    df.to_csv(os.path.join(output_base_dir, f"{sample_key}_volumes.csv"), index=False)
    print(f"[SAVE] CSV guardado para {sample_key}")

# --- 3. Consolidación de resultados ---
def consolidate_results(output_base_dir, real_volume_map, predicted_attributes):
    all_rows = []

    for sample_key, attr in predicted_attributes.items():
        row = {
            "sample_key": sample_key,
            "species": attr["species"],
            "quality": attr["quality"],
            "stage": attr["stage"],
            "score": attr["score"],
            "volume_ml": attr["volume_ml"],
            "area_mm2": attr["area_mm2"],
            "height_mm": attr["height_mm"],
            "real_volume_ml": real_volume_map.get(sample_key, np.nan)
        }
        row["error_abs_ml"] = abs(row["volume_ml"] - row["real_volume_ml"]) if not np.isnan(row["real_volume_ml"]) else np.nan
        row["precision_percent"] = (1 - row["error_abs_ml"] / row["real_volume_ml"])*100 if not np.isnan(row["real_volume_ml"]) else np.nan
        all_rows.append(row)

    df = pd.DataFrame(all_rows)
    master_csv_path = os.path.join(output_base_dir, 'all_volumes_summary.xlsx')
    df.to_excel(master_csv_path, index=False)

    valid_precision = df.dropna(subset=['real_volume_ml', 'precision_percent'])
    if not valid_precision.empty:
        mean_precision = valid_precision['precision_percent'].mean()
        mean_error = valid_precision['error_abs_ml'].mean()
        print(f"\n✅ CONSOLIDACIÓN EXITOSA | ERROR ABSOLUTO PROMEDIO: {mean_error:.3f} mL | PRECISIÓN PROMEDIO: {mean_precision:.2f}%")
        print(f"RESULTADOS GUARDADOS EN: {master_csv_path}")

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
    input_image_dir = "testImages"
    model_path = "output_train/model_0004799.pth" 
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
