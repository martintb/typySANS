import numpy as np 
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import pathlib
import datetime

from typySANS.misc import *
from typySANS.ABSFile import *

from ipywidgets import HBox,VBox,Output,SelectMultiple


class MultiPlotABS(object):
    def __init__(self,file_list,max_lines=10):
        self.file_list_path = [pathlib.Path(i) for i in file_list]
        self.file_list = [pathlib.Path(i).parts[-1] for i in file_list]
        self.max_lines = max_lines

    def update_plot(self,event):
        options = event['owner'].options
        index_list = event['owner'].index
        
        for i in range(self.max_lines):
            line = self.ax.get_lines()[i]
            line.set_xdata([])
            line.set_ydata([])
            line.set_label('')
            
        self.text_output.clear_output()
        with self.text_output:
            lines = []
            for i,index in enumerate(index_list):
                file = self.file_list[index]
                file_path = self.file_list_path[index]
                
                if i>=self.max_lines:
                    print('==> Skipping {}. Can only show {} at a time...'.format(file,self.max_lines))
                    continue
                    
                line = self.lines[i]
                print('--> Showing {}'.format(file))
                df,config = readABS(file_path)
                line.set_xdata(df['q'].values)
                line.set_ydata(df['I'].values)
                line.set_label(file)
                lines.append(file)
        self.ax.relim()
        self.ax.autoscale_view()
        self.ax.legend(lines)
    def build_widget(self):
        
        # init interactive plot
        self.plot_output = Output()
            
        self.text_output = Output()
        self.select = SelectMultiple(options=self.file_list,
                                     layout={'width':'400px'},
                                     rows=20)
        self.select.observe(self.update_plot)
        
        VB = VBox([self.select],layout={'align_self':'center'})
        HB = HBox([VB,self.plot_output])
        widget = VBox([HB,self.text_output])
        
        return widget
    def init_plot(self):
        with self.plot_output:
            fig,ax = plt.subplots()
            self.fig = fig
            self.ax = ax
            
        # init lines
        colors = sns.palettes.color_palette(palette='bright',n_colors=self.max_lines)
        self.lines = []
        for i in range(self.max_lines):
            line = plt.matplotlib.lines.Line2D([],[])
            line.set(color=colors[i],marker='o',ms=3,ls='None')
            ax.add_line(line)
            self.lines.append(line)
        ax.set_xscale('log')
        ax.set_yscale('log')
        
    def run_widget(self):
        widget = self.build_widget()
        self.init_plot()
        return widget
        
        
        