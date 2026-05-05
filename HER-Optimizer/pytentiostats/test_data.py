import softpotato as sp
import file

fileName = 'OCP'
folder = 'data'
delimiter = ','

model = 'chi760e'

dat = file.XY(fileName=fileName, folder=folder, skiprows=13, model=model)
sp.plot(dat.x, dat.y, xlab='E', ylab='i', fig=2, show=1)
