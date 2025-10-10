import os
import torch
from detectron2.engine import DefaultTrainer
from detectron2.config import get_cfg
from detectron2.data.datasets import register_coco_instances
from detectron2.model_zoo import get_config_file
from detectron2.data import DatasetMapper, build_detection_train_loader
from detectron2.data import transforms as T
from detectron2.data import MetadataCatalog 
import json # Necesario para obtener las clases dinámicamente

# -----------------------------
# 1. Custom Trainer con AUMENTACIÓN AGRESIVA (Clave para la Robustez)
# -----------------------------
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
                T.RandomFlip(prob=0.5, horizontal=True, vertical=True), # Agregamos Flip Vertical para vista Top
                
                # 2. AUMENTACIÓN DE COLOR/TEXTURA (Fuerza al modelo a ignorar el fondo)
                T.RandomBrightness(0.6, 1.4),   
                T.RandomSaturation(0.6, 1.4),  
                T.RandomContrast(0.6, 1.4),     
                
                # 3. Rotación (Ayuda a generalizar la forma en ambas vistas)
                T.RandomRotation(angle=[-30, 30], expand=False, center=None, sample_style='choice'),
                
                # 4. Recorte Aleatorio (Fuerza al modelo a detectar objetos parcialmente visibles, útil para la vista SIDE)
                T.RandomCrop('relative_range', (0.7, 1.0))
            ]
        )
        return build_detection_train_loader(cfg, mapper=mapper)


# -----------------------------
# 2. Registro del dataset COCO (Asegurando Metadatos)
# -----------------------------
def setup_dataset():
    json_path = os.path.join("annotations", "coco_annotations.json")
    image_dir = "images"
    dataset_name = "celulas_frascos"

    try:
        register_coco_instances(dataset_name, {}, json_path, image_dir)
    except AssertionError:
        pass
    
    # Obtener categorías reales del JSON para configurar NUM_CLASSES
    with open(json_path, 'r') as f:
        coco_data = json.load(f)
    category_names = [cat['name'] for cat in coco_data['categories']]
    MetadataCatalog.get(dataset_name).thing_classes = category_names
    
    print(f"Dataset '{dataset_name}' registrado.")
    return MetadataCatalog.get(dataset_name)


# -----------------------------
# 3. Entrenamiento del modelo
# -----------------------------
def train_model(metadata):
    cfg = get_cfg()
    cfg.merge_from_file(get_config_file("COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"))

    cfg.MODEL.DEVICE = "cpu"
    print("Usando CPU para el entrenamiento. El tiempo de ejecución será considerable.")
    
    # Dataset y número de clases (dinámico, incluye 'container', 'cell', 'cell_profile', etc.)
    cfg.DATASETS.TRAIN = (metadata.name,)
    cfg.DATASETS.TEST = ()  
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = len(metadata.thing_classes)

    # --- PARÁMETROS CRUCIALES DE ROBUSTEZ ---
    
    # 1. Tasa de Aprendizaje: Más baja para estabilidad con la nueva complejidad de datos.
    cfg.SOLVER.BASE_LR = 0.0001 
    
    # 2. Máximo de Iteraciones: Aumentado para compensar el LR bajo y las transformaciones agresivas.
    cfg.SOLVER.MAX_ITER = 10000 # Aumentado de 1000 a 2500
    
    # 3. Optimización
    cfg.SOLVER.OPTIMIZER = "AdamW"
    cfg.SOLVER.STEPS = [] # Deshabilita la caída de LR automática
    
    # Otros parámetros
    cfg.SOLVER.IMS_PER_BATCH = 2  
    cfg.SOLVER.WEIGHT_DECAY = 0.0001
    cfg.SOLVER.CHECKPOINT_PERIOD = 1000
    
    cfg.OUTPUT_DIR = "output_train"
    os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)
     
    # Inicializar y comenzar el entrenamiento
    trainer = CustomTrainer(cfg)
    trainer.resume_or_load(resume=False)
    print("\nEntrenamiento iniciado con robustez mejorada para vistas Top/Side...")
    trainer.train()
    print("Entrenamiento completado. El modelo es ahora mucho más robusto.")

if __name__ == "__main__":
    metadata = setup_dataset()
    train_model(metadata)