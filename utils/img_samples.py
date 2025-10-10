import os
from pathlib import Path

# Carpeta donde están las imágenes
folder_path = "img"

# Obtener todos los archivos jpg/jpeg ordenados por fecha de creación ascendente
files = sorted(
    (f for f in Path(folder_path).iterdir() if f.suffix.lower() in ['.jpg', '.jpeg']),
    key=lambda x: x.stat().st_ctime
)

# Verificar que la cantidad total es par
if len(files) % 2 != 0:
    print("Advertencia: número impar de archivos. Se espera par para Top y Side.")
    
# Renombrar las imágenes
for i in range(0, len(files), 2):
    sample_num = i // 2 + 1
    top_file = files[i]
    side_file = files[i + 1]
    
    new_top_name = f"Sample_{sample_num:03d}_TOP{top_file.suffix.lower()}"
    new_side_name = f"Sample_{sample_num:03d}_SIDE{side_file.suffix.lower()}"
    
    new_top_path = Path(folder_path) / new_top_name
    new_side_path = Path(folder_path) / new_side_name
    
    # Renombrar archivos
    os.rename(top_file, new_top_path)
    os.rename(side_file, new_side_path)
    
    print(f"Renombrado: {top_file.name} -> {new_top_name}")
    print(f"Renombrado: {side_file.name} -> {new_side_name}")

print("Renombrado completado.")
