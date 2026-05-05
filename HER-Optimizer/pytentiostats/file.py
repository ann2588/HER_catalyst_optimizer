import numpy as np
import pytentiostats.chi760e as chi

#Add LoadITCURVE


class Test:
    '''
    '''
    def __init__(self):
        print('Test from file library')

class Read:
    '''
    '''
    def __init__(self):
        self.file_path = self.folder + '/' + self.fileName + '.txt'  # where to find the format?

    def read(self, text=0, model=0):
        if model == 'chi760e':
            self.delimiter = ','
            self.skiprows = self.search(text)
            if self.skiprows:
                self.data = np.loadtxt(self.file_path, delimiter=self.delimiter,
                            skiprows=self.skiprows)
                self.x = self.data[:,0]
                self.y = self.data[:,1:]
            else:
                print('Could not find string \"' + text + '\" to skip rows.' +\
                      ' Data not loaded.')
                self.x = np.array([])
                self.y = np.array([])
        else:
            self.data = np.loadtxt(self.file_path, delimiter=self.delimiter, 
                        skiprows=self.skiprows)
            self.x = self.data[:,0]
            self.y = self.data[:,1:]

    def search(self, text):
        file = open(self.file_path, 'r')
        count = 0
        flag = 0
        for line in file:
            count += 1
            if text in line:
                return count
        return 0



class LoadXY(Read):
    '''
    '''
    def __init__(self, fileName='file', folder='.', skiprows=0, delimiter=',',
                 model=0): 
        self.fileName = fileName
        self.folder = folder
        Read.__init__(self)
        self.skiprows = skiprows
        self.delimiter = delimiter
        self.read()


class LoadCV(Read):
    '''
    '''
    def __init__(self, fileName='file', folder='.', model=0):
        self.fileName = fileName
        self.folder = folder
        text = 'Potential/V,'
        Read.__init__(self)
        self.read(text, model)
        self.E = self.x
        self.i = self.y


class LoadLSV(Read):
    '''
    '''
    def __init__(self, fileName='file', folder='.', model=0):
        #same as cv
        cv = LoadCV(fileName, folder, model)
        self.E = cv.E
        self.i = cv.i


class LoadCA(Read):
    '''
    '''
    def __init__(self, fileName='file', folder='.', model=0):
        self.fileName = fileName
        self.folder = folder
        text = 'Time/sec,'
        Read.__init__(self)
        self.read(text, model)
        self.t = self.x
        self.i = self.y

class LoadITCURVE(Read):
    '''
    Same as CA
    '''
    def __init__(self, fileName='file', folder='.', model=0):
        self.fileName = fileName
        self.folder = folder
        text = 'Time/sec,'
        Read.__init__(self)
        self.read(text, model)
        self.t = self.x
        self.i = self.y

class LoadVTCURVE(Read):
    '''
    Same as CP
    '''
    def __init__(self, fileName='file', folder='.', model=0):
        self.fileName = fileName
        self.folder = folder
        text = 'Time/sec,'
        Read.__init__(self)
        self.read(text, model)
        self.t = self.x
        self.v = self.y


class LoadOCP(Read):
    '''
    '''
    def __init__(self, fileName='file', folder='.', model=0):
        ca = LoadCA(fileName, folder, model) # Same as CA
        self.t = ca.t
        self.E = ca.i

class LoadEIS(Read):
    '''
    '''
    def __init__(self, fileName='file', folder='.', model=0):
        self.fileName = fileName
        self.folder = folder
        text = 'Freq/Hz,'
        Read.__init__(self)
        self.read(text, model)
        self.F = self.x
        self.rZ = self.y[:,0]
        self.iZ = self.y[:,1]
