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
    "stable_id": "Fig_hessian_full_campaign2",
    "script": __file__,
    "data_keys": "In folder",
    "figure_type": "SI"   # or "Main"
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
from LQV4_forpost import LQBandit
import numpy as np
np.set_printoptions(precision=2, suppress=True)
import pandas as pd


MAKE_PLOTS = True
FEATURES = ["ΔV", "ΔCr", "ΔFe", "ΔCo", "ΔNi", "ΔCu", "ΔMg", "ΔS", "ΔSe", "ΔP", "ΔVolt", "ΔTime"]
P = len(FEATURES)

PAIRS_TO_PLOT = [
    ("ΔCo", "ΔFe"),
    ("ΔCo", "ΔV"),
    ("ΔCo", "ΔCr"),
    ("ΔCo", "ΔVolt"),
    ("ΔCo", "ΔTime"),
    ("ΔCo", "ΔP"),
    ("ΔMg", "ΔFe"),
    ("ΔMg", "ΔV"),
    ("ΔMg", "ΔCr"),
    ("ΔMg", "ΔVolt"),
    ("ΔMg", "ΔTime"),
    ("ΔMg", "ΔP"),
    ("ΔMg", "ΔCo"),
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
    ("ΔTime", "ΔVolt")
]

def reconstruct_H_from_theta(theta_vec: np.ndarray, p: int) -> np.ndarray:
    th = np.ravel(theta_vec)
    need = 1 + p + (p*(p+1))//2
    if th.size < need:
        raise ValueError(f"theta too short: {th.size} < {need}")
    quad = th[1+p : 1+p + (p*(p+1))//2]  # upper-tri row-wise
    
    H = np.zeros((p,p), float)
    idx = 0
    for i in range(p):
        span = p - i
        row = quad[idx:idx+span]; idx += span
        H[i,i] = 2.0*row[0]
        if span > 1:
            H[i, i+1:p] = row[1:]
    H = H + H.T - np.diag(np.diag(H))
    
    return H

def show_heatmap(M, title, suffix=""):
    if not MAKE_PLOTS:
        return
    
    M_masked = M.copy()
    valid_vals = M_masked[np.isnan(M_masked)]
    a = np.nanmax(np.abs(valid_vals)) if valid_vals.size > 0 else 0.1

    cmap = plt.get_cmap('coolwarm_r').copy()
    cmap.set_bad(color = 'white')  
    
    plt.figure(figsize=(3.6, 3.6))
    im = plt.imshow(M_masked, vmin=-a, vmax=a, cmap=cmap)
    plt.colorbar(im, fraction=0.046, pad=0.04)
    plt.xticks(range(P), FEATURES, rotation=90, fontsize=1, font="Arial")
    plt.yticks(range(P), FEATURES, fontsize=1, font="Arial")

    ax = plt.gca()
    ax.xaxis.set_ticks_position('top')
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/{title}_heatmap.eps", format="eps")
    plt.savefig(f"{OUTPUT_DIR}/{title}_heatmap.png", format="png")



num = 590
os.getcwd()
df = pd.read_csv(f"{SCRIPT_DIR}/Set 2/DoE.csv")
CSV_FILENAME_1 = f"{SCRIPT_DIR}/Set 2/DoE_{num}.csv"
df.sample(frac=1, random_state=None).head(num).to_csv(f"{CSV_FILENAME_1}",index=False)
agent = LQBandit(beta=60, csv_file= CSV_FILENAME_1)
H_DOE_120 = reconstruct_H_from_theta(agent.theta.ravel(), P)
show_heatmap(H_DOE_120, 'DoE', 'phi from model')

CSV_FILENAME_2 = f"{SCRIPT_DIR}/Set 2/DoE_{num}_stage1.csv"
pd.concat([pd.read_csv(f"{CSV_FILENAME_1}"), pd.read_csv(f"{SCRIPT_DIR}/Set 2/Campaign2_stage1_only.csv")]).to_csv(CSV_FILENAME_2, index=False)
agent = LQBandit(beta=60, csv_file= CSV_FILENAME_2)
H_STAGE_1 = reconstruct_H_from_theta(agent.theta.ravel(), P)
show_heatmap(H_STAGE_1, 'DoE + stage 1', 'phi from model')

CSV_FILENAME_3 = f"{SCRIPT_DIR}/Set 2/DoE_{num}_stage1_stage2.csv"
pd.concat([pd.read_csv(f"{CSV_FILENAME_2}"), pd.read_csv(f"{SCRIPT_DIR}/Set 2/Campaign2_stage2_only.csv")]).to_csv(CSV_FILENAME_3, index=False)
agent = LQBandit(beta=60, csv_file= CSV_FILENAME_3)
H_STAGE_2 = reconstruct_H_from_theta(agent.theta.ravel(), P)
show_heatmap(H_STAGE_2, 'DoE + stage 2', 'phi from model')