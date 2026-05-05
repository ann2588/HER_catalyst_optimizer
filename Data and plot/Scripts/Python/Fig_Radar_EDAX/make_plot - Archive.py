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
    "stable_id": "Fig_EDAX Radar plot",
    "script": __file__,
    "data_keys": "In script", # or In folder
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

###========================================================================###



import matplotlib.pyplot as plt
import numpy as np
from tabulate import tabulate

elements = ["Mg", "Se", "V", "O", "Fe", "Cu", "Cr", "Ni", "P", "S", "Co"]

desired_order = ['O', 'V', 'Cr', 'Fe', 'Co', 'Ni', 'Cu', 'Mg', 'S', 'Se', 'P']

campaigns = {
    "Campaign1": {"O": 48.7, "Mg": 1.4, "P": 3.2, "V": 3.9, "Cr": 2.0, "Fe": 18.8, "Co": 5.8},
    "Campaign2": {"O": 48.8, "Mg": 3.7, "P": 2.3, "Cr": 2.4, "Fe": 20.0, "Co": 9.8, "Ni": 1.8},
    "Campaign3": {"O": 12.3, "P": 0.5, "Co": 0.6, "Ni": 17.4, "Cu": 56.8},
    "Campaign4": {"O": 12.9, "P": 9.4, "Fe": 30.3, "Co": 34.0},
}

for name, data in campaigns.items():


    rows_dict = {e: data.get(e, 0) for e in elements}


    sorted_rows = [[e, rows_dict.get(e, 0)] for e in desired_order]


    for r in sorted_rows:
        if r[1] == 1:
            r[1] = 0


    print(f"\n=== {name} ===")
    print(tabulate(sorted_rows, headers=["Element", "Value"], 
                   tablefmt="pretty", floatfmt=".3f"))


colors = {
    "Campaign1": "#2F3E75", 
    "Campaign2": "#D98E4A",  
    "Campaign3": "#567C55",  
    "Campaign4": "#B44A3F",  
}

angles = np.linspace(0, 2 * np.pi, len(elements), endpoint=False).tolist()
angles += angles[:1]

plt.rcParams.update({'font.size': 12, 'font.family': 'Arial'})

def normalize_to_100(vals):
    """Normalize so the total sums to 100%, and replace 0 with 1 (for log scale plotting)."""
    vals = np.array(vals, dtype=float)
    total = vals.sum()
    v_norm = vals / total * 100 if total > 0 else vals

    v_norm[v_norm <= 0] = 1
    return np.concatenate((v_norm, [v_norm[0]]))


for name, data in campaigns.items():
    raw = [data.get(e, 0) for e in elements]
    values = normalize_to_100(raw)
    color = colors[name]

    fig, ax = plt.subplots(figsize=(1.6, 1.6), subplot_kw=dict(polar=True))
    ax.fill(angles, values, color=color, alpha=0.4)
    ax.plot(angles, values, color=color, linewidth=1.5)

    # === Log scale ===
    ax.set_rscale('log')
    ax.set_rlim(1, 100)  
    ax.set_rticks([1, 10, 100])
    ax.set_yticklabels([]) 
    ax.tick_params(axis='y', labelsize=3)
    ax.yaxis.grid(True, linestyle='--', linewidth=0.5, alpha=0.7)

    # === Label  ===
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(elements, fontsize=8, fontname='Arial', fontweight='bold')
    ax.grid(color='gray', linestyle='--', linewidth=0.5, alpha=0.7)

    plt.tight_layout(pad=0.5)

    save_dir = OUTPUT_DIR
    plt.savefig(os.path.join(save_dir, f"{name}_Radar_EDAX_max100p.eps"), format="eps", dpi=600)
    plt.savefig(os.path.join(save_dir, f"{name}_Radar_EDAX_max100p.png"), dpi=600)
    plt.close(fig)

