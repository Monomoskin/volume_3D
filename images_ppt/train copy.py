import detectron2
from detectron2.engine import DefaultTrainer
from detectron2.config import get_cfg
from detectron2.data.datasets import register_coco_instances
from detectron2.model_zoo import get_config_file
import os

def setup_dataset():
    """
    Registra el dataset de COCO en el formato que Detectron2 entiende.
    """
    json_path = "annotations/coco_annotations.json"
    image_dir = "images"
    dataset_name = "celulas_frascos"
    
    # Registra el dataset con un nombre único
    register_coco_instances(dataset_name, {}, json_path, image_dir)
    print(f"Dataset '{dataset_name}' registrado.")

def train_model():
    """
    Configura y entrena el modelo de segmentación de instancias.
    """
    # 1. Configurar el modelo
    cfg = get_cfg()
    # Carga la configuración de un modelo pre-entrenado (Mask R-CNN)
    cfg.merge_from_file(get_config_file("COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"))
    
    # 2. Asignar el dataset
    cfg.DATASETS.TRAIN = ("celulas_frascos",)
    cfg.DATASETS.TEST = ()  # No usaremos un dataset de prueba en este ejemplo

    # 3. Definir el número de clases
    # Las clases son 'frasco' y 'celula'. Por lo tanto, el número de clases es 2.
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = 2

    # 4. Parámetros de entrenamiento
    # Número de imágenes que el modelo procesa a la vez. Reduce si te quedas sin memoria.
    cfg.SOLVER.IMS_PER_BATCH = 2
    # La tasa de aprendizaje. Un valor pequeño ayuda a un entrenamiento más estable.
    cfg.SOLVER.BASE_LR = 0.00025
    # El número total de pasos de entrenamiento.
    cfg.SOLVER.MAX_ITER = 300
    
    # 5. Entrenar el modelo
    os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)
    trainer = DefaultTrainer(cfg)
    trainer.resume_or_load(resume=False)
    trainer.train()
    print("Entrenamiento completado. El modelo entrenado se encuentra en la carpeta 'model/'.")
# Continúa en train.py

def train_model():
    cfg = get_cfg()
    cfg.merge_from_file(detectron2.model_zoo.get_config_file("COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"))
    
    # --- CAMBIO AQUÍ ---
    cfg.MODEL.DEVICE = "cpu"  # Le dice al modelo que use la CPU
    # --- FIN DEL CAMBIO ---
    
    cfg.DATASETS.TRAIN = ("celulas_frascos",)
    ...


if __name__ == "__main__":
    setup_dataset()
    train_model()