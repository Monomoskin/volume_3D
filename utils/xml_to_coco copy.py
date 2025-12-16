import xml.etree.ElementTree as ET
import json
import os
import cv2
import numpy as np
import glob
# Importar shapely si no lo tienes ya (necesario para la validación del área si tienes problemas de geometría)
# from shapely.geometry import Polygon 

# Función auxiliar para manejar la lógica de polígonos y polilíneas
def process_points_annotation(node, categories, annotation_id, image_id, volume_attribute=False):
    """Procesa nodos <polyline> o <polygon>."""
    
    # 1. Extracción de etiqueta y puntos
    label = node.get('label')
    if label not in categories:
        return None, annotation_id
    
    points_str = node.get('points').replace(';', ',')
    # Manejar el caso de puntos vacíos o mal formados
    try:
        points = [float(p) for p in points_str.split(',')]
    except ValueError:
        print(f"Advertencia: Anotación inválida o vacía encontrada en la imagen {image_id} para la etiqueta {label}. Saltando.")
        return None, annotation_id

    # 2. Geometría
    segmentation = [points]
    points_np = np.array(points).reshape(-1, 2)
    
    # Si es una polilínea (abierta), el área puede ser inexacta, pero la usamos para compatibilidad COCO
    area = cv2.contourArea(points_np.reshape(-1, 1, 2).astype(np.float32))

    # Bounding Box
    x, y, w, h = cv2.boundingRect(points_np.astype(np.float32))
    bbox = [float(x), float(y), float(w), float(h)]

    # 3. Atributos Adicionales (Volumen)
    volume_value = None
    if volume_attribute:
        volume_attr_node = node.find('attribute[@name="volume"]')
        if volume_attr_node is not None:
            try:
                volume_value = float(volume_attr_node.text)
            except (ValueError, TypeError):
                volume_value = None

    # 4. Construcción de la Anotación
    annotation = {
        "id": annotation_id,
        "image_id": image_id,
        "category_id": categories[label],
        "segmentation": segmentation,
        "area": area,
        "bbox": bbox,
        "iscrowd": 0,
    }
    
    if volume_attribute:
        annotation["attributes"] = {"volume": volume_value}
        
    return annotation, annotation_id + 1

def convert_cvat_to_coco(xml_file_path, image_folder_path, output_json_path):
    
    tree = ET.parse(xml_file_path)
    root = tree.getroot()

    coco_data = {
        "info": {},
        "licenses": [],
        "images": [],
        "annotations": [],
        "categories": []
    }

    annotation_id = 1
    category_id = 1
    categories = {}

    # Mapeo de categorías
    for label_node in root.findall('.//labels/label'):
        label_name = label_node.find('name').text
        if label_name not in categories:
            categories[label_name] = category_id
            coco_data['categories'].append({
                "id": category_id,
                "name": label_name,
                "supercategory": ""
            })
            category_id += 1

    # Itera sobre cada imagen en el XML
    for image_node in root.findall('image'):
        image_id = int(image_node.get('id'))
        file_name = image_node.get('name')
        image_width = int(image_node.get('width'))
        image_height = int(image_node.get('height'))
        
        # Agrega los datos de la imagen
        coco_data['images'].append({
            "id": image_id,
            "width": image_width,
            "height": image_height,
            "file_name": file_name,
            # ... (otros campos opcionales)
        })

        # --- AHORA SE PROCESAN LOS TRES TIPOS DE ANOTACIONES ---
        
        # 1. Procesa Polígonos (Polygon) - ¡SOLUCIÓN PARA CELL Y CELL_PROFILE!
        for polygon_node in image_node.findall('polygon'):
            ann, annotation_id = process_points_annotation(
                polygon_node, categories, annotation_id, image_id, 
                volume_attribute=True # Suponemos que Cell/Cell_Profile tiene el atributo 'volume'
            )
            if ann:
                coco_data['annotations'].append(ann)
                
        # 2. Procesa Polilíneas (Polyline)
        for polyline_node in image_node.findall('polyline'):
            ann, annotation_id = process_points_annotation(
                polyline_node, categories, annotation_id, image_id,
                volume_attribute=True
            )
            if ann:
                coco_data['annotations'].append(ann)


        # 3. Itera sobre las elipses
        for ellipse_node in image_node.findall('ellipse'):
            label = ellipse_node.get('label')
            if label not in categories:
                continue

            cx = float(ellipse_node.get('cx'))
            cy = float(ellipse_node.get('cy'))
            rx = float(ellipse_node.get('rx'))
            ry = float(ellipse_node.get('ry'))
            rotation = float(ellipse_node.get('rotation') or 0.0)
            
            # Conversión de elipse a polígono
            # Nota: cv2.ellipse2Poly requiere que los parámetros sean enteros
            points = cv2.ellipse2Poly((int(cx), int(cy)), (int(rx), int(ry)), int(rotation), 0, 360, 1)
            segmentation = [points.flatten().tolist()]
            
            # Cálculo de Bounding Box y Área
            x, y, w, h = cv2.boundingRect(points)
            bbox = [float(x), float(y), float(w), float(h)]
            area = np.pi * rx * ry # Área exacta de la elipse
            
            # Extraer atributo de volumen si aplica
            volume_value = None
            volume_attr_node = ellipse_node.find('attribute[@name="volume"]')
            if volume_attr_node is not None:
                try:
                    volume_value = float(volume_attr_node.text)
                except (ValueError, TypeError):
                    pass # Dejar como None si falla

            # Agrega los datos de la anotación
            coco_data['annotations'].append({
                "id": annotation_id,
                "image_id": image_id,
                "category_id": categories[label],
                "segmentation": segmentation,
                "area": area,
                "bbox": bbox,
                "iscrowd": 0,
                "attributes": {
                    "volume": volume_value
                }
            })
            annotation_id += 1
    
    # Guarda el archivo JSON
    with open(output_json_path, 'w') as f:
        json.dump(coco_data, f, indent=4)

    print(f"Conversión completada. El archivo COCO JSON se ha guardado en: {output_json_path}")


# Ejemplo de uso:
if __name__ == "__main__":
    # Define las rutas de los archivos y carpetas
    xml_file_path = "annotations/annotations.xml"
    image_folder_path = "images/"
    output_json_path = "annotations/coco_annotations.json"

    # Verificación de que el XML existe
    if not os.path.exists(xml_file_path):
        print(f"Error: El archivo XML no se encuentra en la ruta: {xml_file_path}")
    else:
        convert_cvat_to_coco(xml_file_path, image_folder_path, output_json_path)