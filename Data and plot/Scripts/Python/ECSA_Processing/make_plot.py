import os
import sys

SCRIPT_DIR = os.path.dirname(__file__)
# this points to: Scripts/Python/
SCRIPTS_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
UTIL_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "utils"))
sys.path.append(SCRIPTS_ROOT)
sys.path.append(UTIL_ROOT)

from registry import get_data_folder, get_data

FIGURE_METADATA = {
    "stable_id": "Fig_ECSA",
    "script": __file__,
    "data_keys": ["All data", "result_all_campaign", "Capacitance_all"], # or In folder
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

##================================================================###
'''
This script perform ECSA analysis for the raw data under the parent folder.
Return a cvs file to summarize every experiment in the dataset
'''


import os
import re
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import linregress
import seaborn as sns

plt.rcParams['lines.linewidth'] = 1
plt.rcParams.update({'font.size': 8})  # Apply globally
plt.rcParams.update({'font.family': 'Arial'})  # Apply globally

def extract_experiment_number(experiment_name):
    number_str = ''.join(filter(str.isdigit, experiment_name))
    return int(number_str)


def process_cv_file(file, x_idx, y_diff, target_potential):
    try:
        df = pd.read_csv(file, delimiter='\t')  # Assuming the data is tab-delimited

        new_df = df.copy()
        new_df[['Potential V vs RHE', 'Current mA cm-2']] = new_df['Potential V vs RHE, Current mA cm-2'].str.split(',',
                                                                                                                    expand=True)
        new_df['Potential V vs RHE'] = pd.to_numeric(new_df['Potential V vs RHE'])
        new_df['Current mA cm-2'] = pd.to_numeric(new_df['Current mA cm-2'])
        new_df = new_df.drop('Potential V vs RHE, Current mA cm-2', axis=1)

        midpoint = len(new_df) // 2

        # Adjust split if necessary
        if len(new_df) % 2 != 0:
            midpoint += 1  # Ensure second_half gets the extra row if odd

        first_half = new_df.iloc[:midpoint].copy()
        second_half = new_df.iloc[midpoint:].copy()

        first_half = first_half.sort_values(by='Potential V vs RHE', ascending=True)
        second_half = second_half.sort_values(by='Potential V vs RHE')
        #print(first_half)

        # Doing interpolation
        potential_at_target = target_potential
        current_density_at_target = np.interp(target_potential, first_half['Potential V vs RHE'], first_half['Current mA cm-2'])
        #print(current_density_at_target)
        # Store the current density at target overpotential in y_diff for the regression plot
        y_diff.append(current_density_at_target)

        # Extract the scan rate from the filename to add to x_idx
        pattern = re.compile(r'(\d+)mVs_Efin_*')
        match = pattern.search(file)
        if match:
            number = int(match.group(1))
        x_idx.append(number)

        return new_df, potential_at_target, current_density_at_target
    except Exception as e:
        print(f"Error reading file {file}: {e}")
        return None, None, None


def plot_all_curves(experiment_name, x_idx, y_diff, slope, intercept, r_squared, data_frames, V):
    # Generate the magma color palette with the same number of colors as scan rates
    colors = sns.color_palette("magma", len(x_idx))
    plt.figure(figsize=(2.4, 1.8))

        # Initialize lists for legend control
    handles = []
    labels = []
    scan_rate_labels=[]
    scan_rate_handles = []

    # Add the target potential line first
    target_line = plt.axvline(V, color='gray', linestyle='--', label=f'Target Potential ({V} V)', zorder=3)
    handles.append(target_line)
    labels.append(f'Target Potential ({V} V)')
    i=0
    print(len(x_idx))
    print(x_idx)
    # Plot each individual curve with the hardcoded scan rate labels
    for i, (df, potential_at_target, current_density_at_target) in enumerate(data_frames):
        # Add the target marker for this dataset
        target_marker = plt.scatter(potential_at_target, current_density_at_target,color='red', marker='o',
                                    label=f"Current Density at {V} V" if i == 0 else "", zorder=2, s = 3)
        if i < len(x_idx):  # Ensure we don't exceed the available labels
            line, = plt.plot(df['Potential V vs RHE'], df['Current mA cm-2'], label=f'{x_idx[i]}mV/s', color=colors[i], zorder=1)

        else:
            print('finished')
            #line, = plt.plot(df['Potential V vs RHE'], df['Current mA cm-2'], label=f"File {i + 1}")

        # Store scan rate curve handles for later sorting
        scan_rate_handles.append(line)
        scan_rate_labels.append(f'{x_idx[i]} mV/s' if i < len(x_idx) else f"File {i + 1}")
        if i == 0:  # Only add to legend once to avoid duplicate entries
            handles.append(target_marker)
            labels.append(f"Current Density at {V} V")

    print(scan_rate_labels)
    scan_rate_sorted = sorted(zip(scan_rate_handles, scan_rate_labels), key=lambda x: int(x[1].split()[0]))  
    scan_rate_handles, scan_rate_labels = zip(*scan_rate_sorted)  # Unpack sorted lists

    # Append sorted scan rate curves to the handles and labels lists
    handles.extend(scan_rate_handles)
    labels.extend(scan_rate_labels)

    # Reapply the legend with the correct order
    
    plt.xlabel('Potential V vs RHE')
    plt.ylabel('Current mA cm-2')
    #plt.title(f"All Curves for {experiment_name} with Target Potential at {V} V")
    plt.legend(handles, labels, frameon = False, fontsize = 5, handlelength = 0.5,
               labelspacing=0.2)
    plt.tight_layout(pad = 1)
    file_formats = ['png','eps']
    for fmt in file_formats:
        if experiment_name == "exp564":
            plt.savefig(os.path.join(os.getcwd(), f'{experiment_name}ECSACurve.{fmt}'), dpi=600)
            plt.savefig(os.path.join(OUTPUT_DIR, f'{experiment_name}ECSACurve.{fmt}'), dpi=600)
        plt.savefig(os.path.join(os.getcwd(), f'{experiment_name}ECSACurve.{fmt}'), dpi=600)

    
    # Linear regression plot (Tafel plot)
    plt.figure(figsize=(2.4, 1.8))
    plt.scatter(x_idx, y_diff, label="Data Points", s = 9)
    plt.plot(x_idx, [slope * x + intercept for x in x_idx], color='red',
             label=f'Fit: y={slope:.4f}x+{intercept:.4f}\n$R^2$={r_squared:.4f}')
    plt.xlabel('Scan Rate [mV/s]')
    plt.ylabel(f'Current Density at {V} V [mA/cm^2]')
    #plt.title(f"Tafel Plot for {experiment_name}")
    #plt.legend(frameon=False)
    plt.legend(frameon = False, fontsize = 5, handlelength = 0.5,
               labelspacing=0.2)
    plt.tight_layout(pad = 1)
    file_formats = ['png','eps']
    for fmt in file_formats:
        plt.savefig(os.path.join(os.getcwd(), f'{experiment_name}ECSACurve_LR.{fmt}'), dpi=600)


def process_H2KOH_subfolder(H2KOH_subfolder, experiment_name, results_list):
    print(f"Processing H2KOH subfolder: {H2KOH_subfolder}")
    os.chdir(H2KOH_subfolder)
    files = [file for file in glob.glob('*sr_*mVs*mVvsRHE.txt') if 50 <= int(file.split('sr_')[1].split('mVs')[0]) <= 900]  # Only consider files ending with 'vsRHE.txt' and scan rate between 100 and 500
    files.sort(key=lambda f: int(f.split('sr_')[1].split('mVs')[0]))
    print(f"Number of files found: {len(files)}")

    if len(files) == 0:
        print(f"No files found in {H2KOH_subfolder}")
        os.chdir('..')
        return

    x_idx = []
    y_diff = []
    data_frames = []
    targetV = -0.15

    for file in files:
        df, potential_at_target, current_density_at_target = process_cv_file(file, x_idx, y_diff, targetV)
        if df is not None:
            data_frames.append((df, potential_at_target, current_density_at_target))

    # Perform linear regression on the scan rate vs. current density at -1.5 V
    slope, intercept, r_value, p_value, std_err = linregress(x_idx, y_diff)
    voltage = files[0].split('-')[-1].split('mV')[0] + 'mV'
    results_list.append((experiment_name, voltage, targetV, slope, intercept, r_value ** 2))

    # Plot individual curves, target potential points, and the linear regression plot
    plot_all_curves(experiment_name, x_idx, y_diff, slope, intercept, r_value ** 2, data_frames, targetV)
    os.chdir('..')

def process_main_subfolder(main_subfolder, results_list):
    print(f"Processing main subfolder: {main_subfolder}")
    H2KOH_subfolders = [os.path.join(main_subfolder, f) for f in os.listdir(main_subfolder) if
                        os.path.isdir(os.path.join(main_subfolder, f)) and 'H2KOH' in f]
    print(f"H2KOH subfolders found: {H2KOH_subfolders}")
    for H2KOH_subfolder in H2KOH_subfolders:
        experiment_name = os.path.basename(main_subfolder).split('-')[3]  # Extract experiment name from folder name
        process_H2KOH_subfolder(H2KOH_subfolder, experiment_name, results_list)


def process_folder(folder, results_list, target_experiments=None):
    """Processes subfolders in the given folder. If target_experiments are specified,
    only subfolders matching those experiment IDs will be processed; otherwise, all subfolders are processed."""
    
    os.chdir(folder)
    print(f"Processing folder: {folder}")

    # Get all subfolders in the directory
    all_subfolders = [os.path.join(folder, f) for f in os.listdir(folder) if os.path.isdir(os.path.join(folder, f))]

    # Filter subfolders if target_experiments is provided, else process everything
    main_subfolders = (
        [sub for sub in all_subfolders if any(exp in sub for exp in target_experiments)]
        if target_experiments else all_subfolders
    )

    print(f"Main subfolders found: {main_subfolders}")

    # Process each relevant subfolder
    for main_subfolder in main_subfolders:
        process_main_subfolder(main_subfolder, results_list)

    os.chdir('..')

'''Merge data'''

def extract_experiment_number(experiment_name):
    number_str = ''.join(filter(str.isdigit, experiment_name))
    return int(number_str)

def merge_csv_files(file_paths, output_file, merge_columns):
    """
    Merges multiple CSV files based on specified columns while always using the first column as the index.

    Parameters:
    - file_paths (list of str): List of CSV file paths to merge.
    - output_file (str): Path to save the merged CSV file.
    - merge_columns (list of str): List of column names to merge.

    Returns:
    - None (Saves the merged DataFrame as a CSV file)
    """

    if not file_paths:
        print("No file paths provided.")
        return

    # Load the first file and use the first column as the index
    first_file = file_paths[0]
    df_merged = pd.read_csv(first_file, index_col=0)

    # Keep only specified columns that exist
    df_merged = df_merged[[col for col in merge_columns if col in df_merged.columns]]

    # Merge remaining files
    for file in file_paths[1:]:
        df = pd.read_csv(file, index_col=0)

        # Filter only the specified columns that exist in the current file
        existing_columns = [col for col in merge_columns if col in df.columns]
        df = df[existing_columns]

        # Merge on the index
        df_merged = df_merged.merge(df, left_index=True, right_index=True, how='outer')

    # Save the merged result
    rename_columns = {
        "Overpotential V at 50.0 mA cm-2": "Overpotential @ 50 mA", 
        "Slope": "Cdl mF cm-2",  # Renamed based on assumed meaning
        "Tafel Slope (mV/dec)": "Tafel Slope (mV dec-1)",
        "Exchange Current Density (mA/cm²)": "Exchange Current Density (mA cm-2)",
        "Thickness_nm": "Thickness nm"
        }
    df_merged = df_merged.dropna(subset=df_merged.columns[1:14], how='any')
    
    df_merged.rename(columns={col: rename_columns[col] for col in df_merged.columns if col in rename_columns}, inplace=True)

    if "Cdl mF cm-2" in df_merged.columns:
        df_merged["Cdl mF cm-2"] = -df_merged["Cdl mF cm-2"]*1000

    
    df_merged.sort_values(by='Experiment', key=lambda x: x.apply(extract_experiment_number), inplace=True)

    df_merged.to_csv(output_file)
    print(f"Merged file saved as {output_file}")


if __name__ == "__main__":
        
        pseudo_csv = get_data("Capacitance_all")

        if not os.path.isfile(pseudo_csv):
            base_path = get_data_folder("All data")
            print("[INFO] Processing folder:", base_path)

            results_list = []
            process_folder(base_path, results_list)

            if results_list:
                results_list.sort(key=lambda x: extract_experiment_number(x[0]))
                output_file = pseudo_csv  # 就直接覆蓋
                df_results = pd.DataFrame(results_list, columns=['Experiment','Voltage','E_mid','Slope','Intercept','R^2'])
                df_results.to_csv(output_file, index=False)
                print(f"[INFO] New file saved: {output_file}")

        else:
            print("[INFO] CSV already exists, skipping processing.")
                
            file_paths = [get_data("result_all_campaign"), get_data("Capacitance_all")]

            merge_columns = ["Experiment","Slope", "Overpotential V at 50.0 mA cm-2"]

            output_file = os.path.join(os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "Data")),  "Merged_ovp_cdl_full.csv")
            merge_csv_files(file_paths, output_file, merge_columns)

    