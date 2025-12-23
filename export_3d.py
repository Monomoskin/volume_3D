"""
Exporta modelo 3D (.ply) de frasco + callus usando TOP + SIDE masks
Dependencias:
pip install trimesh shapely opencv-python
"""

import os
import numpy as np
import cv2
import trimesh
from shapely.geometry import Polygon

FRASCO_DIAMETER_MM = 90.0
FRASCO_HEIGHT_MM = 12.0

# ------------------------------------------------------
# Utilities
# ------------------------------------------------------

def mask_to_contour(mask, px_per_mm):
    """
    Convierte máscara binaria a coordenadas XY en mm
    """
    contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    cnt = max(contours, key=cv2.contourArea)
    cnt_mm = cnt[:, 0, :] / px_per_mm
    return cnt_mm

def create_jar_mesh():
    """
    Frasco como cilindro hueco
    """
    outer = trimesh.creation.cylinder(radius=FRASCO_DIAMETER_MM/2, height=FRASCO_HEIGHT_MM, sections=64)
    inner = trimesh.creation.cylinder(radius=FRASCO_DIAMETER_MM/2 - 2, height=FRASCO_HEIGHT_MM+2, sections=64)
    jar = outer.difference(inner)
    jar.visual.face_colors = [200, 200, 200, 80]  # gris translúcido
    jar.apply_translation([0,0,FRASCO_HEIGHT_MM/2])
    return jar

def create_callus_mesh(top_mask, side_mask, px_per_mm, height_mm):
    """
    Reconstruye volumen 3D del callus combinando TOP y SIDE
    top_mask: máscara 2D de la vista superior (bool)
    side_mask: máscara 2D lateral del frasco (bool)
    px_per_mm: conversión pixeles → mm
    height_mm: altura real del frasco/célula
    """
    top_coords = np.argwhere(top_mask)  # indices de píxeles activos
    if len(top_coords) < 3:
        return None

    h_side, w_side = side_mask.shape
    vertices = []

    # Para cada píxel activo en TOP, calcular altura desde SIDE mask
    for y, x in top_coords:
        # Altura de SIDE: contar píxeles activos en columna x
        col_height_px = np.sum(side_mask[:, x])
        z_mm = (col_height_px / h_side) * height_mm
        vertices.append([x / px_per_mm, y / px_per_mm, z_mm])

    vertices = np.array(vertices)
    if len(vertices) < 3:
        return None

    # Crear mesh: usar Convex Hull para un volumen simple
    try:
        mesh = trimesh.convex.convex_hull(vertices)
        mesh.visual.face_colors = [200, 80, 80, 255]  # rojo
        return mesh
    except Exception as e:
        print("Error creando mesh callus:", e)
        return None

# ------------------------------------------------------
# Función principal
# ------------------------------------------------------

def export_sample_3d(sample_key, inst_top, inst_side, frasco_mask_top, frasco_mask_side,
                     height_real_mm, px_per_mm, category_names, output_dir):
    """
    Exporta un .ply combinando frasco + callus
    """
    # Selección de célula
    cell_ids = [
        i for i in range(len(inst_top))
        if category_names[inst_top.pred_classes[i].item()] in ["callus", "potato"]
    ]
    if len(cell_ids) != 1 or height_real_mm is None:
        print(f"[3D] {sample_key}: NO exportado (geometría ambigua)")
        return

    idx = cell_ids[0]
    top_mask = inst_top.pred_masks[idx].numpy().astype(bool)
    side_mask = frasco_mask_side.astype(bool)  # usar la máscara SIDE del frasco entero

    # Crear geometrías
    jar = create_jar_mesh()  # tu función de cilindro transparente
    callus = create_callus_mesh(top_mask, side_mask, px_per_mm, height_real_mm)
    if callus is None:
        print(f"[3D] {sample_key}: error creando callus")
        return

    # Escena 3D
    scene = trimesh.Scene()
    scene.add_geometry(jar, node_name="jar")
    scene.add_geometry(callus, node_name="callus")

    out_path = os.path.join(output_dir, f"{sample_key}_3d.ply")
    scene.export(out_path)
    print(f"[3D] Exportado → {out_path}")