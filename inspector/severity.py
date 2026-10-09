"""Rate how serious a flagged unit looks: size, strength and location of the unusual area.

IMPORTANT: this is a simple rule, not a trained model. The cut-offs in SEVERITY_RULES are
ILLUSTRATIVE. A real factory must set them (what size of flaw is acceptable for their customer).
"""
import cv2
import numpy as np

# Illustrative cut-offs: share of the brush area that looks unusual.
SEVERITY_RULES = {"minor_below": 0.005, "major_below": 0.03}     # < 0.5% minor, < 3% major, else critical
PX_PER_MM = None        # set this once the camera is calibrated (pixels per millimetre); None = report % only
HEAD_FRACTION = 0.55    # top 55% of the brush (the head with the bristles) vs the neck/handle below


def assess(amap, region, score, line_low, line_high):
    """amap: heat map, region: boolean brush mask, score: masked image score."""
    out = {"score": float(score), "verdict": "PASS" if score < line_low else ("REVIEW" if score < line_high else "FAIL"),
           "area_share": 0.0, "area_mm2": None, "where": "-", "box": None, "severity": "-"}
    hot = (amap >= line_low) & region
    n, labels, stats, cents = cv2.connectedComponentsWithStats(hot.astype(np.uint8))
    if n <= 1:
        return out                                   # nothing above the line: no area to describe
    big = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    ys, xs = np.where(region)
    top, bottom = ys.min(), ys.max()
    cy = cents[big][1]
    area_px = int(hot.sum())
    out["area_share"] = area_px / float(region.sum())
    if PX_PER_MM:
        out["area_mm2"] = area_px / (PX_PER_MM ** 2)
    out["where"] = "head / bristles" if (cy - top) / max(1, bottom - top) < HEAD_FRACTION else "neck / handle"
    x, y, w, h = (int(stats[big, c]) for c in (cv2.CC_STAT_LEFT, cv2.CC_STAT_TOP, cv2.CC_STAT_WIDTH, cv2.CC_STAT_HEIGHT))
    out["box"] = (x, y, w, h)
    if out["verdict"] == "PASS":
        out["severity"] = "-"
    elif out["area_share"] < SEVERITY_RULES["minor_below"]:
        out["severity"] = "MINOR"
    elif out["area_share"] < SEVERITY_RULES["major_below"]:
        out["severity"] = "MAJOR"
    else:
        out["severity"] = "CRITICAL"
    return out