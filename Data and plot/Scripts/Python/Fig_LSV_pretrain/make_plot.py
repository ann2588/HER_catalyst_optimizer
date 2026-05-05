import os
import sys

SCRIPT_DIR = os.path.dirname(__file__)
# this points to: Scripts/Python/
SCRIPTS_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
UTIL_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "utils"))
sys.path.append(SCRIPTS_ROOT)
sys.path.append(UTIL_ROOT)

from registry import get_data_folder

FIGURE_METADATA = {
    "stable_id": "Fig_LSV_pretrain",
    "script": __file__,
    "data_keys": "All data", # or In folder
    "figure_type": "Main"   # "SI" or "Main"
}

def get_output_dir(meta):
    base = os.path.dirname(__file__)
    fig_base = "Figures_SI" if meta["figure_type"] == "SI" else "Figures_Main"
    outdir = os.path.join(base, "..", "..", ".." , fig_base, meta["stable_id"])
    os.makedirs(outdir, exist_ok=True)
    return outdir

OUTPUT_DIR = get_output_dir(FIGURE_METADATA)
os.makedirs(OUTPUT_DIR, exist_ok=True)
DATAPATH = get_data_folder(FIGURE_METADATA["data_keys"])

###========================================================================###

from utils.Utilities import *
plt.rcParams['lines.linewidth'] = 1
plt.rcParams.update({'font.size': 8})  # Apply globally
plt.rcParams.update({'font.family': 'Arial'})  # Apply globally
import matplotlib as mpl

global Vmax
Vmax = 600  # Change the maximum number of your exp
colors = sns.color_palette("Spectral", Vmax)
exp_dicts = []
def gtdata():  # this function navigate you to original parent folder and print out the subfolder
    path = DATAPATH
    os.chdir(path)
    folder_ordered = sorted(os.listdir(), key=lambda f: os.path.getctime(os.path.join(os.getcwd(), f)), reverse=True)
    print(folder_ordered)

def SummaryHERCV(folder_P, exp_dicts=exp_dicts, cycle='last', ovp='high'):
    if ovp == 'high':
        xlim = -1.0
    else:
        xlim = -0.4
    gtdata()
    plt.figure(figsize=(4.8, 1.8))
    plt.xlim(0, xlim)
    plt.ylim(12, -140)
    cycle = cycle
    plt.xlabel('Potential V vs. RHE')
    plt.ylabel('Current density mA cm-2')
    
    cmap = plt.get_cmap('Spectral')  # Use the 'Spectral' colormap
    norm = mpl.colors.Normalize(vmin=1, vmax=Vmax)  # Normalization for color map
    # Get experiment directories and sort them
    os.chdir(f'{folder_P}')

    for dir, exp in exp_dicts.items():
        os.chdir(dir)

        # Get the color for this dataset based on the experiment number (exp)
        color_index = int(exp.split('exp')[-1])  # Extract the experiment number
        color = cmap(norm(color_index))  # Map the experiment number to a color

        # Plot the data with the mapped color
        print(f'{exp}')
        PlotHERCV(gasKOH='H2KOH', color=color, label=f'{exp}', cycle=f'{cycle}')

        os.chdir('..')
    plt.bar
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])  # Dummy array for ScalarMappable
    cbar = plt.colorbar(sm, ax=plt.gca(), orientation='vertical')
    cbar.set_label(f'Recipe Index')

    plt.tight_layout(pad = 1.0)
    file_formats = ['png','eps']
    for fmt in file_formats:
        plt.savefig(os.path.join(OUTPUT_DIR, f'LSV_pretrain.{fmt}'), dpi=600)


if __name__ == '__main__':
    gtdata()
    dirs = get_sorted_experiment_dirs(DATAPATH)
    exp_dicts = {dir: dir.split('-')[3] for dir in dirs[:523]}
    SummaryHERCV(folder_P=DATAPATH, exp_dicts=exp_dicts, cycle='last', ovp='high')