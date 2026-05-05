from ismatec.peristaltic_pump import RegloICCFourChannel, ChannelStatus
import ismatec.errors
import time
import numpy as np
#port_pump = 'COM8'
global icc2
global icc1
#icc2 = RegloICCFourChannel('COM5')
iccb.set_counter_clockwise(1)
iccb.set_mode_pump_rpm(1, 100)
#icc1 = RegloICCFourChannel('COM13')

def initialize_pump():
    for i in range(4):
        icc2.set_counter_clockwise(i + 1)
        icc2.start(i+1)
    icc2.set_counter_clockwise(4)
    icc2.set_clockwise(1)
    icc2.set_clockwise(3)  # 2 is discarded because of interference with 3.
    time.sleep(20)
    for i in range(4):
        icc2.stop(i+1)

if __name__ == "__main__":
    icc2.start(1)
    time.sleep(5)
    icc2.stop(1)

