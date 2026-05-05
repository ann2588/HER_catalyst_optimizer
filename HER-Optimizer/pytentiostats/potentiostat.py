import os
import pytentiostats.chi760e as chi
import subprocess
import threading
from threading import Thread
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
#Update command error data: 03/11/2024
# Potentiostat models available: chi760e
# Global variables

folder_save = '.'
model_pstat = 'no pstat'
path = '.'


class ThreadWithReturnValue(Thread):

    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs={}, Verbose=None):
        Thread.__init__(self, group, target, name, args, kwargs)
        self._return = None

    def run(self):
        if self._target is not None:
            self._return = self._target(*self._args,
                                        **self._kwargs)

    def join(self, *args):
        Thread.join(self, *args)
        return self._return

# Function to run the external command and measure time
def run_command_with_timer(command, filename):
    start_time = time.time()
    def measure_time(repeat_time):
        while process.poll() is None:  # While the process is running
            elapsed_time = time.time() - start_time
            print(f"Elapsed Time: {elapsed_time:.2f} seconds", end='\r')
            time.sleep(1)  # Update every 1 second
            if os.path.isfile(folder_save + '/' + filename + '.txt'):
                time.sleep(1)
                # if the measurement keeps longer than 1000s, it may be stucked
                if os.system('tasklist | find "chi760e.exe"') == 0:
                    os.system('taskkill /F /IM chi760e.exe')
                print('Quit chi760e.exe')

            if elapsed_time > 500*(repeat_time):
                if os.system('tasklist | find "chi760e.exe"') == 0:
                    os.system('taskkill /F /IM chi760e.exe')
                slack_bot = os.environ.get(
                    'HER_SLACK_BOT_PATH',
                    str(Path(__file__).resolve().parents[1] / 'Utilities' / 'slack-bot.py')
                )
                if os.path.isfile(slack_bot):
                    os.system(f'python "{slack_bot}" -m "CHI error, duration>500s"')
                print('Rerun chi760e.exe')

                time.sleep(1)

    repeat_time=0
    while os.path.isfile(folder_save + '/' + filename + '.txt') == 0:
    # Start the external command using subprocess
        process = subprocess.Popen(command, shell=True)
        repeat_time +=1
        # Create a thread to measure the elapsed time

        timer_thread = threading.Thread(target=measure_time(repeat_time))
        timer_thread.daemon = True  # Allow the thread to be killed when the main program exits
        timer_thread.start()
        rerun = timer_thread.join()

        # Wait for the external command to complete
        process.wait()

        # Ensure the timer thread has finished
        timer_thread.join()

        # Print the final elapsed time
        elapsed_time = time.time() - start_time
        print(f"\nTotal Elapsed Time: {elapsed_time:.2f} seconds")
    return rerun



class Setup:
    def __init__(self, model=0, path_exe='.', folder='.', verbose=1):
        global folder_save
        folder_save = folder
        global model_pstat
        model_pstat = model
        global path
        path = path_exe
        if verbose:
            self.info()

    def info(self):
        print('\n----------')
        print('Potentiostat model: ' + model_pstat)
        print('Potentiostat path: ' + path)
        print('Save folder: ' + folder_save)
        print('----------\n')

class Technique:
    '''
    '''

    def __init__(self, text='', fileName='CV'):
        self.text = text
        self.fileName = fileName
        self.technique = 'Technique'
        self.bpot = False
        self.ir = False

    def writeToFile(self):
        if model_pstat == 'chi760e':
            file = open(folder_save + '/' + self.fileName + '.mcr', 'wb')
            file.write(self.text.encode('ascii'))
            file.close()

    def run(self):
        if model_pstat == 'chi760e':
            self.message()
            # Write macro:
            self.writeToFile()
            # Run command:
            #time.sleep(10)
            command = path + '/chi760e.exe'
            # Test if i can run command with the macro pre defined
            param = ' /runmacro:\"' + folder_save + '/' + self.fileName + '.mcr\"'
            while os.path.isfile(folder_save + '/' + self.fileName + '.mcr')==False:
                time.sleep(5)
            #rerun_or_not = 1
            #while rerun_or_not ==1:
            print(param)
            rerun_or_not = run_command_with_timer(command + param, self.fileName)
            print(rerun_or_not)
            self.message(start=False)
        else:
            print('\nNo potentiostat selected. Aborting.')

    def message(self, start=True):
        if start:
            print('----------\nStarting ' + self.technique)
            if self.bpot:
                print('Running in bipotentiostat mode')
            if self.ir:
                print('IR compensation is activated')
        else:
            print(self.technique + ' finished\n----------\n')

    def bipot(self, E=-0.5, sens=1e-6):
        if self.technique != 'OCP':
            if model_pstat == 'chi760e':
                self.tech.bipot(E, sens)
                self.text = self.tech.text
                self.bpot = True
        else:
            print('OCP does not have bipotentiostat mode')


    def ircomp(self, Ru=3):
        if self.technique == 'CV':
            if model_pstat == 'chi760e':
                self.ir = True
                self.tech.ircomp(Ru)
                self.text = self.tech.text
        if self.technique == 'LSV':
            if model_pstat == 'chi760e':
                self.ir = True
                self.tech.ircomp(Ru)
                self.text = self.tech.text
        if self.technique == 'i':
            if model_pstat == 'chi760e':
                self.ir = True
                self.tech.ircomp(Ru)
                self.text = self.tech.text
        if self.technique == 'CP':
            if model_pstat == 'chi760e':
                self.ir = True
                self.tech.ircomp(Ru)
                self.text = self.tech.text

        else:print('Only compatible with CV')


class CV(Technique):
    '''
    '''
    def __init__(self, Eini=-0.2, Ev1=0.2, Ev2=-0.2, Efin=-0.2, sr=0.1,
                 dE=0.001, nSweeps=2, sens=1e-6,
                 fileName='CV', header='CV', qt = 2):
        if model_pstat == 'chi760e':
            self.tech = chi.CV(Eini, Ev1, Ev2, Efin, sr, dE, nSweeps, sens,
                          folder_save, fileName, header, path, qt)
            Technique.__init__(self, text=self.tech.text, fileName=fileName)
            self.technique = 'CV'
            print('CV')

   
class LSV(Technique):
    '''
    '''
    def __init__(self, Eini=-0.2, Efin=0.2, sr=0.1, dE=0.001, sens=1e-6,
                 fileName='LSV', header='LSV'):
        if model_pstat == 'chi760e':
            self.tech = chi.LSV(Eini, Efin, sr, dE, sens, folder_save, fileName,
                                header, path, qt=2)
            Technique.__init__(self, text=self.tech.text, fileName=fileName)
            self.technique = 'LSV'

class i(Technique):
    '''
    '''

    def __init__(self, Eini=-0.2, dt = 0.01, ttot = 10, sens=1e-6, fileName = 'ITCURVE', header='ITCURVE'):
        if model_pstat == 'chi760e':
            self.tech = chi.i(Eini, dt, ttot, sens, folder_save, fileName, header, path, qt=2)
            Technique.__init__(self, text=self.tech.text, fileName=fileName)
            self.technique = 'i'

class CA(Technique):
    '''
    '''
    def __init__(self, Estep=0.01, Ehigh=-2, Elow=-2, dt=0.001, ttot=10, sens=1e-6, tstep=4,
                 fileName='CA', header='CA'):
        if model_pstat == 'chi760e':
            self.tech = chi.CA(Estep, Ehigh, Elow, dt, ttot, tstep, sens, folder_save, fileName,
                               header, path, qt=2)
            Technique.__init__(self, text=self.tech.text, fileName=fileName)
            self.technique = 'CA'

class CP(Technique):
    '''
    This method apply a fixed current
    '''
    def __init__(self, Ccat = 7.06e-5, Cano = 0, Ehigh = 1.0, Ehigh_t = 0, Elow = -2.5, Elow_t = 0,
                 tcat = 30, tano = 0.005, pn = 'c', intvl = 0.1, nsweep = 1, fileName='CP', header='CP'):
        if model_pstat == 'chi760e':
            self.tech = chi.CP(Ccat, Cano, Ehigh, Ehigh_t, Elow, Elow_t,
                               tcat, tano, pn, intvl, nsweep, folder_save, fileName, header, path)
            Technique.__init__(self, text=self.tech.text, fileName=fileName)
            self.technique = 'CP'

class OCP(Technique):
    '''
    '''
    def __init__(self, ttot=2, dt=0.01, fileName='OCP', header='OCP'):
        if model_pstat == 'chi760e':
            self.tech = chi.OCP(ttot, dt, folder_save, fileName, header, path)
            Technique.__init__(self, text=self.tech.text, fileName=fileName)
            self.technique = 'OCP'


class EIS(Technique):
    '''
    '''
    def __init__(self, Eini=0.2, fl=1, fh=1e6, amp= 0.01, sens=1e-6,
                 fileName='EIS', header='EIS'):
        if model_pstat == 'chi760e':
            self.tech = chi.EIS(Eini, fl, fh, amp, sens, folder_save, fileName, header,
                 path, qt=2)
            Technique.__init__(self, text=self.tech.text, fileName=fileName)
            self.technique = 'EIS'



if __name__ == '__main__':
    sens = 1e-8
    sr = [0.1, 0.2, 0.5]
    folder = os.environ.get('HER_PSTAT_TEST_DATA', '.')
