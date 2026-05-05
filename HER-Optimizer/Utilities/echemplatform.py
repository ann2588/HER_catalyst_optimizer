import warnings
import numpy as np
import pandas as pd
import sys
import subprocess
import pytentiostats as pstat
from ika.magnetic_stirrer import MagneticStirrer
import time
import datetime
from scipy.signal import find_peaks
from scipy.signal import savgol_filter
from ismatec.peristaltic_pump import RegloICCFourChannel, ChannelStatus
import ismatec.errors
import Utilities.MXII_valve as mxii
import os
import io
import matplotlib.pyplot as plt
import Utilities.portaccess as portaccess
from Hardwaretesting.Valves import changing_port
from datetime import datetime
import Utilities.MFC as MFC
import asyncio
import seaborn as sns
import glob
from pathlib import Path
# %% Basic setting
message_completed = 'Experiment completed'
message_stuck = 'Unusual impedende in electrolyte, Check if the tube stuck'
PROJECT_ROOT = Path(__file__).resolve().parents[1]
script_path = os.environ.get("HER_SLACK_BOT_PATH", str(PROJECT_ROOT / "Utilities" / "slack-bot.py"))
default_path = os.environ.get("HER_DATA_PATH", str(PROJECT_ROOT / "data"))
np.errstate(divide='ignore')
warnings.simplefilter(action='ignore', category=(FutureWarning))

# CHI Setting
model = 'chi760e'
path = os.environ.get('CHI760E_PATH', 'C:/chi')


def get_pstat_path():
    return os.environ.get('CHI760E_PATH', path)


def send_status_message(message):
    if os.path.isfile(script_path):
        subprocess.run([sys.executable, script_path, "-m", message], check=False)

# %% Hardware Connection and Setup
global icca, iccb
plate = MagneticStirrer(device_port=portaccess.port_plate)
switchv = mxii.MX_valve(portaccess.port_switchvalve, ports=2, name='Switching', verbose=True)
valve_slva = mxii.MX_valve(portaccess.port_selectionvalveA, ports=6, name='SelectionA', verbose=True)
valve_slvb = mxii.MX_valve(portaccess.port_selectionvalveB, ports=6, name='SelectionB', verbose=True)
icca = RegloICCFourChannel(portaccess.port_pumpA)
iccb = RegloICCFourChannel(portaccess.port_pumpB)
#%%
# PUMP and VALVE
iccb_channel = {'waste': 1, 'spelec': 2, 'acid': 3, 'koh': 4}
icca_channel = {'water': 1, 'phosphate': 2, 'slvb': 3, 'slva': 4}
switching_position = {'loading': 1, 'injection': 2}
stock_solution_channels_a = {'blank': 1, 'V': 2, 'Mg': 3, 'Fe': 4, 'Co': 5, 'Ni': 6}
stock_solution_channels_b = {'blank': 1, 'Cr': 2, 'P': 3, 'S': 4, 'Se': 5, 'Cu': 6}
volume = {
    '1mL': {'rpm': 33, 'second': 15},  # plating solution
    '2mL': {'rpm': 33, 'second': 30},  # Reaction volume
    '3mL': {'rpm': 50, 'second': 30},  # Reaction volume
    '4mL': {'rpm': 50, 'second': 40},  # Reaction volume
    '5mL': {'rpm': 100, 'second': 20},  # Rinsing
    '6mL': {'rpm': 100, 'second': 25}  # Rinsing
}

# MFC function
async def run_with_retry(coroutine, *args, **kwargs):
    try:
        await coroutine(*args, **kwargs)
    except:
        await coroutine(*args, **kwargs)

def purgeN2(flowrate=50):
    changing_port(switchv, switching_position['loading'])
    asyncio.run(run_with_retry(MFC.n2on, flowrate))

def offN2(flowrate=0):
    asyncio.run(run_with_retry(MFC.n2off, flowrate))

def purgeH2(flowrate=50):
    asyncio.run(run_with_retry(MFC.H2on, flowrate))

def offH2(flowrate=0):
    asyncio.run(run_with_retry(MFC.H2off, flowrate))


#  Utilities for Liquid handling
def stirring(plate=None, stirring_time=30, rpm=800):
    print(f'Stirring at {rpm} rpm for {stirring_time} s')
    plate.start_stirring()
    plate.target_stir_rate = rpm
    time.sleep(stirring_time)
    plate.stop_stirring()
    print('Finished stirring\n')
    time.sleep(5)


def select_solution_rinsing(solution_type=None):
    if solution_type == 'water':
        return icca, icca_channel.get(solution_type, 'water')
    elif solution_type == 'phosphate':
        return icca, icca_channel.get(solution_type, 'phosphate')
    else:
        return iccb, iccb_channel.get(solution_type, 'Channel not found')


def assign_flowrate(volume_add):
    flow_rate = volume.get(volume_add, {}).get('rpm')
    second = volume.get(volume_add, {}).get('second')

    if flow_rate is None or second is None:
        print('The designated volume is not defined')

    return flow_rate, second


def flushing(pump, channel, rpm, second):
    pump.set_mode_pump_rpm(channel, rpm)
    try:
        pump.start(channel)
        print(f'\nStarting {pump} {channel} channel at {rpm} rpm')
    except ismatec.errors.PumpError:
        pump.stop(channel)
        print(f'\n{pump} {channel} keeps stopped because 0 rpm assigned.')
    time.sleep(second)
    pump.stop(channel)

#%%
def pumping_waste_out(time=40):
    plate.start_stirring()
    flushing(iccb, 1, 100, time)
def add_solution(solution_type_rinse, volume_add):
    plate.start_stirring()
    pump, channel = select_solution_rinsing(solution_type_rinse)
    flow_rate, second = assign_flowrate(volume_add)
    flushing(pump, channel, flow_rate, second)
def cell_rinsing(rinsing_solution, target_solution=None, repetitions=3, acidrinse=False):
    def run_solution(solution, volume = '5mL'):
        for _ in range(repetitions):
            plate.start_stirring()
            add_solution(solution, volume)  # pump control
            pumping_waste_out()  # pump control
            print(_ + 1, ' rinsed by ', solution)
        print('Cell rinsed by ', solution, ' completed')

    pumping_waste_out()  # Initial waste_out() call
    run_solution(rinsing_solution, '6mL')
    if target_solution != None:
        run_solution(target_solution, '5mL')
        print('Cell rinsing completed')
        add_solution(target_solution, '4mL')  # pump control
        print(target_solution, ' added to cell')
    else:
        add_solution('water', '4mL')
        print('Cell rinsing completed')
    if acidrinse == True:
        stirring(plate, 600)
        print('Acid rinsing completed')
def titration(element, number_of_drops, pump, valve, valve_port, pump_channel):  # to be optimized to use acid/base as little as possible
    print(valve, valve_port)
    changing_port(valve, valve_port)
    #changing_port(switchv, switching_position['loading'])
    purgeN2()

    # load mode initial filling
    pump.set_mode_pump_rpm(pump_channel, 100)  # check the input value
    pump.start(pump_channel)
    time.sleep(10)
    pump.stop(pump_channel)
    # 5s per titration
    # number of drops acts as input passed into pH_titration
    # start stirring here ( estimate a time )
    # optimize the work flow and time to make it time efficient
    for i in range(number_of_drops):
        plate.start_stirring()
        pump.set_mode_pump_rpm(pump_channel, 20)
        pump.start(pump_channel)  # initial filling of each tube
        time.sleep(3)
        changing_port(switchv, switching_position['injection'])
        print(f'Injecting {element}')
        pump.start(pump_channel)
        time.sleep(3)
        changing_port(switchv, switching_position['loading'])
        time.sleep(1)
        pump.stop(pump_channel)

def select_solution(element= None):
    if element in ['V', 'Mg', 'Fe', 'Co', 'Ni']:
        valve = valve_slva
        valve_port = stock_solution_channels_a[element]
        pump = icca  # to remove the quote
        pump_channel = icca_channel['slva']
    elif element in ['Cr', 'S', 'Se', 'Cu', 'P']:
        valve = valve_slvb
        valve_port = stock_solution_channels_b[element]
        pump = icca  # to remove the quote
        pump_channel = icca_channel['slvb']
    elif element in ['blank']:
        #elif element in ['blanka']:  # define blank as the blank in selection valve a here
        #    valve = valve_slva
        #    valve_port = stock_solution_channels_a['blank']
        #    pump = icca
        #    pump_channel = icca_channel['slva']
        #elif element in ['blankb']:  # define blank as the blank in selection valve a here
        valve = valve_slvb
        valve_port = stock_solution_channels_b['blank']
        pump = icca
        pump_channel = icca_channel['slvb']
    else:
        raise ValueError("Element not recognized")  # Do sth else to add blank solution
    return valve, valve_port, pump, pump_channel
#%%
def titration_rinsing(valve, valve_port,pump, pump_channel):
    changing_port(valve, valve_port)
    changing_port(switchv, switching_position['loading'])
    pump.set_mode_pump_rpm(pump_channel, 100)  # check the input value
    pump.start(pump_channel)
    time.sleep(15)
    pump.stop(pump_channel)

#%% Utilitis for Plating Solution Making
#Pass one of the following samples to test the plating solution module
titrationmoduletestsample = {'V': 1, 'Cr': 1, 'Mg': 1, 'Fe': 1, 'Co': 1, 'Ni': 1, 'Cu': 1, 'S': 1, 'Se': 1, 'P': 1}
#rinsingvalvesample = {'blanka':5, 'blankb':5}
#%%
def test_make_solution_module(sample):
    '''
    This function run every channel in making solution module for 1 droplet
    please run this function and check in person to see if every channel is working

    '''
    for element, partition in sample.items():
        if element in ['V', 'Cr', 'Mg', 'Fe', 'Co', 'Ni', 'Cu', 'S', 'Se', 'P', 'blank']:
            if partition == 0.0:
                continue
            else:
                valve, valve_port, pump, pump_channel = select_solution(element=element)
                plate.start_stirring()
                print(
                    f'Adding {element} for {int(partition)} times with {valve} at port {valve_port}, {pump} running at channel {pump_channel}')
                titration(element, int(partition), pump, valve, valve_port, pump_channel)
                if valve == valve_slva:
                    print(f'Rinsing titration channel by blank solution from {valve_slva}')
                    titration_rinsing(valve_slva, stock_solution_channels_a['blank'], icca,
                                      pump_channel=icca_channel['slva'])
                elif valve == valve_slvb:  # valve == valve_slvb
                    print(f'Rinsing titration channel by blank solution from {valve_slvb}')
                    titration_rinsing(valve_slvb, stock_solution_channels_b['blank'], icca,
                                  pump_channel=icca_channel['slvb'])
                else:
                    continue
        else:
            continue
    print('make_solution_test finished')

#%%
def make_solution(sample:dict):
    global valve
    cell_rinsing('water', 'spelec', 3)
    pumping_waste_out()
    add_solution('spelec', '4mL')
    add_solution('spelec', '1mL')# pump control
    print('1 mL spelec added to cell')
    for element, partition in sample.items():
        if element in ['V', 'Cr', 'Mg', 'Fe', 'Co', 'Ni', 'Cu', 'S', 'Se', 'P']:
            if partition == 0.0:
                continue
            else:
                valve, valve_port, pump, pump_channel = select_solution(element=element)
                plate.start_stirring()
                print(
                    f'Adding {element} for {int(partition)} times with {valve} at port {valve_port}, {pump} running at channel {pump_channel}')
                titration(element, int(partition), pump, valve, valve_port, pump_channel)
                if valve == valve_slva:
                    print(f'Rinsing titration channel by blank solution from {valve_slva}')
                    titration_rinsing(valve_slva, stock_solution_channels_a['blank'], icca, pump_channel=icca_channel['slva'])
                elif valve == valve_slvb: #valve == valve_slvb
                    print(f'Rinsing titration channel by blank solution from {valve_slvb}')
                    titration_rinsing(valve_slvb, stock_solution_channels_b['blank'], icca, pump_channel=icca_channel['slvb'])
                else:
                    continue
        else:
            continue
    #add_solution('spelec', '2mL')  # pump control
    print('spelec added to cell to 5 mL total volume')
#%%
doepath = "HER-Optimizer/batch_pretrain_doe.csv" # PLACE THE PATH OF YOUR DoE.csv here
#%%
def doeprocess(doepath:str = doepath,start:int=0):
    '''
    This function process the provided DoE in csv file into a dictionary with number of experiment
    '''
    # NOTE: The element series here is different from the order of channel
    # access DoE and turn it into a series of experiment
    element = ['V', 'Cr', 'Mg', 'Fe', 'Co', 'Ni', 'Cu', 'S', 'Se', 'P', 'blank', 'Volt','Time']
    trials = pd.read_csv(doepath, sep=',', index_col=0)
    exp_dicts = {}
    for i in range(trials.shape[0]):
        ext = trials.iloc[i].tolist()
        element_dict = {el: ex for el, ex in zip(element, ext)}
        #element_dict["blank"] = 70 - sum(element_dict.values())
        exp_dicts[f'exp{i+start}'] = element_dict
    print(exp_dicts)
    return exp_dicts

#Todo: How to incoorporate the blanka and blankb into process?

#%% Echem utilities
def create_directory(path):
    """Create a directory if it doesn't already exist."""
    os.makedirs(path, exist_ok=True)
def generate_timestamp():
    """Generate a timestamp string."""
    datetime_str = datetime.now().isoformat(timespec='seconds')
    return datetime_str.replace(" ", "_").replace(":", "_")

def getOCP(child_filepath, time_ocp=5):
    model = 'chi760e'
    path = get_pstat_path()
    pstat.Setup(model=model, path_exe=path, folder=child_filepath)
    print('Measuring OCP')
    ocpname = f"OCP_{generate_timestamp()}"
    ocp = pstat.OCP(ttot=time_ocp, dt=0.01, fileName=ocpname)
    time.sleep(10)
    ocp.run()
    time.sleep(5)
    ocp_data = pstat.LoadOCP(ocpname, folder=child_filepath, model=model)
    print('Finished measuring OCP\n')
    print('Waiting 15 s')
    time.sleep(15)
    print('Finished waiting\n')
    return ocp_data.E
def getRu(child_filepath, ocp_data_E):
    print('Measuring EIS at OCP and get Ru')
    Eini = np.mean(ocp_data_E)
    runame = f"EIS_{generate_timestamp()}"
    eis = pstat.EIS(Eini=Eini, fl=5e5, fh=1e6, amp=0.005, fileName=runame, header='EIS for Ru')
    time.sleep(5)
    eis.run()
    time.sleep(5)
    eis_data = pstat.LoadEIS(runame, folder=child_filepath, model='chi760e')
    Ru = eis_data.rZ[np.argmax(eis_data.iZ)]
    print('Finished measuring EIS at OCP and get Ru\n')
    print(f'Ru: {Ru}')
    print('Waiting 15 s')
    time.sleep(15)
    print('Finished waiting\n')
    return Ru
#%%
def LSV_converter_inexp(potential, current, phosphate=False):
    '''
    Convert LSV from Ag/AgCl to RHE scale
    '''
    evsrhe = potential + 0.205 + (7.6 if phosphate else 13.7) * 0.059
    currend = -current / 0.0706858 * 1000  # for Pt disk
    # Todo write a file exported as txt.
    return {'potential_RHE': evsrhe, 'current_density': currend}
#%%
def LSV_getoverpotential(x, y, criteria):
    '''
    input: LSV curve
    return: potential at criteria current
    '''
    smoothed_x = savgol_filter(x, window_length=5, polyorder=3, mode='nearest')
    smoothed_y = savgol_filter(y, window_length=5, polyorder=3, mode='nearest')
    #plt.plot(smoothed_x, smoothed_y)
    return np.interp(criteria, smoothed_y, smoothed_x)
#%%
def plot_cv_data(cvrhe, filepath, filename, xlim=None, ylim=None):
    """
    This function plots the CV data.
    :param cvrhe: Dictionary containing 'potential_RHE' and 'current_density'
    :param filepath: Path to save the plot
    :param filename: Name of the file to save the plot
    """
    plt.figure()
    plt.plot(cvrhe['potential_RHE'], cvrhe['current_density'])
    plt.xlabel('Potential (V vs. RHE)')
    plt.ylabel('Current Density (mA cm-2)')
    plt.title('CV')
    if xlim is not None:
        plt.xlim(xlim)
    if ylim is not None:
        plt.ylim(ylim)
    plt.savefig(os.path.join(filepath, f"{filename}.png"))


def find_nearest_index(cvref_E, Ev1, threshold=0.0005):
    """
    Find the index of the element in cvref.E that is closest to Ev1 and the difference is less than threshold.
    """
    differences = np.abs(cvref_E - Ev1)
    valid_indices = np.where(differences < threshold)
    if len(valid_indices) == 0:
        raise ValueError("No valid index found with the given threshold.")
    return valid_indices

def save_cvrhe_to_txt(cvrhe, filepath, filename):
    """
    This function saves the CV data to a text file with comma-separated values.
    :param cvrhe: Tuple containing potential_RHE and current_density
    :param filepath: Path to save the text file
    :param filename: Name of the file to save the text file
    """
    txt_filename = f"{filename}vsRHE.txt"
    with open(os.path.join(filepath, txt_filename), 'w') as f:
        f.write("Potential V vs RHE, Current mA cm-2\n")
        for potential, current in zip(cvrhe['potential_RHE'], cvrhe['current_density']):
            f.write(f"{potential},{current}\n")

def run_ca(time=120, Hz=1, sensitivity=1e-3):
    caname = f"CA_{generate_timestamp()}"
    caheader = 'CA'
    ca = pstat.CA(Estep=1, Ehigh=1, Elow=-1.5, dt=0.1, ttot=1 / Hz, sens=sensitivity, fileName=caname, header=caheader, tstep=time + 1)
    ca.run()
    return caname

def LSV_HER(mainpath, sample, note='LSVinKOH', criteria_current=10):
    '''
    This function do LSV scan automatically and extend potential until the max reach 10mA cm-2 #Todo
    :param mainpath: The path to store the data
    :param sample: Your Sample name
    :param note: This LSV typically run in KOH
    :param criteria_current: current density in positive value (deal with negative value)
    :return: Overpotential in negative value
    '''
    filename = sample
    main_filepath = mainpath
    create_directory(main_filepath)

    datetime_str = generate_timestamp()
    adding = f'{sample}-{datetime_str}-{note}'

    child_filepath = os.path.join(main_filepath, adding)
    create_directory(child_filepath)

    model = 'chi760e'
    path = get_pstat_path()
    pstat.Setup(model=model, path_exe=path, folder=child_filepath)

    # N2 Purging at 20 sccm for 30 mins
    print('Start purging N2 for 30 mins')
    #asyncio.run(MFC.n2on())
    #time.sleep(1800)
    #asyncio.run(MFC.n2off())
    print('Stop purging')


    stirring(plate, 30)
    time.sleep(30)

    ocp_data_E = getOCP(child_filepath)
    Ru = getRu(child_filepath, ocp_data_E)

    # LSV measurement
    # plate.start_stirring()
    Efin_LSV = -1.7
    sr_lsv = 0.050
    max_current = 0
    plt.figure()
    plt.xlim(0, -1.6)
    plt.ylim(0, -15.0)
    plt.xlabel('E (V vs. RHE)')
    plt.ylabel('Current Density (mA cm-2)')
    eta = 0

    while max_current <= criteria_current and Efin_LSV >= -3.0:
        print(f'Measuring LSV at {sr_lsv} V/s')
        fileName = filename + '_LSV_{:.0f}mVs_Efin_{:.0f}mV'.format(sr_lsv * 1000, Efin_LSV * 1000)
        header = 'LSV ran at {:.0f} mVs with Efin at {:.0f}mV'.format(sr_lsv * 1000, Efin_LSV * 1000)
        lsv = pstat.LSV(Eini=-0.6, Efin=Efin_LSV, sr=sr_lsv, dE=0.001, sens=1e-4, fileName=fileName,
                        header=header)  # E to be customized
        lsv.ircomp(Ru=Ru)  # Ru get from EIS
        time.sleep(5)
        lsv.run()
        time.sleep(5)
        # plate.stop_stirring()
        data = pstat.LoadLSV(fileName, folder=child_filepath, model=model)
        lsvrhe = LSV_converter_inexp(data.E, data.i, phosphate=True)
        max_current = max(-lsvrhe['current_density'])
        print(lsvrhe['potential_RHE'])
        plt.plot(lsvrhe['potential_RHE'], lsvrhe['current_density'])
        plt.xlabel('E (V vs. RHE)')
        plt.ylabel('Current Density (mA cm-2)')
        # plt.legend(title=f'{sample}')
        print('Finished measuring LSV')
        # stirring
        stirring(plate, stirring_time=30)
        print('Waiting 15 s')
        time.sleep(15)
        print('Finished waiting\n')
        if max_current > criteria_current:
            smoothed_x = savgol_filter(np.asarray(lsvrhe['potential_RHE']), window_length=5, polyorder=3,
                                       mode='nearest')
            smoothed_y = savgol_filter(np.asarray(lsvrhe['current_density']), window_length=5, polyorder=3,
                                       mode='nearest')
            # Debug statements to check the shapes and contents of the arrays
            print(f"Shape of smoothed_x: {smoothed_x.shape}")
            print(f"Shape of smoothed_y: {smoothed_y.shape}")

            # Ensure the arrays are 1-dimensional
            if smoothed_x.ndim > 1:
                smoothed_x = smoothed_x.flatten()
            if smoothed_y.ndim > 1:
                smoothed_y = smoothed_y.flatten()
            plt.plot(smoothed_x, smoothed_y)
            eta = np.interp(-criteria_current, smoothed_y, smoothed_x)
            print(eta)
            # Store eta here
            plt.legend(title=f'{sample}')
            plt.savefig(child_filepath + '/' + fileName + '.png')
            #plt.show()
            break
        else:
            Efin_LSV -= 0.2
            print(
                f'Maximum current density = {max_current}  < {criteria_current} mA. extend the potential window to {Efin_LSV}')
    #plt.show()
    return eta
#%%
def LSV_Regeneration(mainpath, sample, note='LSVinPhos', Efin_LSV=-2.1, current_criteria=5):
    ''' #Todo merge it with the LSV_HER(), there are basically the same with different parameters
    This function run LSV scan automatically and extend potential until the current reach current_criteria mA cm-2 #Todo
    :param mainpath: The path to store the data
    :param sample: Your Sample name
    :param note: This LSV typically run in Phosphate buffer
    :param criteria_current: current density in positive value (deal with negative value)
    :return: Onsetpotential V vs. RHE in negative value
    '''
    filename = sample
    main_filepath = mainpath
    create_directory(main_filepath)

    datetime_str = generate_timestamp()
    adding = f'{sample}-{datetime_str}-{note}'

    child_filepath = os.path.join(main_filepath, adding)
    create_directory(child_filepath)

    model = 'chi760e'
    path = get_pstat_path()
    pstat.Setup(model=model, path_exe=path, folder=child_filepath)

    stirring(plate, 30)
    time.sleep(30)

    ocp_data_E = getOCP(child_filepath)
    Ru = getRu(child_filepath, ocp_data_E)

    # LSV measurement
    # plate.start_stirring()
    # Efin_LSV = -2.1
    sr_lsv = 0.050
    max_current = 0
    plt.figure()
    plt.xlim(0, -1.75)
    plt.ylim(0, -5.0)
    plt.xlabel('E (V vs. RHE)')
    plt.ylabel('Current Density (mA cm-2)')
    onset = 0
    while max_current <= current_criteria and Efin_LSV >= -2.5:
        print(f'Measuring LSV at {sr_lsv} V/s')
        fileName = filename + '_LSV_{:.0f}mVs_Efin_{:.0f}mV'.format(sr_lsv * 1000, Efin_LSV * 1000)
        header = 'LSV ran at {:.0f} mVs with Efin at {:.0f}mV'.format(sr_lsv * 1000, Efin_LSV * 1000)
        lsv = pstat.LSV(Eini=-0.6, Efin=Efin_LSV, sr=sr_lsv, dE=0.001, sens=1e-4, fileName=fileName,
                        header=header)  # E to be customized
        lsv.ircomp(Ru=Ru)  # Ru get from EIS
        time.sleep(5)
        lsv.run()
        time.sleep(5)
        # plate.stop_stirring()
        data = pstat.LoadLSV(fileName, folder=child_filepath, model=model)
        lsvrhe = LSV_converter_inexp(data.E, data.i, phosphate=True)
        max_current = max(-lsvrhe['current_density'])
        print(lsvrhe['potential_RHE'])
        plt.plot(lsvrhe['potential_RHE'], lsvrhe['current_density'])
        plt.xlabel('E (V vs. RHE)')
        plt.ylabel('Current Density (mA cm-2)')
        plt.xlim(0,-1.6)
        # plt.legend(title=f'{sample}')
        print('Finished measuring LSV')
        # stirring



        if max_current > current_criteria:
            smoothed_x = savgol_filter(np.asarray(lsvrhe['potential_RHE']), window_length=5, polyorder=3, mode='nearest')
            smoothed_y = savgol_filter(np.asarray(lsvrhe['current_density']), window_length=5, polyorder=3, mode='nearest')
            # Debug statements to check the shapes and contents of the arrays
            print(f"Shape of smoothed_x: {smoothed_x.shape}")
            print(f"Shape of smoothed_y: {smoothed_y.shape}")

            # Ensure the arrays are 1-dimensional
            if smoothed_x.ndim > 1:
                smoothed_x = smoothed_x.flatten()
            if smoothed_y.ndim > 1:
                smoothed_y = smoothed_y.flatten()
            plt.plot(smoothed_x, smoothed_y)
            onset =  np.interp(-current_criteria, smoothed_y, smoothed_x)
            #onset = LSV_getoverpotential(lsvrhe['potential_RHE'], lsvrhe['current_density'], -current_criteria)
            plt.legend()
            plt.savefig(child_filepath + '/' + fileName + '.png')

        else:
            Efin_LSV -= 0.2
            print(
                f'Maximum current density = {max_current}  < {current_criteria} mA. extend the potential window to {Efin_LSV}')
        stirring(plate, stirring_time=30)
    #plt.show()
    plt.close()
    # onset = onset-0.205-7.6*0.059 #convert V vs. RHE back to V vs. Ag/AgCl scale
    return onset  # in RHE scale
def LSV_fixrange(mainpath:str, sample:str, note='LSVinPhos', Efin_LSV=-2.3):
    '''
    This function do LSV scan automatically within fix potential range [-0.9, -2.3]
    :param mainpath: The path to store the data
    :param sample: Your Sample name
    :param note: This LSV typically run in KOH
    :return: The maximum current density
    '''
    filename = sample
    main_filepath = mainpath
    create_directory(main_filepath)

    datetime_str = generate_timestamp()
    adding = f'{sample}-{datetime_str}-{note}'

    child_filepath = os.path.join(main_filepath, adding)
    create_directory(child_filepath)

    model = 'chi760e'
    path = get_pstat_path()
    pstat.Setup(model=model, path_exe=path, folder=child_filepath)

    stirring(plate, 30)
    time.sleep(30)

    ocp_data_E = getOCP(child_filepath)
    Ru = getRu(child_filepath, ocp_data_E)

    # LSV measurement
    # plate.start_stirring()
    # Efin_LSV = -2.1
    sr_lsv = 0.050
    max_current = 0
    plt.figure()
    plt.xlim(0, -2.0)
    plt.ylim(0, -5.0)
    plt.xlabel('E (V vs. RHE)')
    plt.ylabel('Current Density (mA cm-2)')
    print(f'Measuring LSV at {sr_lsv} V/s')
    fileName = filename + '_LSV_{:.0f}mVs_Efin_{:.0f}mV'.format(sr_lsv * 1000, Efin_LSV * 1000)
    header = 'LSV ran at {:.0f} mVs with Efin at {:.0f}mV'.format(sr_lsv * 1000, Efin_LSV * 1000)
    lsv = pstat.LSV(Eini=-0.6, Efin=Efin_LSV, sr=sr_lsv, dE=0.001, sens=1e-4, fileName=fileName,
                    header=header)  # E to be customized
    lsv.ircomp(Ru=Ru)  # Ru get from EIS
    time.sleep(5)
    lsv.run()
    time.sleep(5)
    plate.stop_stirring()
    data = pstat.LoadLSV(fileName, folder=child_filepath, model=model)
    lsvrhe = LSV_converter_inexp(data.E, data.i, phosphate=True)
    #ndata_E, ndata_i = LSV_converter_inexp(data.E, data.i, phosphate=True)
    smoothed_x = savgol_filter(np.asarray(lsvrhe['potential_RHE']), window_length=5, polyorder=3, mode='nearest')
    smoothed_y = savgol_filter(np.asarray(lsvrhe['current_density']), window_length=5, polyorder=3, mode='nearest')
    # Debug statements to check the shapes and contents of the arrays
    print(f"Shape of smoothed_x: {smoothed_x.shape}")
    print(f"Shape of smoothed_y: {smoothed_y.shape}")

    # Ensure the arrays are 1-dimensional
    if smoothed_x.ndim > 1:
        smoothed_x = smoothed_x.flatten()
    if smoothed_y.ndim > 1:
        smoothed_y = smoothed_y.flatten()
    plt.plot(smoothed_x, smoothed_y)
    onsetP = np.interp(-5, smoothed_y, smoothed_x)
    #onsetP = LSV_getoverpotential(ndata_E, ndata_i[:, 0], -5)
    plt.plot(lsvrhe['potential_RHE'], lsvrhe['current_density'])
    print('Finished measuring LSV')
    # stirring
    stirring(plate, stirring_time=30)
    print('Waiting 15 s')
    time.sleep(15)
    print('Finished waiting\n')
    plt.legend()
    plt.savefig(child_filepath + '/' + fileName + '.png')
    #plt.show()
    plt.close()
    return onsetP

def electrodeposition(mainpath, sample, E_ed, Time_ed, note='Deposition'):
    '''
    This function perform electrodeposition with designated potential and time
    :param mainpath: The dic you want to store your data
    :param sample: Sample name
    :param E_ed: Potential for electrodeposition in negative value
    :param Time_ed: Deposition time in second
    :param note:
    :return: #Todo Return integrated C
    '''
    # CHI Settings

    filename = sample
    main_filepath = mainpath
    create_directory(main_filepath)

    datetime_str = generate_timestamp()
    adding = f'{sample}-{datetime_str}-{note}'

    child_filepath = os.path.join(main_filepath, adding)
    create_directory(child_filepath)

    model = 'chi760e'
    path = get_pstat_path()
    pstat.Setup(model=model, path_exe=path, folder=child_filepath)

    stirring(plate, 30)
    time.sleep(30)

    ocp_data_E = getOCP(child_filepath)
    Ru = getRu(child_filepath, ocp_data_E)

    # deposition start
    print('Electrodeposition started.')
    plate.start_stirring()
    time.sleep(15)
    fileName = sample + '_it_Edep_{:.0f}mV'.format(E_ed * 100)
    header = 'Electrodeposition at potential = {:.1f}mV'.format(E_ed)
    itcurve = pstat.i(Eini=E_ed, dt=0.1, ttot=Time_ed, sens=1e-3, fileName=fileName, header=header)  # Todo
    itcurve.ircomp(Ru=Ru)  # Ru get from EIS
    itcurve.run()
    time.sleep(5)
    plate.stop_stirring()
    itcurve_data = pstat.LoadITCURVE(fileName=fileName, folder=child_filepath, model=model)
    plt.figure()
    plt.plot(itcurve_data.t, -itcurve_data.i / 0.0706858 * 1000)
    plt.xlabel('$Time$ / s')
    plt.ylabel('Current density (mA cm-2)')
    plt.legend(title=f'E = {E_ed}')
    plt.savefig(child_filepath + '/' + 'ITCURVE' + '.png')
    plt.show()
    print('Finished electrodeposition\n')
    print('Waiting 15 s')
    time.sleep(15)
    print('Finished waiting\n')
    # charge = np.trapz(itcurve_data.i[:,0],itcurve_data.t)
def insitu_echem_regeneration(mainpath: str):
    '''
    This function perform electrode regeneration by following procedure
    1. Rinsing Cell with water and 50 mM phosphate buffer
    2. Record LSV in Phosphate buffer as criteria for Pre-Regeneration with 5 mA as current criteria
    3. Rinse cell with 1 M HNO3 and stir for 10 mins
    4. Change solvent to phosphate and run ACV for 180 s at 1 hz, +1V, -1.5V
    5. Record LSV in Phosphate buffer as criteria for Post-Regeneration with 1 mA as current criteria
    6. If onsetpotential at 5 mA difference < 0.01 V, current converged. If not, go back to step 5.
    7. If the onset potential @ 5 mA cm-2 < criteria -1.5 V vs. RHE. If not, current converged but potential not reach criteria, go back to Step3 again.
    8. If  rinse_times > 3, the catalyst cannot be removed by regeneration protocol. Error report. and (Supposedly) break function.
    NOTE: NOT INCLUDE LSV IN KOH
    The criteria should correspond to the criteria of onset potential @ 10 mA cm -2 < -1.0 V vs. RHE
    :param mainpath: your dictionary
    :return: None
    :Todo:
    '''
    model = 'chi760e'
    path = get_pstat_path()
    pstat.Setup(model=model, path_exe=path, folder=mainpath)
    cell_rinsing('water', 'phosphate', 1)
    LSV_Regeneration(mainpath, f'Pre-Regen', current_criteria=2, Efin_LSV=-1.9)
    print('Electrode Regeneration start...')
    rinse_times = 1
    onset_array = []
    while rinse_times <= 3:
        cell_rinsing('water', 'acid', acidrinse=True, repetitions=1)
        cell_rinsing('water', 'phosphate', 1)
        run_ca(180)
        i = 1
        # Set the onset potential at 10 mA because the potential curve can growth really fast before any generation
        onset = LSV_Regeneration(mainpath, f'{rinse_times}acid_{i}ac', current_criteria=2)  # set criteria for onset potential
        onset_array.append(onset)  # Ag/AgCl scale
        print('onset_array: ', onset_array)
        bkg_array = []
        bkg = 0
        Converged = True
        while Converged:
            i += 1
            run_ca(180)
            bkg = LSV_fixrange(mainpath, f'{rinse_times}acid_{i}ac', Efin_LSV=-2.3)
            # RUN LSV FOR SINGLE LINE IN RANGE FROM INIAL TO ONSET POTENTIAL AND RETURN THE MAX CURRENT
            bkg_array.append(bkg)
            print('bkg_array: ', bkg_array)
            if i > 8:
                print('Error: Current didn\'t converge. Check the status of electrode or rinsed by acid again')
                break
            if len(bkg_array) >= 2:
                if abs((bkg_array[-1] - bkg_array[-2])) <= 0.01:
                    Converged = False
                    print('Current difference: ', (bkg_array[-1] - bkg_array[-2]))
                    print('Current decay converged. Check the Onset potential again')
                else:
                    print('Current difference: ', (bkg_array[-1] - bkg_array[-2]))
                    print('Current is still decaying. Run another AC again')
            else:
                continue

        post_onset = LSV_Regeneration(mainpath, f'Post-Regen{rinse_times}', Efin_LSV=-2.3, current_criteria=2)
        onset_array.append(post_onset)  # in RHE
        print('Onset array : ', onset_array)  # write it into CSV
        e_criteria = -1.5  # V vs RHE at 5 mA cm^2, should correspond to -1.0 at 10 mA cm^2 in KOH
        if post_onset <= e_criteria or post_onset == 0:  # both in RHE
            print(
                f'Onset potential at 1 mA is {post_onset} V vs Ag/AgCl. reaching minimum. Electrode Regeneration completed')
            break
        elif post_onset == 0:
            print('Onset potential cannot reach 1 mA at -2.5 V vs Ag/AgCl. Electrode inert enough. Electrode Regeneration completed')

        else: #post_onset >= e_criteria
            rinse_times += 1
            print(f'Onset potential {post_onset} didnt reach minimum. Rinsed by acid again')
            if rinse_times == 3:
                print(f'Error: Catalyst cannot be removed by regeneration protocol. Please check the electrode')
    # cell_rinsing('water','koh', 1)
    # eta = LSV_HER(mainpath, 'RegeneratedGCEinKOH', criteria_current = 5)
    # print(eta)
    # if eta < -1.5:
    #    print(f'Onset potential {eta} V vs. RHE lower than criteria -1.6 V vs RHE in KOH. Please check the electrode')

def run_CV_HER_lowE(mainpath, sample, Note, sr_cv=50):
    """
    Run a CV experiment and save the results.

    Parameters:
    - mainpath: The main directory path for saving results.
    - sample: Sample name as a string.
    - Note: Note to add to the directory name.
    - sr_cv: Scan rate for CV, default is 50.
    """
    main_filepath = mainpath
    create_directory(main_filepath)

    datetime_str = generate_timestamp()
    adding = f'{sample}-{datetime_str}-{Note}'
    child_filepath = os.path.join(main_filepath, adding)
    create_directory(child_filepath)

    model = 'chi760e'
    path = get_pstat_path()
    pstat.Setup(model=model, path_exe=path, folder=child_filepath)
    filename = sample

    # Stirring the plate for 30 seconds
    time.sleep(30)

    ocp_data_E = getOCP(child_filepath)
    Ru = getRu(child_filepath, ocp_data_E)
    ocp_data_E = np.mean(ocp_data_E)
    print(ocp_data_E)

    Eini, Ev1, Ev2, Efin = -1.00, -1.4, -1.00, -1.00
    stirring(plate, 60)
    fileName = f'{filename}_CV_{sr_cv / 1000:.0f}mVs'
    cvheader = f'CV ran at {sr_cv / 1000:.0f} mVs'
    sr_cv /= 1000

    cv = pstat.CV(
        Eini=Eini, Ev1=Ev1, Ev2=Ev2, Efin=Efin, nSweeps=10, dE=0.001, sr=sr_cv,
        sens=1E-3, fileName=fileName, header=cvheader, qt=60
    )

    cv.ircomp(Ru=Ru)
    time.sleep(5)
    cv.run()
    time.sleep(5)

    data = pstat.LoadCV(fileName, folder=child_filepath, model=model)
    plot_cv_data(data, child_filepath, fileName)

    print(f'Finished measuring CV at {sr_cv * 1000:.0f} mV/s')
    plate.stop_stirring()
    time.sleep(15)

    return cv

#%%
def run_CV_HER_varyE(mainpath, sample, gas, sr_cv=50):
    """
    Run a CV experiment and save the results.

    Parameters:
    - mainpath: The main directory path for saving results.
    - sample: Sample name as a string.
    - sr_cv: Scan rate for CV, default is 50.
    """
    main_filepath = mainpath
    create_directory(main_filepath)

    datetime_str = generate_timestamp()
    adding = f'{sample}-{datetime_str}-{gas}'
    child_filepath = os.path.join(main_filepath, adding)
    create_directory(child_filepath)

    model = 'chi760e'
    path = get_pstat_path()
    pstat.Setup(model=model, path_exe=path, folder=child_filepath)
    filename = sample

    # Stirring the plate for 30 seconds
    time.sleep(30)
    sr_cv = 50
    ocp_data_E = getOCP(child_filepath)
    Ru = getRu(child_filepath, ocp_data_E)
    if gas == 'H2KOH' and Ru > 100:
        Ru_temp = getRu(child_filepath, ocp_data_E)
        if Ru_temp > 6:
            send_status_message(message_stuck)
            breakpoint()
        else: Ru = Ru_temp
    ocp_data_E = np.mean(ocp_data_E)
    print(f'OCP: {ocp_data_E}')

    Eini, Ev1, Ev2, Efin = -1.00, -1.4, -1.00, -1.00
    while Ev1 >= -3.0:
        stirring(plate, 60)
        fileName = f'{filename}_CV_{sr_cv:.0f}mVs_Efin_{Ev1*1000:.0f}mV'
        cvheader = f'CV ran at {sr_cv:.0f} mVs'
        cv = pstat.CV(
            Eini=Eini, Ev1=Ev1, Ev2=Ev2, Efin=Efin, nSweeps=6, dE=0.001, sr=sr_cv/1000,
            sens=1E-3, fileName=fileName, header=cvheader, qt=60
        )
        cv.ircomp(Ru=Ru)
        time.sleep(5)
        cv.run()
        time.sleep(5)

        cvref = pstat.LoadCV(fileName, folder=child_filepath, model=model)
        cvrhe = LSV_converter_inexp(cvref.E, cvref.i[:,0])
        plot_cv_data(cvrhe, child_filepath, fileName)
        save_cvrhe_to_txt(cvrhe, child_filepath, fileName)
        current_threshold = 7.07E-4 # current density 10 mA cm-2
        nearest_index = find_nearest_index(cvref.E, Ev1,0.0005)  # Find the index of the nearest x-value
        y_at_Ev1 = cvref.i[nearest_index, 0]  # Get the y-value at the nearest x-value

        # Check if y value is below the threshold
        if y_at_Ev1[0][-1] < 7.07E-5:
            Ev1 -= 0.2
        elif y_at_Ev1[0][-1] > 5.25E-3:
            sr_cv = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900]
            for sr in sr_cv:

                fileName = f'{filename}_CV_sr_{sr:.0f}mVs_Efin_{Ev1 * 1000:.0f}mV'
                cvheader = f'CV ran at {sr:.0f} mVs'
                cv2 = pstat.CV(
                    Eini=Eini, Ev1=Ev1, Ev2=Ev2, Efin=Efin, nSweeps=2, dE=0.001, sr=sr / 1000,
                    sens=1E-2, fileName=fileName, header=cvheader, qt=2
                )
                cv2.ircomp(Ru=Ru)
                time.sleep(5)
                cv2.run()
                time.sleep(5)

                cvref = pstat.LoadCV(fileName, folder=child_filepath, model=model)
                cvrhe = LSV_converter_inexp(cvref.E, cvref.i[:, 0])
                plot_cv_data(cvrhe, child_filepath, fileName)
                save_cvrhe_to_txt(cvrhe, child_filepath, fileName)
            break
        else:
            Ev1 -= 0.1

        print(f'Finished measuring CV at {sr_cv} mV/s with Efin at {Ev1 * 1000:.0f} V')
        plate.stop_stirring()
        time.sleep(15)
    # This line didnt work, the plot should be processed later after the experiment
    files = glob.glob('*mVvsRHE*')
    sns.set_palette("flare", 8)
    for file in files:
        df = pd.read_csv(file)
        plt.plot(df['Potential V vs RHE'], df[' Current mA cm-2'])
    plt.xlabel('Potential (V vs RHE)')
    plt.ylabel('Current Density (mA cm-2)')
    plt.savefig(os.path.join(child_filepath, f"{filename}.png"))
    #plt.show()

    return cv

    #indices = find_nearest_index(cvref.E, min_potential value, 0.0005)
    #for idx in indices:
    #    plt.plot(cvref.E[idx], cvref[])
