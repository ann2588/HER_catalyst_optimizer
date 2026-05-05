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
    "stable_id": "Fig_volcano_rebuild_campaign1",
    "script": __file__,
    "data_keys": "Campaign1",
    "figure_type": "Main"   # or 或 "Main"
}

def get_output_dir(meta):
    base = os.path.dirname(__file__)
    fig_base = "Figures_SI" if meta["figure_type"] == "SI" else "Figures_Main"
    outdir = os.path.join(base, "..", "..", ".." , fig_base, meta["stable_id"])
    os.makedirs(outdir, exist_ok=True)
    return outdir

OUTPUT_DIR = get_output_dir(FIGURE_METADATA)
os.makedirs(OUTPUT_DIR, exist_ok=True)

###========================================================================###

import numpy as np
import matplotlib.pyplot as plt
import itertools
from typing import List, Tuple
from matplotlib.colors import LogNorm, SymLogNorm, LinearSegmentedColormap

# Global figure/font settings
plt.rcParams.update({
    'font.size': 6,
})

# ===================== User settings =====================
CSV_FILENAME = get_data("Campaign1")
CENTER_EXP_ID = 'exp715'
LAMBDA_REG = 1e-6

FEATURES = ["ΔV", "ΔCr", "ΔMg", "ΔFe", "ΔCo", "ΔNi", "ΔCu", "ΔS", "ΔSe", "ΔP", "ΔVolt", "ΔTime"]
P = len(FEATURES)

PAIRS_TO_PLOT: List[Tuple[str, str]] = [
    ("ΔCo", "ΔFe"),
    ("ΔCo", "ΔV"),
    ("ΔCo", "ΔCr"),
    ("ΔCo", "ΔVolt"),
    ("ΔCo", "ΔTime"),
    ("ΔCo", "ΔP"),
    ("ΔFe", "ΔVolt"),
    ("ΔFe", "ΔTime"),
    ("ΔFe", "ΔCr"),
    ("ΔFe", "ΔV"),
    ("ΔFe", "ΔP"),
    ("ΔV", "ΔCr"),
    ("ΔV", "ΔVolt"),
    ("ΔV", "ΔTime"),
    ("ΔV", "ΔP"),
    ("ΔCr", "ΔVolt"),
    ("ΔCr", "ΔTime"),
    ("ΔCr", "ΔP"),
    ("ΔP", "ΔVolt"),
    ("ΔP", "ΔTime"),
    ("ΔTime", "ΔVolt"),
]

'''
PAIRS_TO_PLOT: List[Tuple[str, str]] = [
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
'''
FIXED_VAL_SCALED = 0.0    
GRID_N = 201

PLOT_EIGENPLANE = False
EIGENPLANE_RANGE = 0.6
EIGENPLANE_GRID = 201

SAVE_FIG = True
SCALE_RANGE_Z = (-1.0, 0.0)   
APPLY_GLOBAL_SCALING = True   

# ========== User toggles for raw/scaled slice plotting ==========
DRAW_RAW = False      
DRAW_SCALED = True    
LogLINTHRESH = 1   
SymLINTHRESH = 0.1   
COLORMAP_BASE = 'turbo'    
CMAP_TOP_WHITE = 0.15      


def build_cmap_with_white_top(base_name: str, top_frac: float) -> LinearSegmentedColormap:
    base = plt.cm.get_cmap(base_name, 256)
    colors = base(np.linspace(0, 1, 256))
    n_top = int(256 * max(0.0, min(1.0, top_frac)))
    if n_top > 0:
        top = colors[-n_top:]
        white = np.ones_like(top)
        alpha = np.linspace(0.0, 1.0, n_top)[:, None]
        colors[-n_top:] = top * (1 - alpha) + white * alpha
    return LinearSegmentedColormap.from_list(f"{base_name}_topwhite{int(top_frac*100)}", colors)

CMAP_DISPLAY = build_cmap_with_white_top(COLORMAP_BASE, CMAP_TOP_WHITE)
from LQV4_forpost import LQBandit

# ===================== Helpers =====================
def ridge_inverse(A: np.ndarray, lam: float) -> np.ndarray:
    return np.linalg.inv(A + lam * np.eye(A.shape[0]))

def reconstruct_H_from_theta(theta_vec: np.ndarray, p: int) -> np.ndarray:
    if theta_vec.ndim == 2:
        theta_vec = theta_vec.ravel()
    expected_len = 1 + p + (p * (p + 1)) // 2
    if len(theta_vec) < expected_len:
        raise ValueError(f"theta length {len(theta_vec)} < expected {expected_len} for p={p}")
    start = 1 + p
    quad = theta_vec[start : start + (p * (p + 1)) // 2]
    H = np.zeros((p, p), dtype=float)
    idx = 0
    for i in range(p):
        span = p - i
        row = quad[idx : idx + span]
        idx += span
        H[i, i] = 2.0 * row[0]
        if span > 1:
            H[i, i+1:p] = row[1:]
    H = H + H.T - np.diag(np.diag(H))
    return H

def linear_scale_to_range(Z: np.ndarray, zmin: float, zmax: float, lo: float, hi: float) -> np.ndarray:

    Z = np.asarray(Z, dtype=float)
    if not np.isfinite(zmax - zmin) or (zmax == zmin):
        return np.full_like(Z, 0.5*(lo+hi))
    return lo + (Z - zmin) * (hi - lo) / (zmax - zmin)

def scale_vec(u, lo_val, hi_val, lo=-1.0, hi=1.0, pivot=0.0):

    u = np.asarray(u, dtype=float)
    lo_val = np.asarray(lo_val, dtype=float)
    hi_val = np.asarray(hi_val, dtype=float)
    out = np.zeros_like(u, dtype=float)


    if np.all(hi_val == lo_val):
        return out


    if np.all(pivot <= lo_val):
        denom = hi_val - lo_val if np.isscalar(hi_val) else np.where((hi_val - lo_val) != 0, (hi_val - lo_val), 1.0)
        out = 0.0 + (u - lo_val) * (hi - 0.0) / denom
        return out

    if np.all(pivot >= hi_val):
        denom = hi_val - lo_val if np.isscalar(hi_val) else np.where((hi_val - lo_val) != 0, (hi_val - lo_val), 1.0)
        out = lo + (u - lo_val) * (0.0 - lo) / denom
        return out


    mask_lo = (u <= pivot)
    denom_lo = (pivot - lo_val)
    denom_lo_safe = denom_lo if np.isscalar(denom_lo) else np.where(denom_lo != 0, denom_lo, 1.0)
    out[mask_lo] = lo + (u[mask_lo] - lo_val) * (0.0 - lo) / denom_lo_safe

    mask_hi = (u > pivot)
    denom_hi = (hi_val - pivot)
    denom_hi_safe = denom_hi if np.isscalar(denom_hi) else np.where(denom_hi != 0, denom_hi, 1.0)
    out[mask_hi] = 0.0 + (u[mask_hi] - pivot) * (hi - 0.0) / denom_hi_safe

    return out

def unscale_vec(u_scaled, lo_vec, hi_vec, lo=-1.0, hi=1.0):

    u_scaled = np.asarray(u_scaled, dtype=float)
    lo_vec = np.asarray(lo_vec, dtype=float)
    hi_vec = np.asarray(hi_vec, dtype=float)
    denom = (hi - lo)
    denom = denom if denom != 0 else 1.0
    out = lo_vec + (u_scaled - lo) * (hi_vec - lo_vec) / denom
    out = np.where((hi_vec - lo_vec) != 0, out, lo_vec)
    return out


def unscale_vec_zero_pivot(s, lo_val, hi_val, lo=-1.0, hi=1.0, pivot=0.0):

    s = np.asarray(s, dtype=float)
    out = np.empty_like(s, dtype=float)
    lo_v = float(lo_val); hi_v = float(hi_val)

    # 退化
    if hi_v == lo_v:
        out.fill(lo_v)
        return out

    if pivot <= lo_v:
        out = lo_v + (s - 0.0) * (hi_v - lo_v) / (hi - 0.0)
        return out
    if pivot >= hi_v:

        out = lo_v + (s - lo) * (hi_v - lo_v) / (0.0 - lo)
        return out

    mask_lo = (s <= 0)
    out[mask_lo] = lo_v + (s[mask_lo] - lo) * (pivot - lo_v) / (0.0 - lo)
    mask_hi = (s > 0)
    out[mask_hi] = pivot + (s[mask_hi] - 0.0) * (hi_v - pivot) / (hi - 0.0)
    return out

def estimate_global_range_on_raw_box(f_on_raw, u_lo, u_hi, n_random=20000, seed=42, include_vertices=True):
    rng = np.random.default_rng(seed)
    Zmin, Zmax = np.inf, -np.inf

    P = len(u_lo)
    if include_vertices:
        for bits in itertools.product([0, 1], repeat=P):
            corner = np.array(bits, dtype=float)
            u = u_lo + corner*(u_hi - u_lo)
            z = f_on_raw(u)
            Zmin = min(Zmin, z); Zmax = max(Zmax, z)

    U = rng.random((n_random, P))
    U = u_lo + U*(u_hi - u_lo)
    for u in U:
        z = f_on_raw(u)
        Zmin = min(Zmin, z); Zmax = max(Zmax, z)

    mid = 0.5*(u_lo + u_hi)
    z0 = f_on_raw(mid)
    Zmin = min(Zmin, z0); Zmax = max(Zmax, z0)

    return float(Zmin), float(Zmax)

# ===================== Fit centered model and extract (Q,g,intercept) =====================
agent = LQBandit(beta=60, csv_file=CSV_FILENAME)

try:
    exp_index = list(agent.exp_ids).index(CENTER_EXP_ID)
except ValueError as e:
    raise SystemExit(f"Cannot find experiment id '{CENTER_EXP_ID}' in agent.exp_ids") from e

x0 = agent.x[exp_index].reshape(1, -1)   # (1, P) center in original feature space
x0_flat = x0.ravel()

# Clarify: agent.x is already scaled. Keep explicit scaled/raw centers.
x0_scaled = x0.ravel()  # already scaled per note
x0_raw = agent.scaler_x.inverse_transform(x0_scaled.reshape(1, -1)).ravel()

# Convenience evaluator: model in SCALED space (inputs are scaled features)
def f_on_scaled_s(s_scaled: np.ndarray) -> float:
    s_scaled = np.asarray(s_scaled, dtype=float).ravel()
    xc = s_scaled - x0_scaled
    return 0.5 * float(xc @ Q @ xc) + float(g @ xc) + intercept


u_lo = agent.x.min(axis=0)   # shape (P,)
u_hi = agent.x.max(axis=0)   # shape (P,)

# Compute global min and max for x-axis scaling across all features
x_global_min = np.min(u_lo)
x_global_max = np.max(u_hi)
X_centered = agent.x - x0
Phi = agent.phi(X_centered)
cov = Phi.T @ Phi
theta_centered = ridge_inverse(cov, LAMBDA_REG) @ (Phi.T @ agent.y)
theta_vec = np.array(theta_centered).ravel()
if len(theta_vec) < 1 + P:
    raise SystemExit("theta too short; cannot extract linear part.")
intercept = float(theta_vec[0])
g = theta_vec[1:1+P].astype(float)
Q = reconstruct_H_from_theta(theta_vec, P).astype(float)

basename = os.path.splitext(os.path.basename(CSV_FILENAME))[0]
feat_to_idx = {name: i for i, name in enumerate(FEATURES)}


def f_on_raw_u(u_raw: np.ndarray) -> float:
    xc = u_raw - x0_flat
    return 0.5 * float(xc @ Q @ xc) + float(g @ xc) + intercept

# ===================== Global Z-range over raw box [u_lo,u_hi] =====================
Zmin_global, Zmax_global = estimate_global_range_on_raw_box(
    f_on_raw_u, u_lo, u_hi, n_random=20000, include_vertices=True
)

def z_raw_to_scaled(z_raw: float) -> float:
    if APPLY_GLOBAL_SCALING:
        return float(linear_scale_to_range(np.array(z_raw), Zmin_global, Zmax_global,
                                        SCALE_RANGE_Z[0], SCALE_RANGE_Z[1]))
    return float(z_raw)


# ===================== 2D slices (axes in raw x-space, rescaled for display) =====================
def plot_pair_slice_rescaled(fname1: str, fname2: str, n=201):
    """
    Build a mesh in RAW space around x0, evaluate the model in SCALED space, and plot against RAW (relative) axes.

    Special windows:
    - For feature index 10 (11th): ±0.5 (raw)
    - For feature index 11 (12th): ±100 (raw)
    - Others: ±30 (raw)

    Evaluation:
    - For each mesh point u_raw, compute s = agent.scaler_x.transform(u_raw),
        evaluate f_on_scaled_s(s), then unstandardize z via z = z_value*agent.y_std + agent.y_mean.

    Axes:
    - Plot against Δ(raw) relative to x0_raw so the center is (0,0).
    """
    i = feat_to_idx[fname1]
    j = feat_to_idx[fname2]

    # Helper to choose window half-width (raw units) per dimension
    def half_width(idx: int) -> float:
        if idx == 10:
            return 0.5  # 11th feature
        if idx == 11:
            return 100.0  # 12th feature
        return 30.0

    hw_i = half_width(i)
    hw_j = half_width(j)

    # Build raw grids around center
    grid_raw_i = np.linspace(x0_raw[i] - hw_i, x0_raw[i] + hw_i, n)
    grid_raw_j = np.linspace(x0_raw[j] - hw_j, x0_raw[j] + hw_j, n)

    # Relative axes (Δ raw from center) for plotting extents/ticks
    rel_i = grid_raw_i - x0_raw[i]
    rel_j = grid_raw_j - x0_raw[j]

    # Prepare containers
    Z = np.empty((n, n), dtype=float)

    # Optional transform round-trip checks at a few points (center and corners)
    def check_roundtrip(raw_point: np.ndarray) -> float:
        s = agent.scaler_x.transform(raw_point.reshape(1, -1)).ravel()
        raw_back = agent.scaler_x.inverse_transform(s.reshape(1, -1)).ravel()
        return float(np.max(np.abs(raw_back - raw_point)))

    # Build a template raw vector anchored at x0_raw
    base_raw = x0_raw.copy()

    # Debug: check a few sample points
    samples = [
        base_raw,
        base_raw.copy(),
        base_raw.copy(),
        base_raw.copy()
    ]
    samples[1][i] = x0_raw[i] - hw_i; samples[1][j] = x0_raw[j] - hw_j
    samples[2][i] = x0_raw[i] + hw_i; samples[2][j] = x0_raw[j] - hw_j
    samples[3][i] = x0_raw[i] + hw_i; samples[3][j] = x0_raw[j] + hw_j
    max_diffs = [check_roundtrip(p) for p in samples]


    # Evaluate over mesh (transform BEFORE sending to the model; unstandardize z afterwards)
    for a in range(n):
        for b in range(n):
            u_raw = base_raw.copy()
            u_raw[i] = grid_raw_i[a]
            u_raw[j] = grid_raw_j[b]
            s = agent.scaler_x.transform(u_raw.reshape(1, -1)).ravel()
            z_value = f_on_scaled_s(s)
            z_plot = z_value * agent.y_std + agent.y_mean
            Z[a, b] = z_plot

    # Plot against relative RAW axes
    plt.figure(figsize=(1.4, 1.2))
    im = plt.imshow(
        Z.T,
        origin='lower',
        extent=[rel_i.min(), rel_i.max(), rel_j.min(), rel_j.max()],
        aspect='auto',
        cmap='viridis',
        vmin=-1, vmax=-0.15,
    )
    #cbar = plt.colorbar(im, fraction=0.046, pad=0.04)
    #cbar.set_ticks([-1.0, -0.15])
    #cbar.ax.tick_params(labeltop=True, labelbottom=True)

    # Ticks at symmetric positions around 0 within the actual extents
    def tick_candidates(lo, hi, base):
        vals = np.array([-base, -base/2, 0.0, base/2, base])
        return [v for v in vals if (v >= lo and v <= hi)]

    xt = tick_candidates(rel_i.min(), rel_i.max(), hw_i)
    yt = tick_candidates(rel_j.min(), rel_j.max(), hw_j)
    # Format tick labels: one decimal if axis feature is ΔVolt, else integer
    if fname1 == "ΔVolt":
        plt.xticks(xt, [f"{v:.1f}" for v in xt])
    else:
        plt.xticks(xt, [f"{v:.0f}" for v in xt])

    if fname2 == "ΔVolt":
        plt.yticks(yt, [f"{v:.1f}" for v in yt])
    else:
        plt.yticks(yt, [f"{v:.0f}" for v in yt])

    # Mark the center
    #plt.scatter([0.0], [0.0], marker='o')

    plt.xlabel(f"{fname1} (raw)")
    plt.ylabel(f"{fname2} (raw)")
    #plt.title(f"Relative RAW contour around x0 | [{fname1}, {fname2}] | windows: ±{hw_i}, ±{hw_j}")
    plt.tight_layout()
    if SAVE_FIG:
        out = f"{fname1}_{fname2}.eps"
        outpath = os.path.join(OUTPUT_DIR, out)
        plt.savefig(outpath, dpi=300)
        print(f"[saved] {outpath}")


if DRAW_SCALED:
    for n1, n2 in PAIRS_TO_PLOT:
        plot_pair_slice_rescaled(n1, n2, n=GRID_N)
