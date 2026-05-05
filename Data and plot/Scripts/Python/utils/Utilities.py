# %%
import os, re
import glob
import pandas as pd
import numpy as np
from scipy.signal import savgol_filter
import datetime
from matplotlib import pyplot as plt
from scipy.stats import linregress
import seaborn as sns
import time

# %%
'''# %% Common os function
os.chdir(os.path.dirname(os.getcwd())) # Go back to parent folder
os.listdir() 
os.getcwd() #Get current folder
#os.chdir('EffectOfAConMaterialRemoval')
os.chdir(os.path.dirname(os.getcwd())) # Go back to parent folder 
'''

colors = sns.color_palette("Spectral", 600)  # Change the maximun number of your exp
# Bach data processing start
def gtdata():  # this function navigate you to original parent folder and print out the subfolder
    path = "Data/All data"
    os.chdir(path)
    folder_ordered = sorted(os.listdir(), key=lambda f: os.path.getctime(os.path.join(os.getcwd(), f)), reverse=True)
    print(folder_ordered)


def gtparent():
    os.chdir(os.path.dirname(os.getcwd()))
    print(os.getcwd())


datapath = os.path.join(os.getcwd(), "OutputCSV")


def save_csv(filename, df, filepath=datapath):
    df.to_csv(os.path.join(filepath, f'{filename}.csv'), index=True)


# Utilities
def fdtitle(string, filename):
    flag = 0
    index = 0
    file1 = open(filename, "r")
    # Loop through the file line by line
    for line in file1:
        index += 1
        # checking string is present in line or not
        if string in line:
            flag = 1
            break
        # checking condition for string found or not
    if flag == 0:
        file1.close()
        print('String', string, 'Not Found')
    else:
        file1.close()
        return index


#gtdata()


# %
def get_sorted_experiment_dirs(base_path):
    # List all items in the base directory
    try:
        all_items = os.listdir(base_path)
    except FileNotFoundError:
        print(f"The directory {base_path} does not exist.")
        return []

    # Filter out directories that match the pattern "YYYY-MM-DD-exp{number}"
    exp_dirs = []
    for d in all_items:
        dir_path = os.path.join(base_path, d)
        if os.path.isdir(dir_path) and re.match(r'\d{4}-\d{2}-\d{2}-exp\d+', d):
            exp_dirs.append(d)
        elif os.path.isdir(dir_path) and re.match(r'\d{4}-\d{2}-\d{2}-Initial', d):
            exp_dirs.append(d)
        else:
            continue

    # Debug: Print filtered directories
    print("Filtered directories:", exp_dirs)

    # Sort the experiment directories based on the experiment number
    try:
        exp_dirs.sort(key=lambda x: int(re.search(r'exp(\d+)', x).group(1)) if re.search(r'exp(\d+)', x) else -1)
    except Exception as e:
        print(f"Error during sorting: {e}")
        return []

    # Debug: Print sorted directories
    print("Sorted directories:", exp_dirs)

    return exp_dirs


# 

def find_nearest_index(cvref_E, vertex, threshold=0.0005):
    """
    Find the index of the element in cvref.E that is closest to Ev1 and the difference is less than threshold.
    """
    differences = np.abs(cvref_E - vertex)
    valid_indices = np.where(differences < threshold)
    if len(valid_indices) == 0:
        raise ValueError("No valid index found with the given threshold.")
    return valid_indices


def LSV_converter(col_name, col, phosphate=False, KPi=False):
    phvalue = {
        "KOH": 13.7,
        "0p05MPhos": 7.6,
        "1MKPi": 7,
        "spelec": 3.6}

    area = {
        'PtDisk': 0.0706858,
        'GCE': 0.0706858,
        'Customized': 7,
    }

    if col_name == 'Potential V vs ref':
        if phosphate == True:
            return col + 0.205 + phvalue['0p05MPhos'] * 0.059
        elif KPi == True:
            return col + 0.205 + phvalue['1MKPi'] * 0.059
        else:
            return col + 0.205 + phvalue['KOH'] * 0.059
    elif col_name == 'Current A':
        return -col / area['GCE'] * 1000


def LSV_getoverpotential(x, y, criteria):
    smoothed_x = savgol_filter(x[::-1], window_length=5, polyorder=3, mode='nearest')
    smoothed_y = savgol_filter(y[::-1], window_length=5, polyorder=3, mode='nearest')
    plt.plot(smoothed_x, smoothed_y)
    overpotential = np.interp(criteria, smoothed_y, smoothed_x)
    return overpotential

    # Smooth LSV curve


# This function match timestamp in string
def extract_datetime(timestamp):
    match = re.search(r'\d{4}-\d{2}-\d{2}T\d{2}_\d{2}_\d{2}', timestamp)
    return match.group(0)


# Script

# %%

# This function print out all the available file and dictionary under path.
def PotentialConversion(HERelec='KOH'):
    '''
    This function process all the LSV respected to all kinds of electrolyte based on the foldername
    hold for all kinds of electrolyte
    If processing the 1MKPi please specified in input HERelec
    '''
    dirs = glob.glob('*Regen*')  # find folder for LSV
    print(dirs)
    for dir in dirs:
        os.chdir(dir)  # change to that LSV folder
        files_raw = glob.glob('*LSV*mV.txt')  # Find all the file with pattern
        # Put your function below
        # Read LSV curve under a folder
        for file in files_raw:
            skiprow = fdtitle('Potential/V', file)
            titles = ['Potential V vs ref', 'Current A']
            df = pd.read_csv(file, skiprows=skiprow - 1, header=0, names=titles)
            if 'inPhos' in dir:
                converted_df = pd.DataFrame({col: LSV_converter(col, df[col], phosphate=True) for col in df.columns})
            else:
                if HERelec == 'KPi':
                    converted_df = pd.DataFrame(
                        {col: LSV_converter(col, df[col], phosphate=False, KPi=True) for col in df.columns})
                else:  # The HERelec was KOH
                    converted_df = pd.DataFrame(
                        {col: LSV_converter(col, df[col], phosphate=False) for col in df.columns})
            converted_df.columns = ['Potential V vs RHE', ' Current mA cm-2']
            converted_df.to_csv(file[:-4] + 'vsRHE' + file[-4:], index=False)  # THis write code into txt

        # Put your function above
        os.chdir(os.path.dirname(os.getcwd()))  # Go back to parent folder

# LSV under different folder, return overpotential and provide mean and std, plot for KOH Only
# %
def PlotLSV(Solvent: str, color_index, label: str, criteria_current=1):
    # colors = sns.color_palette("Paired")
    dirs = glob.glob('*LSV*')
    if Solvent == 'Phos':
        dirs = [file for file in dirs if 'inPhos' in file]
    elif Solvent == 'KOH':
        dirs = [file for file in dirs if 'inKOH' in file]
    elif Solvent == 'CoSex':
        dirs = [file for file in dirs if 'CoSex' in file]
    else:
        dirs = [file for file in dirs if 'Regenerated' in file]

    # dirs = sorted(dirs, key=extract_datetime)
    df_eta = pd.DataFrame({'Filename': [], 'Overpotential': []})
    eta = []
    for _, dir in enumerate(dirs):
        os.chdir(dir)
        files = glob.glob('*mVvsRHE*.txt')
        sorted_files = sorted(files, key=lambda x: int(x.split("_Efin_-")[-1].replace("mVvsRHE.txt", "")), reverse=True)
        try:
            df = pd.read_csv(sorted_files[0])
            plt.plot(df['Potential V vs RHE'], df['Current mA cm-2'], label=f'{label}', color=colors[color_index])
            overpotential = LSV_getoverpotential(df['Potential V vs RHE'], df['Current mA cm-2'], -criteria_current)
            new_row = [f'{sorted_files[0].split("_LSV_")[0]}', overpotential]
            df_eta.loc[len(df_eta)] = new_row
            eta.append(overpotential)
            os.chdir(os.path.dirname(os.getcwd()))
        except:
            os.chdir(os.path.dirname(os.getcwd()))

    else:
        print("continue")

    return df_eta  # this is a list


# %%
def PlotRegeneratedLSV(color, label: str, condition):
    # colors = sns.color_palette("Paired")
    if condition == "Regenerated":
        regdirs = glob.glob('Regenerated*')
    elif condition == "Pre-Regen":
        regdirs = glob.glob('Pre-Regen*')
    elif condition == "Post-Regen":
        regdirs = glob.glob('Post-Regen*')

    if regdirs:
        os.chdir(regdirs[0])
        print(os.getcwd())
    else:
        print("No directories found matching the pattern '*Regenerated*'")
    print(regdirs)
    # os.chdir(regdirs[0])
    files = glob.glob('*mVvsRHE*.txt')
    sorted_files = sorted(files, key=lambda x: int(x.split("_Efin_-")[-1].replace("mVvsRHE.txt", "")), reverse=True)
    print(sorted_files[0])
    try:
        df = pd.read_csv(sorted_files[0])
        print(df)
        plt.plot(df['Potential V vs RHE'], df[' Current mA cm-2'], label=label, color=color)
        # overpotential = LSV_getoverpotential(df['Potential V vs RHE'], df['Current mA cm-2'],-criteria_current)
        # new_row = [f'{sorted_files[0].split("_LSV_")[0]}', overpotential]
        # df_eta.loc[len(df_eta)] = new_row
        # eta.append(overpotential)
        os.chdir('..')
    except:
        os.chdir('..')


# 
def PlotLastCV(df, file):
    match = re.search(r'(-?\d+)mVvsRHE', file)
    vertex = 0.0132
    nearest_index = find_nearest_index(df['Potential V vs RHE'], vertex, 0.0005)
    fstdf = df.iloc[nearest_index[0]:nearest_index[1]]
    plt.plot(fstdf['Potential V vs RHE'], fstdf[' Current mA cm-2'])
    # print(f'Eini:{vertex}, index:{nearest_index}')
    # slice the CV profile


# 
def PlotHERCV(gasKOH: str, color, label: str, cycle: str):
    # colors = sns.color_palette("Paired")
    regdirs = glob.glob(f'*{gasKOH}*')
    if regdirs:

        os.chdir(regdirs[0])
    else:
        print("No directories found matching the pattern '*Regenerated*'")
    # print(regdirs)
    # os.chdir(regdirs[0])
    files = glob.glob('*50mV*mVvsRHE.txt')
    sorted_files = sorted(files, key=lambda x: int(x.split("_Efin_-")[-1].replace("mVvsRHE.txt", "")), reverse=True)
    print(sorted_files)
    try:
        df = pd.read_csv(sorted_files[0])
        print(sorted_files[0])
        if cycle == 'last':
            vertex = 0.01329
            nearest_index = find_nearest_index(df['Potential V vs RHE'], vertex, 0.0005)
            print(nearest_index)
            fstdf = df.iloc[nearest_index[0][2]:]
            plt.plot(fstdf['Potential V vs RHE'], fstdf[' Current mA cm-2'], label=label, color=color)
            os.chdir('..')
        elif cycle == 'first':
            vertex = 0.013
            nearest_index = find_nearest_index(df['Potential V vs RHE'], vertex, 0.0005)
            fstdf = df.iloc[nearest_index[0][0]:nearest_index[0][1] + 1]
            plt.plot(fstdf['Potential V vs RHE'], fstdf[' Current mA cm-2'], label=label, color=color)
            os.chdir('..')
        else:
            plt.plot(df['Potential V vs RHE'], df[' Current mA cm-2'], label=label, color=color)
            # overpotential = LSV_getoverpotential(df['Potential V vs RHE'], df['Current mA cm-2'],-criteria_current)
            # new_row = [f'{sorted_files[0].split("_LSV_")[0]}', overpotential]
            # df_eta.loc[len(df_eta)] = new_row
            # eta.append(overpotential)
            os.chdir('..')
    except:
        os.chdir('..')


# 
def PlotsrdepCV(gasKOH: str):
    colors = sns.color_palette("rocket", 10)
    regdirs = glob.glob(f'*{gasKOH}*')
    if regdirs:

        os.chdir(regdirs[0])
    else:
        print("No directories found matching the pattern '*Regenerated*'")
    files = glob.glob('*sr*mVvsRHE.txt')
    sorted_files = sorted(files, key=lambda x: int(x.split("_sr_")[1].split("mVs")[0]), reverse=False)
    print(sorted_files)
    for x, dir in enumerate(sorted_files):
        df = pd.read_csv(sorted_files[x])
        plt.plot(df['Potential V vs RHE'], df[' Current mA cm-2'],
                 label=f"{int(sorted_files[x].split('_sr_')[1].split('mVs')[0])} mV/s", color=colors[x])


def SaveMergedSRDepCV(gasKOH: str, output_csv: str = "merged_data.csv"):
    # Find all directories matching the pattern
    regdirs = glob.glob(f'*{gasKOH}*')
    if regdirs:
        os.chdir(regdirs[0])  # Change to the first matching directory
    else:
        print("No directories found matching the pattern '*Regenerated*'")
        return

    # Find and sort files matching the pattern
    files = glob.glob('*sr*mVvsRHE.txt')
    sorted_files = sorted(files, key=lambda x: int(x.split("_sr_")[1].split("mVs")[0]), reverse=True)

    # Initialize an empty DataFrame
    merged_df = pd.DataFrame()

    # Loop through each file, read it, and append to the main DataFrame
    for x, file in enumerate(sorted_files):
        df = pd.read_csv(file)
        # Add a column for the scan rate based on the filename
        df['Scan Rate (mV/s)'] = int(file.split('_sr_')[1].split('mVs')[0])
        merged_df = pd.concat([merged_df, df], ignore_index=True)

    # Save the merged DataFrame as a CSV
    merged_df.to_csv(output_csv, index=False)
    print(f"Data merged and saved to {output_csv}")


# %%
'''
# Plot CA in Parent folder
files_CA = glob.glob('CA*.txt')
plt.xlabel('Time/s')
plt.ylabel('Current Density mA cm-2')
plt.xlim(-1,120.0)

for file in files_CA:
    skiprow = fdtitle('Time/sec', file)
    titles = ['Time/s', 'Current/A']
    df = pd.read_csv(file, skiprows=skiprow - 1, header=0, names=titles)
    df['Current/A']=df['Current/A'].apply(lambda x: x/0.0706858*1000 ).rename('Current Density mA cm-2')
    plt.plot(df['Time/s'], df['Current/A'], label=file)
plt.legend(frameon=False)
try:
    plt.savefig(os.path.join(os.getcwd(),'Plot/CAforRegeneration.png'), dpi = 600)
except FileNotFoundError:
    os.mkdir('Plot')
    plt.savefig(os.path.join(os.getcwd(),'Plot/CAforRegeneration.png'), dpi = 600)
plt.show()
'''


###  Get evolution of OCP value
# todo: How to print in creat time order ? deal with
def PlotOCP(Solvent='KOH'):
    df_ocp = pd.DataFrame(columns=['Time', 'File', 'OCP_value'])
    dirs = glob.glob('*LSV*')
    if Solvent == 'Phos':
        dirs = [file for file in dirs if 'inPhos' in file]
    else:
        dirs = [file for file in dirs if 'inKOH' in file]

    for dir in dirs:
        os.chdir(dir)  # change to that LSV folder
        files_ocp = glob.glob('*OCP*.txt')  # Find all the file with pattern
        files = glob.glob('*OCP*.txt')
        for file in files:
            skiprow = fdtitle('Time/sec', file)
            titles = ['Time/s', 'Potential V vs ref']
            df = pd.read_csv(file, skiprows=skiprow - 1, header=0, names=titles)
            ocp = df['Potential V vs ref'].mean()
            index = len(df_ocp)
            df_ocp.loc[index] = [None, dir, ocp]

        os.chdir(os.path.dirname(os.getcwd()))
    print(df_ocp)
    df_ocp['Time'] = df_ocp['File'].str.extract(r'(\d{4}-\d{2}-\d{2}T\d{2}_\d{2}_\d{2})')
    df_ocp['Time'] = pd.to_datetime(df_ocp['Time'], format='%Y-%m-%dT%H_%M_%S')
    sorted_df_ocp = df_ocp.sort_values(by='Time')
    print(sorted_df_ocp)
    return sorted_df_ocp


### Get Deposition curve
# Plot Dep in Parent folder
def Plotitcurve(label, color):
    dirs = glob.glob('*Deposit*')
    # dirs = sorted(dirs, key=extract_datetime)
    for _, dir in enumerate(dirs):
        os.chdir(dir)
        files_Dep = glob.glob('*Deposition*.txt')

        for file in files_Dep:
            skiprow = fdtitle('Time/sec', file)
            titles = ['Time/s', 'Current/A']
            df = pd.read_csv(file, skiprows=skiprow - 1, header=0, names=titles)
            df['Current/A'] = df['Current/A'].apply(lambda x: x / 0.0706858 * 1000).rename('Current Density mA cm-2')
            df.rename(columns={'Current/A': 'Current Density mA cm-2'}, inplace=True)
            # print(df)
            area = np.trapz(df['Current Density mA cm-2'], x=df['Time/s'])
            print(f'{dir} {area}')
            plt.plot(df['Time/s'], df['Current Density mA cm-2'], label=label, color=color)
        os.chdir(os.path.dirname(os.getcwd()))
    return area
