import cv2
import numpy as np
import os
import torch
from detectron2.engine import DefaultPredictor
from detectron2.config import get_cfg
from detectron2.data import MetadataCatalog, DatasetCatalog
from detectron2.utils.visualizer import Visualizer, ColorMode
from detectron2.data.datasets import register_coco_instances
from detectron2.model_zoo import get_config_file
import json

if __name__ == "__main__":
    # Rutas a tu imagen de prueba, al modelo entrenado y al resultado
    test_image_path = "testImages/IMG_1576.jpeg"
    model_path = "output/model_final.pth" 
    output_image_path = "predicted_image.jpg"
    
    # 1. Registrar el dataset y asignar las clases manualmente
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

    # 2. Configurar el predictor
    cfg = get_cfg()
    cfg.merge_from_file(get_config_file("COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"))
    cfg.MODEL.WEIGHTS = model_path
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = 2
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.7
    cfg.MODEL.DEVICE = "cpu"
    predictor = DefaultPredictor(cfg)
    
    # 3. Asegurarse de que el modelo y la imagen existen
    if not os.path.exists(model_path):
        print("Error: El modelo entrenado no se encuentra en la ruta especificada.")
    if not os.path.exists(test_image_path):
        print("Error: La imagen de prueba no se encuentra en la ruta especificada.")
    
    if os.path.exists(model_path) and os.path.exists(test_image_path):
        # 4. Cargar la imagen y obtener las predicciones
        im = cv2.imread(test_image_path)
        outputs = predictor(im)
        instances = outputs["instances"].to("cpu")
        
        # 5. Visualizar las predicciones
        v = Visualizer(im[:, :, ::-1], metadata, scale=1.0, instance_mode=ColorMode.SEGMENTATION)
        out = v.draw_instance_predictions(instances)
        
        # --- CAMBIO IMPORTANTE AQUÍ ---
        final_image = out.get_image()[:, :, ::-1]
        final_image = cv2.cvtColor(final_image, cv2.COLOR_RGB2BGR) # Convierte el formato de la imagen para que sea compatible con OpenCV
        # ----------------------------

        # 6. Obtener los datos para el cálculo de volumen
        pred_classes = instances.pred_classes
        pred_masks = instances.pred_masks
        
        thing_classes = metadata.thing_classes
        frasco_id = thing_classes.index("container")
        celula_id = thing_classes.index("cell")

        # 7. Encontrar la máscara del frasco para calibración de escala
        frasco_mask = None
        for i, class_id in enumerate(pred_classes):
            if class_id == frasco_id:
                frasco_mask = pred_masks[i].numpy()
                break
        
        if frasco_mask is None:
            print("Frasco no detectado. No se puede realizar la calibración ni estimar el volumen.")
        else:
            # 8. Calcular el factor de conversión
            FRASCO_DIAMETER_MM = 90.0
            frasco_area_pixels = np.sum(frasco_mask)
            frasco_area_mm2 = np.pi * (FRASCO_DIAMETER_MM / 2)**2
            pixels_to_mm2 = frasco_area_mm2 / frasco_area_pixels
            print(f"Factor de conversión de píxeles a mm²: {pixels_to_mm2:.6f}")
            
            # 9. Estimar el volumen y dibujar el texto
            volumes = []
            print("\nEstimación de volúmenes de las células:")
            for i, class_id in enumerate(pred_classes):
                if class_id == celula_id:
                    celula_mask = pred_masks[i].numpy()
                    area_pixels = np.sum(celula_mask)
                    area_mm2 = area_pixels * pixels_to_mm2
                    CELULA_HEIGHT_MM = 2
                    volumen_mm3 = area_mm2 * CELULA_HEIGHT_MM
                    volumen_ml = volumen_mm3 / 1000
                    volumes.append(volumen_ml)
                    
                    y_coords, x_coords = np.where(celula_mask)
                    center_x, center_y = np.mean(x_coords), np.mean(y_coords)
                    
                    text = f"{volumen_ml:.6f} mL"
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    font_scale = 0.5
                    color = (0, 0, 255) # Rojo
                    thickness = 1
                    
                    cv2.putText(final_image, text, (int(center_x), int(center_y)), font, font_scale, color, thickness, cv2.LINE_AA)
                    
                    print(f"  - Célula detectada: Volumen estimado = {volumen_ml:.6f} mL")
            
            cv2.imwrite(output_image_path, final_image)
            print(f"\nImagen con predicciones y volúmenes guardada en: {output_image_path}")
            
    else:
        print("Asegúrate de que el modelo y la imagen existen en las rutas correctas.")