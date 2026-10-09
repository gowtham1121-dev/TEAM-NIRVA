"""Turn an anomaly score into PASS / REVIEW / FAIL using two thresholds.

below tau_low            -> PASS
tau_low .. tau_high      -> REVIEW  (a person decides)
tau_high and above       -> FAIL
"""
import numpy as np

PASS, REVIEW, FAIL = "PASS", "REVIEW", "FAIL"


def decide(score, tau_low, tau_high):
    if score < tau_low:
        return PASS
    if score < tau_high:
        return REVIEW
    return FAIL


def counts(good_scores, defect_scores, tau_low, tau_high):
    """How many good / defective units end up as PASS, REVIEW, FAIL."""
    g = np.asarray(good_scores)
    d = np.asarray(defect_scores)
    return {
        "good_pass": int((g < tau_low).sum()),
        "good_review": int(((g >= tau_low) & (g < tau_high)).sum()),
        "good_fail": int((g >= tau_high).sum()),          # false rejects
        "defect_pass": int((d < tau_low).sum()),          # escapes
        "defect_review": int(((d >= tau_low) & (d < tau_high)).sum()),
        "defect_fail": int((d >= tau_high).sum()),
        "n_good": len(g),
        "n_defect": len(d),
    }


def rates(c):
    n = c["n_good"] + c["n_defect"]
    return {
        "escape_rate": c["defect_pass"] / c["n_defect"],        # defective units that were passed
        "false_reject_rate": c["good_fail"] / c["n_good"],       # good units that were failed
        "review_rate": (c["good_review"] + c["defect_review"]) / n,
    }


def cost_per_1000(good_scores, defect_scores, tau_low, tau_high,
                  c_escape, c_false_reject, c_review, defect_rate):
    """Expected cost of inspecting 1000 units.

    defect_rate is how many units on the real line are defective (for example 0.05 = 5%).
    The checking set often has far more defects than a real line, so we re-weight it.
    """
    c = counts(good_scores, defect_scores, tau_low, tau_high)
    ng, nd = c["n_good"], c["n_defect"]
    per_good = (c["good_fail"] * c_false_reject + c["good_review"] * c_review) / ng
    per_defect = (c["defect_pass"] * c_escape + c["defect_review"] * c_review) / nd
    return 1000 * ((1 - defect_rate) * per_good + defect_rate * per_defect)


def best_thresholds(good_scores, defect_scores, c_escape, c_false_reject, c_review, defect_rate):
    """Try every sensible pair of thresholds and keep the cheapest one."""
    allv = np.sort(np.concatenate([good_scores, defect_scores]))
    mids = (allv[:-1] + allv[1:]) / 2
    candidates = np.concatenate([[allv[0] - 1e-6], mids, [allv[-1] + 1e-6]])
    best = None
    for lo in candidates:
        for hi in candidates[candidates >= lo]:
            cost = cost_per_1000(good_scores, defect_scores, lo, hi,
                                 c_escape, c_false_reject, c_review, defect_rate)
            if best is None or cost < best[0] - 1e-12:
                best = (cost, float(lo), float(hi))
    return best[1], best[2], best[0]


def starter_thresholds(good_scores):
    """Thresholds from good photos only (no defect examples needed on day one).

    Common 'mean + 3 standard deviations' rule for tau_low, and double that distance for tau_high.
    """
    g = np.asarray(good_scores)
    return float(g.mean() + 3 * g.std()), float(g.mean() + 6 * g.std())