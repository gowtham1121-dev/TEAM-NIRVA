"""A small, readable PatchCore implementation (runs on a normal laptop CPU).

Idea in plain words:
  1. Cut every normal photo into small patches and describe each patch with numbers
     (a "feature") using a pretrained image model.
  2. Keep a representative sample of those normal patches. This is the "memory bank".
  3. For a new photo, describe its patches the same way. A patch that is far from
     every patch in the memory bank looks unusual, so it is probably a defect.
"""
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
from torchvision import models
from torchvision.models.feature_extraction import create_feature_extractor
from torchvision.transforms.functional import gaussian_blur

IMG_EXTS = {".png", ".jpg", ".jpeg", ".bmp"}
IMAGENET_MEAN = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1)
IMAGENET_STD = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)


def list_images(folder):
    folder = Path(folder)
    if not folder.exists():
        return []
    return sorted(p for p in folder.iterdir() if p.suffix.lower() in IMG_EXTS)


def load_image(path, size):
    """Open a photo, resize it to size x size, return a tensor (3, size, size) with values 0..1."""
    img = Image.open(path).convert("RGB").resize((size, size), Image.Resampling.BILINEAR)
    arr = np.asarray(img, dtype=np.float32) / 255.0
    return torch.from_numpy(arr).permute(2, 0, 1)


def greedy_coreset(features, n_select, proj_dim=128, seed=0, log=print):
    """Pick n_select patches that cover the whole set as evenly as possible.

    Each step picks the patch that is currently farthest from everything already picked.
    A small random projection (proj_dim numbers per patch) keeps this fast.
    """
    gen = torch.Generator().manual_seed(seed)
    proj = torch.randn(features.shape[1], proj_dim, generator=gen) / proj_dim ** 0.5
    z = features @ proj
    chosen = [int(torch.randint(len(z), (1,), generator=gen))]
    min_dist = ((z - z[chosen[0]]) ** 2).sum(1)
    for step in range(1, n_select):
        i = int(torch.argmax(min_dist))
        chosen.append(i)
        min_dist = torch.minimum(min_dist, ((z - z[i]) ** 2).sum(1))
        if log and step % 1000 == 0:
            log(f"   coreset: picked {step} of {n_select} patches")
    return torch.tensor(chosen)


class PatchCore:
    def __init__(self, backbone="wide_resnet50_2", image_size=256,
                 coreset_ratio=0.1, feature_dim=512):
        self.backbone = backbone
        self.image_size = image_size
        self.coreset_ratio = coreset_ratio
        self.feature_dim = feature_dim
        self.memory_bank = None

        if backbone == "wide_resnet50_2":
            net = models.wide_resnet50_2(weights=models.Wide_ResNet50_2_Weights.IMAGENET1K_V1)
        elif backbone == "resnet18":
            net = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)
        else:
            raise ValueError("backbone must be 'wide_resnet50_2' or 'resnet18'")
        net.eval()
        # We only need two middle layers of the model, not its final answer.
        self.extractor = create_feature_extractor(net, {"layer2": "l2", "layer3": "l3"}).eval()

    @torch.no_grad()
    def _features(self, batch):
        """batch: (B, 3, H, W) values 0..1  ->  one feature vector per patch."""
        x = (batch - IMAGENET_MEAN) / IMAGENET_STD
        out = self.extractor(x)
        l2 = F.avg_pool2d(out["l2"], 3, 1, 1)   # blend each patch with its neighbours
        l3 = F.avg_pool2d(out["l3"], 3, 1, 1)
        l3 = F.interpolate(l3, size=l2.shape[-2:], mode="bilinear", align_corners=False)
        f = torch.cat([l2, l3], dim=1)           # (B, C, h, w)
        b, c, h, w = f.shape
        f = f.permute(0, 2, 3, 1).reshape(b * h * w, c)
        target = min(self.feature_dim, c)
        f = F.adaptive_avg_pool1d(f.unsqueeze(1), target).squeeze(1)
        return f, (h, w)

    @torch.no_grad()
    def fit(self, paths, batch_size=8, log=print):
        """Learn what 'normal' looks like from a list of good photos."""
        feats = []
        for i in range(0, len(paths), batch_size):
            batch = torch.stack([load_image(p, self.image_size) for p in paths[i:i + batch_size]])
            f, _ = self._features(batch)
            feats.append(f)
            if log:
                log(f"   read {min(i + batch_size, len(paths))} of {len(paths)} normal images")
        feats = torch.cat(feats)
        n_keep = max(1, int(len(feats) * self.coreset_ratio))
        if log:
            log(f"   {len(feats)} patches found, keeping {n_keep} representative ones...")
        keep = greedy_coreset(feats, n_keep, log=log)
        self.memory_bank = feats[keep].contiguous()

    @torch.no_grad()
    def predict(self, batch):
        """batch: (B, 3, H, W) -> (image_scores, anomaly_maps).

        anomaly_maps has shape (B, image_size, image_size): bigger = more unusual.
        """
        b = batch.shape[0]
        f, (h, w) = self._features(batch)
        dist = torch.cdist(f, self.memory_bank).min(dim=1).values   # distance to closest normal patch
        amap = dist.view(b, 1, h, w)
        amap = F.interpolate(amap, size=(self.image_size, self.image_size),
                             mode="bilinear", align_corners=False)
        amap = gaussian_blur(amap, kernel_size=33, sigma=4.0)
        scores = amap.flatten(1).max(dim=1).values
        return scores, amap[:, 0]

    def save(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        torch.save({"memory_bank": self.memory_bank,
                    "backbone": self.backbone, "image_size": self.image_size,
                    "coreset_ratio": self.coreset_ratio, "feature_dim": self.feature_dim}, path)

    @classmethod
    def load(cls, path):
        """Load a model saved with save()."""
        ck = torch.load(path, map_location="cpu")
        model = cls(backbone=ck["backbone"], image_size=ck["image_size"],
                    coreset_ratio=ck["coreset_ratio"], feature_dim=ck["feature_dim"])
        model.memory_bank = ck["memory_bank"]
        return model