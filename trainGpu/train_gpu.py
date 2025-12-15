import os
import torch
from detectron2.engine import DefaultTrainer
from detectron2.config import get_cfg
from detectron2.data.datasets import register_coco_instances
from detectron2.model_zoo import get_config_file
from detectron2.data import DatasetMapper, build_detection_train_loader
from detectron2.data import transforms as T
from detectron2.data import MetadataCatalog 
import json 

# Definir dispositivo: usar "mps" para Apple Silicon M1/M2, fallback a "cpu"
device = "mps" if torch.backends.mps.is_available() else "cpu"
print(f"Usando dispositivo: {device}")

class CustomTrainer(DefaultTrainer):
    @classmethod
    def build_train_loader(cls, cfg):
        mapper = DatasetMapper(
            cfg, 
            is_train=True, 
            augmentations=[
                # 1. Transformaciones Geométricas Estándar
                T.ResizeShortestEdge(
                    short_edge_length=(512, 512),
                    max_size=1024,
                    sample_style='choice'
                ),
                # === CÓDIGO CORREGIDO ===
                T.RandomFlip(prob=0.5, horizontal=True, vertical=False), # Flip Horizontal (TOP/SIDE)
                T.RandomFlip(prob=0.5, horizontal=False, vertical=True), # Flip Vertical (Útil para TOP)
                # ========================
                
                # 2. AUMENTACIÓN DE COLOR/TEXTURA
                T.RandomBrightness(0.6, 1.4),   
                T.RandomSaturation(0.6, 1.4),  
                T.RandomContrast(0.6, 1.4),     
                
                # 3. Rotación
                T.RandomRotation(angle=[-30, 30], expand=False, sample_style='choice'),
                
                # 4. Recorte Aleatorio
                T.RandomCrop('relative_range', (0.7, 1.0))
            ]
        )
        return build_detection_train_loader(cfg, mapper=mapper)
def setup_dataset():
    json_path = os.path.join("annotations", "coco_annotations.json")
    image_dir = "images"
    dataset_name = "celulas_frascos"
    
    try:
        register_coco_instances(dataset_name, {}, json_path, image_dir)
    except AssertionError:
        pass
    
    with open(json_path, 'r') as f:
        coco_data = json.load(f)
    category_names = [cat['name'] for cat in coco_data['categories']]
    MetadataCatalog.get(dataset_name).thing_classes = category_names
    
    print(f"Dataset '{dataset_name}' registrado.")
    return MetadataCatalog.get(dataset_name)

def train_model(metadata):
    cfg = get_cfg()
    cfg.merge_from_file(get_config_file("COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"))

    cfg.MODEL.DEVICE = device  # Aquí usar "mps" o "cpu"
    
    cfg.DATASETS.TRAIN = (metadata.name,)
    cfg.DATASETS.TEST = ()  
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = len(metadata.thing_classes)

    cfg.SOLVER.BASE_LR = 0.0001 
    cfg.SOLVER.MAX_ITER = 10000
    cfg.SOLVER.OPTIMIZER = "AdamW"
    cfg.SOLVER.STEPS = [] 
    cfg.SOLVER.IMS_PER_BATCH = 1  
    cfg.SOLVER.WEIGHT_DECAY = 0.0001
    cfg.SOLVER.CHECKPOINT_PERIOD = 1000

    # ==========================================================
    # SOLUCIÓN: Desactivar workers para evitar el error 'shapely' en subprocesos
    cfg.DATALOADER.NUM_WORKERS = 0  # <--- ¡ESTA ES LA LÍNEA CLAVE!
    # ==========================================================


    cfg.OUTPUT_DIR = "output_train"
    os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)
     
    trainer = CustomTrainer(cfg)
    trainer.resume_or_load(resume=False)
    print("\nEntrenamiento iniciado...")
    trainer.train()
    print("Entrenamiento completado.")

if __name__ == "__main__":
    metadata = setup_dataset()
    train_model(metadata)
