import cv2
import numpy as np
import os
import json
import csv
import pandas as pd # <-- ¡NECESITAS INSTALAR PANDAS!
from detectron2.engine import DefaultPredictor
from detectron2.config import get_cfg
from detectron2.data import MetadataCatalog
from detectron2.data.datasets import register_coco_instances
from detectron2.utils.visualizer import Visualizer, ColorMode
from detectron2.model_zoo import get_config_file
import torch

# INSTALAR PANDAS: Abre tu terminal (con el entorno virtual activado) y ejecuta:
# pip install pandas

# --- 1. Helper function (Sin cambios) ---
def find_highest_score_instance(instances, class_id):
    """
    Returns the instance with the highest score for a given class ID.
    Returns a Detectron2 'Instances' object.
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

# --- NUEVA FUNCIÓN: Consolida todos los resultados en un único CSV ---
def consolidate_results(output_base_dir):
    """
    Combines all individual volume CSV files into a single master CSV file 
    and adds a column for manual measurement input.
    """
    # ... (lectura de archivos sin cambios) ...

    all_files = [os.path.join(output_base_dir, f) for f in os.listdir(output_base_dir) if f.endswith('_volumes.csv')]
    
    if not all_files:
        print("\nNo individual volume CSV files found to consolidate.")
        return

    # Creamos una lista de DataFrames
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

    # Concatenamos todos los DataFrames
    master_df = pd.concat(all_data, ignore_index=True)
    
    # El campo 'center' está como lista, lo normalizamos
    if 'center' in master_df.columns:
        # Aseguramos que la columna 'center' sea una cadena antes de procesarla
        master_df['center'] = master_df['center'].astype(str)
        master_df[['center_x', 'center_y']] = master_df['center'].str.strip('[]').str.split(', ', expand=True).astype(float)
        master_df = master_df.drop(columns=['center'])

    # *** ¡CAMBIO CLAVE AQUÍ! ***
    # Añadimos la columna vacía para que el usuario ingrese el valor real
    master_df['real_volume_ml'] = np.nan 

    # Reordenamos las columnas para mayor claridad
    cols = ['image_name', 'class_name', 'volume_ml', 'real_volume_ml', 'score', 'cell_index', 'center_x', 'center_y']
    master_df = master_df.reindex(columns=cols)

    # Guardamos el archivo maestro
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

    # ... (Resto del setup sin cambios) ...

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

    frasco_diameter_mm = 90.0

    category_names = [cat['name'] for cat in coco_data['categories']]
    MetadataCatalog.get(dataset_name).thing_classes = category_names
    metadata = MetadataCatalog.get(dataset_name)

    # --- Predictor Configuration ---
    cfg = get_cfg()
    cfg.merge_from_file(get_config_file("COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"))
    cfg.MODEL.WEIGHTS = model_path
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = len(category_names)
    
    # UMBRAL BAJO PARA DIAGNÓSTICO: (Si ves 'callus' ahora, el modelo está aprendiendo pero débilmente.)
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.70 
    
    cfg.MODEL.DEVICE = "cpu"
    predictor = DefaultPredictor(cfg)

    # Get class IDs
    frasco_id = category_names.index("container")
    potato_cell_id = category_names.index("cell") 
    callus_cell_id = category_names.index("callus") 
    cell_class_ids = [potato_cell_id, callus_cell_id] 
    
    # --- Process images ---
    for image_name in os.listdir(input_image_dir):
        if not image_name.lower().endswith(('.jpg', '.jpeg', '.png')):
            continue
        
        image_path = os.path.join(input_image_dir, image_name)
        base_name = os.path.splitext(image_name)[0]
        output_image_path = os.path.join(output_base_dir, f"{base_name}_predicted.jpg")
        output_json_path = os.path.join(output_base_dir, f"{base_name}_volumes.json")
        output_csv_path = os.path.join(output_base_dir, f"{base_name}_volumes.csv")

        print(f"\nProcessing image: {image_path}")
        im = cv2.imread(image_path)
        if im is None:
            print(f"Failed to load image {image_path}. Skipping.")
            continue

        outputs = predictor(im)
        instances = outputs["instances"].to("cpu")

        # --- Detect Container ---
        frasco_instance = find_highest_score_instance(instances, frasco_id)
        if frasco_instance is None:
            print("Container not detected. Skipping image.")
            continue

        frasco_mask = frasco_instance.pred_masks[0].cpu().numpy().astype(bool)

        # Calculate pixel to mm² conversion factor
        y_coords, x_coords = np.where(frasco_mask)
        if x_coords.size == 0:
            print("Empty container mask. Skipping.")
            continue
        
        width_pixels = x_coords.max() - x_coords.min()
        pixels_per_mm = width_pixels / frasco_diameter_mm
        pixels_to_mm2 = 1 / (pixels_per_mm ** 2)
        print(f"Conversion factor (pixels -> mm²): {pixels_to_mm2:.6f}")

        # --- Detect Cells within Container ---
        volume_results = []
        celula_height_mm = 3.4

        for idx in range(len(instances)):
            current_class_id = instances.pred_classes[idx].item()

            if current_class_id not in cell_class_ids:
                continue
            
            cell_mask = instances.pred_masks[idx].numpy().astype(bool)

            intersection = np.logical_and(frasco_mask, cell_mask)
            if np.sum(cell_mask) == 0 or np.sum(intersection) / np.sum(cell_mask) < 0.9: 
                continue

            # Calculate volume
            area_mm2 = np.sum(cell_mask) * pixels_to_mm2
            volumen_ml = (area_mm2 * celula_height_mm) / 1000
            
            y_c, x_c = np.where(cell_mask)
            center_x, center_y = int(np.mean(x_c)), int(np.mean(y_c))
            
            class_name = category_names[current_class_id] 

            volume_results.append({
                "cell_index": idx,
                "class_name": class_name, 
                "volume_ml": volumen_ml,
                "center": [center_x, center_y],
                "score": instances.scores[idx].item()
            })

        if not volume_results:
            print("No cells detected within the container.")
        else:
            print(f"Estimated volumes for {len(volume_results)} cells:")
            for v in volume_results:
                print(f"  - {v['class_name']} {v['cell_index']}: {v['volume_ml']:.6f} mL (Score: {v['score']:.2f})")

        # --- Visualization and Saving Results (Sin cambios funcionales) ---
        v = Visualizer(im[:, :, ::-1], metadata, scale=1.0, instance_mode=ColorMode.SEGMENTATION)
        out = v.draw_instance_predictions(instances)
        final_image = out.get_image()

        final_image = cv2.cvtColor(final_image, cv2.COLOR_RGB2BGR)
        if final_image.dtype != np.uint8:
            final_image = (final_image * 255).astype(np.uint8)

        # Draw volumes with black outline for high contrast
        for v in volume_results:
            text = f"{v['class_name']}: {v['volume_ml']:.3f} mL"
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.6
            center_x, center_y = v['center']
            
            cv2.putText(final_image, text, (center_x, center_y), font, font_scale, (0, 0, 0), 3, cv2.LINE_AA)
            cv2.putText(final_image, text, (center_x, center_y), font, font_scale, (255, 255, 255), 1, cv2.LINE_AA)

        cv2.imwrite(output_image_path, final_image)
        print(f"Image saved: {output_image_path}")

        # Save results to JSON and CSV
        with open(output_json_path, "w") as f:
            json.dump(volume_results, f, indent=4)
            
        with open(output_csv_path, "w", newline="") as csvfile:
            fieldnames=["cell_index", "class_name", "volume_ml", "center", "score"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(volume_results)
        print("Results saved in JSON and CSV.")
    
    # --- Llamar a la función de consolidación al final de main ---
    consolidate_results(output_base_dir)

if __name__ == "__main__":
    main()