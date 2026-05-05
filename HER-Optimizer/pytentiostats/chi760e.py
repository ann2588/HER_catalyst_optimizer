## Add Ru in LSV technique
## Add it-curve in technique

class CV:
    def __init__(self, Eini, Ev1, Ev2, Efin, sr, dE, nSweeps, sens,
                 folder, fileName, header, path_lib, qt):
        self.fileName = fileName
        self.folder = folder
        self.text = ''
        # correcting parameters:
        Ei = Eini
        if Ev1 > Ev2:
            eh = Ev1
            el = Ev2
            pn = 'p'
        else:
            eh = Ev2
            el = Ev1
            pn = 'n'
        nSweeps = nSweeps + 1  # final e from chi is enabled by default

        # building macro:
        self.head = 'c\x02\0\0\nfolder: ' + folder + '\nfileoverride\n' + \
                    'header: ' + header + '\n\n'
        self.body = 'tech=cv\nei=' + str(Ei) + '\neh=' + str(eh) + '\nel=' + \
                    str(el) + '\npn=' + pn + '\ncl=' + str(nSweeps) + \
                    '\nefon\nef=' + str(Efin) + '\nsi=' + str(dE) + \
                    '\nqt=' + str(qt) + '\nv=' + str(sr) + '\nsens=' + str(sens) + '\nflt1=3\nflt2=3\nflt3=3\nflt4=0\nflt5=0'
        self.body2 = self.body + \
                     '\nrun\nsave:' + self.fileName + '\ntsave:' + self.fileName
        self.foot = '\n forcequit: yesiamsure'
        self.text = self.head + self.body2 + self.foot

    def bipot(self, E2, sens2):
        self.body2 = self.body + \
                     '\ne2=' + str(E2) + '\nsens2=' + str(sens2) + '\ni2on' + \
                     '\nrun\nsave:' + self.fileName + '\ntsave:' + self.fileName
        self.foot = '\n forcequit: yesiamsure'
        self.text = self.head + self.body2 + self.foot

    def ircomp(self, Ru):
        self.body2 = self.body + '\nmir=' + str(Ru) + '\nircompon\n' + \
                     '\nrun\nsave:' + self.fileName + '\ntsave:' + self.fileName
        self.foot = '\n forcequit: yesiamsure'
        self.text = self.head + self.body2 + self.foot


class LSV:
    '''
    '''
    # Todo
    def __init__(self, Eini, Efin, sr, dE, sens, folder, fileName, header,
                 path_exe, qt=2):
        self.fileName = fileName
        self.folder = folder
        self.text = ''
        self.head = 'C\x02\0\0\nfolder: ' + folder + '\nfileoverride\n' + \
                    'header: ' + header + '\n\n'
        self.body = 'tech=lsv\nei=' + str(Eini) + '\nef=' + str(Efin) + \
                    '\nv=' + str(sr) + '\nsi=' + str(dE) + \
                    '\nqt=' + str(qt) + '\nsens=' + str(sens)
        self.body2 = self.body + \
                     '\nrun\nsave:' + self.fileName + '\ntsave:' + self.fileName
        self.foot = '\n forcequit: yesiamsure'
        self.text = self.head + self.body2 + self.foot

    def bipot(self, E2, sens2):
        self.body2 = self.body + \
                     '\ne2=' + str(E2) + '\nsens2=' + str(sens2) + '\ni2on' + \
                     '\nrun\nsave:' + self.fileName + '\ntsave:' + self.fileName
        self.foot = '\n forcequit: yesiamsure'
        self.text = self.head + self.body2 + self.foot

    ## To test if it is applicable
    def ircomp(self, Ru):
        self.body2 = self.body + '\nmir=' + str(Ru) + '\nircompon\n' + \
                     '\nrun\nsave:' + self.fileName + '\ntsave:' + self.fileName
        self.foot = '\n forcequit: yesiamsure'
        self.text = self.head + self.body2 + self.foot


class CA:
    '''
    '''

    def __init__(self, Estep, Ehigh, Elow, dt, ttot, tstep, sens, folder, fileName, header,
                 path_exe, direction='n', qt=2):
        self.fileName = fileName
        self.folder = folder
        self.text = ''
        self.head = 'C\x02\0\0\nfolder: ' + folder + '\nfileoverride\n' + \
                    'header: ' + header + '\n\n'
        self.body = 'tech=ca\nei=' + str(Estep) +'\neh=' + str(Ehigh) +'\nel=' + str(Elow) +'\npn='+ direction + '\ncl=' + str(tstep) +'\npw=' + str(ttot) + \
                    '\nsi=' + str(dt) + '\nqt=' + str(qt) + \
                    '\nsens=' + str(sens)
        self.body2 = self.body + \
                     '\nrun\nsave:' + self.fileName + '\ntsave:' + self.fileName
        self.foot = '\n forcequit: yesiamsure'
        self.text = self.head + self.body2 + self.foot

    def bipot(self, E2, sens2):
        self.body2 = self.body + \
                     '\ne2=' + str(E2) + '\nsens2=' + str(sens2) + '\ni2on' + \
                     '\nrun\nsave:' + self.fileName + '\ntsave:' + self.fileName
        self.foot = '\n forcequit: yesiamsure'
        self.text = self.head + self.body2 + self.foot

class i:
    '''
    Eini = initial E (V)
    dt = scale interval (sec)
    ttot = Run time (sec)
    dt = Quiet time (sec)
    ## todo Scales during Run @@
    sens = sensitivity (A/V)
    '''


    def __init__(self, Eini, dt, ttot, sens, folder, fileName, header, path_exe, qt=2):
        self.fileName = fileName
        self.folder = folder
        self.text = ''
        self.head = 'C\x02\0\0\nfolder: ' + folder + '\nfileoverride\n' + \
                    'header: ' + header + '\n\n'
        self.body = 'tech=i-t\nei=' + str(Eini) + '\nsi=' + str(dt) + \
                    '\nst=' + str(ttot) + '\nqt=' + str(qt) + \
                    '\nsc=' + str(1) + '\nsens=' + str(sens)
        self.body2 = self.body + \
                     '\nrun\nsave:' + self.fileName + '\ntsave:' + self.fileName
        self.foot = '\n forcequit: yesiamsure'
        self.text = self.head + self.body2 + self.foot

    def bipot(self, E2, sens2):
        self.body2 = self.body + \
                     '\ne2=' + str(E2) + '\nsens2=' + str(sens2) + '\ni2on' + \
                     '\nrun\nsave:' + self.fileName + '\ntsave:' + self.fileName
        self.foot = '\n forcequit: yesiamsure'
        self.text = self.head + self.body2 + self.foot

    ## To test if it is applicable
    def ircomp(self, Ru):
        self.body2 = self.body + '\nmir=' + str(Ru) + '\nircompon\n' + \
                     '\nrun\nsave:' + self.fileName + '\ntsave:' + self.fileName
        self.foot = '\n forcequit: yesiamsure'
        self.text = self.head + self.body2 + self.foot

class CP:
    '''
    Todo : add param
    '''


    def __init__(self, Ccat, Cano, Ehigh, Ehigh_t, Elow, Elow_t, tcat, tano,  pn,
                 intvl, nsweep, folder, fileName, header, path):
        self.fileName = fileName
        self.folder = folder
        self.text = ''
        self.head = 'C\x02\0\0\nfolder: ' + folder + '\nfileoverride\n' + \
                    'header: ' + header + '\n\n'


        self.body = 'tech=cp\nccat=' + str(Ccat) + '\ncano=' + str(Cano) + \
                     '\nehigh=' + str(Ehigh)+ '\nehight=' + str(Ehigh_t) + \
                     '\nelow=' + str(Elow)+ '\nelowt=' + str(Elow_t) + \
                     '\ntcat=' + str(tcat) + '\ntano=' + str(tano) + \
                     '\npn=' + pn +\
                     '\nintvl=' + str(intvl) + '\nnsweep=' + str(nsweep)
        self.body2 = self.body + \
                     '\nrun\nsave:' + self.fileName + '\ntsave:' + self.fileName
        self.foot = '\n forcequit: yesiamsure'
        self.text = self.head + self.body2 + self.foot


class OCP:
    '''
        Assumes OCP is between +- 10 V
    '''

    def __init__(self, ttot, dt, folder, fileName, header, path_exe):
        self.fileName = fileName
        self.folder = folder
        self.text = ''
        self.head = 'C\x02\0\0\nfolder: ' + folder + '\nfileoverride\n' + \
                    'header: ' + header + '\n\n'
        self.body = 'tech=ocpt\nst=' + str(ttot) + '\neh=10' + \
                    '\nel=-10' + '\nsi=' + str(dt) + \
                    '\nrun\nsave:' + self.fileName + '\ntsave:' + self.fileName
        self.foot = '\nforcequit: yesiamsure'
        self.text = self.head + self.body + self.foot


class EIS:
    '''
    ei = initial potential in V, -10~+10
    fl = low frequency in Hz,  0.0001~10000
    fh = high frequency in Hz, 0.001 ~ 100000
    amp = ac amplitude in V(half peak to peak, 0.001 ~0.4
    qt =quiescent time before run in s , 0-100000
    sens = sensitivity in A/V
    impautosens = automatic sensitivity selection ???
    '''

    def __init__(self, Eini, fl, fh, amp, sens, folder, fileName, header,
                 path_lib, qt=2):
        self.fileName = fileName
        self.folder = folder
        self.text = ''
        self.head = 'C\x02\0\0\nfolder: ' + folder + '\nfileoverride\n' + \
                    'header: ' + header + '\n\n'
        self.body = 'tech=imp\nei=' + str(Eini) + '\nfl=' + str(fl) + '\nfh=' + \
                    str(fh) + '\namp=' + str(amp) + '\nqt=' + str(qt) + \
                    '\nsens=' + str(sens)
        self.body2 = self.body + \
                     '\nrun\nsave:' + self.fileName + '\ntsave:' + self.fileName

        self.foot = '\nforcequit: yesiamsure'
        self.text = self.head + self.body2 + self.foot


class Read:
    '''
    '''

    def __init__(self, fileName, folder):
        self.fileName = fileName
        self.folder = folder
