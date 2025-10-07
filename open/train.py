import os
from detectron2.engine import DefaultTrainer
from detectron2.config import get_cfg
from detectron2.data.datasets import register_coco_instances
from detectron2.model_zoo import get_config_file
import torch

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
    Configura y entrena el modelo de segmentación de instancias optimizado para pequeñas células
    """
    cfg = get_cfg()
    # Modelo preentrenado Mask R-CNN R101-FPN
    cfg.merge_from_file(get_config_file("COCO-InstanceSegmentation/mask_rcnn_R_101_FPN_3x.yaml"))
    
    # --- Dispositivo ---
    if torch.backends.mps.is_available():
        cfg.MODEL.DEVICE = "mps"
        print("Usando GPU MPS")
    else:
        cfg.MODEL.DEVICE = "cpu"
        print("Usando CPU")

    # --- Dataset ---
    cfg.DATASETS.TRAIN = ("celulas_frascos",)
    cfg.DATASETS.TEST = ()  # no hay validación por ahora

    # --- Número de clases ---
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = 2  # 'container' y 'cell'

    # --- Hiperparámetros ---
    cfg.SOLVER.IMS_PER_BATCH = 2  # ajusta según RAM/VRAM
    cfg.SOLVER.BASE_LR = 0.00025
    cfg.SOLVER.MAX_ITER = 3000  # más iteraciones para mejor convergencia
    cfg.SOLVER.STEPS = []  # no decrecer lr automáticamente

    # Ajustes para pequeñas células
    cfg.MODEL.ROI_HEADS.BATCH_SIZE_PER_IMAGE = 128
    cfg.MODEL.ROI_HEADS.POSITIVE_FRACTION = 0.7
    cfg.MODEL.PIXEL_MEAN = [123.675, 116.28, 103.53]
    cfg.MODEL.PIXEL_STD = [58.395, 57.12, 57.375]

    # --- Carpeta de salida ---
    cfg.OUTPUT_DIR = "model"
    os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)

    # --- Entrenamiento ---
    trainer = DefaultTrainer(cfg)
    trainer.resume_or_load(resume=False)
    print("Entrenamiento iniciado...")
    trainer.train()
    print("Entrenamiento completado. Revisa la carpeta 'model/'")

if __name__ == "__main__":
    setup_dataset()
    train_model()
