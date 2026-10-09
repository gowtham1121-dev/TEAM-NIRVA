"""The one object the app talks to: give it a photo, get back a decision.

    from inspector.inspector import Inspector
    insp = Inspector.load("models/toothbrush_v1.pt", "models/toothbrush_v3_thresholds.json")
    result = insp.inspect("some_photo.png", overlay_path="heatmap.png")

The result is a plain dict, so it can go straight into a database row or a JSON API reply.
"""
import json
import time
from pathlib import Path

import cv2
import numpy as np

from inspector.patchcore import PatchCore
from inspector.region import masked_predict
from inspector.severity import assess


class Inspector:
    def __init__(self, model, thresholds, model_name="model", thresholds_name="thresholds", policy="starter"):
        self.model = model
        if policy == "starter":          # day-one lines built from good photos only (has a real REVIEW band)
            self.line_low, self.line_high = thresholds["starter_tau_low"], thresholds["starter_tau_high"]
        else:                            # lines tuned with defect examples
            self.line_low, self.line_high = thresholds["tau_low"], thresholds["tau_high"]
        self.policy, self.model_name, self.thresholds_name = policy, model_name, thresholds_name

    @classmethod
    def load(cls, model_path, thresholds_path, policy="starter"):
        model = PatchCore.load(Path(model_path))
        thresholds = json.load(open(thresholds_path))
        return cls(model, thresholds, Path(model_path).name, Path(thresholds_path).name, policy)

    def inspect(self, image_path, overlay_path=None):
        t = time.time()
        score, amap, region = masked_predict(self.model, image_path)
        r = assess(amap, region, score, self.line_low, self.line_high)
        result = {
            "image": str(image_path), "verdict": r["verdict"], "score": round(score, 4),
            "severity": r["severity"], "unusual_area_share": round(r["area_share"], 4),
            "unusual_area_mm2": r["area_mm2"], "where": r["where"], "box": r["box"],
            "review_from": round(self.line_low, 4), "fail_from": round(self.line_high, 4),
            "policy": self.policy, "model": self.model_name, "thresholds": self.thresholds_name,
        }
        if overlay_path is not None:
            self._save_overlay(image_path, amap, region, r["box"], r["verdict"], overlay_path)
            result["overlay"] = str(overlay_path)
        result["ms"] = round((time.time() - t) * 1000, 1)       # includes the overlay if one was written
        return result

    def _save_overlay(self, image_path, amap, region, box, verdict, out_path):
        size = self.model.image_size
        img = cv2.resize(cv2.imread(str(image_path)), (size, size))
        shown = np.where(region, amap, 0)
        norm = np.clip((shown - self.line_low * 0.6) / max(1e-6, self.line_high * 1.2 - self.line_low * 0.6), 0, 1)
        heat = cv2.applyColorMap((norm * 255).astype(np.uint8), cv2.COLORMAP_JET)
        alpha = (norm * 0.6)[..., None]
        out = (img * (1 - alpha) + heat * alpha).astype(np.uint8)
        colour = {"PASS": (80, 180, 60), "REVIEW": (0, 190, 255), "FAIL": (60, 60, 230)}[verdict]
        if box and verdict != "PASS":
            x, y, w, h = box
            cv2.rectangle(out, (x, y), (x + w, y + h), colour, 2)
        cv2.rectangle(out, (0, 0), (size - 1, 26), colour, -1)
        cv2.putText(out, verdict, (8, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(out_path), out)