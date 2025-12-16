import os
import json
import torch
import torch.nn as nn
import torch.nn.functional as F
from detectron2.structures import Boxes, BitMasks
import cv2
from detectron2.data.detection_utils import read_image
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
# 1️⃣ LABEL MAPS (SIN CAMBIOS)
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
# 2️⃣ DATASET (SIN CAMBIOS)
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

    print(f"Dataset '{dataset_name}' registrado.")
    return dataset_name

# =====================================================
# 3️⃣ AUMENTACIONES MEJORADAS (DEL CÓDIGO ANTERIOR)
# =====================================================
def get_train_augmentations(cfg):
    """Aumentaciones fuertes como en el código anterior que funcionaba"""
    return [
        # 1. Transformaciones Geométricas Estándar
        T.ResizeShortestEdge(
            short_edge_length=(512, 512),
            max_size=1024,
            sample_style='choice'
        ),
        # Flip horizontal Y vertical (crucial para TOP/SIDE)
        T.RandomFlip(prob=0.5, horizontal=True),
        T.RandomFlip(prob=0.5, vertical=True), 
        
        # 2. AUMENTACIÓN DE COLOR/TEXTURA (más agresiva)
        T.RandomBrightness(0.6, 1.4),   
        T.RandomSaturation(0.6, 1.4),  
        T.RandomContrast(0.6, 1.4),     
        
        # 3. Rotación (IMPORTANTE para generalización)
        T.RandomRotation(angle=[-30, 30], expand=False, center=None, sample_style='choice'),
        
        # 4. Recorte Aleatorio (ayuda a detectar objetos parciales)
        T.RandomCrop('relative_range', (0.7, 1.0))
    ]

# =====================================================
# 4️⃣ DATASET MAPPER (USANDO NUEVAS AUMENTACIONES)
# =====================================================
class CallusDatasetMapper(DatasetMapper):
    def __init__(self, cfg, is_train=True):
        # ← CAMBIO: Usa las aumentaciones fuertes
        super().__init__(cfg, is_train, augmentations=get_train_augmentations(cfg))

    def __call__(self, dataset_dict):
        dataset_dict = dataset_dict.copy()
        image = read_image(dataset_dict["file_name"], format=self.image_format)
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

            attr = ann.get("attributes", {})

            volumes.append(VOL_MAP.get(str(attr.get("volume", "small")), 0))
            qualities.append(QUAL_MAP.get(str(attr.get("quality", "good")), 0))
            species.append(SPECIES_MAP.get(str(attr.get("species", "Phyllostachys edulis")), 0))
            stages.append(STAGE_MAP.get(str(attr.get("stage", "early")), 0))

        instances.gt_boxes = Boxes(
            BoxMode.convert(torch.tensor(boxes, dtype=torch.float32), BoxMode.XYWH_ABS, BoxMode.XYXY_ABS)
        )
        instances.gt_classes = torch.tensor(classes, dtype=torch.int64)
        instances.gt_volume = torch.tensor(volumes, dtype=torch.int64)
        instances.gt_quality = torch.tensor(qualities, dtype=torch.int64)
        instances.gt_species = torch.tensor(species, dtype=torch.int64)
        instances.gt_stage = torch.tensor(stages, dtype=torch.int64)

        instances.gt_masks = BitMasks.from_polygon_masks(
            masks, image.shape[0], image.shape[1]
        )

        dataset_dict["instances"] = instances
        return dataset_dict

# =====================================================
# 5️⃣ ROI HEADS MULTITAREA (SIN CAMBIOS)
# =====================================================
@ROI_HEADS_REGISTRY.register()
class CallusROIHeads(StandardROIHeads):
    def __init__(self, cfg, input_shape):
        super().__init__(cfg, input_shape)
        dim = self.box_head._output_size
        self.fc_volume = nn.Linear(dim, 3)
        self.fc_quality = nn.Linear(dim, 3)
        self.fc_species = nn.Linear(dim, 2)
        self.fc_stage = nn.Linear(dim, 3)

    def forward(self, images, features, proposals, targets=None):
        proposals_or_instances, losses = super().forward(
            images, features, proposals, targets
        )

        if self.training:
            proposals = proposals_or_instances
            proposal_boxes = [p.proposal_boxes for p in proposals]
            feature_list = [features[f] for f in self.in_features]
            box_features = self.box_head(
                self.box_pooler(feature_list, proposal_boxes)
            )

            gt_volume = torch.cat([p.gt_volume for p in proposals])
            gt_quality = torch.cat([p.gt_quality for p in proposals])
            gt_species = torch.cat([p.gt_species for p in proposals])
            gt_stage = torch.cat([p.gt_stage for p in proposals])

            losses["loss_volume"] = F.cross_entropy(self.fc_volume(box_features), gt_volume)
            losses["loss_quality"] = F.cross_entropy(self.fc_quality(box_features), gt_quality)
            losses["loss_species"] = F.cross_entropy(self.fc_species(box_features), gt_species)
            losses["loss_stage"] = F.cross_entropy(self.fc_stage(box_features), gt_stage)

            return proposals, losses

        else:
            instances = proposals_or_instances
            boxes = [inst.pred_boxes for inst in instances]
            feature_list = [features[f] for f in self.in_features]
            box_features = self.box_head(
                self.box_pooler(feature_list, boxes)
            )

            vols = self.fc_volume(box_features).argmax(dim=1)
            quals = self.fc_quality(box_features).argmax(dim=1)
            species = self.fc_species(box_features).argmax(dim=1)
            stages = self.fc_stage(box_features).argmax(dim=1)

            for inst, v, q, s, st in zip(instances, vols, quals, species, stages):
                inst.pred_volume = v
                inst.pred_quality = q
                inst.pred_species = s
                inst.pred_stage = st

            return instances, {}

# =====================================================
# 6️⃣ TRAINER HÍBRIDO (MEJOR DE AMBOS MUNDOS)
# =====================================================
class CallusTrainer(DefaultTrainer):
    @classmethod
    def build_train_loader(cls, cfg):
        return build_detection_train_loader(
            cfg, mapper=CallusDatasetMapper(cfg, True)
        )

# =====================================================
# 7️⃣ TRAIN OPTIMIZADO (PARÁMETROS DEL CÓDIGO QUE FUNCIONABA)
# =====================================================
def train(dataset_name, metadata):
    cfg = get_cfg()
    cfg.merge_from_file(
        get_config_file("COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml")
    )

    # ← CAMBIOS CLAVE DEL CÓDIGO ANTERIOR:
    cfg.MODEL.DEVICE = "cpu"
    cfg.DATALOADER.NUM_WORKERS = 0  # ← CRÍTICO para macOS
    cfg.MODEL.ROI_HEADS.NAME = "CallusROIHeads"
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = len(metadata.thing_classes)

    cfg.DATASETS.TRAIN = (dataset_name,)
    cfg.DATASETS.TEST = ()

    # ← PARÁMETROS OPTIMIZADOS:
    cfg.SOLVER.IMS_PER_BATCH = 4      # ← Mayor batch size
    cfg.SOLVER.BASE_LR = 0.0001       # ← Learning rate probado
    cfg.SOLVER.MAX_ITER = 15000       # ← MÁS iteraciones (crucial)
    cfg.SOLVER.OPTIMIZER = "AdamW"    # ← Optimizador estable
    cfg.SOLVER.STEPS = []
    cfg.SOLVER.WEIGHT_DECAY = 0.0001
    cfg.SOLVER.CHECKPOINT_PERIOD = 300  # ← Frecuencia probada

    cfg.OUTPUT_DIR = "./output_callus"
    os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)

    # ← Sistema de checkpoint robusto (sin cambios)
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
    dataset_name = setup_dataset()
    metadata = MetadataCatalog.get(dataset_name)
    train(dataset_name, metadata)
