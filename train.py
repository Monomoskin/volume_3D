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

# ==============================================================================
# 0. AUMENTACIONES (FUNCIÓN AUXILIAR)
# ==============================================================================
def get_train_augmentations(cfg):
    """Define la lista de aumentaciones a usar en el entrenamiento."""
    return [
        # 1. Transformaciones Geométricas Estándar
        T.ResizeShortestEdge(
            short_edge_length=(512, 512),
            max_size=1024,
            sample_style='choice'
        ),
        # Usamos T.RandomFlip con prob=0.5 y ambas direcciones
        T.RandomFlip(prob=0.5, horizontal=True),
        T.RandomFlip(prob=0.5, vertical=True), 
        
        # 2. AUMENTACIÓN DE COLOR/TEXTURA
        T.RandomBrightness(0.6, 1.4),   
        T.RandomSaturation(0.6, 1.4),  
        T.RandomContrast(0.6, 1.4),     
        
        # 3. Rotación
        T.RandomRotation(angle=[-30, 30], expand=False, center=None, sample_style='choice'),
        
        # 4. Recorte Aleatorio
        T.RandomCrop('relative_range', (0.7, 1.0))
    ]

# ==============================================================================
# 1. CUSTOM TRAINER
#    Sobreescribe build_mapper para inyectar los aumentos sin tocar build_train_loader.
# ==============================================================================
class CustomTrainer(DefaultTrainer):
    @classmethod
    def build_mapper(cls, cfg, is_train=True):
        if not is_train:
            return super().build_mapper(cfg, is_train)
            
        # Retorna el mapper con las transformaciones definidas en la función auxiliar
        return DatasetMapper(
            cfg, 
            is_train=True, 
            augmentations=get_train_augmentations(cfg)
        )

# ==============================================================================
# 2. REGISTRO DEL DATASET COCO
# ==============================================================================
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


# ==============================================================================
# 3. ENTRENAMIENTO DEL MODELO
# ==============================================================================
def train_model(metadata):
    cfg = get_cfg()
    cfg.merge_from_file(get_config_file("COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"))

    # --- CONFIGURACIÓN DE DISPOSITIVO Y ESTABILIDAD ---
    cfg.MODEL.DEVICE = "cpu"
    print("Usando CPU para el entrenamiento. El tiempo de ejecución será considerable.")
    
    # SOLUCIÓN CRÍTICA: Desactivar workers para estabilidad en macOS (necesario incluso en CPU a veces)
    cfg.DATALOADER.NUM_WORKERS = 0 

    # --- PARÁMETROS DEL MODELO ---
    cfg.DATASETS.TRAIN = (metadata.name,)
    cfg.DATASETS.TEST = ()  
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = len(metadata.thing_classes)

    # --- PARÁMETROS CRUCIALES DE ROBUSTEZ ---
    cfg.SOLVER.BASE_LR = 0.0001 
    cfg.SOLVER.MAX_ITER = 10000 
    cfg.SOLVER.OPTIMIZER = "AdamW"
    cfg.SOLVER.STEPS = [] 
    
    # IMS_PER_BATCH: Se puede aumentar en CPU (de 2 a 4). 
    # Mantenemos 4, pero si la CPU tiene poca RAM, habría que bajarlo a 2.
    cfg.SOLVER.IMS_PER_BATCH = 4  
    
    cfg.SOLVER.WEIGHT_DECAY = 0.0001
    cfg.SOLVER.CHECKPOINT_PERIOD = 300
    
    cfg.OUTPUT_DIR = "output_train"
    os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)
    # --- REANUDAR DESDE CHECKPOINT SI EXISTE ---
    last_checkpoint = os.path.join(cfg.OUTPUT_DIR, "last_checkpoint")
    resume_flag = False

    if os.path.exists(last_checkpoint):
        last_model = open(last_checkpoint, "r").read().strip()
        cfg.MODEL.WEIGHTS = last_model
        resume_flag = True
        print(f"🔁 Reanudando desde checkpoint: {last_model}")
    else:
        cfg.MODEL.WEIGHTS = (
            "detectron2://COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x/137849600/model_final_f10217.pkl"
        )
        print("🚀 No se encontró checkpoint previo. Entrenamiento desde cero.")

    print("\nEntrenamiento iniciado con robustez mejorada para vistas Top/Side...")
    trainer = CustomTrainer(cfg)
    trainer.resume_or_load(resume=resume_flag)
    trainer.train()
    print("Entrenamiento completado.")

    # Inicializar y comenzar el entrenamiento
    # trainer = CustomTrainer(cfg)
    # trainer.resume_or_load(resume=False)
    # print("\nEntrenamiento iniciado con robustez mejorada para vistas Top/Side...")
    # trainer.train()
    # print("Entrenamiento completado. El modelo es ahora mucho más robusto.")

if __name__ == "__main__":
    metadata = setup_dataset()
    train_model(metadata)