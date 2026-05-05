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
    "stable_id": "Fig_surface_redox",
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
import matplotlib

global Vmax
Vmax = 600  # Change the maximum number of your exp
colors = sns.color_palette("Spectral", Vmax)
exp_dicts = []
def gtdata():  # this function navigate you to original parent folder and print out the subfolder
    path = DATAPATH
    os.chdir(path)
    folder_ordered = sorted(os.listdir(), key=lambda f: os.path.getctime(os.path.join(os.getcwd(), f)), reverse=True)
    print(folder_ordered)

def IndividualSRCV(folder_P, exp_dicts):
    gtdata();
    os.chdir(folder_P)

    for dir, exp in exp_dicts.items():
        print(dir, exp)
        plt.figure(figsize=(2.4, 1.8))
        plt.xlim(0.0, -0.65)
        plt.ylim(100, -150)
        plt.xlabel('Potential V vs. RHE')
        plt.ylabel('Current density mA cm-2')
        os.chdir(dir)
        PotentialConversion()

        cmap = plt.get_cmap('rocket')  # Use the 'Spectral' colormap
        PlotsrdepCV(gasKOH='H2KOH')
        plt.tight_layout(pad = 1.0)
        file_formats = ['png','eps']
        for fmt in file_formats:
            if exp == 'exp27':
                plt.savefig(os.path.join(OUTPUT_DIR, f'SRDEPCV_{exp}.{fmt}'), dpi=600)
            plt.savefig(os.path.join(os.getcwd(), f'SRDEPCV_{exp}.{fmt}'), dpi=600)
        #plt.legend(frameon=False) # turn on/off as needed
        os.chdir('..')
        os.chdir('..')

if __name__ == '__main__':
    gtdata()
    dirs = get_sorted_experiment_dirs(DATAPATH)
    exp_dicts = {dir: dir.split('-')[3] for dir in dirs[:523]}
    IndividualSRCV(DATAPATH, exp_dicts=exp_dicts)