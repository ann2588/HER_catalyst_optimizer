from alicat import FlowController
import MXII_valve as mxii
#from Hardwaretesting.MFC import control_MFC
#from Hardwaretesting.pump import *  # it is making copies from this file, remember to check and change the port number
#from Hardwaretesting.stir import stirring
from Hardwaretesting.Valves import changing_port
#from tqdm import tqdm
#from ika.magnetic_stirrer import MagneticStirrer
from portaccess import port_plate, port_pumpA, port_pumpB, port_switchvalve
from echemchemplatform import channel_flow,pumping_waste_out, iccB
import time

#%% #to be customized for plating solution preparation.
# define hardwares using USB COM address
flow_controller = FlowController(port='COM5')

plate = MagneticStirrer(device_port=port_plate)
valve_switch = mxii.MX_valve(port_switchvalve, ports=2, name='Switching', verbose=True)
#valve_select = mxii.MX_valve('COM4', ports=6, name='Selection', verbose=True)

# pump is already defined in pump.py
print('Filling the pump tubing ...')
#initialize_pump()

switching_position = {'loading':1, 'injection':2}

#%%

def pH_titration(number_of_drops, stock_solution_type=None): # to be optimized to use acid/base as little as possible

    changing_port(valve_switch,switching_position['loading'])

    #%% Gas flow
    #flow_controller.set_pressure(160) gas flow #bubbling check
    iccB.set_mode_pump_rpm(4,100)
    iccB.start(4)

    #%% fill titration
    iccB.set_mode_pump_rpm(3, 100)
    iccB.start(3)
    time.sleep(20)
    iccB.stop(3)
    pHs = []
    # 5s per titration
    for i in range(number_of_drops):
        iccB.set_mode_pump_rpm(3, 20)
        iccB.start(3)
        time.sleep(5)
        changing_port(valve_switch, switching_position['injection'])
        print(f'Injecting {stock_solution_type}')
        iccB.start(3)
        time.sleep(10)
        changing_port(valve_switch,switching_position['loading'])
        time.sleep(3)
        iccB.stop(3)
        #stirring(plate, 200,10)

def injection():
    #initial filling
    iccB.set_mode_pump_rpm(3, 20)
    iccB.start(3)
    time.sleep(5)

    changing_port(valve_switch, switching_position['injection'])
    print(f'Injecting')


    iccB.start(3)
    time.sleep(10)
    changing_port(valve_switch, switching_position['loading'])
    time.sleep(3)
    iccB.stop(3)


