import os
import json
import torch
import torch.nn as nn
import torch.nn.functional as F

from detectron2.config import get_cfg
from detectron2.engine import DefaultTrainer
from detectron2.model_zoo import get_config_file
from detectron2.modeling import ROI_HEADS_REGISTRY
from detectron2.modeling.roi_heads import StandardROIHeads

from detectron2.data import (
    DatasetMapper,
    build_detection_train_loader,
    MetadataCatalog,
)
from detectron2.data.datasets import register_coco_instances
from detectron2.data import transforms as T
from detectron2.data.detection_utils import read_image

from detectron2.structures import (
    Boxes,
    Instances,
    BitMasks,
    BoxMode,
)

QUAL_MAP = {
    "good": 0,
    "regular": 1,
    "poor": 2,
}

STAGE_MAP = {
    "early": 0,
    "middle": 1,
    "advanced": 2,
}

SPECIES_MAP = {
    "Phyllostachys edulis": 0,
    "Other": 1,
}

INV_QUAL_MAP = {v: k for k, v in QUAL_MAP.items()}
INV_STAGE_MAP = {v: k for k, v in STAGE_MAP.items()}
INV_SPECIES_MAP = {v: k for k, v in SPECIES_MAP.items()}

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

    print(f"Dataset '{dataset_name}' registrado.")
    return dataset_name

def get_train_augmentations(cfg):
    return [
        T.ResizeShortestEdge(
            short_edge_length=(512, 512),
            max_size=1024,
            sample_style="choice",
        ),
        T.RandomFlip(prob=0.5, horizontal=True),  # flip horizontal
        T.RandomFlip(prob=0.5, horizontal=True), # flip vertical
        T.RandomBrightness(0.6, 1.4),
        T.RandomContrast(0.6, 1.4),
        T.RandomSaturation(0.6, 1.4),
        T.RandomRotation(angle=[-30, 30]),
        T.RandomCrop("relative_range", (0.7, 1.0)),
    ]

class CallusDatasetMapper(DatasetMapper):
    def __init__(self, cfg, is_train=True):
        super().__init__(
            cfg,
            is_train,
            augmentations=get_train_augmentations(cfg),
        )

    def __call__(self, dataset_dict):
        dataset_dict = dataset_dict.copy()

        image = read_image(
            dataset_dict["file_name"],
            format=self.image_format,
        )

        aug_input = T.AugInput(image)
        self.augmentations(aug_input)
        image = aug_input.image

        dataset_dict["image"] = torch.as_tensor(
            image.transpose(2, 0, 1),
            dtype=torch.float32,
        )

        if "annotations" not in dataset_dict or len(dataset_dict["annotations"]) == 0:
            return None

        instances = Instances(image.shape[:2])

        boxes, classes, masks = [], [], []
        qualities, species, stages = [], [], []

        for ann in dataset_dict["annotations"]:
            boxes.append(ann["bbox"])
            classes.append(ann["category_id"])
            masks.append(ann["segmentation"])

            attr = ann.get("attributes", {})

            qualities.append(
                QUAL_MAP.get(attr.get("quality", "good"), 0)
            )
            species.append(
                SPECIES_MAP.get(
                    attr.get("species", "Phyllostachys edulis"), 0
                )
            )
            stages.append(
                STAGE_MAP.get(attr.get("stage", "early"), 0)
            )

        instances.gt_boxes = Boxes(
            BoxMode.convert(
                torch.tensor(boxes, dtype=torch.float32),
                BoxMode.XYWH_ABS,
                BoxMode.XYXY_ABS,
            )
        )

        instances.gt_classes = torch.tensor(classes, dtype=torch.int64)
        instances.gt_quality = torch.tensor(qualities, dtype=torch.int64)
        instances.gt_species = torch.tensor(species, dtype=torch.int64)
        instances.gt_stage = torch.tensor(stages, dtype=torch.int64)

        instances.gt_masks = BitMasks.from_polygon_masks(
            masks,
            image.shape[0],
            image.shape[1],
        )

        dataset_dict["instances"] = instances
        return dataset_dict

@ROI_HEADS_REGISTRY.register()
class CallusROIHeads(StandardROIHeads):
    def __init__(self, cfg, input_shape):
        super().__init__(cfg, input_shape)

        dim = self.box_head._output_size

        # Clasificadores biológicos
        self.fc_quality = nn.Linear(dim, 3)   # good / regular / poor
        self.fc_species = nn.Linear(dim, 2)   # moso / other
        self.fc_stage = nn.Linear(dim, 3)     # early / middle / advanced

    def forward(self, images, features, proposals, targets=None):
        # Forward estándar de Mask R-CNN
        proposals_or_instances, losses = super().forward(
            images, features, proposals, targets
        )

        # =========================
        # TRAINING
        # =========================
        if self.training:
            proposals = proposals_or_instances

            # Extraer features de las cajas
            box_features = self.box_head(
                self.box_pooler(
                    [features[f] for f in self.in_features],
                    [p.proposal_boxes for p in proposals],
                )
            )

            # Ground truth
            gt_quality = torch.cat([p.gt_quality for p in proposals], dim=0)
            gt_species = torch.cat([p.gt_species for p in proposals], dim=0)
            gt_stage = torch.cat([p.gt_stage for p in proposals], dim=0)

            # Predicciones
            pred_quality = self.fc_quality(box_features)
            pred_species = self.fc_species(box_features)
            pred_stage = self.fc_stage(box_features)

            # Losses biológicas
            losses["loss_quality"] = F.cross_entropy(pred_quality, gt_quality)
            losses["loss_species"] = F.cross_entropy(pred_species, gt_species)
            losses["loss_stage"] = F.cross_entropy(pred_stage, gt_stage)

            # Pesos (para no dominar sobre bbox/mask)
            losses["loss_quality"] *= 0.3
            losses["loss_species"] *= 0.3
            losses["loss_stage"] *= 0.3

            return proposals, losses

        # =========================
        # INFERENCE
        # =========================
        instances = proposals_or_instances

        boxes = [i.pred_boxes for i in instances if len(i) > 0]
        if len(boxes) == 0:
            return instances, {}

        box_features = self.box_head(
            self.box_pooler(
                [features[f] for f in self.in_features],
                boxes,
            )
        )

        start = 0
        for inst in instances:
            n = len(inst)
            if n == 0:
                continue

            inst.pred_quality = self.fc_quality(
                box_features[start:start + n]
            ).argmax(dim=1)

            inst.pred_species = self.fc_species(
                box_features[start:start + n]
            ).argmax(dim=1)

            inst.pred_stage = self.fc_stage(
                box_features[start:start + n]
            ).argmax(dim=1)

            start += n

        return instances, {}

class CallusTrainer(DefaultTrainer):
    @classmethod
    def build_train_loader(cls, cfg):
        return build_detection_train_loader(
            cfg,
            mapper=CallusDatasetMapper(cfg, is_train=True),
        )

def train(dataset_name, resume_checkpoint=None):
    cfg = get_cfg()
    cfg.merge_from_file(
        get_config_file(
            "COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"
        )
    )

    cfg.MODEL.DEVICE = "cpu"
    cfg.MODEL.ROI_HEADS.NAME = "CallusROIHeads"
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = len(
        MetadataCatalog.get(dataset_name).thing_classes
    )

    cfg.DATASETS.TRAIN = (dataset_name,)
    cfg.DATASETS.TEST = ()

    cfg.DATALOADER.NUM_WORKERS = 0

    cfg.SOLVER.IMS_PER_BATCH = 2
    cfg.SOLVER.BASE_LR = 1e-4
    cfg.SOLVER.MAX_ITER = 5000
    cfg.SOLVER.OPTIMIZER = "AdamW"
    cfg.SOLVER.STEPS = []
    cfg.SOLVER.CHECKPOINT_PERIOD = 300

    cfg.OUTPUT_DIR = "./output_train"
    os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)

    trainer = CallusTrainer(cfg)

    # --- Manejo de checkpoints ---
    resume_flag = False
    if resume_checkpoint and os.path.exists(resume_checkpoint):
        # Si se especifica un checkpoint concreto
        trainer.resume_or_load(resume=False)
        trainer.checkpointer.load(resume_checkpoint)
        print(f"🔁 Reanudando desde checkpoint específico: {resume_checkpoint}")
    else:
        # Buscar automáticamente el último checkpoint guardado por Detectron2
        last_checkpoint = trainer.checkpointer.get_checkpoint_file()
        if last_checkpoint and os.path.exists(last_checkpoint):
            resume_flag = True
            print(f"🔁 Reanudando desde último checkpoint detectado: {last_checkpoint}")
        else:
            cfg.MODEL.WEIGHTS = "detectron2://COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x/137849600/model_final_f10217.pkl"
            print("🚀 No se encontró checkpoint previo. Entrenamiento desde cero.")

    # --- Iniciar entrenamiento ---
    trainer.resume_or_load(resume=resume_flag)
    print("\n🏋️ Entrenamiento iniciado...")
    trainer.train()
    print("✅ Entrenamiento completado.")

if __name__ == "__main__":
    dataset_name = setup_dataset()
    train(dataset_name)
