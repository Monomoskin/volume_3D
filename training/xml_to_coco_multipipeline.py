import xml.etree.ElementTree as ET
import json
import os
import cv2
import numpy as np

# ==============================================================================
# ATRIBUTOS POR CLASE
# ==============================================================================
CLASS_ATTRIBUTE_SCHEMA = {
    "callus": {
        "volume": None,
        "quality": "unknown",
        "species": "unknown",
        "stage": "unknown"
    },
    "potato": {
        "volume": None
    },
    "cell_profile": {
        "volume": None
    },
    "container_top": {},
    "container_side": {}
}

# Map CVAT attribute names to our JSON keys
ATTRIBUTE_NAME_MAP = {
    "volume": "volume",
    "Callus Quality": "quality",
    "Bamboo Species": "species",
    "Embryogenic Stage": "stage"
}

# ==============================================================================
# HELPERS
# ==============================================================================

def extract_attributes(node, label):
    """
    Extrae y normaliza atributos según la clase y el esquema definido
    """
    attrs = CLASS_ATTRIBUTE_SCHEMA.get(label, {}).copy()

    for attr_node in node.findall("attribute"):
        cvat_name = attr_node.get("name", "").strip()
        key = ATTRIBUTE_NAME_MAP.get(cvat_name)
        if key and key in attrs:
            value = attr_node.text.strip() if attr_node.text else None
            if key == "volume":
                try:
                    attrs[key] = float(value)
                except (ValueError, TypeError):
                    pass
            else:
                attrs[key] = value or attrs[key]

    return attrs

def process_points_annotation(node, categories, annotation_id, image_id, image_name):
    """
    Procesa nodos <polygon> o <polyline> y asigna atributos
    """
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

    pts = np.array(points).reshape(-1, 2).astype(np.float32)
    area = float(cv2.contourArea(pts))
    x, y, w, h = cv2.boundingRect(pts)

    annotation = {
        "id": annotation_id,
        "image_id": image_id,
        "category_id": categories[label],
        "segmentation": [points],
        "area": area,
        "bbox": [float(x), float(y), float(w), float(h)],
        "iscrowd": 0,
        "attributes": extract_attributes(node, label)
    }

    return annotation, annotation_id + 1

# ==============================================================================
# CONVERTER
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

    # --------------------------------------------------
    # CATEGORIES
    # --------------------------------------------------
    for label_node in root.findall(".//labels/label"):
        name = label_node.find("name").text
        categories[name] = cat_id
        coco["categories"].append({"id": cat_id, "name": name, "supercategory": ""})
        cat_id += 1

    # --------------------------------------------------
    # IMAGES + ANNOTATIONS
    # --------------------------------------------------
    for image_node in root.findall("image"):
        image_id = int(image_node.get("id"))
        image_name = image_node.get("name")

        coco["images"].append({
            "id": image_id,
            "file_name": image_name,
            "width": int(image_node.get("width")),
            "height": int(image_node.get("height")),
        })

        # ---------- POLYGONS ----------
        for poly in image_node.findall("polygon"):
            ann, ann_id = process_points_annotation(poly, categories, ann_id, image_id, image_name)
            if ann:
                coco["annotations"].append(ann)

        # ---------- POLYLINES ----------
        for polyline in image_node.findall("polyline"):
            ann, ann_id = process_points_annotation(polyline, categories, ann_id, image_id, image_name)
            if ann:
                coco["annotations"].append(ann)

        # ---------- ELLIPSES ----------
        for ellipse in image_node.findall("ellipse"):
            label = ellipse.get("label")
            if label not in categories:
                continue

            cx = float(ellipse.get("cx"))
            cy = float(ellipse.get("cy"))
            rx = float(ellipse.get("rx"))
            ry = float(ellipse.get("ry"))
            rot = float(ellipse.get("rotation") or 0)

            points = cv2.ellipse2Poly((int(cx), int(cy)), (int(rx), int(ry)), int(rot), 0, 360, 3)
            x, y, w, h = cv2.boundingRect(points)
            area = float(np.pi * rx * ry)

            annotation = {
                "id": ann_id,
                "image_id": image_id,
                "category_id": categories[label],
                "segmentation": [points.flatten().tolist()],
                "area": area,
                "bbox": [float(x), float(y), float(w), float(h)],
                "iscrowd": 0,
                "attributes": extract_attributes(ellipse, label)
            }

            coco["annotations"].append(annotation)
            ann_id += 1

    # --------------------------------------------------
    # SAVE
    # --------------------------------------------------
    with open(output_json_path, "w") as f:
        json.dump(coco, f, indent=2)

    print(f"✅ COCO JSON generado correctamente: {output_json_path}")

# ==============================================================================
# RUN
# ==============================================================================

if __name__ == "__main__":
    convert_cvat_to_coco(
        "annotations/annotations.xml",
        "annotations/coco_annotations_multiattr.json"
    )
