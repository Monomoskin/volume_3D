import os
import json
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from detectron2.engine import DefaultTrainer
from detectron2.config import get_cfg
from detectron2.data.datasets import register_coco_instances
from detectron2.model_zoo import get_config_file
from detectron2.data import DatasetMapper, MetadataCatalog
from detectron2.data import transforms as T
from detectron2.modeling import ROI_HEADS_REGISTRY, StandardROIHeads
from detectron2.modeling.poolers import ROIPooler
from detectron2.data import detection_utils as utils
from detectron2.structures import Instances
# ==============================================================================
# 0. DEFINICIÓN DE CLASES PARA LOS ATRIBUTOS
# ==============================================================================
SPECIES = ["moso", "other"]
QUALITY = ["poor", "medium", "good"]
STAGE = ["non_embryogenic", "embryogenic"]

# ==============================================================================
# 1. AUMENTACIONES
# ==============================================================================
def get_train_augmentations(cfg):
    return [
        T.ResizeShortestEdge(
            short_edge_length=(512, 512),
            max_size=1024,
            sample_style='choice'
        ),
        T.RandomFlip(prob=0.5, horizontal=True),
        T.RandomFlip(prob=0.5, vertical=True),
        T.RandomBrightness(0.6, 1.4),
        T.RandomSaturation(0.6, 1.4),
        T.RandomContrast(0.6, 1.4),
        T.RandomRotation(angle=[-30, 30], expand=False, center=None, sample_style='choice'),
        T.RandomCrop('relative_range', (0.7, 1.0))
    ]

# ==============================================================================
# 2. CUSTOM DATASET MAPPER PARA ATRIBUTOS
# ==============================================================================

class CallusDatasetMapper(DatasetMapper):
    def __call__(self, dataset_dict):
        dataset_dict = super().__call__(dataset_dict)
        instances = dataset_dict["instances"]

        # Mapas de atributos
        species_map = {"unknown": 0, "bamboo_moso": 1, "other": 2}
        quality_map = {"unknown": 0, "high": 1, "medium": 2, "low": 3}
        stage_map   = {"unknown": 0, "early": 1, "mid": 2, "late": 3}

        # Detectron2 no pasa las anotaciones originales a ROIHeads, así que hay que extraer del dataset_dict["annotations"]
        species_list = []
        quality_list = []
        stage_list = []

        # Asegurarse de que las instancias estén alineadas con las cajas/masks
        for ann in dataset_dict.get("annotations", []):
            attrs = ann.get("attributes", {})
            species_list.append(species_map.get(attrs.get("species", "unknown"), 0))
            quality_list.append(quality_map.get(attrs.get("quality", "unknown"), 0))
            stage_list.append(stage_map.get(attrs.get("stage", "unknown"), 0))

        # Convertir en tensores
        if len(species_list) == len(instances):
            instances.species = torch.tensor(species_list, dtype=torch.long)
            instances.quality = torch.tensor(quality_list, dtype=torch.long)
            instances.stage   = torch.tensor(stage_list, dtype=torch.long)
        else:
            # ⚠️ Si hay desalineación, asignamos zeros para no romper entrenamiento
            N = len(instances)
            instances.species = torch.zeros(N, dtype=torch.long)
            instances.quality = torch.zeros(N, dtype=torch.long)
            instances.stage   = torch.zeros(N, dtype=torch.long)

        dataset_dict["instances"] = instances
        return dataset_dict

# ==============================================================================
# 3. CUSTOM ROIHEADS PARA ATRIBUTOS
# ==============================================================================
class AttributeHead(nn.Module):
    def __init__(self, in_dim, num_classes):
        super().__init__()
        self.fc = nn.Linear(in_dim, num_classes)

    def forward(self, x):
        return self.fc(x)


@ROI_HEADS_REGISTRY.register()
class CallusROIHeads(StandardROIHeads):
    def __init__(self, cfg, input_shape):
        super().__init__(cfg, input_shape)
        dim = self.box_head.output_shape.channels
        self.species_head = AttributeHead(dim, len(SPECIES))
        self.quality_head = AttributeHead(dim, len(QUALITY))
        self.stage_head   = AttributeHead(dim, len(STAGE))

    def _shared_roi_features(self, features, instances):
        box_features = self.box_pooler([features[f] for f in self.in_features],
                                       [x.proposal_boxes for x in instances])
        box_features = self.box_head(box_features)
        return box_features

    def forward(self, images, features, proposals, targets=None):
        instances, losses = super().forward(images, features, proposals, targets)

        if self.training and targets is not None:
            box_features = self._shared_roi_features(features, proposals)

            # Solo instancias de 'callus' que tienen atributos
            callus_targets = [t for t in targets if hasattr(t, "species")]

            if callus_targets:
                callus_indices = [i for i, t in enumerate(targets) if hasattr(t, "species")]
                callus_features = box_features[callus_indices]

                species_targets = torch.cat([t.species for t in callus_targets])
                quality_targets = torch.cat([t.quality for t in callus_targets])
                stage_targets   = torch.cat([t.stage   for t in callus_targets])

                losses.update({
                    "loss_species": F.cross_entropy(self.species_head(callus_features), species_targets),
                    "loss_quality": F.cross_entropy(self.quality_head(callus_features), quality_targets),
                    "loss_stage":   F.cross_entropy(self.stage_head(callus_features),   stage_targets),
                })

        return instances, losses

# ==============================================================================
# 4. CUSTOM TRAINER
# ==============================================================================
class CustomTrainer(DefaultTrainer):
    @classmethod
    def build_mapper(cls, cfg, is_train=True):
        return CallusDatasetMapper(cfg, is_train=True)

# ==============================================================================
# 5. REGISTRO DEL DATASET
# ==============================================================================
def setup_dataset():
    json_path = os.path.join("annotations", "coco_annotations_multiattr.json")
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
# 6. ENTRENAMIENTO
# ==============================================================================
def train_model(metadata):
    cfg = get_cfg()
    cfg.merge_from_file(get_config_file("COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"))

    cfg.MODEL.DEVICE = "cpu"
    cfg.DATALOADER.NUM_WORKERS = 0
    cfg.DATASETS.TRAIN = (metadata.name,)
    cfg.DATASETS.TEST = ()
    cfg.MODEL.ROI_HEADS.NAME = "CallusROIHeads"
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = len(metadata.thing_classes)

    cfg.SOLVER.BASE_LR = 0.0001
    cfg.SOLVER.MAX_ITER = 5000
    cfg.SOLVER.OPTIMIZER = "AdamW"
    cfg.SOLVER.STEPS = []
    cfg.SOLVER.IMS_PER_BATCH = 2
    cfg.SOLVER.WEIGHT_DECAY = 0.0001
    cfg.SOLVER.CHECKPOINT_PERIOD = 300

    cfg.OUTPUT_DIR = "output_train_attr"
    os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)

    last_checkpoint = os.path.join(cfg.OUTPUT_DIR, "last_checkpoint")
    resume_flag = False

    if os.path.exists(last_checkpoint):
        last_model = open(last_checkpoint, "r").read().strip()
        cfg.MODEL.WEIGHTS = last_model
        resume_flag = True
        print(f"🔁 Reanudando desde checkpoint: {last_model}")
    else:
        cfg.MODEL.WEIGHTS = "detectron2://COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x/137849600/model_final_f10217.pkl"
        print("🚀 Entrenamiento desde cero.")

    trainer = CustomTrainer(cfg)
    trainer.resume_or_load(resume=resume_flag)
    trainer.train()
    print("✅ Entrenamiento completado.")

# ==============================================================================
# 7. RUN
# ==============================================================================
if __name__ == "__main__":
    metadata = setup_dataset()
    train_model(metadata)
