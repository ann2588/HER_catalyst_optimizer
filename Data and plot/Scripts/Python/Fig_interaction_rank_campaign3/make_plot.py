import os
import sys

SCRIPT_DIR = os.path.dirname(__file__)
# this points to: Scripts/Python/
SCRIPTS_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
UTIL_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "utils"))
sys.path.append(SCRIPTS_ROOT)
sys.path.append(UTIL_ROOT)


from registry import get_data
FIGURE_METADATA = {
    "stable_id": "Fig_interaction_rank_campaign3",
    "script": __file__,
    "data_keys": "In folder",
    "figure_type": "Main"   # or "Main"
}

def get_output_dir(meta):
    base = os.path.dirname(__file__)
    fig_base = "Figures_SI" if meta["figure_type"] == "SI" else "Figures_Main"
    outdir = os.path.join(base, "..", "..", ".." , fig_base, meta["stable_id"])
    os.makedirs(outdir, exist_ok=True)
    return outdir

OUTPUT_DIR = get_output_dir(FIGURE_METADATA)
os.makedirs(OUTPUT_DIR, exist_ok=True)
# -----------------------------

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from matplotlib.path import Path as MplPath
from matplotlib.patches import PathPatch
import numpy as np
np.set_printoptions(precision=2, suppress=True)
from Matrix_toolbox_C1 import *
import pandas as pd

PAIRS_TO_PLOT =  [
    ("ΔCu", "ΔNi"),
    ("ΔCu", "ΔP"),
    ("ΔCu", "ΔVolt"),
    ("ΔCu", "ΔTime"),
    ("ΔNi", "ΔVolt"),
    ("ΔNi", "ΔTime"),
    ("ΔNi", "ΔP"),
    ("ΔP", "ΔVolt"),
    ("ΔP", "ΔTime"),
    ("ΔTime", "ΔVolt"),
]
# Treat swapped pairs as identical (unordered)
_ALLOWED_UNORDERED = {frozenset((a, b)) for (a, b) in PAIRS_TO_PLOT if a !=b}
print

def _is_pair_allowed(lab):
    left, right = lab.split("–")
    return frozenset((left, right)) in _ALLOWED_UNORDERED

def _canon_label(a, b, FEATURES):
    ia, ib = FEATURES.index(a), FEATURES.index(b)
    return f"{a}–{b}" if ia <= ib else f"{b}–{a}"

# -----------------------------
# Label helpers
# -----------------------------
def _pair_labels(FEATURES):
    """All P×P pair labels aligned with row-major ravel() order: (i=0..P-1, j=0..P-1)."""
    P = len(FEATURES)
    return [f"{FEATURES[i]}–{FEATURES[j]}" for i in range(P) for j in range(P)]

def _top10_ordered(v, labels_all, use_abs_for_rank=True):
    """
    Pick top-10 indices by |v| (or raw v), then order bottom->top (ascending magnitude)
    so the largest ends up at the top of the stack.
    Returns: vals, labs, idx (all length 10).
    """
    scores = np.abs(v) if use_abs_for_rank else v
    idx10 = np.argsort(-scores)[:15]
    order = idx10[np.argsort(np.abs(v[idx10]))]   # small->large
    vals  = v[order]
    labs  = [labels_all[k] for k in order]
    return vals, labs, order

def _bottoms_and_heights(vals, gap):
    """Return bottoms and heights for stacked bar with a fixed gap between segments."""
    h = np.abs(vals)
    b = np.cumsum(np.r_[0.0, h[:-1] + gap])
    return b, h

# -----------------------------
# Cubic Bézier (S-shaped ribbon) helpers
# -----------------------------
def _cubic_bezier(p0, p1, p2, p3, t):
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float)
    p2 = np.asarray(p2, float); p3 = np.asarray(p3, float)
    t = np.asarray(t, float)[:, None]
    one = 1.0 - t
    return (one**3)*p0 + 3*one**2*t*p1 + 3*one*t**2*p2 + (t**3)*p3

def _cubic_bezier_deriv(p0, p1, p2, p3, t):
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float)
    p2 = np.asarray(p2, float); p3 = np.asarray(p3, float)
    t = np.asarray(t, float)[:, None]
    one = 1.0 - t
    return 3*one**2*(p1 - p0) + 6*one*t*(p2 - p1) + 3*t**2*(p3 - p2)

def _ribbon_between_s(ax, x0, y0, x1, y1, width, color,
                      alpha=0.25, bend=0.20, s_amp=0.25, flip=False, n=160):
    """
    Draw an S-shaped ribbon between (x0,y0) and (x1,y1) using a cubic Bézier centerline.
    - bend: horizontal pull (0..~0.5). Larger = more lateral bow.
    - s_amp: vertical 'S' amplitude as a fraction of |y1 - y0|.
    - flip: toggles the S direction to reduce overlaps.
    - width: ribbon thickness in data units (match bar height units).
    """
    if width <= 0:
        return

    p0 = np.array([x0, y0], float)
    p3 = np.array([x1, y1], float)

    dx = x1 - x0
    dy = y1 - y0
    sign = -1.0 if flip else 1.0
    dv = s_amp * max(1e-9, abs(dy)) * sign

    # Control points bow toward the center with opposite vertical nudges
    c1 = np.array([x0 + bend*dx, y0 + 0.5*dy + dv], float)
    c2 = np.array([x1 - bend*dx, y1 - 0.5*dy - dv], float)

    t = np.linspace(0.0, 1.0, n)
    center  = _cubic_bezier(p0, c1, c2, p3, t)        # (n,2)
    tangent = _cubic_bezier_deriv(p0, c1, c2, p3, t)  # (n,2)

    # Normals for width offset
    nrm = np.stack([-tangent[:, 1], tangent[:, 0]], axis=1)
    nrm_len = np.linalg.norm(nrm, axis=1, keepdims=True)
    nrm_len[nrm_len == 0] = 1.0
    unit_n = nrm / nrm_len

    half_w = width / 2.0
    upper = center + unit_n * half_w
    lower = center - unit_n * half_w

    verts = np.vstack([upper, lower[::-1], upper[0:1]])
    codes = [MplPath.MOVETO] + [MplPath.LINETO]*(len(upper)-1) + \
            [MplPath.LINETO]*len(lower) + [MplPath.CLOSEPOLY]
    patch = PathPatch(MplPath(verts, codes), facecolor=color, edgecolor='none', alpha=alpha)
    ax.add_patch(patch)

# -----------------------------
# Label helpers
# -----------------------------
def _pair_labels(FEATURES):
    P = len(FEATURES)
    return [f"{FEATURES[i]}–{FEATURES[j]}" for i in range(P) for j in range(P)]

def _top10_ordered(v, labels_all, use_abs_for_rank=True):
    scores = np.abs(v) if use_abs_for_rank else v
    idx10 = np.argsort(-scores)[:8]
    order = idx10[np.argsort(np.abs(v[idx10]))]   # small->large -> largest ends on top
    vals  = v[order]
    labs  = [labels_all[k] for k in order]
    return vals, labs, order

def _bottoms_and_heights(vals, gap):
    h = np.abs(vals)
    b = np.cumsum(np.r_[0.0, h[:-1] + gap])
    return b, h

# -----------------------------
# Cubic Bézier (S-shaped ribbon) helpers
# -----------------------------
def _cubic_bezier(p0, p1, p2, p3, t):
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float)
    p2 = np.asarray(p2, float); p3 = np.asarray(p3, float)
    t = np.asarray(t, float)[:, None]
    one = 1.0 - t
    return (one**3)*p0 + 3*one**2*t*p1 + 3*one*t**2*p2 + (t**3)*p3

def _cubic_bezier_deriv(p0, p1, p2, p3, t):
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float)
    p2 = np.asarray(p2, float); p3 = np.asarray(p3, float)
    t = np.asarray(t, float)[:, None]
    one = 1.0 - t
    return 3*one**2*(p1 - p0) + 6*one*t*(p2 - p1) + 3*t**2*(p3 - p2)

def _ribbon_between_s(ax, x0, y0, x1, y1, width, color,
                      alpha=0.25, bend=0.22, s_amp=0.30, flip=False, n=160,
                      zorder=1):
    """
    S-shaped ribbon between (x0,y0) and (x1,y1).
    zorder controls drawing order (lower = behind).
    """
    if width <= 0:
        return

    p0 = np.array([x0, y0], float)
    p3 = np.array([x1, y1], float)

    dx = x1 - x0
    dy = y1 - y0
    sign = -1.0 if flip else 1.0
    dv = s_amp * max(1e-9, abs(dy)) * sign

    c1 = np.array([x0 + bend*dx, y0 + 0.5*dy + dv], float)
    c2 = np.array([x1 - bend*dx, y1 - 0.5*dy - dv], float)

    t = np.linspace(0.0, 1.0, n)
    center  = _cubic_bezier(p0, c1, c2, p3, t)
    tangent = _cubic_bezier_deriv(p0, c1, c2, p3, t)

    nrm = np.stack([-tangent[:, 1], tangent[:, 0]], axis=1)
    nrm_len = np.linalg.norm(nrm, axis=1, keepdims=True)
    nrm_len[nrm_len == 0] = 1.0
    unit_n = nrm / nrm_len

    half_w = width / 2.0
    upper = center + unit_n * half_w
    lower = center - unit_n * half_w

    verts = np.vstack([upper, lower[::-1], upper[0:1]])
    codes = [MplPath.MOVETO] + [MplPath.LINETO]*(len(upper)-1) + \
            [MplPath.LINETO]*len(lower) + [MplPath.CLOSEPOLY]
    patch = PathPatch(MplPath(verts, codes), facecolor=color, edgecolor='none', alpha=alpha)
    ax.add_patch(patch)

def _topN_unordered_allowed(H, FEATURES, N=8, combine='sum_abs'):
    """
    Build scores over allowed unordered pairs (A,B) == (B,A), then take top-N.
    combine: 'sum_abs' | 'max_abs' | 'l2'
    """
    idx = {f:i for i, f in enumerate(FEATURES)}
    labs, vals = [], []
    for pair in _ALLOWED_UNORDERED:
        a, b = tuple(pair)
        if a in idx and b in idx:
            ia, ib = idx[a], idx[b]
            if combine == 'sum_abs':
                score = abs(H[ia, ib]) + abs(H[ib, ia])
            elif combine == 'max_abs':
                score = max(abs(H[ia, ib]), abs(H[ib, ia]))
            elif combine == 'l2':
                score = float(np.hypot(H[ia, ib], H[ib, ia]))
            else:
                score = abs(H[ia, ib]) + abs(H[ib, ia])
            labs.append(_canon_label(a, b, FEATURES))
            vals.append(float(score))
    if not vals:
        return np.array([]), [], np.array([], dtype=int)
    vals = np.array(vals, float)
    top = np.argsort(-vals)[:N]
    vals_top = vals[top]
    labs_top = [labs[i] for i in top]
    order = np.argsort(vals_top)  # bottom -> top
    return vals_top[order], [labs_top[i] for i in order], order
def _print_topN_unordered_with_values(H, FEATURES, N=8, combine='sum_abs'):
    """
    Return and print the top-N unordered feature pairs ranked by |H[a,b]|.
    Only return H[a,b] (original signed value).
    combine: 'abs' | 'sum_abs' | 'max_abs' | 'l2'
    """
    idx = {f: i for i, f in enumerate(FEATURES)}
    records = []

    for pair in _ALLOWED_UNORDERED:
        a, b = tuple(pair)
        if a in idx and b in idx:
            ia, ib = idx[a], idx[b]
            val_ab = H[ia, ib]
            val_ba = H[ib, ia]

            # define score for ranking
            if combine == 'abs':
                score = abs(val_ab)
            elif combine == 'sum_abs':
                score = abs(val_ab) + abs(val_ba)
            elif combine == 'max_abs':
                score = max(abs(val_ab), abs(val_ba))
            elif combine == 'l2':
                score = float(np.hypot(val_ab, val_ba))
            else:
                score = abs(val_ab)

            records.append({
                "pair": _canon_label(a, b, FEATURES),
                "H[a,b]": val_ab,
                "score": score
            })

    if not records:
        print("⚠️ No valid pairs found.")
        return pd.DataFrame()

    df = pd.DataFrame(records).sort_values("score", ascending=False).head(N)

    print(f"=== Top {N} unordered pairs by {combine} ===")
    print(df[["pair", "H[a,b]"]].to_string(index=False, float_format=lambda x: f"{x:8.4f}"))

    return df[["pair", "H[a,b]"]]

# -----------------------------
# Plot 3 bars + ribbons (including cross ribbons L↔R behind middle bar)
# -----------------------------
def plot_three_top10_with_sankey_links(
    H_DoE, H_STAGE_1, H_STAGE_2, FEATURES,
    gap=0.05,
    bar_width=0.5,
    x_left=0.0, x_mid=1.0, x_right=2.0,
    label_rotation=0,
    use_abs_for_rank=True,
    link_alpha=0.25,
    link_bend=1.0,
    link_s_amp=0.1,
    link_x_inset=0.1,
    cmap_name="Set3",
    figsize=(4.8, 2.4),
    title="Top-10 across DoE, Stage 1, Stage 2 with Sankey-style links",
    save_path=None
):
    valsL, labsL, _ = _topN_unordered_allowed(H_DoE,    FEATURES, N=8, combine='max_abs')
    dfL = _print_topN_unordered_with_values(H_DoE, FEATURES, N=8, combine='max_abs')
    hab_dictL = dict(zip(dfL["pair"], dfL["H[a,b]"]))

    valsM, labsM, _ = _topN_unordered_allowed(H_STAGE_1, FEATURES, N=8, combine='max_abs')
    dfM = _print_topN_unordered_with_values(H_STAGE_1, FEATURES, N=8, combine='max_abs')
    hab_dictM = dict(zip(dfM["pair"], dfM["H[a,b]"]))
    
    valsR, labsR, _ = _topN_unordered_allowed(H_STAGE_2, FEATURES, N=8, combine='max_abs')
    dfR = _print_topN_unordered_with_values(H_STAGE_2, FEATURES, N=8, combine='max_abs')
    hab_dictR = dict(zip(dfR["pair"], dfR["H[a,b]"]))

    bL, hL = _bottoms_and_heights(valsL, gap)
    bM, hM = _bottoms_and_heights(valsM, gap)
    bR, hR = _bottoms_and_heights(valsR, gap)

    # --- Top-align bars: shift bottoms so all three stacks share the same top ---
    TL = (bL[-1] + hL[-1]) if len(hL) else 0.0
    TM = (bM[-1] + hM[-1]) if len(hM) else 0.0
    TR = (bR[-1] + hR[-1]) if len(hR) else 0.0
    T_max = max(TL, TM, TR)
    bL = bL + (T_max - TL)
    bM = bM + (T_max - TM)
    bR = bR + (T_max - TR)

    # Global color map across all three bars
    uniq_labs = list(dict.fromkeys(labsL + labsM + labsR))
    cmap = cm.get_cmap(cmap_name, max(8, len(uniq_labs)))
    color_map = {lab: cmap(i) for i, lab in enumerate(uniq_labs)}

    fig, ax = plt.subplots(figsize=figsize)

    # ---- L↔R cross ribbons (behind middle bar) ----
    posL = {lab: (b + h/2, h) for lab, b, h in zip(labsL, bL, hL)}
    posM = {lab: (b + h/2, h) for lab, b, h in zip(labsM, bM, hM)}
    posR = {lab: (b + h/2, h) for lab, b, h in zip(labsR, bR, hR)}

    common_LR_only = set(labsL).intersection(labsR) - set(labsM)
    x0_LR = x_left + bar_width/2
    x1_LR = x_right - bar_width/2

    def _flip_for_label(label):
        return (hash(label) & 1) == 1

    for lab in common_LR_only:
        if not _is_pair_allowed(lab):
            continue
        y0, h0_ = posL[lab]
        y1, h1_ = posR[lab]
        w = min(h0_, h1_)
        # draw with very low zorder so it's BEHIND the middle bar and other ribbons
        _ribbon_between_s(ax, x0_LR, y0, x1_LR, y1, w, color_map[lab],
                          alpha=link_alpha*0.9, bend=link_bend, s_amp=link_s_amp,
                          flip=_flip_for_label(lab), n=200, zorder=0)

    # ---- Draw bars (left and right first, mid later so it's on top of cross ribbons) ----
    for x, vals, labs, btm, hts, hab_dict in [
        (x_left,  valsL, labsL, bL, hL, hab_dictL),
        (x_right, valsR, labsR, bR, hR, hab_dictR),
    ]:
        for h, b, lab, raw in zip(hts, btm, labs, vals):
            # 從對應的 hab_dict 取原始 H[a,b]，若沒有則使用 raw
            raw_val = hab_dict.get(lab, raw)
            ax.bar(x, h, bottom=b, width=bar_width, color=color_map[lab],
                edgecolor="white", zorder=2)
            ax.text(x, b + h/2, f"{lab}\\{raw_val:.2f}",
                    ha="center", va="center", fontsize=6,
                    rotation=label_rotation, zorder=3)

    # ---- L↔M ribbons (in front of cross ribbons, behind middle bar) ----
    common_LM = set(labsL).intersection(labsM)
    x0_LM = x_left + bar_width/2
    x1_LM = x_mid - bar_width/2
    for lab in common_LM:
        if not _is_pair_allowed(lab):
            continue
        y0, h0_ = posL[lab]
        y1, h1_ = posM[lab]
        w = min(h0_, h1_)
        _ribbon_between_s(ax, x0_LM, y0, x1_LM, y1, w, color_map[lab],
                          alpha=link_alpha, bend=link_bend, s_amp=link_s_amp,
                          flip=_flip_for_label(lab), n=160, zorder=1)

    # ---- Draw middle bar last so it's on top ----
    for h, b, lab, raw in zip(hM, bM, labsM, valsM):
        ax.bar(x_mid, h, bottom=b, width=bar_width, color=color_map[lab],
               edgecolor="white", zorder=3)
        raw_val = hab_dictM.get(lab, raw)
        ax.text(x_mid, b + h/2, f"{lab}\\{raw_val:.2f}",
                ha="center", va="center", fontsize=6, rotation=label_rotation, zorder=4)

    # ---- M↔R ribbons (in front of cross ribbons, behind right bar text) ----
    common_MR = set(labsM).intersection(labsR)
    x0_MR = x_mid + bar_width/2
    x1_MR = x_right - bar_width/2
    for lab in common_MR:
        if not _is_pair_allowed(lab):
            continue
        y0, h0_ = posM[lab]
        y1, h1_ = posR[lab]
        w = min(h0_, h1_)
        _ribbon_between_s(ax, x0_MR, y0, x1_MR, y1, w, color_map[lab],
                          alpha=link_alpha, bend=link_bend, s_amp=link_s_amp,
                          flip=_flip_for_label(lab), n=160, zorder=2)

    # ---- Clean look ----
    y_max = T_max + 0.2
    ax.set_xlim(min(x_left, x_mid, x_right) - 0.6, max(x_left, x_mid, x_right) + 0.6)
    ax.set_ylim(0.0, y_max)
    ax.set_xticks([]); 
    #ax.set_yticks([])
    ax.set_frame_on(False)
    #ax.set_title(title, pad=16)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=300)
    return fig, ax

# -----------------------------

import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)
from matplotlib import MatplotlibDeprecationWarning
warnings.filterwarnings("ignore", category=MatplotlibDeprecationWarning)
from LQV4_forpost import LQBandit
# -----------------------------
num = 590
os.getcwd()
df = pd.read_csv(f"{SCRIPT_DIR}/Set 2/DoE.csv")
CSV_FILENAME_1 = f"{SCRIPT_DIR}/Set 2/DoE_{num}.csv"
df.sample(frac=1, random_state=None).head(num).to_csv(f"{CSV_FILENAME_1}",index=False)
agent = LQBandit(beta=60, csv_file= CSV_FILENAME_1)
H_DOE_120 = reconstruct_H_from_theta(agent.theta.ravel(), P)

CSV_FILENAME_2 = f"{SCRIPT_DIR}/Set 2/DoE_{num}_stage1.csv"
pd.concat([pd.read_csv(f"{CSV_FILENAME_1}"), pd.read_csv(f"{SCRIPT_DIR}/Set 2/Campaign3_stage1_only.csv")]).to_csv(CSV_FILENAME_2, index=False)
agent = LQBandit(beta=60, csv_file= CSV_FILENAME_2)
H_STAGE_1 = reconstruct_H_from_theta(agent.theta.ravel(), P)

CSV_FILENAME_3 = f"{SCRIPT_DIR}/Set 2/DoE_{num}_stage1_stage2.csv"
pd.concat([pd.read_csv(f"{CSV_FILENAME_2}"), pd.read_csv(f"{SCRIPT_DIR}/Set 2/Campaign3_stage2_only.csv")]).to_csv(CSV_FILENAME_3, index=False)
agent = LQBandit(beta=60, csv_file= CSV_FILENAME_3)
H_STAGE_2 = reconstruct_H_from_theta(agent.theta.ravel(), P)

# -----------------------------
fig, ax = plot_three_top10_with_sankey_links(H_DOE_120, H_STAGE_1, H_STAGE_2, FEATURES, save_path = f'{OUTPUT_DIR}/Campaign3sanki.eps')
fig, ax = plot_three_top10_with_sankey_links(H_DOE_120, H_STAGE_1, H_STAGE_2, FEATURES, save_path = f'{OUTPUT_DIR}/Campaign3sanki.png')