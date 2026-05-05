'''
Author: Muxin Xiong
Editor: Yi-An Lai
This file process extract overpotentials from raw data. either in H2KOH or Phosphate
Assign parent folder and run ProcessMultipleOverpotential(path) to batch process the overpotentials
After running ProcessMultipleOverpotential(), the data could be proceed to perform hypothesis test for regeneration or get overpotential from csv file
'''

import os
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

    for i in np.arange(0.5, 10.5, 0.5):
        closest_idx = abs(abs(section['Current mA cm-2']) - i).idxmin()

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

def grab_lsv_data(df, experiment_name, voltage, results_list):
    new_df = df.copy()
    new_df[['Potential V vs RHE', 'Current mA cm-2']] = new_df['Potential V vs RHE, Current mA cm-2'].str.split(',',
                                                                                                                expand=True)
    new_df['Potential V vs RHE'] = pd.to_numeric(new_df['Potential V vs RHE'])
    new_df['Current mA cm-2'] = pd.to_numeric(new_df['Current mA cm-2'])
    new_df = new_df.drop('Potential V vs RHE, Current mA cm-2', axis=1)

    # Divide DataFrame into 6 sections
    #sections = [new_df.loc[int((idx - 1) * (len(new_df) / 6)):int(idx * (len(new_df) / 6)) - 1] for idx in range(1, 7)]

    # Process single segment
    section = new_df
    row_data = []

    for i in np.arange(0.5, 10.5, 0.5):
        closest_idx = abs(abs(section['Current mA cm-2']) - i).idxmin()

        if abs(abs(section['Current mA cm-2'][closest_idx]) - i) < 0.25:
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

def process_lsv_file(file, experiment_name, results_list):
    print(f"Processing file: {file}")
    try:
        df = pd.read_csv(file, delimiter='\t')  # Assuming the data is tab-delimited
        print(f"Data loaded from {file}, number of points: {len(df)}")
        print(df.head())  # Print the first few rows to confirm data is read correctly

        # Extract voltage from filename
        voltage = file.split('-')[-1].split('mV')[0] + 'mV'

        grab_lsv_data(df, experiment_name, voltage, results_list)
    except Exception as e:
        print(f"Error reading file {file}: {e}")

def process_H2KOH_subfolder(subfolder, experiment_name, results_list):
    print(f"Processing H2KOH subfolder: {subfolder}")
    os.chdir(subfolder)
    files = glob.glob('*_CV_50mV*mVvsRHE.txt')  # Only consider files ending with 'vsRHE.txt'
    print(f"Number of files found: {len(files)}")
    print(files)
    # for file in files[-1]:
    #    process_cv_file(files, experiment_name, results_list)
    # Select the CV with highest potential range
    # Assume processing the file converted to RHE scale
    process_cv_file(files[-1], experiment_name, results_list)
    os.chdir('..')

def process_LSV_subfolder(subfolder, experiment_name, results_list):
    print(f"Processing LSVinKOH subfolder: {subfolder}")
    os.chdir(subfolder)
    files = glob.glob('*_LSV_50mV*mVvsRHE.txt')  # Only consider files ending with 'vsRHE.txt'
    print(f"Number of files found: {len(files)}")
    print(f"founded files:{files[-1]}")
    # Assume processing the file converted to RHE scale
    process_lsv_file(files[-1], experiment_name, results_list)
    os.chdir('..')

'''
def process_main_subfolder(main_subfolder, results_list, electrolytes:str):

    print(f"Processing main subfolder: {main_subfolder}")
    subfolders = [os.path.join(main_subfolder, f) for f in os.listdir(main_subfolder) if
                        os.path.isdir(os.path.join(main_subfolder, f)) and f'{electrolytes}' in f]

    print(f"{electrolytes} subfolders found: {subfolders}")
    if electrolytes == 'H2KOH':
        for subfolder in subfolders:
            experiment_name = os.path.basename(subfolder).split('-')[0]  # Extract experiment name from folder name
            process_H2KOH_subfolder(subfolder, experiment_name, results_list)
    elif electrolytes == 'LSVinPhos':
        for subfolder in subfolders:
            experiment_name = os.path.basename(subfolder).split('-')[0]  # Extract experiment name from folder name
            process_LSVinPhos_subfolder(subfolder, experiment_name, results_list)
    else:
        raise ValueError('Please provide either H2KOH or LSVinPhos')
'''

def process_main_subfolder(main_subfolder, results_list, electrolytes: str):
    print(f"Processing main subfolder: {main_subfolder}")

    # Dictionary to map electrolytes to their respective processing functions
    processing_functions = {
        'H2KOH': process_H2KOH_subfolder,
        'Pre-Regen': process_LSV_subfolder,
        'Post-Regen1': process_LSV_subfolder,
        'Regenerated': process_LSV_subfolder
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
    base_path = f'{path}'  # Update this with your folder name
    results_list = []

    ELECTROLYTES = ['H2KOH', 'Pre-Regen', 'Post-Regen1', 'Regenerated']
    ELECTROLYTES = ['H2KOH', 'Pre-Regen', 'Post-Regen1', 'Regenerated']
    for electrolytes in ELECTROLYTES:
        df_results = []
        df_10mA = []
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

            # Save all results to CSV
            output_file = os.path.join(base_path, f'{electrolytes}_overpotentials_current.csv')
            if os.path.exists(output_file):
                os.remove(output_file)
                print(f"Deleted existing file: {output_file}")

            print(f"Attempting to save results to {output_file}")
            df_results.to_csv(output_file, index=False)
            print(f"Results saved to {output_file}")

            # Save 10 mA results to CSV
            output_file = os.path.join(base_path, f'Overpotentials.csv')
            if os.path.exists(output_file):
                os.remove(output_file)
                print(f"Deleted existing file: {output_file}")
            df_10mA = df_results[['Experiment', 'Overpotential V at 10.0 mA/cm2']]
            print(f"Attempting to save results to {output_file}")
            df_10mA.to_csv(output_file, index=False)
            print(f"Results saved to {output_file}")

        else:
            print("No results to save.")

def ProcessSingleOverpotential(path: str):
    base_path = f'{path}'  # Update this with your folder name
    results_list = []

    ELECTROLYTES = ['H2KOH']
    for electrolytes in ELECTROLYTES:
        df_results = []
        df_50mA = []
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

            # Save all results to CSV
            output_file = os.path.join(base_path, f'{electrolytes}_overpotentials_current.csv')
            if os.path.exists(output_file):
                os.remove(output_file)
                print(f"Deleted existing file: {output_file}")

            print(f"Attempting to save results to {output_file}")
            df_results.to_csv(output_file, index=False)
            print(f"Results saved to {output_file}")

            # Save 50 mA results to CSV
            output_file = os.path.join(base_path, f'{electrolytes}_overpotentials_10to50mA.csv')
            if os.path.exists(output_file):
                os.remove(output_file)
                print(f"Deleted existing file: {output_file}")
            df_50mA = df_results[['Experiment', 'Overpotential V at 10.0 mA/cm2', 'Overpotential V at 20.0 mA/cm2', 'Overpotential V at 30.0 mA/cm2', 'Overpotential V at 40.0 mA/cm2', 'Overpotential V at 50.0 mA/cm2']]
            print(f"Attempting to save results to {output_file}")
            df_50mA.to_csv(output_file, index=False)
            print(f"Results saved to {output_file}")

        else:
            print("No results to save.")


def get_overpotential_by_experiment(csv_file, experiment_name):
    # Read the CSV file into a pandas DataFrame
    df = pd.read_csv(csv_file)

    # Filter the DataFrame to find the row where the first column matches the experiment_name
    matching_row = df[df['Experiment'] == experiment_name]

    # If a matching row is found, return the value from the second column
    if not matching_row.empty:
        return matching_row.iloc[0, 1]  # Second column is at index 1 (0-based index)
    else:
        return None  # Return None if no matching experiment is found

def get_overpotentials_by_experiment(csv_file, experiment_name):
    # Read the CSV file into a pandas DataFrame
    df = pd.read_csv(csv_file)

    # Filter the DataFrame to find the row where the first column matches the experiment_name
    matching_row = df[df['Experiment'] == experiment_name]

    # If a matching row is found, return the value from the second column
    if not matching_row.empty:
        return matching_row.iloc[0, 1:6].to_numpy()  # Second column is at index 1 (0-based index)
    else:
        return None  # Return None if no matching experiment is found

def Reindex(CSVFILE):

    data = pd.read_csv(CSVFILE)

    # Re-index the 'Experiment' column with a 4-digit notation like 'exp0001'
    # Extracting the numeric part of 'expXX' and reformatting it
    data['exp_num'] = data['Experiment'].apply(lambda x: int(re.search(r'\d+', x).group()) if pd.notnull(x) else None)
    data['Experiment'] = data['exp_num'].apply(lambda x: f'exp{str(x).zfill(4)}' if pd.notnull(x) else None)

    # Find the minimum and maximum 'exp_num' values for the re-indexing
    min_exp = data['exp_num'].min()
    max_exp = data['exp_num'].max()

    # Create a complete range of 'expXXXX' indices
    complete_indices = [f'exp{str(i).zfill(4)}' for i in range(min_exp, max_exp + 1)]

    # Identify the missing indices
    existing_indices = data['Experiment'].tolist()
    missing_indices = [idx for idx in complete_indices if idx not in existing_indices]

    # Create a DataFrame for the missing indices with NaN for other columns
    missing_data = pd.DataFrame({'Experiment': missing_indices})

    # Add NaN columns for the missing data points
    for col in data.columns:
        if col != 'Experiment':
            missing_data[col] = pd.NA

    # Add the missing rows to the original DataFrame
    complete_data = pd.concat([data, missing_data], ignore_index=True).sort_values(by='Experiment').reset_index(drop=True)

    # Drop the helper 'exp_num' column
    complete_data.drop(columns=['exp_num'], inplace=True)

    complete_data.to_csv(CSVFILE)

def Refillmissingrows(path):
    # Load the uploaded CSV file
    file_path = os.path.join(path,"H2KOH_overpotentials_current.csv")
    data = pd.read_csv(file_path)

    # Extract the numeric part from the 'Experiment' column to handle lower-case labels like 'exp1'
    experiment_ids = pd.to_numeric(data['Experiment'].str.extract(r'exp(\d+)')[0], errors='coerce')

    # Drop NaN values to ensure only valid experiment IDs are processed
    experiment_ids_clean = experiment_ids.dropna().astype(int)

    # Determine the min and max experiment numbers
    min_exp = experiment_ids_clean.min()
    max_exp = experiment_ids_clean.max()

    # Create the full range of expected experiment numbers
    full_range = pd.Series(range(min_exp, max_exp + 1), name='Experiment')

    # Identify missing experiment IDs by comparing with the existing ones
    missing_ids = full_range[~full_range.isin(experiment_ids_clean)]

    # Create placeholder rows with NaN-filled values for the missing experiments
    missing_rows = pd.DataFrame({
        'Experiment': missing_ids.apply(lambda x: f'exp{x}')
    })
    missing_rows = missing_rows.reindex(columns=data.columns).fillna(float('nan'))

    # Combine the original data with the missing rows
    combined_data = pd.concat([data, missing_rows])

    # Extract the numeric part for sorting
    combined_data['Experiment_Num'] = combined_data['Experiment'].str.extract(r'(\d+)').astype(int)

    # Sort based on the numeric part of the experiment labels
    combined_data = combined_data.sort_values(by='Experiment_Num').drop(columns='Experiment_Num').reset_index(drop=True)

    combined_data.to_csv(file_path, index=False)