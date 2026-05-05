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
    "stable_id": "Fig_Tafel",
    "script": __file__,
    "data_keys": ["All data"], # or In folder
    "figure_type": "Main"   # 或 "Main"
}

def get_output_dir(meta):
    base = os.path.dirname(__file__)
    fig_base = "Figures_SI" if meta["figure_type"] == "SI" else "Figures_Main"
    outdir = os.path.join(base, "..", "..", ".." , fig_base, meta["stable_id"])
    os.makedirs(outdir, exist_ok=True)
    return outdir


OUTPUT_DIR = get_output_dir(FIGURE_METADATA)
os.makedirs(OUTPUT_DIR, exist_ok=True)

###==========================================================================###
'''
This script perform Tafel slope analysis for the raw data under the parent folder.
Return a cvs file to summarize every experiment in the dataset

'''



import os, re
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import linregress

plt.rcParams['lines.linewidth'] = 1
plt.rcParams.update({'font.size': 8})  # Apply globally

import warnings
warnings.filterwarnings(
    "ignore",
    message=".*PostScript backend does not support transparency.*"
)

def extract_experiment_number(experiment_name):
    number_str = ''.join(filter(str.isdigit, experiment_name))
    return int(number_str)

def calculate_overpotential(df, potential_col='Potential V vs RHE'):
    return df[potential_col] * 1000  # Convert V to mV for overpotential

def plot_log_current_density_with_linear_fit(df, experiment_name):
    # Calculate log current density if not already calculated
    new_df = df.copy()
    new_df[['Potential V vs RHE', 'Current mA cm-2']] = new_df['Potential V vs RHE, Current mA cm-2'].str.split(',', expand=True)
    new_df['Potential V vs RHE'] = pd.to_numeric(new_df['Potential V vs RHE'])
    new_df['Current mA cm-2'] = pd.to_numeric(new_df['Current mA cm-2'])
    new_df = new_df.drop('Potential V vs RHE, Current mA cm-2', axis=1)

    # Divide DataFrame into 6 sections and process only the 5th section
    sections = [new_df.loc[int((idx - 1) * (len(new_df) / 6)):int(idx * (len(new_df) / 6)) - 1.5] for idx in range(1, 7)]
    section = sections[5].copy()

    # Calculate overpotential and log current density for the 5th section
    section['Overpotential mV'] = calculate_overpotential(section)
    section['Log Current Density'] = np.log10(abs(section['Current mA cm-2']))

    # Filter for Log Current Density in the range 0.6 to 1.5
    filtered_df = section[(section['Log Current Density'] >= 0.6) & (section['Log Current Density'] <= 1.5)].copy()

    # Perform linear regression on the filtered data
    slope, intercept, r_value, p_value, std_err = linregress(filtered_df['Log Current Density'], filtered_df['Potential V vs RHE'])
    tafel_slope_mV_per_dec = abs(slope * 1000)  # Convert from V/dec to mV/dec
    exchange_current_density = 10**(-intercept / slope)
    r_squared = r_value**2

    # Print the results
    print(f"Tafel slope: {tafel_slope_mV_per_dec:.4f} mV/decade")
    print(f"Exchange current density (i₀): {exchange_current_density:.4e} mA/cm²")

    # Optimized Plot Settings
    plt.figure(figsize=(2.4, 1.8))
    plt.plot(section['Log Current Density'], section['Potential V vs RHE'], 'o', label='Data Points', color='blue', alpha=0.6, markersize=3)

    # Plot the linear fit
    plt.plot(filtered_df['Log Current Density'], slope * filtered_df['Log Current Density'] + intercept, 'r-', label='Linear Fit', linewidth=1)

    # Labeling and Styling
    plt.xlabel('Log[Current Density (mA cm⁻²)]')
    plt.ylabel('Potential (V vs RHE)')

    # Legend at the bottom left corner for Data Points and Linear Fit
    plt.legend(['Data Points', 'Linear Fit'], loc='lower left', frameon=False)

    # Save and Show Plot
    plt.tight_layout(pad = 1)
    file_formats = ['png','eps']
    for fmt in file_formats:
        if experiment_name == "exp430":
            plt.savefig(os.path.join(OUTPUT_DIR, f'Tafel_Linear_Fit_{experiment_name}.{fmt}'), dpi=600)
            plt.savefig(os.path.join(os.getcwd(), f'Tafel_Linear_Fit_{experiment_name}.{fmt}'), dpi=600)
        plt.savefig(os.path.join(os.getcwd(), f'Tafel_Linear_Fit_{experiment_name}.{fmt}'), dpi=600)

    return tafel_slope_mV_per_dec, exchange_current_density, r_squared

def process_H2KOH_subfolder(H2KOH_subfolder, experiment_name, results_list):
    print(f"Processing H2KOH subfolder: {H2KOH_subfolder}")
    os.chdir(H2KOH_subfolder)
    files = glob.glob('*_CV_50mV*mVvsRHE.txt')  # Only consider files ending with 'vsRHE.txt'
    print(f"Number of files found: {len(files)}")
    sorted_files = sorted(
        files,
        key=lambda f: int(re.search(r'_Efin_(-?\d+)mVvsRHE', f).group(1))
    )

    if len(files) == 0:
        print(f"No Tafel files found in {H2KOH_subfolder}")
        os.chdir('..')
        return


    try:
        df = pd.read_csv(sorted_files[0], delimiter='\t')
        print(f"Processing file: {sorted_files[0]}")

        # Call the linear fit function and update the results list
        tafel_slope, exchange_current_density, r_squared = plot_log_current_density_with_linear_fit(df, experiment_name)
        results_list.append((experiment_name, tafel_slope, exchange_current_density, r_squared))

        print(f"Results: Tafel Slope = {tafel_slope:.2f} mV/dec, i₀ = {exchange_current_density:.2e} mA cm⁻², R² = {r_squared:.4f}")

    except Exception as e:
        print(f"Error processing file {sorted_files[0]}: {e}")

    os.chdir('..')

def process_main_subfolder(main_subfolder, results_list):
    print(f"Processing main subfolder: {main_subfolder}")
    H2KOH_subfolders = [os.path.join(main_subfolder, f) for f in os.listdir(main_subfolder) if
                        os.path.isdir(os.path.join(main_subfolder, f)) and 'H2KOH' in f]

    for H2KOH_subfolder in H2KOH_subfolders:
        experiment_name = os.path.basename(main_subfolder).split('-')[3]
        print(experiment_name)
        process_H2KOH_subfolder(H2KOH_subfolder, experiment_name, results_list)

def process_folder(folder, results_list, target_experiments = None):
    os.chdir(folder)
    all_subfolders = [os.path.join(folder, f) for f in os.listdir(folder) if os.path.isdir(os.path.join(folder, f))]
    main_subfolders = (
        [sub for sub in all_subfolders if any(exp in sub for exp in target_experiments)]
        if target_experiments else all_subfolders
    )

    for main_subfolder in main_subfolders:
        process_main_subfolder(main_subfolder, results_list)

    os.chdir('..')

def main():
    base_path = get_data_folder(FIGURE_METADATA["data_keys"][0])
    results_list = []
    process_folder(base_path, results_list)
    if results_list:
        df_results = pd.DataFrame(results_list, columns=['Experiment', 'Tafel Slope (mV/dec)', 'Exchange Current Density (mA/cm²)', 'R²'])
        output_file = os.path.join(os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", "Data")), 'Tafel_Analysis_all_campaign.csv')
        df_results.to_csv(output_file, index=False)
        print(f"Results saved to {output_file}")
    else:
        print("No results to save.")

if __name__ == "__main__":
    main()
