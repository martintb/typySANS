import numpy as np 
import pandas as pd
import matplotlib.pyplot as plt
import pathlib
import datetime

from typySANS.misc import *
from typySANS.ABSFile import *

from ipywidgets import Dropdown,IntSlider,FloatLogSlider,FloatSlider,HBox,VBox,Output,Label,Checkbox,Tab

class TrimPlot(object):
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
        self.bg_out.clear_output()
        for i,(config,sdf) in enumerate(self.df_lines.iterrows()):
            trimLo,trimHi,bgLoc = self.df_slider.loc[config].values
            
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


            mask = x[sl]>bgLoc.value
            sdf['bgx'].set_xdata(bgLoc.value)
            if self.apply_bg.value and (sum(mask)>0):
                bgVal = y[sl][mask].mean()
            else:
                bgVal = 0.0

            with self.bg_out:
                print('{}: {}'.format(config,bgVal))

            if bgVal>0:
                sdf['bgy'].set_visible(True)
                sdf['bgy'].set_ydata(bgVal)
            else:
                sdf['bgy'].set_visible(False)
            
            sdf['all'].set_xdata(x)
            sdf['all'].set_ydata(y)
            sdf['trim'].set_xdata(x[sl])
            sdf['trim'].set_ydata(y[sl]*self.df_shift.loc[config]-bgVal)
                
            sdf['trim'].set_color(self.df_colors.loc[config])
            sdf['all'].set_color(self.df_colors.loc[config])
            
            # need to enforce zorder because matplotlib seems to scramble
            # the order randomly on update
            sdf['trim'].set_zorder(-i)
            sdf['all'].set_zorder(-i)
            
            # hide the original data if user desires
            sdf['all'].set_visible(self.show_original.value)

            # make sure data fits in range
            plt.gca().relim()
            plt.gca().autoscale()
                
    def init_plot(self):
        df_lines = []
        for i,config in enumerate(self.df_xy.index):
            trimLo,trimHi,bgLoc = self.df_slider.loc[config].values
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

            # show bg_subtraction
            bgLoc.value = x1[-10] # set the initial location of the bg subtractor
            line3 = plt.axhline(y1[-10:].mean(),color=color,ls=':',lw=0.5)
            line4 = plt.axvline(bgLoc.value,color=color,ls=':',lw=0.5)
            line3.set_visible(False) # hide the bg subtraction value (y) until user changes to something reasonable

            with self.bg_out:
                print('{}: {}'.format(config,y1[-10:].mean()))


            # need to enforce zorder because matplotlib seems to scramble
            # the order randomly on update
            line1.set_zorder(-i)
            line2.set_zorder(-i)
            
            df_lines.append([line1,line2,line3,line4])
        plt.gca().set_xscale('log')
        plt.gca().set_yscale('log')
        plt.gca().set_ylabel('dΣ/dΩ [$cm^{-1}$]')
        plt.gca().set_xlabel('q [$Å^{-1}$]')
        leg = plt.legend()
        # leg = plt.legend(bbox_to_anchor=(1.05,0.5),loc=6)
        # leg.set_draggable(True)
        self.df_lines = pd.DataFrame(df_lines,columns=['all','trim','bgy','bgx'],index=self.df_xy.index)
        
    def build_shift_table(self):
        shiftConfig = eval(self.shift_config.value)
        if not (shiftConfig in self.df_xy.index):
            shiftConfig = None
            
        self.df_trim = self.df_slider.applymap(lambda x: x.value)[['Lo','Hi']]
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
        
        # slider array for trimming datapoints
        vbox1 = [HBox([Label('Trim-Lo')],layout={'justify_content':'center'}) ]
        vbox2 = [HBox([Label('Trim-Hi')],layout={'justify_content':'center'}) ]
        self.apply_bg = Checkbox(value=False,description='Subtract BG?')
        vbox3 = [HBox([self.apply_bg],layout={'justify_content':'center'}) ]
        for config in self.df_all.columns:
            sl1 = IntSlider(min=0,max=25,value=7,description='{}'.format(config))
            sl1.style.handle_color = self.df_colors.loc[config]
            vbox1.append(sl1)
            
            sl2 = IntSlider(min=0,max=100,value=15,description='{}'.format(config))
            sl2.style.handle_color = self.df_colors.loc[config]
            vbox2.append(sl2)

            # sl3 = FloatSlider(min=0.001,max=1,value=0.5,description='{}'.format(config))
            sl3 = FloatLogSlider(min=-3,max=0,value=0.5,description='{}'.format(config))
            sl3.style.handle_color = self.df_colors.loc[config]
            vbox3.append(sl3)
        widget.append(HBox([VBox(vbox1), VBox(vbox2)]))
        
        ## store slider objects in dataframe
        self.df_slider = pd.DataFrame(np.transpose([vbox1[1:],vbox2[1:],vbox3[1:]]),index=self.df_all.columns,columns=['Lo','Hi','bgLoc'])
        # self.df_bgslider = pd.DataFrame(np.transpose(vbox3[1:]),index=self.df_all.columns,columns=['Lo','Hi'])
        
        # dropdown for shift-configuration selection
        ops = ['None']
        ops += [str(i) for i in self.df_all.columns.values]
        self.shift_config = Dropdown(options=ops,description='Shift-To:')
        self.shift_factors_out = Output()
        self.show_original = Checkbox(value=True,description='Show Original Data')
        vbox4 = [VBox([self.shift_config,self.show_original]),self.shift_factors_out]

        # widget.append(HBox([VBox(vbox3),VBox(vbox4)]))
        self.bg_out = Output()
        widget.append(HBox([VBox(vbox3),self.bg_out]))
        widget.append(HBox(vbox4))
        
        tabs = Tab(widget)
        tabs.set_title(0,'Data Trimming')
        tabs.set_title(1,'Subtract BG')
        tabs.set_title(2,'Curve Shift')

        self.debug_out = Output()
        return VBox([self.select,tabs,self.debug_out])
    
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
        self.apply_bg.observe(self.update_plot)
        
        return widget
    
