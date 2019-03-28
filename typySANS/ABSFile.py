'''
WIP

All reading/writing of ABS files should be outsourced to this routine
'''
import numpy as np
import pandas as pd
import datetime
import pathlib

def readABS(fpath,trimLo=0,trimHi=0):
    '''Read ASCII .ABS files and, if possible, extract instrument configuration 
    
    This method attempts to flexibly handle the two types of ABS files generated from the NCNR 
    Igor macros: single-configuration reduced data and multi-configuration combined files. ABS 
    files have a variable number of header lines and then 6 columns of data: q, I, dI, dq, 
    meanQ, ShadowFactor.
    
    Arguments
    ---------
    fpath: str or pathlib.Path
        Full path with filename to an ABS file
    
    trimLo,trimHi: int
        Number of points to remove from the low-q and hi-q ends of the dataset, respectively
    
    Returns:
    --------
    df: pandas.Dataframe
        A dataframe with columns: q, I, dI, dq, meanQ, ShadowFactor
    
    config: dict
        For single-configuration ABS files: A dictionary of instrument parameters read from the header
        For multi-configuration ABS files: empty dictionary
    
    '''
    config_dict={}
    with open(fpath,'r') as f:
        skiprows = 1
        while True:
            line = f.readline()
            skiprows+=1
            
            if 'LABEL:' in line:
                label = line.split(':')[-1]
            elif 'MON CNT' in line:
                keys1 = ['MONCNT','LAMBDA','DET ANG','DET DIST','TRANS','THICK','AVE','STEP']
                values1 = f.readline().split()
                keys2 = ['BCENT(X,Y)','A1(mm)','A2(mm)','A1A2DIST(m)','DL/L','BSTOP(mm)','DET_TYP']
                _ = f.readline()
                values2 = f.readline().split()
                config_dict = {k:v for k,v in zip(keys1+keys2,values1+values2)}
                skiprows += 2
            elif 'The 6 columns are' in line:
                break
            
    data_table = np.loadtxt(fpath,skiprows=skiprows)
    data_table = data_table[trimLo:-1-trimHi]
    df = pd.DataFrame(data_table,columns=['q','I','dI','dq','qbar','shadfac'],)
    return df,config_dict

def writeABS(fname,dfABS,dfShift,shiftConfig,df_trim,path='./',shift=True,sort_by_q=True):
    header  = 'COMBINED FILE CREATED: {}\n'
    header += 'pyNSORT-ed {} ' + '+ {} '*(dfABS.shape[0]-1) + '\n'
    header += 'normalized to   {}\n'
    header += 'multiplicative factors: ' + '{} '*dfABS.shape[0] + '\n'
    header += 'The 6 columns are | Q (1/A) | I(Q) (1/cm) | std. dev. I(Q) (1/cm) | sigmaQ | meanQ | ShadowFactor|\n'
    
    path = pathlib.Path(path) / fname
    with open(path,'w') as f:
        now = datetime.datetime.strftime(datetime.datetime.now(),'%T %D')
        if shiftConfig is None:
            shiftFile = 'None'
        else:
            shiftFile = dfABS.loc[shiftConfig]
        f.write(header.format(now,*dfABS.values,shiftFile,*dfShift.values))
        
    allABSData = []
    for config,fname in dfABS.iteritems():
        if pd.isna(fname):
            continue
        trimLo = df_trim.loc[config]['Lo']
        trimHi = df_trim.loc[config]['Hi']
        ABSData,_ = readABS(fname,trimLo,trimHi)
        ABSData = ABSData.values
        if shift:
            ABSData[:,1]*=dfShift.loc[config] #shift I
            ABSData[:,2]*=dfShift.loc[config] #shift sigmaI
        allABSData.append(ABSData)
            
    allABSData = np.vstack(allABSData)
    if sort_by_q:
        sort_mask = np.argsort(allABSData[:,0])
        allABSData = allABSData[sort_mask] 
    with open(path,'ba') as f:
        np.savetxt(f,allABSData)


   

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
