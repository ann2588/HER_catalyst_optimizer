#import ElectroLab as elab
import pytentiostats as pstat
import os

# Set parameters:
#fileName = 'itcurvetesting' #your file name
folder = os.environ.get('HER_PSTAT_TEST_DATA', '.')
path = os.environ.get('CHI760E_PATH', 'C:/chi')
model = 'chi760e'

pstat.Setup(model=model, path_exe=path, folder=folder)

# Potentiostat setup:
#pstat.Setup(fileName, folder, model)

#%% Test itcurve macro
# Run it curve experiment
#itcurve = pstat.ITCURVE()
itcurve = pstat.i(Eini=-1.3, dt = 0.01, ttot = 10, sens=1e-6, fileName='ITCURVE', header='ITCURVE') #Todo

itcurve.run()

#%%
itcurve_data = pstat.LoadITCURVE('ITCURVE',folder=folder, model=model)


#%% Original code
# Run experiment:
cv = pstat.CV(Eini=-0.5, Ev1=0.5, Ev2=-0.5, Efin=-0.5, sr=0.1, fileName=fileName)
cv.bipot(E=0.5) # Bipotentiostat option available
cv.run()

# Load CV data file:
data = pstat.LoadCV(fileName, folder, model)

# Plot CV:
elab.plot(data.E, data.i, xlab='$E$ / V', ylab='$i$ / A')
elab.savefig(fileName)
