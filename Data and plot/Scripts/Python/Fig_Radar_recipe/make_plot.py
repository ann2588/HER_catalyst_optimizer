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
    "stable_id": "Fig_Recipe Radar plot",
    "script": __file__,
    "data_keys": "result_forRadar", # or In folder
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


import numpy as np
import pandas as pd
import os
import matplotlib.pyplot as plt
from tabulate import tabulate

# Use the specified file path
file_path = get_data(FIGURE_METADATA["data_keys"])
df = pd.read_csv(file_path)

# === elemental composition ===

components = ["Mg", "Se", "V", "Fe", "Cu", "Cr", "Ni", "P", "S", "Co"]
readout_column = 'Overpotential V at 50.0 mA cm-2'

# === convert equivalent to abs concentration ===
def absolute_concentration(values):
    """
    Compute absolute concentration as:
    C_i = X_i * 0.2 * 50e-6 / (sum(X_all) * 50e-6 + 5e-3)
    Result in mol/L (M)
    If computed concentration is zero, replace with 1e-6 M (≈0.001 mM)
    """
    total = values.sum()
    numerator = values * 0.2 * 50e-6
    denominator = (total * 50e-6) + 5e-3
    if denominator == 0:
        return np.zeros_like(values)
    abs_conc = numerator / denominator

    # === Avoid zero values for log plotting ===
    abs_conc[abs_conc <= 0] = 1e-3  # 1 μM floor
    return abs_conc

# === Radar Chart  ===
def plot_radar_chart(exp_id, color):
    row = df[df['Experiment'] == exp_id]
    if row.empty:
        print(f"Experiment {exp_id} not found.")
        return

    exp_data = row.iloc[0]
    values_raw = exp_data[components].to_numpy(dtype=float)
    values_abs_M = absolute_concentration(values_raw)
    values_abs_mM = values_abs_M * 1000  # convert to mM

    # >>> Print absolute concentration table (mM)
    print(f"\n=== Absolute concentration for {exp_id} ===")
    data_table = pd.DataFrame({
        "Element": components,
        "Raw Value": values_raw,
        "Abs. Concentration (mM)": values_abs_mM
    })

    desired_order = ['V', 'Cr', 'Fe', 'Co', 'Ni', 'Cu', 'Mg', 'S', 'Se', 'P']

    sorted_table = data_table.set_index("Element").loc[desired_order].reset_index()
    float_cols = ["Raw Value", "Abs. Concentration (mM)"]
    sorted_table[float_cols] = sorted_table[float_cols].round(1)
    sorted_table.loc[
        sorted_table["Abs. Concentration (mM)"] == 1,
        "Abs. Concentration (mM)"
    ] = 0

    print(tabulate(sorted_table, headers="keys",
                showindex=False, tablefmt="pretty", floatfmt=".1f"))

    # === Prepare radar data ===
    values = np.concatenate((values_abs_mM, [values_abs_mM[0]]))  # close radar loop
    angles = np.linspace(0, 2 * np.pi, len(components), endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(1.6, 1.6), subplot_kw=dict(polar=True))
    cmap = plt.colormaps.get_cmap('YlGnBu_r')

    # === Use logarithmic scale ===
    ax.set_rscale('log')
    ax.set_rlim(1, 100)  
    ax.set_rticks([1, 10, 100])
    ax.set_yticklabels([])  
    ax.tick_params(axis='y', labelsize=3)
    ax.yaxis.grid(True, linestyle='--', linewidth=0.5, alpha=0.7)
    # === Plot data ===
    ax.fill(angles, values, color=color, alpha=0.4)
    ax.plot(angles, values, color=color, linewidth=1.2)

    # === Axis labels ===
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(components, fontsize=8, fontname='Arial', fontweight='bold')

    # === Aesthetic tweaks ===
    ax.grid(color='gray', linestyle='--', linewidth=0.5, alpha=0.7)
    plt.tight_layout(pad=0.5)

    # === Save output ===
    save_dir = OUTPUT_DIR
    plt.savefig(os.path.join(save_dir, f"{exp_id}_Radar_Recipe_log_100mM.png"), dpi=600)
    plt.savefig(os.path.join(save_dir, f"{exp_id}_Radar_Recipe_log_100mM.eps"), dpi=600)
    plt.close(fig)

    return data_table

# === 範例使用 ===
colors = {
    "campaign1": "#2F3E75",  
    "campaign2": "#D98E4A",  
    "campaign3": "#567C55",  
    "campaign4": "#B44A3F",  
    "campaign5": "#2E2E2E" 

}

plot_radar_chart('exp59', colors['campaign1']) ## Campaign 1 starting
plot_radar_chart('exp136',  colors['campaign2']) ## Campaign 2 starting
plot_radar_chart('exp169', colors['campaign3']) ## Campaign 3 starting
plot_radar_chart('exp518', colors['campaign4']) ## Campaign 4 starting
plot_radar_chart('exp590', colors['campaign5']) ## Campaign 5 starting

plot_radar_chart('exp715', colors['campaign1']) ## Campaign 1 optimal
plot_radar_chart('exp839', colors['campaign2']) ## Campaign 2 optimal
plot_radar_chart('exp931', colors['campaign3']) ## Campaign 3 optimal
plot_radar_chart('exp1031', colors['campaign4']) ## Campaign 4 optimal
plot_radar_chart('exp1238', colors['campaign5']) ## Campaign 5 optimal