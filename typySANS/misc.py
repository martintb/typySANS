import numpy as np
import pandas as pd

def buildShiftTable(df_xy,df_trim,shiftConfig):
    n_configs = df_xy.shape[0]
    
    if shiftConfig is None:
        shiftTable = np.ones(n_configs)
    else:
        shiftIndex  = df_xy.index.get_loc(shiftConfig) # get index of curve to shift to
        
        shiftTable = []
        for currIndex in range(n_configs):
            # determine which direction the shiftIndex is in (higher or lower q)
            shiftDir = np.sign(currIndex-shiftIndex) 
            shift = 1.0 #default shift is no-shift
            if not (shiftDir==0):
                # need to walk from "shiftIndex" curve back to currIndex
                # and 'build' shifting coefficient
                for j in range(shiftIndex,currIndex,shiftDir):
                    j1 = j
                    j2 = j+shiftDir
                    sl1 = slice(df_trim.iloc[j1]['Lo'],-1-df_trim.iloc[j1]['Hi'],None)
                    sl2 = slice(df_trim.iloc[j2]['Lo'],-1-df_trim.iloc[j2]['Hi'],None)
                    q1 = df_xy.iloc[j1]['q'].values[sl1]
                    I1 = df_xy.iloc[j1]['I'].values[sl1]
                    q2 = df_xy.iloc[j2]['q'].values[sl2]
                    I2 = df_xy.iloc[j2]['I'].values[sl2]
                    shiftFac = calcShift(q1,I1,q2,I2)[0]
                    shift *= shiftFac
                    # print('Calculating For:',currIndex,'Between',j1,j2,'CurrShift',shiftFac,'CumShift',shift)
            shiftTable.append(shift)

    df_shift = pd.Series(shiftTable,index=df_xy.index,name='shiftFactors')
    return df_shift

def calcShift(q1,I1,q2,I2):
    '''Calculate the shift coefficient needed to align two intensity curves 
    
    The reduced, measured intensity from two different instrument configurations 
    will often have vertical intensity shifts due to a number of measurement and 
    instrumental reasons. This method allows one to calculate the scale factor needed
    to bring the two curves into alignment.
    
    Arguments
    ---------
        q1,q2: np.ndarray
            An array of q-values (wavenumbers) of each measured intensity input
        
        I1,I2: np.ndarray
            An array of intensity values
    
    Returns
    -------
    scale factor mean: float
        Average shift coefficient 
    
    scale factor std: float
        Standard deviation of shift coefficient
    '''
    minQ = max(q1.min(),q2.min())
    maxQ = min(q1.max(),q2.max())
    mask = np.logical_and(q2>=minQ,q2<=maxQ)
    if not mask.sum()>0:
        raise ValueError('Need overlapping q in order to calculate shift factor! Did you trim too much?')
    
    I1p = np.interp(q2,q1,I1)
    scale = I1p[mask]/I2[mask]
    
    return scale.mean(),scale.std()