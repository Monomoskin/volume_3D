import os
import torch
from detectron2.engine import DefaultTrainer
from detectron2.config import get_cfg
from detectron2.data.datasets import register_coco_instances
from detectron2.model_zoo import get_config_file
from detectron2.data import DatasetMapper, build_detection_train_loader
from detectron2.data import transforms as T # Importa las transformaciones

# --- 1. Custom Trainer for Robustness ---
class CustomTrainer(DefaultTrainer):
    @classmethod
    def build_train_loader(cls, cfg):
        # Mapper with AGGRESSIVE DATA AUGMENTATION (KEY TO FIX CALLUS DETECTION)
        mapper = DatasetMapper(
            cfg, 
            is_train=True, 
            augmentations=[
                # 1. Standard Geometric Transformations
                T.ResizeShortestEdge(
                    short_edge_length=(512, 512),
                    max_size=1024,
                    sample_style='choice'
                ),
                T.RandomFlip(prob=0.5, horizontal=True, vertical=False),
                
                # 2. COLOR & TEXTURE AUGMENTATION (Forces the model to ignore color)
                # This makes yellow cells look dark and dark calluses look bright.
                T.RandomBrightness(0.6, 1.4),   # Brightness variation
                T.RandomSaturation(0.6, 1.4),  # Color intensity variation
                T.RandomContrast(0.6, 1.4),     # Contrast variation
                
                # 3. Rotation (Helps generalize shape)
                T.RandomRotation(angle=[-15, 15], expand=False, center=None, sample_style='choice')
            ]
        )
        return build_detection_train_loader(cfg, mapper=mapper)


# --- 2. Dataset Registration ---
def setup_dataset():
    json_path = os.path.join("annotations", "coco_annotations.json")
    image_dir = "images"
    dataset_name = "celulas_frascos"

    register_coco_instances(dataset_name, {}, json_path, image_dir)
    print(f"Dataset '{dataset_name}' successfully registered.")


# --- 3. Model Training ---
def train_model():
    cfg = get_cfg()
    cfg.merge_from_file(get_config_file("COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"))

    cfg.MODEL.DEVICE = "cpu"
    cfg.DATASETS.TRAIN = ("celulas_frascos",)
    cfg.DATASETS.TEST = ()  
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = 3

    # Hyperparameters for training.
    cfg.SOLVER.IMS_PER_BATCH = 2  
    cfg.SOLVER.BASE_LR = 0.00025
    
    # INCREASED ITERATIONS are necessary because the model must learn from the vastly
    # increased variability introduced by the new augmentations.
    cfg.SOLVER.MAX_ITER = 1000 
    
    cfg.SOLVER.CHECKPOINT_PERIOD = 200
    cfg.SOLVER.OPTIMIZER = "AdamW"
    cfg.SOLVER.WEIGHT_DECAY = 0.0001
    
    cfg.OUTPUT_DIR = "output_train"
    os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)

    # Initialize and start the trainer using the CUSTOM TRAINER
    trainer = CustomTrainer(cfg)
    trainer.resume_or_load(resume=False)
    trainer.train()
    print("Training complete. The model is now much more robust to color/texture changes.")

if __name__ == "__main__":
    setup_dataset()
    train_model()