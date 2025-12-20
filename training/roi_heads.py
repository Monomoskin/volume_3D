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
SPECIES = ["moso", "other"]
QUALITY = ["poor", "medium", "good"]
STAGE = ["non_embryogenic", "embryogenic"]
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
class AttributeHead(nn.Module):
    def __init__(self, in_dim, num_classes):
        super().__init__()
        self.fc = nn.Linear(in_dim, num_classes)

    def forward(self, x):
        return self.fc(x)

