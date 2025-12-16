import xml.etree.ElementTree as ET
import json
import os
import cv2
import numpy as np

# ==============================================================================
# ATRIBUTOS NORMALIZADOS
# ==============================================================================

DEFAULT_ATTRIBUTES = {
    "volume": None,
    "quality": "unknown",
    "stage": "unknown",
    "species": "unknown",
}

def extract_attributes(node):
    """
    Extrae y normaliza atributos desde CVAT XML
    """
    attrs = DEFAULT_ATTRIBUTES.copy()

    for attr in node.findall("attribute"):
        name = attr.get("name", "").strip()
        value = attr.text.strip() if attr.text else "unknown"

        if name == "volume":
            try:
                attrs["volume"] = float(value)
            except:
                pass
        elif name == "Callus Quality":
            attrs["quality"] = value
        elif name == "Bamboo Species":
            attrs["species"] = value
        elif name == "Embryogenic Stage":
            attrs["stage"] = value

    return attrs


# ==============================================================================
# POLYGON / POLYLINE
# ==============================================================================

def process_points_annotation(node, categories, annotation_id, image_id):
    label = node.get("label")
    if label not in categories:
        return None, annotation_id

    points_str = node.get("points")
    if not points_str:
        return None, annotation_id

    try:
        points = [float(p) for p in points_str.replace(";", ",").split(",")]
    except ValueError:
        return None, annotation_id

    if len(points) < 6:
        return None, annotation_id

    segmentation = [points]
    pts = np.array(points).reshape(-1, 2).astype(np.float32)

    area = cv2.contourArea(pts)
    x, y, w, h = cv2.boundingRect(pts)

    annotation = {
        "id": annotation_id,
        "image_id": image_id,
        "category_id": categories[label],
        "segmentation": segmentation,
        "area": float(area),
        "bbox": [float(x), float(y), float(w), float(h)],
        "iscrowd": 0,
        "attributes": extract_attributes(node),
    }

    return annotation, annotation_id + 1


# ==============================================================================
# MAIN CONVERTER
# ==============================================================================

def convert_cvat_to_coco(xml_file_path, output_json_path):
    tree = ET.parse(xml_file_path)
    root = tree.getroot()

    coco = {
        "info": {},
        "licenses": [],
        "images": [],
        "annotations": [],
        "categories": [],
    }

    categories = {}
    cat_id = 1
    ann_id = 1

    # Categorías
    for label_node in root.findall(".//labels/label"):
        name = label_node.find("name").text
        categories[name] = cat_id
        coco["categories"].append({
            "id": cat_id,
            "name": name,
            "supercategory": ""
        })
        cat_id += 1

    # Imágenes
    for image_node in root.findall("image"):
        image_id = int(image_node.get("id"))
        coco["images"].append({
            "id": image_id,
            "file_name": image_node.get("name"),
            "width": int(image_node.get("width")),
            "height": int(image_node.get("height")),
        })

        # Polygon
        for poly in image_node.findall("polygon"):
            ann, ann_id = process_points_annotation(poly, categories, ann_id, image_id)
            if ann:
                coco["annotations"].append(ann)

        # Polyline
        for polyline in image_node.findall("polyline"):
            ann, ann_id = process_points_annotation(polyline, categories, ann_id, image_id)
            if ann:
                coco["annotations"].append(ann)

        # Ellipse (container)
        for ellipse in image_node.findall("ellipse"):
            label = ellipse.get("label")
            if label not in categories:
                continue

            cx = float(ellipse.get("cx"))
            cy = float(ellipse.get("cy"))
            rx = float(ellipse.get("rx"))
            ry = float(ellipse.get("ry"))
            rot = float(ellipse.get("rotation") or 0)

            points = cv2.ellipse2Poly(
                (int(cx), int(cy)),
                (int(rx), int(ry)),
                int(rot),
                0, 360, 5
            )

            x, y, w, h = cv2.boundingRect(points)
            area = float(np.pi * rx * ry)

            coco["annotations"].append({
                "id": ann_id,
                "image_id": image_id,
                "category_id": categories[label],
                "segmentation": [points.flatten().tolist()],
                "area": area,
                "bbox": [float(x), float(y), float(w), float(h)],
                "iscrowd": 0,
                "attributes": DEFAULT_ATTRIBUTES.copy(),  # container también tiene attributes
            })

            ann_id += 1

    with open(output_json_path, "w") as f:
        json.dump(coco, f, indent=2)

    print(f"✅ COCO JSON generado correctamente: {output_json_path}")


# ==============================================================================
# RUN
# ==============================================================================

if __name__ == "__main__":
    convert_cvat_to_coco(
        "annotations/annotations.xml",
        "annotations/coco_annotations.json"
    )
