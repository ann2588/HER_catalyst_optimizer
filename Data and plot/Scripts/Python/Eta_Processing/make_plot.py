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
    "stable_id": "Eta_processing",
    "script": __file__,
    "data_keys": ["All data"], # or In folder
    "figure_type": "Main"   # or "Main"
}

def get_output_dir(meta):
    base = os.path.dirname(__file__)
    fig_base = "Figures_SI" if meta["figure_type"] == "SI" else "Figures_Main"
    outdir = os.path.join(base, "..", "..", ".." , fig_base, meta["stable_id"])
    os.makedirs(outdir, exist_ok=True)
    return outdir

OUTPUT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", "Data")) # DATA path


###=========================================================###

'''
Author: Muxin Xiong
Editor: Yi-An Lai
This file process extract overpotentials from raw data. either in H2KOH or Phosphate
Assign parent folder and run ProcessMultipleOverpotential(path) to batch process the overpotentials
After running ProcessMultipleOverpotential(), the data could be proceed to perform hypothesis test for regeneration or get overpotential from csv file
'''

import os, re
import glob
import pandas as pd
import numpy as np


def extract_experiment_number(experiment_name):
    number_str = ''.join(filter(str.isdigit, experiment_name))
    print(f'number_str: {number_str}')
    return int(number_str)

def grab_cv_data(df, experiment_name, voltage, results_list, SINGLE = False):
    new_df = df.copy()
    new_df[['Potential V vs RHE', 'Current mA cm-2']] = new_df['Potential V vs RHE, Current mA cm-2'].str.split(',',
                                                                                                                expand=True)
    new_df['Potential V vs RHE'] = pd.to_numeric(new_df['Potential V vs RHE'])
    new_df['Current mA cm-2'] = pd.to_numeric(new_df['Current mA cm-2'])
    new_df = new_df.drop('Potential V vs RHE, Current mA cm-2', axis=1)

    # Divide DataFrame into 6 sections
    sections = [new_df.loc[int((idx - 1) * (len(new_df) / 6)):int(idx * (len(new_df) / 6)) - 1] for idx in range(1, 7)]

    # Process only the fifth section
    section = sections[4]  # sections is zero-indexed, so 5th section is at index 4
    row_data = []
    if experiment_name == "exp590":
        print("Processing exp590 ")
    for i in np.arange(0.5, 10.5, 0.5):
        closest_idx = abs(abs(section['Current mA cm-2']) - i).idxmin()
        if experiment_name == "exp590":
            print(closest_idx)
        if abs(abs(section['Current mA cm-2'][closest_idx]) - i) < 1:
            row_data.append(section.loc[closest_idx, 'Potential V vs RHE'])
            row_data.append(section.loc[closest_idx, 'Current mA cm-2'])
        else:
            row_data.append(np.nan)
            row_data.append(np.nan)

    for i in [20.0, 30.0, 40.0, 50.0]:
        closest_idx = abs(abs(section['Current mA cm-2']) - i).idxmin()

        if abs(abs(section['Current mA cm-2'][closest_idx]) - i) < 1:
            row_data.append(section.loc[closest_idx, 'Potential V vs RHE'])
            row_data.append(section.loc[closest_idx, 'Current mA cm-2'])
        else:
            row_data.append(np.nan)
            row_data.append(np.nan)

    # Append the row to the results list with the experiment identifier and voltage
    row_data.insert(0, voltage)
    row_data.insert(0, experiment_name)
    results_list.append(row_data)



def process_cv_file(file, experiment_name, results_list):
    print(f"Processing file: {file}")
    try:
        df = pd.read_csv(file, delimiter='\t')  # Assuming the data is tab-delimited
        print(f"Data loaded from {file}, number of points: {len(df)}")
        print(df.head())  # Print the first few rows to confirm data is read correctly

        # Extract voltage from filename
        voltage = file.split('-')[-1].split('mV')[0] + 'mV'

        grab_cv_data(df, experiment_name, voltage, results_list)
    except Exception as e:
        print(f"Error reading file {file}: {e}")

def process_H2KOH_subfolder(subfolder, experiment_name, results_list):
    print(f"Processing H2KOH subfolder: {subfolder}")
    os.chdir(subfolder)
    files = glob.glob('*_CV_50mV*mVvsRHE.txt')  # Only consider files ending with 'vsRHE.txt'
    print(f"Number of files found: {len(files)}")
    sorted_files = sorted(
        files,
        key=lambda f: int(re.search(r'_Efin_(-?\d+)mVvsRHE', f).group(1))
    )

    # Select the CV with highest potential range
    # Assume processing the file converted to RHE scale
    process_cv_file(sorted_files[0], experiment_name, results_list)
    os.chdir('..')

def process_main_subfolder(main_subfolder, results_list, electrolytes: str):
    print(f"Processing main subfolder: {main_subfolder}")

    # Dictionary to map electrolytes to their respective processing functions
    processing_functions = {
        'H2KOH': process_H2KOH_subfolder
    }

    # Validate electrolyte input
    if electrolytes not in processing_functions:
        raise ValueError('Please provide either H2KOH or LSVinPhos')

    # Identify subfolders containing the specified electrolyte
    subfolders = [
        os.path.join(main_subfolder, f) for f in os.listdir(main_subfolder)
        if os.path.isdir(os.path.join(main_subfolder, f)) and electrolytes in f
    ]

    print(f"{electrolytes} subfolders found: {subfolders}")

    # Process each subfolder using the appropriate function
    for subfolder in subfolders:
        print(f"Processing subfolder: {subfolder}")
        experiment_name = os.path.basename(main_subfolder).split('-')[3]  # Extract experiment name
        print(experiment_name)
        processing_functions[electrolytes](subfolder, experiment_name, results_list)


def process_master_folder(folder, results_list, electrolytes):
    os.chdir(folder)


    print(f"Processing folder: {folder}")
    main_subfolders = [os.path.join(folder, f) for f in os.listdir(folder) if os.path.isdir(os.path.join(folder, f))]
    print(f"Main subfolders found: {main_subfolders}")
    for main_subfolder in main_subfolders:
        if 'Initial' in main_subfolder:
            continue
        else:
            process_main_subfolder(main_subfolder, results_list, electrolytes)

    os.chdir('..')



def ProcessMultipleOverpotential(path: str):
    base_path = path  # Update this with your folder name
    results_list = []

    ELECTROLYTES = ['H2KOH']
    for electrolytes in ELECTROLYTES:
        df_results = []
        df = []
        results_list = []
        process_master_folder(base_path, results_list, electrolytes)

        if results_list:
            # Sort the results list by experiment number
            results_list.sort(key=lambda x: extract_experiment_number(x[0]))

            # Create DataFrame from results list
            columns = ['Experiment', 'Voltage']

            for i in np.arange(0.5, 10.5, 0.5):
               columns += [f'Overpotential V at {i} mA/cm2', f'Current Density {i} mA/cm2']
            for i in [20.0, 30.0, 40.0, 50.0]:
               columns += [f'Overpotential V at {i} mA/cm2', f'Current Density {i} mA/cm2']

            df_results = pd.DataFrame(results_list, columns=columns)

            # Save results to CSV
            output_file = os.path.join(OUTPUT_DIR, f'HER_Overpotentials_all_campaign.csv')
            if os.path.exists(output_file):
                os.remove(output_file)
                print(f"Deleted existing file: {output_file}")
            df = df_results[['Experiment','Overpotential V at 2.0 mA/cm2', 'Overpotential V at 10.0 mA/cm2', 'Overpotential V at 50.0 mA/cm2']]
            print(f"Attempting to save results to {output_file}")
            df.to_csv(output_file, index=False)
            print(f"Results saved to {output_file}")

        else:
            print("No results to save.")



#%%
if __name__ == "__main__":
    path = get_data_folder(FIGURE_METADATA["data_keys"][0])
    ProcessMultipleOverpotential(path)