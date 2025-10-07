import os
from detectron2.engine import DefaultTrainer
from detectron2.config import get_cfg
from detectron2.data.datasets import register_coco_instances
from detectron2.model_zoo import get_config_file

# --- 1. Dataset Registration ---
# This function registers your dataset with Detectron2.
# Using os.path.join for better path handling.
def setup_dataset():
    # Make sure these paths are correct relative to where you run the script.
    json_path = os.path.join("annotations", "coco_annotations.json")
    image_dir = "images"
    dataset_name = "celulas_frascos"

    # Register the dataset.
    register_coco_instances(dataset_name, {}, json_path, image_dir)
    print(f"Dataset '{dataset_name}' successfully registered.")

# --- 2. Model Training ---
def train_model():
    cfg = get_cfg()
    # Use a pre-trained model and merge its configuration.
    cfg.merge_from_file(get_config_file("COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"))

    # Set device to CPU.
    cfg.MODEL.DEVICE = "cpu"

    # Configure the dataset for training.
    cfg.DATASETS.TRAIN = ("celulas_frascos",)
    cfg.DATASETS.TEST = ()  # No validation set for this example.

    # Number of classes: 'container' , 'cell' and "callus".
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = 3

    # Hyperparameters for training.
    cfg.SOLVER.IMS_PER_BATCH = 2  # A small increase for better gradient estimates.
    cfg.SOLVER.BASE_LR = 0.00025
    cfg.SOLVER.MAX_ITER = 5000  # Increased iterations for better model convergence.
    cfg.SOLVER.CHECKPOINT_PERIOD = 50  # Save model more frequently.
    cfg.SOLVER.OPTIMIZER = "AdamW"
    cfg.SOLVER.WEIGHT_DECAY = 0.0001
    
    # Output directory for checkpoints and logs.
    cfg.OUTPUT_DIR = "output_train"
    os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)

    # Initialize and start the trainer.
    trainer = DefaultTrainer(cfg)
    trainer.resume_or_load(resume=False)
    trainer.train()
    print("Training complete. Check the 'output_train/' directory for the final model.")

if __name__ == "__main__":
    setup_dataset()
    train_model()