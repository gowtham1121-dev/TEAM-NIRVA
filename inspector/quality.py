"""Input-quality gate: is this photo fit to be judged at all?

Sharpness uses the same measure as the teammate's image_quality.py (variance of the Laplacian).
The limits are learned from the GOOD training photos only and saved next to the model.
"""
import json
from pathlib import Path

import cv2


def measure(path):
    img = cv2.imread(str(path))
    if img is None:
        return None, None
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var()), float(gray.mean())


def learn_limits(paths, blur_share=0.5, bright_margin=0.2):
    """blur limit = half of the blurriest normal photo; brightness limits = normal range +/- 20%."""
    pairs = [measure(p) for p in paths]
    blurs = [b for b, _ in pairs if b is not None]
    lights = [l for _, l in pairs if l is not None]
    return {"blur_min": blur_share * min(blurs), "bright_min": (1 - bright_margin) * min(lights),
            "bright_max": (1 + bright_margin) * max(lights), "learned_from": len(blurs)}


class QualityGate:
    def __init__(self, limits):
        self.limits = limits

    @classmethod
    def load(cls, path):
        return cls(json.load(open(path)))

    def check(self, path):
        blur, bright = measure(path)
        if blur is None:
            return {"ok": False, "reason": "unreadable image", "blur": None, "brightness": None}
        L = self.limits
        if blur < L["blur_min"]:
            reason = "blurry"
        elif not (L["bright_min"] <= bright <= L["bright_max"]):
            reason = "too dark" if bright < L["bright_min"] else "too bright"
        else:
            reason = ""
        return {"ok": reason == "", "reason": reason, "blur": round(blur, 2), "brightness": round(bright, 2)}