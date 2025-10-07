import xml.etree.ElementTree as ET
import json
import os
import cv2
import glob
import numpy as np

def convert_cvat_to_coco(xml_file_path, image_folder_path, output_json_path):
    """
    Convierte un archivo de anotaciones de CVAT en formato XML a COCO JSON.

    Args:
        xml_file_path (str): Ruta al archivo de anotaciones XML de CVAT.
        image_folder_path (str): Ruta a la carpeta que contiene las imágenes.
        output_json_path (str): Ruta donde se guardará el archivo COCO JSON.
    """

    tree = ET.parse(xml_file_path)
    root = tree.getroot()

    # Estructura del diccionario COCO
    coco_data = {
        "info": {},
        "licenses": [],
        "images": [],
        "annotations": [],
        "categories": []
    }

    # ID de anotación y categoría
    annotation_id = 1
    category_id = 1
    categories = {}

    # Mapea las etiquetas de CVAT a IDs de categoría
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
            "license": 0,
            "flickr_url": "",
            "coco_url": "",
            "date_captured": ""
        })

        # Itera sobre los polígonos (polyline)
        for polyline_node in image_node.findall('polyline'):
            label = polyline_node.get('label')
            if label not in categories:
                continue
            
            # Reemplaza los ';' con ',' y luego divide la cadena
            points_str = polyline_node.get('points').replace(';', ',')
            points = [float(p) for p in points_str.split(',')]
            
            # La segmentación en COCO es una lista de listas de puntos
            segmentation = [points]
            
            # Convierte la lista plana a un array de NumPy
            points_np = np.array(points).reshape(-1, 2)
            
            # Calcula el Bounding Box a partir de los puntos
            x_coords = points_np[:, 0]
            y_coords = points_np[:, 1]
            min_x, min_y = np.min(x_coords), np.min(y_coords)
            max_x, max_y = np.max(x_coords), np.max(y_coords)
            bbox_width = max_x - min_x
            bbox_height = max_y - min_y
            bbox = [min_x, min_y, bbox_width, bbox_height]
            
            # Calcula el área del polígono
            area = cv2.contourArea(points_np.reshape(-1, 1, 2).astype(np.float32))

            # Extraer el atributo de volumen
            volume_attr_node = polyline_node.find('attribute[@name="volume"]')
            volume_value = None
            if volume_attr_node is not None:
                try:
                    volume_value = float(volume_attr_node.text)
                except (ValueError, TypeError):
                    volume_value = None  # Asignar None si la conversión falla

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


        # Itera sobre las elipses
        for ellipse_node in image_node.findall('ellipse'):
            label = ellipse_node.get('label')
            if label not in categories:
                continue

            # Extracción de parámetros de la elipse
            cx = float(ellipse_node.get('cx'))
            cy = float(ellipse_node.get('cy'))
            rx = float(ellipse_node.get('rx'))
            ry = float(ellipse_node.get('ry'))
            
            rotation_str = ellipse_node.get('rotation')
            if rotation_str is not None:
                rotation = float(rotation_str)
            else:
                rotation = 0.0
            
            # Convierte la elipse a polígono para COCO
            points = cv2.ellipse2Poly((int(cx), int(cy)), (int(rx), int(ry)), int(rotation), 0, 360, 1)
            segmentation = [points.flatten().tolist()]
            
            # Calcula el Bounding Box y el área de la elipse
            x, y, w, h = cv2.boundingRect(points)
            bbox = [float(x), float(y), float(w), float(h)]
            area = np.pi * rx * ry

            # Agrega los datos de la anotación
            coco_data['annotations'].append({
                "id": annotation_id,
                "image_id": image_id,
                "category_id": categories[label],
                "segmentation": segmentation,
                "area": area,
                "bbox": bbox,
                "iscrowd": 0,
            })
            annotation_id += 1
    
    # Guarda el archivo JSON
    with open(output_json_path, 'w') as f:
        json.dump(coco_data, f, indent=4)

    print(f"Conversión completada. El archivo COCO JSON se ha guardado en: {output_json_path}")
    
# ---

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
        # Llama a la función de conversión
        convert_cvat_to_coco(xml_file_path, image_folder_path, output_json_path)