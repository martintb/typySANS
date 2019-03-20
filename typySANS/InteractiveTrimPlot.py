import numpy as np 
import pandas as pd
import matplotlib.pyplot as plt

from ipywidgets import Dropdown,IntSlider,HBox,VBox,Output,Label,Checkbox

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

def writeABS(fname,dfABS,dfShift,shiftConfig,trimLo,trimHi,path='./',shift=True):
    header  = 'COMBINED FILE CREATED: {}\n'
    header += 'pyNSORT-ed   {}	  +  {}	  +  {}	 + none\n'
    header += 'normalized to   {}\n'
    header += 'multiplicative factor 1 =   {}	 multiplicative factor 2 =    {}	 multiplicative factor 3 =            {}\n'
    header += 'The 6 columns are | Q (1/A) | I(Q) (1/cm) | std. dev. I(Q) (1/cm) | sigmaQ | meanQ | ShadowFactor|\n'
    
    path = pathlib.Path(path) / fname
    with open(path,'w') as f:
        now = datetime.datetime.strftime(datetime.datetime.now(),'%T %D')
        f.write(header.format(now,*dfABS.values,dfABS.loc[shiftConfig],*dfShift.values))
        
    with open(path,'ba') as f:
        for config,fname in dfABS.iteritems():
            ABSData,_ = readABS(fname,trimLo,trimHi)
            ABSData = ABSData.values
            if shift:
                ABSData[:,1]*=dfShift[config] #shift I
                ABSData[:,2]*=dfShift[config] #shift sigmaI
            np.savetxt(f,ABSData)
            
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

class InteractiveTrimmingPlot(object):
    def __init__(self,df):
        
        self.df_all = df #base NSORTPath dataframe
        
        # all data_frames will have config index 
        # (corresponding to df.columns)
        self.df_xy             = None #I,q data
        self.df_lines          = None #matplotlib line objects
        self.df_shift          = None #vertical shift factors
        self.df_trim           = None #Lo/Hi data trim values
        
        self.shift_factors_out = None
        
        colors = ['red','green','blue','orange','magenta']
        self.df_colors= pd.Series(colors[:df.shape[1]],index=df.columns)
        
    def get_data(self,event):
        sys_select = self.select.value
        df_xy = []
        index = []
        for i,(config,fpath) in enumerate(self.df_all.loc[sys_select].iteritems()):
            if pd.isna(fpath):
                continue
            index.append(config)
            sdf = readABS(fpath)[0]
            df_xy.append(sdf.set_index('q',drop=False)[['q','I','dI']])
        self.n_configs = len(index)
        index = pd.MultiIndex.from_tuples(index)
        self.df_xy = pd.Series(df_xy,index=index)
        self.df_xy = self.df_xy.sort_index(axis=0)
        
        if not self.df_lines is None:
            self.update_plot(None)
            
    def update_plot(self,event):
        self.build_shift_table()
        
        for i,(config,sdf) in enumerate(self.df_lines.iterrows()):
            
            if not (config in self.df_xy.index):
                sdf['trim'].set_visible(False)
                sdf['all'].set_visible(False)
                continue
            else:
                sdf['trim'].set_visible(True)
                sdf['all'].set_visible(True)
            
            x = self.df_xy.loc[config]['q'].values
            y = self.df_xy.loc[config]['I'].values
            
            trimLo = self.df_trim.loc[config]['Lo']
            trimHi = self.df_trim.loc[config]['Hi']
            sl = slice(trimLo,-1-trimHi)
            
            sdf['all'].set_xdata(x)
            sdf['all'].set_ydata(y)
            sdf['trim'].set_xdata(x[sl])
            sdf['trim'].set_ydata(y[sl]*self.df_shift.loc[config])
            
            sdf['trim'].set_color(self.df_colors.loc[config])
            sdf['all'].set_color(self.df_colors.loc[config])
            
            # need to enforce zorder because matplotlib seems to scramble
            # the order randomly on update
            sdf['trim'].set_zorder(-i)
            sdf['all'].set_zorder(-i)
            
            # hide the original data if user desires
            sdf['all'].set_visible(self.show_original.value)
                
    def init_plot(self):
        df_lines = []
        for i,config in enumerate(self.df_xy.index):
            trimLo,trimHi = self.df_slider.loc[config].values
            sl = slice(trimLo.value,-1-trimHi.value)
            
            color = self.df_colors.loc[config]
            
            x1  = self.df_xy.loc[config]['q'].values
            y1  = self.df_xy.loc[config]['I'].values
            dy1 = self.df_xy.loc[config]['dI'].values
            kw = {'ls':'None','ms':3,'marker':'o'}
            
            # unfortunately error bars are uber difficult to update in matplotlib
            # so we don't display them (for now)
            # line1,_,_ = plt.errorbar(x1,y1,yerr=dy1,color=color,mfc='white',**kw)
            # line2,_,_ = plt.errorbar(x1[sl],y1[sl],yerr=dy1[sl],color=color,**kw)
            line1, = plt.plot(x1,y1,color=color,mfc='white',**kw)
            line2, = plt.plot(x1[sl],y1[sl],color=color,label=config,**kw)
            
            # need to enforce zorder because matplotlib seems to scramble
            # the order randomly on update
            line1.set_zorder(-i)
            line2.set_zorder(-i)
            
            df_lines.append([line1,line2])
        plt.gca().set_xscale('log')
        plt.gca().set_yscale('log')
        plt.gca().set_ylabel('dΣ/dΩ [$cm^{-1}$]')
        plt.gca().set_xlabel('q [$Å^{-1}$]')
        leg = plt.legend()
        # leg = plt.legend(bbox_to_anchor=(1.05,0.5),loc=6)
        # leg.set_draggable(True)
        self.df_lines = pd.DataFrame(df_lines,columns=['all','trim'],index=self.df_xy.index)
        
    def build_shift_table(self):
        shiftConfig = eval(self.shift_config.value)
        if not (shiftConfig in self.df_xy.index):
            shiftConfig = None
            
        self.df_trim = self.df_slider.applymap(lambda x: x.value)
        self.df_shift = buildShiftTable(self.df_xy,self.df_trim,shiftConfig)
        
        # display shift factors in table
        if not self.shift_factors_out is None:
            self.shift_factors_out.clear_output()
            with self.shift_factors_out:
                print('*-- Shift Factors --*')
                display(self.df_shift)
        return self.df_shift 
    
    
    def build_widget(self):
        widget = []
        
        # dropdown for system selection
        # checkbox for showing/hiding unmodified data
        self.select = Dropdown(options=self.df_all.index.values,description='System:')
        self.show_original = Checkbox(value=True,description='Show Original Data')
        widget.append(HBox([self.select,self.show_original]))
        
        # slider array for trimming datapoints
        vbox1 = [HBox([Label('Trim-Lo')],layout={'justify_content':'center'}) ]
        vbox2 = [HBox([Label('Trim-Hi')],layout={'justify_content':'center'}) ]
        for config in self.df_all.columns:
            sl1 = IntSlider(min=0,max=25,value=7,description='{}'.format(config))
            sl1.style.handle_color = self.df_colors.loc[config]
            vbox1.append(sl1)
            
            sl2 = IntSlider(min=0,max=50,value=15,description='{}'.format(config))
            sl2.style.handle_color = self.df_colors.loc[config]
            vbox2.append(sl2)
        widget.append(HBox([VBox(vbox1), VBox(vbox2)]))
        
        ## store slider objects in dataframe
        self.df_slider = pd.DataFrame(np.transpose([vbox1[1:],vbox2[1:]]),index=self.df_all.columns,columns=['Lo','Hi'])
        
        # dropdown for shift-configuration selection
        ops = ['None']
        ops += [str(i) for i in self.df_all.columns.values]
        self.shift_config = Dropdown(options=ops,description='Shift-To:')
        self.shift_factors_out = Output()
        widget.append(HBox([self.shift_config]))
        widget.append(HBox([self.shift_factors_out]))
        
        self.debug_out = Output()
        widget.append(HBox([self.debug_out]))
            
        return VBox(widget)
    
    def run_widget(self):
        '''Primary entry point for users'''
        widget = self.build_widget()
        
        self.get_data(None)# init data reading
        self.select.observe(self.get_data) #observer for system update
        self.build_shift_table()
        
        # init plot and plot-update observers 
        self.init_plot()
        self.df_slider.applymap(lambda x: x.observe(self.update_plot))
        self.shift_config.observe(self.update_plot)
        self.show_original.observe(self.update_plot)
        
        return widget
    
