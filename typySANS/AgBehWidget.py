import numpy as np
import matplotlib as mpl
import xarray as xr

import ipywidgets
import plotly.subplots
import plotly.graph_objs as go

from typySANS.FitUtil import init_image_mesh,init_gaussian1D_lmfit,init_gaussian2D_lmfit
from typySANS.ImageWidget import ImageWidget
from typySANS.Fit1DWidget import Fit1DWidget
from typySANS.Fit2DWidget import Fit2DWidget
from typySANS.IntegratorWidget import IntegratorWidget


class AgBehWidget:
    def __init__(self,df):
        self.df = df
        self.check()

        self.model1D,self.param1D = init_gaussian1D_lmfit()
        self.model2D,self.param2D = init_gaussian2D_lmfit()
        self.wavelengths = sorted(self.df.wavelength.unique())
        
        self.data_view = AgBehWidget_DataView(self.wavelengths)
    
    def build_widgets(self):
        self.Fit1DWidgets = {}
        self.Fit2DWidgets = {}
        self.IntegratorWidgets = {}
        
        for wavelength,sdf in self.df.groupby('wavelength'):
            sdf_trans = sdf.query('transmission==True')
            sdf_scatt = sdf.query('transmission==False')
            Fit2D = Fit2DWidget(
                sdf_trans.img.values[0],
                self.model2D,
                self.param2D,
            )
            
            Integrator = IntegratorWidget(
                sdf_scatt.img.values[0],
                x0= Fit2D.get_fit_param('x0').value,
                y0= Fit2D.get_fit_param('y0').value,
                wavelength=sdf_scatt.wavelength.values[0],
                SDD=sdf_scatt.SDD.values[0],
            )
            
            x,y = Integrator.get_integrated_data()
            Fit1D = Fit1DWidget(
                x,y,
                self.model1D,
                self.param1D,
            )
            Fit1D.data_view.add_vertical_line(0.1076,y0=y.min(),y1=y.max())
            
            self.Fit2DWidgets[wavelength]  = Fit2D
            self.IntegratorWidgets[wavelength]  = Integrator
            self.Fit1DWidgets[wavelength]  = Fit1D
        
    def check(self):
        for i,(index,sdf) in enumerate(self.df.groupby('wavelength')):
            if not (len(sdf)==2):
                strval=f'There should be one transmission and one scattering file for each wavelength. Found:\n{sdf}'
                raise ValueError(strval)
                
    def run(self):
        self.build_widgets()
        self.data_view.build_tabs(
            self.Fit2DWidgets,
            self.IntegratorWidgets,
            self.Fit1DWidgets,
        )
        self.data_view.build_buttons()
        
        update_button = self.data_view.buttons.children[-1]
        update_button.on_click(
            lambda x: self.data_view.update_summary(self.Fit1DWidgets)
        )
        
        VBox = ipywidgets.VBox([
            self.data_view.buttons,
            self.data_view.tabs
        ])
        return VBox
        
class AgBehWidget_DataView:
    def __init__(self,wavelengths):
        self.wavelengths = wavelengths
        self.tabs = None
        self.N = len(self.wavelengths)
        self.progress=None
    def prog_string(self,i):
        return str(i) + f'/{self.N} Wavelengths Processed'
    def init_progress(self):
        self.hbox = ipywidgets.HBox([ 
            ipywidgets.IntProgress(min=0,max=len(self.wavelengths)),
            ipywidgets.Label(self.prog_string(0))
        ])
        
        self.progress = self.hbox.children[0]
        self.prog_label = self.hbox.children[1]
        display(self.hbox)
        
    def build_tabs(self,Fit2DWidgets,IntegratorWidgets,Fit1DWidgets):
        if self.progress is None:
            self.init_progress()
            
        self.tabs = ipywidgets.Tab()
        children = []
        for i,wavelength in enumerate(self.wavelengths):
            self.progress.value = i
            self.prog_label.value = self.prog_string(i)
            
            self.tabs.set_title(i,'λ={}'.format(wavelength))
            
            Fit2D = Fit2DWidgets[wavelength].run()
            Integrator = IntegratorWidgets[wavelength].run()
            Fit1D = Fit1DWidgets[wavelength].run()
            
            sub_tab = ipywidgets.Tab()
            sub_tab.children = [Fit2D,Integrator,Fit1D]
            sub_tab.set_title(0,'Fit Beam Center')
            sub_tab.set_title(1,'Azimuthal Integration')
            sub_tab.set_title(2,'1D Gaussian Fit')
            children.append(sub_tab)
        
        self.build_summary(Fit1DWidgets)
        children.append(self.summary)
        self.tabs.set_title(i+1,'Summary'.format(wavelength))
        
        self.progress.value = i+1
        self.prog_label.value = self.prog_string(i+1)
        self.tabs.children = children
        
    def build_buttons(self):
        button1 = ipywidgets.Button(description='Fit Beam Center')
        button2 = ipywidgets.Button(description='Azimuthal Integration')
        button3 = ipywidgets.Button(description='1D Gaussian Fit')
        button4 = ipywidgets.Button(description='Update Summary')
        
        button1.on_click(lambda x: self.select_tab(0))
        button2.on_click(lambda x: self.select_tab(1))
        button3.on_click(lambda x: self.select_tab(2))
        self.buttons = ipywidgets.HBox([button1,button2,button3,button4])
        
    def select_tab(self,tab_selection):
        for i,tab in enumerate(self.tabs.children):
            if not ('λ' in self.tabs.get_title(i)):
                continue
            tab.selected_index=tab_selection
    
    def update_summary(self,Fit1DWidgets):
        y = []
        yerr = []
        for i,wavelength in enumerate(self.wavelengths):
            y.append(Fit1DWidgets[wavelength].get_fit_param('center').value)
            yerr.append(Fit1DWidgets[wavelength].get_fit_param('center').stderr)
        self.summary.data[0].y = y
        self.summary.data[0].error_y = dict(array=yerr)
            
    def build_summary(self,Fit1DWidgets):
        y = []
        yerr = []
        for i,wavelength in enumerate(self.wavelengths):
            y.append(Fit1DWidgets[wavelength].get_fit_param('center').value)
            yerr.append(Fit1DWidgets[wavelength].get_fit_param('center').stderr)
        
        self.summary = go.FigureWidget()
        self.summary.add_scatter(y=y,error_y={'array':yerr})
        
        yval = 0.1076
        self.summary.add_shape( 
            xref='paper', x0=0, x1=1, y0=yval, y1=yval, line=dict(dash='dash'))
        
        
        for pct in [0.5,1]:
            for sign in [1.0,-1.0]:
                yval = 0.1076*(1.00+sign*pct/100)
                self.summary.add_shape(
                    xref='paper', x0=0, x1=1, y0=yval, y1=yval, line=dict(dash='dot',color='red') 
                )

        self.summary.add_annotation(x=0.5,y=0.1076*(1.00-0.5/100),text='0.5% Error')
        self.summary.update_layout(
            xaxis_title = 'Wavelength',
            yaxis_title = 'AgBeh Peak q',
            xaxis=dict(
                tickmode='array',
                tickvals=[i for i,_ in enumerate(self.wavelengths)],
                ticktext=self.wavelengths,
            )
        )
            
        
        
