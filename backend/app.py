from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import pandas as pd
import os
from datetime import datetime
import os.path
import uuid # Módulo para generar IDs únicos si fuera necesario (aunque ya usamos timestamp)

# Importamos la función de predicción. 
# Esto también inicializa el modelo Detectron2 (si predict.py está bien configurado).
try:
    from predict import predict_volume_and_save_images 
except ImportError:
    print("ERROR: No se pudo importar 'predict.py'. Usando función mock de seguridad.")
    # Función de seguridad (mock) si falla la importación de predict.py
    def predict_volume_and_save_images(uploaded_top_path, uploaded_side_path, output_dir, cell_name):
        return 0.0, "Error en predicción", "Error en predicción"


app = Flask(__name__)
# Configuración CORS: permite la comunicación con el frontend de React
CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}})

# --- 1. CONFIGURACIÓN DE RUTAS ---
# BASE_DIR es la carpeta 'backend'
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) 
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploaded_images')
PREDICTED_FOLDER = os.path.join(BASE_DIR, 'predicted_images')
# El archivo de log se guarda en la carpeta principal del proyecto
LOG_FILE = os.path.join(os.path.dirname(BASE_DIR), 'data_log.csv') 

# Asegurar que las carpetas existan
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PREDICTED_FOLDER, exist_ok=True)


# --- 2. FUNCIONES DE UTILIDAD ---

def load_data_log():
    """Carga o crea el archivo de registro (CSV)."""
    if os.path.exists(LOG_FILE):
        return pd.read_csv(LOG_FILE)
    else:
        # Definir la estructura del DataFrame
        return pd.DataFrame(columns=['Cell Name', 'Measurement ID', 'Upload Date', 'Estimated Volume (mL)', 'Image Location (Top)', 'Image Location (Side)'])


# --- 3. ENDPOINTS DE SERVICIO Y LÓGICA ---

@app.route('/api/predicted_images/<path:filename>')
def serve_predicted_image(filename):
    """
    Endpoint para servir imágenes estáticas desde la carpeta 'predicted_images'.
    Necesario para que el navegador pueda acceder a las imágenes generadas por Detectron2.
    """
    # El 'filename' debe contener la estructura de carpetas (Ej: 2025-10-13/CelulaA/CelulaA_TOP_predicted.jpg)
    return send_from_directory(PREDICTED_FOLDER, filename)


@app.route('/api/analyze', methods=['POST'])
def analyze_cell():
    """
    Endpoint principal para recibir imágenes, procesar y registrar datos.
    """
    # 1. Validar la solicitud
    if 'cell_name' not in request.form or 'image_top' not in request.files or 'image_side' not in request.files:
        return jsonify({"error": "Faltan datos requeridos (cell_name, image_top, o image_side)."}), 400

    cell_name = request.form['cell_name']
    file_top = request.files['image_top']
    file_side = request.files['image_side']
    
    # Datos temporales para nombres y organización
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    timestamp = now.strftime("%Y%m%d%H%M%S")
    measurement_id = f"{cell_name}-{timestamp}"
    
    # 2. Definir Rutas de Guardado (Estructura: Fecha/Célula)
    
    # Rutas para archivos subidos (originales)
    day_upload_dir = os.path.join(UPLOAD_FOLDER, date_str)
    cell_upload_dir = os.path.join(day_upload_dir, cell_name) 
    os.makedirs(cell_upload_dir, exist_ok=True) # Crea carpetas si no existen

    # Rutas para archivos predichos (resultados)
    day_predicted_dir = os.path.join(PREDICTED_FOLDER, date_str)
    cell_predicted_dir = os.path.join(day_predicted_dir, cell_name)
    os.makedirs(cell_predicted_dir, exist_ok=True) # Aseguramos la existencia de la carpeta de resultados

    # Nomenclatura del archivo con timestamp para unicidad
    filename_top = f"{cell_name}_top_{timestamp}{os.path.splitext(file_top.filename)[1]}"
    filename_side = f"{cell_name}_side_{timestamp}{os.path.splitext(file_side.filename)[1]}"
    
    path_top = os.path.join(cell_upload_dir, filename_top)
    path_side = os.path.join(cell_upload_dir, filename_side)
    
    # 3. Guardar Imágenes Originales
    file_top.save(path_top)
    file_side.save(path_side)

    # 4. Ejecutar Lógica de Estimación (Llamada a predict.py)
    try:
        estimated_volume, predicted_top_path, predicted_side_path = predict_volume_and_save_images(
            path_top, 
            path_side, 
            cell_predicted_dir, # Carpeta donde guardar las imágenes resultantes
            cell_name
        )
    except Exception as e:
        print(f"Error grave durante la predicción para {cell_name}: {e}")
        return jsonify({"error": f"Error interno en el modelo de predicción: {str(e)}"}), 500

    # 5. Registrar en el archivo CSV/Excel
    df = load_data_log()
    new_row = {
        'Cell Name': cell_name,
        'Measurement ID': measurement_id,
        'Upload Date': now.strftime("%Y-%m-%d %H:%M:%S"),
        'Estimated Volume (mL)': estimated_volume,
        'Image Location (Top)': path_top, 
        'Image Location (Side)': path_side, 
    }
    
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_csv(LOG_FILE, index=False)


    # 6. Devolver la respuesta al Frontend
    
    # Construir las rutas URL relativas para el endpoint 'serve_predicted_image'
    top_url_path = os.path.join(date_str, cell_name, os.path.basename(predicted_top_path))
    side_url_path = os.path.join(date_str, cell_name, os.path.basename(predicted_side_path))

    return jsonify({
        "status": "success",
        "measurement_id": measurement_id,
        "cell_name": cell_name,
        "estimated_volume": estimated_volume,
        # Devolvemos las URLs completas para que React pueda usarlas directamente
        "predicted_image_top_url": f"http://localhost:5000/api/predicted_images/{top_url_path}", 
        "predicted_image_side_url": f"http://localhost:5000/api/predicted_images/{side_url_path}",
    }), 200

# --- 4. EJECUCIÓN DEL SERVIDOR ---

if __name__ == '__main__':
    print(f"Log de datos guardado en: {LOG_FILE}")
    print("Iniciando servidor Flask...")
    # debug=True es útil durante el desarrollo, pero debe ser False en un entorno de producción
    app.run(debug=True, port=5000)