import pytentiostats as pstat
import os

folder = os.environ.get('HER_PSTAT_TEST_DATA', '.')
path_pstat = os.environ.get('CHI760E_PATH', 'C:/chi')
pstat_model = 'chi760e'
#pstat.Setup(model=model, path_exe=path, folder=child_filepath)
pstat.Setup(folder_save=folder, pstat_model=pstat_model, path_pstat=path_pstat, verbose=1)

#tech = ITCURVE()
#tech.run

tech = CV()
tech.bipot(E=1)
tech.run()

tech = OCP()
tech.run()


