import os
import sys

SCRIPT_DIR = os.path.dirname(__file__)
# this points to: Scripts/Python/
SCRIPTS_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
UTIL_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "utils"))
sys.path.append(SCRIPTS_ROOT)
sys.path.append(UTIL_ROOT)

from registry import get_data_path

FIGURE_METADATA = {
    "stable_id": "Fig_Ovp_trajectory",
    "script": __file__,
    "data_keys": "All_Ovp_Cdl", # or In folder
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
DATAPATH = get_data_path(FIGURE_METADATA["data_keys"])
###========================================================================###

import os
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import matplotlib as mpl


############################
# UNIVERSAL FIGURE TEMPLATE
############################

mpl.rcParams.update({

    # font
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial"],
    "font.size": 6,

    # axes
    "axes.labelsize": 6,
    "axes.titlesize": 3,
    "axes.linewidth": 0.5,

    # ticks
    "xtick.labelsize": 6,
    "ytick.labelsize": 6,
    "xtick.major.width": 0.5,
    "xtick.minor.width": 0.5,
    "ytick.minor.width": 0.5,
    "ytick.major.width": 0.5,
    "xtick.major.size": 3,
    "ytick.major.size": 3,

    # legend
    "legend.fontsize": 6,
    "legend.frameon": False,

    # lines
    #"lines.linewidth": 1,

    # savefig
    "savefig.dpi": 300
})

# =========================
# User inputs
# =========================
csv_path = DATAPATH
output_dir = OUTPUT_DIR

X0list       = [59, 136, 169, 518, 590]
startinglist = [609, 729, 859, 979, 1099]
endlist      = [728, 858, 978, 1098, 1258]

namemap = {
    59:  "campaign1",
    136: "campaign2",
    169: "campaign3",
    518: "campaign4",
    590: "campaign5"
}

colormap = {
    59: "Blues",
    136: "Oranges",
    169: "Greens",
    518: "Purples",
    590: "Grays"
}

# =========================
# Load data
# =========================
df = pd.read_csv(csv_path)

# Clean experiment ID: "exp609" -> 609
df["ExpID"] = (
    df["Experiment"]
    .astype(str)
    .str.extract(r"exp\s*#?\s*(\d+)", expand=False)
    .astype(int)
)

# Overpotential column
ycol = "Overpotential @ 50 mA"

# Optional:
# If you want eta50 to be shown as positive values, uncomment this line
# df[ycol] = df[ycol].abs()

# Make output folder
Path(output_dir).mkdir(parents=True, exist_ok=True)

# =========================
# Plot each campaign
# =========================
for x0_id, start_id, end_id in zip(X0list, startinglist, endlist):
    campaign_name = namemap[x0_id]
    cmap_name = colormap[x0_id]

    # Build trial ID list
    exp_ids = list(range(start_id, end_id + 1))
    trial_numbers = np.arange(1, len(exp_ids) + 1)

    # Extract campaign rows in the exact order of exp_ids
    sub = (
        df.set_index("ExpID")
          .reindex(exp_ids)
          .reset_index()
    )

    y = sub[ycol].to_numpy()

    # Get X0 reference value if available
    x0_val = np.nan
    if x0_id in df["ExpID"].values:
        x0_val = df.loc[df["ExpID"] == x0_id, ycol].iloc[0]

    # Generate progressive colors within each colormap
    cmap = plt.get_cmap(cmap_name)
    colors = cmap(np.linspace(0.35, 0.85, len(y[y<-0.1])))

    # Plot
    fig, ax = plt.subplots(figsize= (1.5, 1.2), dpi=300)

    # line
    #ax.plot(trial_numbers, y, lw=1.2, color=cmap(0.65), alpha=0.8, zorder=1)

    # scatter with evolving shade
    mask = y < -0.1
    ax.scatter(trial_numbers[mask], y[mask], c=colors, s=10, edgecolor=(0.85, 0.85, 0.85), linewidths = 0.3 , zorder=2)

    # X0 reference line
    if not np.isnan(x0_val):
        ax.axhline(
            x0_val,
            ls="--",
            lw=1.0,
            color="black",
            alpha=0.7,
            label=f'X0 = exp{x0_id}'
        )

    #ax.set_title(f"{campaign_name}: overpotential evolution", fontsize=12)
    #ax.set_xlabel("Trial number")
    #ax.set_ylabel(r"$\eta_{50}$ vs RHE")
    ax.set_ylim([-1, 0])
    ax.set_xlim(1, 120)

    # If you want exactly 1–120 on x even when missing rows exist
    ax.set_xticks([1, 30, 60, 90, 120])
    ax.set_yticks([-1.0, -0.5, 0.0])

    # nice frame
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(direction="out")

    # warn if missing experiments
    missing_mask = sub[ycol].isna()
    n_missing = missing_mask.sum()
    if n_missing > 0:
        print(f"[Warning] {campaign_name}: {n_missing} experiment(s) missing in CSV.")
        missing_trials = trial_numbers[missing_mask.to_numpy()]
        '''
        ax.scatter(
            missing_trials,
            np.full_like(missing_trials, np.nanmin(y[np.isfinite(y)]) if np.isfinite(y).any() else 0),
            marker="x",
            s=40,
            color="red",
            label="Missing data"
        )
        '''

    if not np.isnan(x0_val) or n_missing > 0:
        ax.legend(frameon=False)

    plt.tight_layout()

    save_path_png = os.path.join(output_dir, f"{campaign_name}_eta50_evolution.png")
    plt.savefig(save_path_png, dpi=300, bbox_inches="tight")
    save_path_svg = os.path.join(output_dir, f"{campaign_name}_eta50_evolution.svg")
    plt.savefig(save_path_svg, bbox_inches="tight")
    plt.close()

print(f"Done. Figures saved in: {output_dir}")