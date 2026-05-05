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
    "stable_id": "Fig_LSV_trajectory",
    "script": __file__,
    "data_keys": "All data", # or In folder
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

import os
import re
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import seaborn as sns
plt.rcParams['lines.linewidth'] = 1
plt.rcParams.update({'font.size': 5})  # Apply globally

def extract_experiment_number(experiment_name):
    number_str = ''.join(filter(str.isdigit, experiment_name))
    return int(number_str)

def process_cv_file(file, experiment_name):
        
        df = pd.read_csv(file, delimiter='\t')  # Assuming the data is tab-delimited
        corrected_df = df.copy()
        corrected_df[['Potential V vs RHE', 'Current mA cm-2']] = corrected_df['Potential V vs RHE, Current mA cm-2'].str.split(',',expand=True)
        corrected_df['Potential V vs RHE'] = pd.to_numeric(corrected_df['Potential V vs RHE'])
        corrected_df['Current mA cm-2'] = pd.to_numeric(corrected_df['Current mA cm-2'])
        corrected_df = corrected_df.drop('Potential V vs RHE, Current mA cm-2', axis=1)

        pattern = re.compile(r'(\d+)mVs_Efin_*')
        match = pattern.search(file)
        if match:
            sr = int(match.group(1))

        return sr, corrected_df 

def plot_some_bkscan(results_dict, startexp, endexp, filename, color_assign):

    # Filter the results dictionary to include only experiments within the specified range
    filtered_results = {exp: data for exp, data in results_dict.items() if startexp <= int(exp.split('exp')[-1]) <= endexp}

    colors = sns.color_palette(color_assign, len(filtered_results))
    plt.rcParams.update({'font.size': 5})  # Apply globally
    plt.figure(figsize=(2.0, 1.4))
    plt.xlim(0.1, -1.0)
    plt.ylim(10, -140)

    # Plot each individual curve without a legend
    for i, (exp, data) in enumerate(filtered_results.items()):
        sr, df = data
        midpoint = len(df) // 2
        first_half = df.iloc[:midpoint].copy()
        second_half = df.iloc[midpoint:].copy()
        offset = second_half['Current mA cm-2'].iloc[-1]
        print(offset)
        # Plot without legend
        plt.plot(second_half['Potential V vs RHE'], second_half['Current mA cm-2']-offset, color=colors[i],linewidth = 1)

        # Debugging check for colors
        print(f"Experiment: {exp}, Color: {colors[i]}")

    plt.xlabel('Potential V vs. RHE')
    plt.ylabel('Current density (mA/cm$^2$)')

    
    cmap = plt.get_cmap(color_assign)
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=0, vmax=len(filtered_results)-1))
    sm.set_array([])
    bar = plt.colorbar(sm, ax=plt.gca(), orientation='vertical')
    bar.set_ticks([])    
    # Save the figure with legend
    plt.tight_layout(pad = 0.5)
    plt.savefig(f"{OUTPUT_DIR}/{filename}.eps")
    plt.savefig(f"{OUTPUT_DIR}/{filename}.png", dpi=600)     

def plot_some_bkscan_animated(results_dict, startexp, endexp, filename, color_assign):
    # Filter the results dictionary to include only experiments within the specified range
    filtered_results = {exp: data for exp, data in results_dict.items() if startexp <= int(exp.split('exp')[-1]) <= endexp}

    colors = sns.color_palette(color_assign, len(filtered_results))  # Adjusted the color palette size based on filtered results
    plt.rcParams.update({'font.size': 12})  # Apply globally
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    ax.set_xlim(0.1, -1.0)
    ax.set_ylim(20, -140)
    ax.set_xlabel('Potential V vs. RHE')
    ax.set_ylabel('Current density (mA cm⁻²)')
    # Create a color bar
    cmap = plt.get_cmap(color_assign)
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=0, vmax=len(filtered_results)-1))
    sm.set_array([])
    plt.colorbar(sm, ax=plt.gca(), orientation='vertical', label='Experiment Index')

    # Adjust layout to prevent cropping
    plt.tight_layout()

    # Create a list of data to plot
    plots_data = []
    for i, (exp, data) in enumerate(filtered_results.items()):
        sr, df = data
        midpoint = len(df) // 2
        #first_half = df.iloc[:midpoint].copy()
        second_half = df.iloc[midpoint:].copy()
        offset = second_half['Current mA cm-2'].iloc[-1]
        print(offset)
        plots_data.append((second_half['Potential V vs RHE'], second_half['Current mA cm-2']-offset, colors[i]))
        # Plot without legend

    # Animation function
    def animate(i):
        if i < len(plots_data):
            x, y, color = plots_data[i]
            ax.plot(x, y, color=color)
        return ax,

    ani = animation.FuncAnimation(fig, animate, frames=len(plots_data), interval=200, repeat=False)

    # Save animation with bbox_inches to prevent cropping
    ani.save(f"{OUTPUT_DIR}/{filename}.gif", writer='pillow', dpi=600)

def process_H2KOH_subfolder(H2KOH_subfolder, experiment_name, results_list, results_dict):
    print(f"Processing H2KOH subfolder: {H2KOH_subfolder}")
    os.chdir(H2KOH_subfolder)
    
    files = glob.glob('*sr_50mVs*vsRHE.txt')  # Only consider files ending with 'vsRHE.txt'
    print(f"Number of files found: {len(files)}")

    if not files:
        print(f"No files found in {H2KOH_subfolder}")
        os.chdir('..')
        return

    current_densities = np.arange(10, 60, 10)  # [10, 20, 30, 40, 50] mA/cm²
    for file in files:
        sr, corrected_df = process_cv_file(file, experiment_name)
        results_dict[experiment_name] = (sr, corrected_df)

        second_half = corrected_df.iloc[len(corrected_df) // 2:].copy()  # Extract backward scan

        # Interpolate potential values at different current densities
        overpotentials = [experiment_name] + [
            np.interp(-i, second_half['Current mA cm-2'], second_half['Potential V vs RHE'])
            for i in current_densities
        ]

        expected_length = len(current_densities) + 1  # Experiment name + interpolated values
        print(f"Appending row (Expected {expected_length} values, Got {len(overpotentials)}) → {overpotentials}")
        
        if len(overpotentials) != expected_length:
            print("Error: Mismatched row length! Skipping entry.")
            continue

        results_list.append(overpotentials)

    os.chdir('..')


def process_main_subfolder(main_subfolder, results_list,results_dict):
    print(f"Processing main subfolder: {main_subfolder}")
    print(os.listdir(main_subfolder))
    H2KOH_subfolders = [os.path.join(main_subfolder, f) for f in os.listdir(main_subfolder) if
                        os.path.isdir(os.path.join(main_subfolder, f)) and 'H2KOH' in f]
    print(f"H2KOH subfolders found: {H2KOH_subfolders}")
    
    for H2KOH_subfolder in H2KOH_subfolders:
        experiment_name = os.path.basename(main_subfolder).split('-')[3]  # Extract experiment name from folder name
        process_H2KOH_subfolder(H2KOH_subfolder, experiment_name, results_list, results_dict)
    
    
        

def process_folder(folder, results_list, target_experiments=None):
    """Processes subfolders in the given folder. If target_experiments are specified,
    only subfolders matching those experiment IDs will be processed; otherwise, all subfolders are processed."""
    
    os.chdir(folder)
    print(f"Processing folder: {folder}")

    # Get all subfolders in the directory
    all_subfolders = [os.path.join(folder, f) for f in os.listdir(folder) if os.path.isdir(os.path.join(folder, f))]
    results_dict = {}
    # Filter subfolders if target_experiments is provided, else process everything
    main_subfolders = (
        [sub for sub in all_subfolders if any(exp in sub for exp in target_experiments)]
        if target_experiments else all_subfolders
    )

    print(f"Main subfolders found: {main_subfolders}")

    # Process each relevant subfolder
    for main_subfolder in main_subfolders:
        process_main_subfolder(main_subfolder, results_list, results_dict)
    print(results_dict)
    os.chdir('..')
    X0list       = [59, 136, 169, 518, 590]
    startinglist = [609, 729, 859, 979,1099]
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

    for x0, start, end in zip(X0list, startinglist, endlist):
        name = namemap.get(x0, f"{x0}")   # fallback
        color = colormap.get(x0, f"{x0}")
        print(x0, start, end, name)
        
        fname = f"{name}_trajectory_LSV"

        plot_some_bkscan(
            results_dict,
            start,
            end,
            fname,
            color
        )

        plot_some_bkscan_animated(
            results_dict,
            start,
            end,
            fname,
            color
        )


def main():
    base_path = get_data_folder(FIGURE_METADATA["data_keys"])  # Update this with your folder name
    results_list = []
    process_folder(base_path, results_list)

if __name__ == "__main__":
    main()
