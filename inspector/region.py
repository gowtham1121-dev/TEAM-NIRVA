"""Find the brush in a photo and score only that region.

This is the ONE place that decides 'where do we look'. The app, the evaluation and the
threshold calibration must all call masked_predict(), so the scores always mean the same thing.
"""
import cv2
import numpy as np

from inspector.patchcore import load_image

MARGIN = 0.04            # margin around the brush, as a share of the image size


def brush_region(path, size, margin=MARGIN):
    """True where the brush is. Bright object on a dark background -> Otsu threshold."""
    gray = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    gray = cv2.resize(gray, (size, size), interpolation=cv2.INTER_AREA)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(binary)
    if n <= 1:                                   # nothing found: do not hide anything
        return np.ones((size, size), dtype=bool)
    biggest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    region = (labels == biggest).astype(np.uint8)
    contours, _ = cv2.findContours(region, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    filled = np.zeros_like(region)
    cv2.drawContours(filled, contours, -1, 1, thickness=-1)           # fill holes inside the brush
    k = max(3, int(size * margin) * 2 + 1)
    filled = cv2.dilate(filled, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    return filled.astype(bool)


def masked_predict(model, path):
    """Returns (score, heat map, region). The score is the maximum heat INSIDE the brush region."""
    size = model.image_size
    _, maps = model.predict(load_image(path, size).unsqueeze(0))
    amap = maps[0].numpy()
    region = brush_region(path, size)
    score = float(amap[region].max()) if region.any() else float(amap.max())
    return score, amap, region