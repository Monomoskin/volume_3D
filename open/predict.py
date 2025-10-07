import cv2
import numpy as np
import os
import json
import csv
from detectron2.engine import DefaultPredictor
from detectron2.config import get_cfg
from detectron2.data import MetadataCatalog
from detectron2.utils.visualizer import Visualizer, ColorMode
from detectron2.data.datasets import register_coco_instances
from detectron2.model_zoo import get_config_file

# -----------------------
# Funciones auxiliares
# -----------------------
def clean_mask(mask):
    """Aplica operaciones morfológicas para limpiar la máscara."""
    mask = mask.astype(np.uint8)
    kernel = np.ones((3, 3), np.uint8)  # kernel más pequeño para células pequeñas
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    return mask

def filter_small_masks(masks, min_pixels=5):
    """Elimina máscaras demasiado pequeñas (probables falsos positivos)."""
    filtered = []
    for mask in masks:
        if np.sum(mask) >= min_pixels:
            filtered.append(mask)
    return filtered

def mask_iou(mask1, mask2):
    """Calcula IoU entre dos máscaras binarias."""
    intersection = np.logical_and(mask1, mask2).sum()
    union = np.logical_or(mask1, mask2).sum()
    if union == 0:
        return 0
    return intersection / union

def filter_duplicate_masks(masks, iou_threshold=0.5):
    """Filtra máscaras que se solapan demasiado (IoU > threshold)."""
    keep = []
    for i, m1 in enumerate(masks):
        duplicate = False
        for j in keep:
            if mask_iou(m1, masks[j]) > iou_threshold:
                duplicate = True
                break
        if not duplicate:
            keep.append(i)
    return keep

def draw_volumes_on_image(image, masks, volumes):
    """Dibuja los volúmenes sobre la imagen."""
    for i, mask in enumerate(masks):
        y_coords, x_coords = np.where(mask)
        if len(y_coords) == 0:
            continue
        center_x, center_y = int(np.mean(x_coords)), int(np.mean(y_coords))
        text = f"{volumes[i]:.4f} mL"
        cv2.putText(image, text, (center_x, center_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)
    return image

def save_volumes_json(volumes_list, json_path):
    with open(json_path, "w") as f:
        json.dump(volumes_list, f, indent=4)
    print(f"Resultados de volúmenes guardados en JSON: {json_path}")

def save_volumes_csv(volumes_list, csv_path):
    with open(csv_path, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=["cell_index", "volume_ml", "center"])
        writer.writeheader()
        for row in volumes_list:
            writer.writerow(row)
    print(f"Resultados de volúmenes guardados en CSV: {csv_path}")

# -----------------------
# Función principal
# -----------------------
def main():
    # --- Rutas ---
    test_image_path = "images/IMG_1350.jpeg"
    model_path = "output/model_final.pth"
    output_image_path = "predicted_image.jpg"
    output_json_path = "volumes.json"
    output_csv_path = "volumes.csv"

    # --- Registrar dataset ---
    dataset_name = "celulas_frascos"
    json_path = "annotations/coco_annotations.json"
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

    # --- Configurar predictor ---
    cfg = get_cfg()
    cfg.merge_from_file(get_config_file("COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"))
    cfg.MODEL.WEIGHTS = model_path
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = len(category_names)
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.6
    cfg.MODEL.DEVICE = "cpu"
    predictor = DefaultPredictor(cfg)

    # --- Verificar existencia de archivos ---
    if not os.path.exists(model_path) or not os.path.exists(test_image_path):
        print("Error: El modelo o la imagen de prueba no se encuentran.")
        return

    # --- Cargar imagen y predecir ---
    im = cv2.imread(test_image_path)
    outputs = predictor(im)
    instances = outputs["instances"].to("cpu")

    # --- Visualización ---
    v = Visualizer(im[:, :, ::-1], metadata, scale=1.0, instance_mode=ColorMode.SEGMENTATION)
    out = v.draw_instance_predictions(instances)
    final_image = out.get_image()[:, :, ::-1]
    final_image = cv2.cvtColor(final_image, cv2.COLOR_RGB2BGR)

    # --- IDs de clases ---
    frasco_id = metadata.thing_classes.index("container")
    celula_id = metadata.thing_classes.index("cell")

    # --- Encontrar máscara del frasco ---
    frasco_mask = None
    for i, class_id in enumerate(instances.pred_classes):
        if class_id == frasco_id:
            frasco_mask = instances.pred_masks[i].numpy()
            break
    if frasco_mask is None:
        print("Frasco no detectado. No se puede calibrar ni estimar volumen.")
        return

    # --- Calibración usando ancho del frasco (8cm) ---
    FRASCO_DIAMETER_MM = 90.0
    y_coords, x_coords = np.where(frasco_mask)
    width_pixels = x_coords.max() - x_coords.min()
    pixels_per_mm = width_pixels / FRASCO_DIAMETER_MM
    pixels_to_mm2 = 1 / (pixels_per_mm ** 2)
    print(f"Factor de conversión de píxeles a mm²: {pixels_to_mm2:.6f}")

    # --- Estimar volúmenes ---
    celula_masks = []
    volumes = []
    volume_results = []

    for i, class_id in enumerate(instances.pred_classes):
        if class_id == celula_id:
            mask = clean_mask(instances.pred_masks[i].numpy())
            celula_masks.append(mask)

    # Filtrar máscaras pequeñas
    celula_masks = filter_small_masks(celula_masks, min_pixels=5)
    # Filtrar duplicadas
    if len(celula_masks) > 1:
        keep_indices = filter_duplicate_masks(celula_masks, iou_threshold=0.5)
        celula_masks = [celula_masks[i] for i in keep_indices]

    print(f"Número de máscaras de células después de filtrar: {len(celula_masks)}")

    for i, mask in enumerate(celula_masks):
        area_pixels = np.sum(mask)
        area_mm2 = area_pixels * pixels_to_mm2
        CELULA_HEIGHT_MM =1   # ajustar si los volúmenes son muy pequeños
        volumen_mm3 = area_mm2 * CELULA_HEIGHT_MM
        volumen_ml = volumen_mm3 / 1000
        volumes.append(volumen_ml)

        y_c, x_c = np.where(mask)
        center_x, center_y = int(np.mean(x_c)), int(np.mean(y_c))

        volume_results.append({
            "cell_index": i,
            "volume_ml": volumen_ml,
            "center": [center_x, center_y]
        })
        print(f" - Célula detectada: Volumen estimado = {volumen_ml:.6f} mL")

    # --- Dibujar textos y guardar resultados ---
    final_image = draw_volumes_on_image(final_image, celula_masks, volumes)
    cv2.imwrite(output_image_path, final_image)
    print(f"\nImagen con predicciones y volúmenes guardada en: {output_image_path}")

    save_volumes_json(volume_results, output_json_path)
    save_volumes_csv(volume_results, output_csv_path)

# -----------------------
if __name__ == "__main__":
    main()
