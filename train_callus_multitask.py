import os
import json
import torch
import torch.nn as nn
import torch.nn.functional as F
import cv2
from detectron2.config import get_cfg
from detectron2.engine import DefaultTrainer, DefaultPredictor
from detectron2.data import (
    DatasetMapper,
    build_detection_train_loader,
    MetadataCatalog
)
from detectron2.data.datasets import register_coco_instances
from detectron2.data import transforms as T
from detectron2.structures import BoxMode, Instances, BitMasks
from detectron2.model_zoo import get_config_file
from detectron2.modeling import ROI_HEADS_REGISTRY
from detectron2.modeling.roi_heads import StandardROIHeads

# =====================================================
# 1️⃣ LABEL MAPS (CONSISTENTES CON TU DATASET)
# =====================================================
VOL_MAP = {"small": 0, "medium": 1, "large": 2}
QUAL_MAP = {"good": 0, "regular": 1, "poor": 2}
STAGE_MAP = {"early": 0, "middle": 1, "advanced": 2}
SPECIES_MAP = {"Phyllostachys edulis": 0, "Other": 1}

INV_VOL_MAP = {v: k for k, v in VOL_MAP.items()}
INV_QUAL_MAP = {v: k for k, v in QUAL_MAP.items()}
INV_STAGE_MAP = {v: k for k, v in STAGE_MAP.items()}
INV_SPECIES_MAP = {v: k for k, v in SPECIES_MAP.items()}

# =====================================================
# 2️⃣ DATASET
# =====================================================
def setup_dataset():
    dataset_name = "callus_dataset"
    json_path = "annotations/coco_annotations.json"
    image_dir = "images"

    try:
        register_coco_instances(dataset_name, {}, json_path, image_dir)
    except AssertionError:
        pass

    with open(json_path) as f:
        coco = json.load(f)

    MetadataCatalog.get(dataset_name).thing_classes = [
        c["name"] for c in coco["categories"]
    ]

    return dataset_name

# =====================================================
# 3️⃣ AUGMENTATIONS
# =====================================================
def get_augmentations():
    return [
        T.ResizeShortestEdge((512, 512), 1024),
        T.RandomFlip(horizontal=True, prob=0.5),
        T.RandomBrightness(0.8, 1.2),
        T.RandomContrast(0.8, 1.2),
        T.RandomSaturation(0.8, 1.2),
    ]

# =====================================================
# 4️⃣ DATASET MAPPER (LEE attributes)
# =====================================================
class CallusDatasetMapper(DatasetMapper):
    def __init__(self, cfg, is_train=True):
        super().__init__(cfg, is_train, augmentations=get_augmentations())

    def __call__(self, dataset_dict):
        dataset_dict = dataset_dict.copy()
        image = self._read_image(dataset_dict["file_name"])
        aug_input = T.AugInput(image)
        transforms = self.augmentations(aug_input)
        image = aug_input.image

        dataset_dict["image"] = torch.as_tensor(image.transpose(2, 0, 1))

        if "annotations" not in dataset_dict:
            return dataset_dict

        instances = Instances(image.shape[:2])

        boxes, classes, masks = [], [], []
        volumes, qualities, species, stages = [], [], [], []

        for ann in dataset_dict["annotations"]:
            boxes.append(ann["bbox"])
            classes.append(ann["category_id"])
            masks.append(ann["segmentation"])

            attr = ann["attributes"]
            volumes.append(VOL_MAP[attr["Volume"]])
            qualities.append(QUAL_MAP[attr["Callus Quality"]])
            species.append(SPECIES_MAP[attr["Bamboo Species"]])
            stages.append(STAGE_MAP[attr["Embryogenic Stage"]])

        instances.gt_boxes = BoxMode.convert(
            torch.tensor(boxes),
            BoxMode.XYWH_ABS,
            BoxMode.XYXY_ABS
        )
        instances.gt_classes = torch.tensor(classes)
        instances.gt_volume = torch.tensor(volumes)
        instances.gt_quality = torch.tensor(qualities)
        instances.gt_species = torch.tensor(species)
        instances.gt_stage = torch.tensor(stages)

        instances.gt_masks = BitMasks.from_polygon_masks(
            masks, image.shape[0], image.shape[1]
        )

        dataset_dict["instances"] = instances
        return dataset_dict

# =====================================================
# 5️⃣ ROI HEADS MULTITAREA
# =====================================================
@ROI_HEADS_REGISTRY.register()
class CallusROIHeads(StandardROIHeads):
    def __init__(self, cfg, input_shape):
        super().__init__(cfg, input_shape)

        dim = self.box_head.output_size
        self.fc_volume = nn.Linear(dim, 3)
        self.fc_quality = nn.Linear(dim, 3)
        self.fc_species = nn.Linear(dim, 2)
        self.fc_stage = nn.Linear(dim, 3)

    def forward(self, images, features, proposals, targets=None):
        outputs = super().forward(images, features, proposals, targets)

        if self.training:
            box_features = self.box_head(
                self.box_pooler(features, [p.proposal_boxes for p in proposals])
            )

            gt_volume = torch.cat([p.gt_volume for p in proposals])
            gt_quality = torch.cat([p.gt_quality for p in proposals])
            gt_species = torch.cat([p.gt_species for p in proposals])
            gt_stage = torch.cat([p.gt_stage for p in proposals])

            outputs["loss_volume"] = F.cross_entropy(self.fc_volume(box_features), gt_volume)
            outputs["loss_quality"] = F.cross_entropy(self.fc_quality(box_features), gt_quality)
            outputs["loss_species"] = F.cross_entropy(self.fc_species(box_features), gt_species)
            outputs["loss_stage"] = F.cross_entropy(self.fc_stage(box_features), gt_stage)

            return outputs

        else:
            instances = outputs[0]["instances"]

            box_features = self.box_head(
                self.box_pooler(features, [instances.pred_boxes])
            )

            instances.pred_volume = self.fc_volume(box_features).argmax(dim=1)
            instances.pred_quality = self.fc_quality(box_features).argmax(dim=1)
            instances.pred_species = self.fc_species(box_features).argmax(dim=1)
            instances.pred_stage = self.fc_stage(box_features).argmax(dim=1)

            return [{"instances": instances}]

# =====================================================
# 6️⃣ TRAINER
# =====================================================
class CallusTrainer(DefaultTrainer):
    @classmethod
    def build_train_loader(cls, cfg):
        return build_detection_train_loader(
            cfg, mapper=CallusDatasetMapper(cfg, True)
        )

# =====================================================
# 7️⃣ TRAIN
# =====================================================
# =====================================================
# 7️⃣ TRAIN CON CHECKPOINT AUTOMÁTICO
# =====================================================
def train():
    dataset_name = setup_dataset()

    cfg = get_cfg()
    cfg.merge_from_file(
        get_config_file("COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml")
    )

    cfg.MODEL.DEVICE = "cpu"  # cambia a cuda si puedes
    cfg.MODEL.ROI_HEADS.NAME = "CallusROIHeads"
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = 1

    cfg.DATASETS.TRAIN = (dataset_name,)
    cfg.DATASETS.TEST = ()

    cfg.SOLVER.IMS_PER_BATCH = 2
    cfg.SOLVER.BASE_LR = 1e-4
    cfg.SOLVER.MAX_ITER = 10000
    cfg.SOLVER.STEPS = []
    
    # 🔹 Guardar checkpoint cada 400 iteraciones
    cfg.SOLVER.CHECKPOINT_PERIOD = 400

    cfg.OUTPUT_DIR = "./output_callus"
    os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)

    # --- Revisar si hay checkpoint previo ---
    last_checkpoint_path = os.path.join(cfg.OUTPUT_DIR, "last_checkpoint")
    resume_flag = False

    if os.path.exists(last_checkpoint_path):
        with open(last_checkpoint_path, "r") as f:
            last_model = f.read().strip()
        cfg.MODEL.WEIGHTS = last_model
        resume_flag = True
        print(f"🔁 Reanudando desde checkpoint: {last_model}")
    else:
        cfg.MODEL.WEIGHTS = (
            "detectron2://COCO-InstanceSegmentation/"
            "mask_rcnn_R_50_FPN_3x/137849600/model_final_f10217.pkl"
        )
        print("🚀 No se encontró checkpoint previo. Entrenamiento desde cero.")

    trainer = CallusTrainer(cfg)
    trainer.resume_or_load(resume=resume_flag)
    trainer.train()

# =====================================================
if __name__ == "__main__":
    train()
