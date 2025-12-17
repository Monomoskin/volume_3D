import xml.etree.ElementTree as ET
import json
import os
import cv2
import numpy as np

# ==============================================================================
# HELPERS
# ==============================================================================

def resolve_container_label(original_label, image_name):
    """
    Separa container en container_top / container_side según el nombre de la imagen
    """
    if original_label != "container":
        return original_label

    name = image_name.lower()
    if "_top" in name:
        return "container_top"
    elif "_side" in name:
        return "container_side"
    else:
        # fallback seguro
        return "container"


def process_points_annotation(
    node, categories, annotation_id, image_id, image_name
):
    """
    Procesa nodos <polygon> o <polyline>
    """

    raw_label = node.get("label")
    label = resolve_container_label(raw_label, image_name)

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

    area = float(cv2.contourArea(pts))
    x, y, w, h = cv2.boundingRect(pts)

    annotation = {
        "id": annotation_id,
        "image_id": image_id,
        "category_id": categories[label],
        "segmentation": segmentation,
        "area": area,
        "bbox": [float(x), float(y), float(w), float(h)],
        "iscrowd": 0,
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
    # CATEGORIES (FORZAMOS container_top y container_side)
    # --------------------------------------------------
    base_labels = []

    for label_node in root.findall(".//labels/label"):
        name = label_node.find("name").text
        base_labels.append(name)

    final_labels = []
    for lbl in base_labels:
        if lbl == "container":
            final_labels.extend(["container_top", "container_side"])
        else:
            final_labels.append(lbl)

    for lbl in sorted(set(final_labels)):
        categories[lbl] = cat_id
        coco["categories"].append({
            "id": cat_id,
            "name": lbl,
            "supercategory": ""
        })
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
            ann, ann_id = process_points_annotation(
                poly, categories, ann_id, image_id, image_name
            )
            if ann:
                coco["annotations"].append(ann)

        # ---------- POLYLINES ----------
        for polyline in image_node.findall("polyline"):
            ann, ann_id = process_points_annotation(
                polyline, categories, ann_id, image_id, image_name
            )
            if ann:
                coco["annotations"].append(ann)

        # ---------- ELLIPSES ----------
        for ellipse in image_node.findall("ellipse"):
            raw_label = ellipse.get("label")
            label = resolve_container_label(raw_label, image_name)

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
                0, 360, 3
            )

            segmentation = [points.flatten().tolist()]
            x, y, w, h = cv2.boundingRect(points)
            area = float(np.pi * rx * ry)

            coco["annotations"].append({
                "id": ann_id,
                "image_id": image_id,
                "category_id": categories[label],
                "segmentation": segmentation,
                "area": area,
                "bbox": [float(x), float(y), float(w), float(h)],
                "iscrowd": 0,
            })

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
        "annotations/coco_annotations.json"
    )
