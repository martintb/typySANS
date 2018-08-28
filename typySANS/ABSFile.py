import numpy as np
import pandas as pd
import pathlib

   

def writeABS(fname,df,shifts,trim,path='./',shift=True):
    header  = 'COMBINED FILE CREATED: {}\n'
    header += 'pyNSORT-ed   {}	  +  {}	  +  {}	 + none\n'
    header += 'normalized to   {}\n'
    header += 'multiplicative factor 1-2 =   {}	 multiplicative factor 2-3 =    {}	 multiplicative factor 3-4 =            0\n'
    header += 'The 6 columns are | Q (1/A) | I(Q) (1/cm) | std. dev. I(Q) (1/cm) | sigmaQ | meanQ | ShadowFactor|\n'
    
    path = pathlib.Path(path) / fname
    with open(path,'w') as f:
        if shift:
            shift_1 = shifts['shift_1'][0]
            shift_2 = shifts['shift_2'][0]
        else:
            shift_1 = shift_2 = 1.0
        f.write(header.format('today',df.LowQ,df.MidQ,df.HighQ,df.MidQ,shift_1,shift_2))
        
    with open(path,'ba') as f:
        for qlabel in ['LowQ','MidQ','HighQ']:
            _,_,_,_,data,dataTrim = getTrimmedABSData(df[qlabel],trim[qlabel])
            if shift:
                dataTrim[:,1]*=shifts[qlabel] #shift I
                dataTrim[:,2]*=shifts[qlabel] #shift sigmaI
            np.savetxt(f,dataTrim)
            
    print('Wrote ABS file:',path)

class ABSFile(object):
    '''
    ToDo:
        Convert ABSwriter above to be better
        Add in operators to combine ABS files
        Make interactive slicing easier 
    '''
    def __init__(self,fname,low_cut=None,high_cut=None):
        self.low_cut = low_cut
        self.high_cut = high_cut
        self.mask = slice(low_cut,-high_cut)


        self._q             = np.array([]) #empty array so slicing works in getter
        self._I             = np.array([])
        self._sigI          = np.array([])
        self._sigQ          = np.array([])
        self._meanQ         = np.array([])
        self._ShadowFactor  = np.array([])

        self.fname = fname
        self.readABSData(fname)

    @property 
    def q(self):
        return self._q[self.mask]
    @q.setter 
    def q(self,val):
        self._q = val

    @property 
    def I(self):
        return self._I[self.mask]
    @I.setter 
    def I(self,val):
        self._I = val

    @property 
    def sigI(self):
        return self._sigI[self.mask]
    @sigI.setter 
    def sigI(self,val):
        self._sigI = val

    @property 
    def sigQ(self):
        return self._sigQ[self.mask]
    @sigQ.setter 
    def sigQ(self,val):
        self._sigQ = val

    @property 
    def meanQ(self):
        return self._meanQ[self.mask]
    @meanQ.setter 
    def meanQ(self,val):
        self._meanQ = val

    @property 
    def ShadowFactor(self):
        return self._ShadowFactor[self.mask]
    @ShadowFactor.setter 
    def ShadowFactor(self,val):
        self._ShadowFactor = val

    def readABSData(self,fname):
        '''
        | Q (1/A) | I(Q) (1/cm) | std. dev. I(Q) (1/cm) | sigmaQ | meanQ | ShadowFactor|

        '''
        q, I, sigI, sigQ, meanQ, shadowFactor = np.loadtxt(fname,skiprows=14).T

        self._q = q
        self._I = I
        self._sigI = sigI
        self._sigQ = sigQ
        self._meanQ = meanQ
        self.ShadowFactor = ShadowFactor

    def __divide__(self,other):
        '''
        Calculate the shift factor between two curves
        '''
        #find overlapping  Q
        minQ = max(self.q.min(),other.q.min())
        maxQ = min(self.q.max(),other.q.max())
        mask = np.logical_and(other.q>minQ,other.q<maxQ)
        
        # interpolate this objects I values onto the other objects
        # q-scale
        I_interp= np.interp(other.q,self.q,self.I)

        scale = I_interp/other.I
        
        return scale.mean(),scale.std()
