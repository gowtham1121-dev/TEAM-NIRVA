"""Shared test code: score every test photo and measure how good the model is."""
import time
from pathlib import Path

import numpy as np
from PIL import Image
from sklearn.metrics import roc_auc_score

from inspector.patchcore import list_images, load_image


def load_mask(root, image_path, size):
    """True defect area for a test image (all False for good images)."""
    mask_path = Path(root) / "ground_truth" / "defective" / f"{image_path.stem}_mask.png"
    if image_path.parent.name == "good" or not mask_path.exists():
        return np.zeros((size, size), dtype=bool)
    m = Image.open(mask_path).convert("L").resize((size, size), Image.Resampling.NEAREST)
    return np.asarray(m) > 0


def evaluate(model, root):
    root = Path(root)
    good = list_images(root / "test" / "good")
    bad = list_images(root / "test" / "defective")
    items = [(p, 0) for p in good] + [(p, 1) for p in bad]
    size = model.image_size

    scores, maps, masks, labels, times = [], [], [], [], []
    for i, (p, label) in enumerate(items):
        t = time.time()
        s, a = model.predict(load_image(p, size).unsqueeze(0))
        elapsed = time.time() - t
        if i > 0:                       # skip the first image (warm-up)
            times.append(elapsed)
        scores.append(float(s[0]))
        maps.append(a[0].numpy())
        masks.append(load_mask(root, p, size))
        labels.append(label)

    scores = np.array(scores)
    labels = np.array(labels)
    pixel_auroc = roc_auc_score(np.concatenate([m.ravel() for m in masks]),
                                np.concatenate([a.ravel() for a in maps]))
    highest_good = scores[labels == 0].max()
    return {
        "image_auroc": float(roc_auc_score(labels, scores)),
        "pixel_auroc": float(pixel_auroc),
        "defects_above_every_good": int((scores[labels == 1] > highest_good).sum()),
        "n_defective": int((labels == 1).sum()),
        "good_scores": scores[labels == 0].tolist(),
        "defect_scores": scores[labels == 1].tolist(),
        "ms_per_image": float(np.mean(times) * 1000),
    }