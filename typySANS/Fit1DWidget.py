import numpy as np
import matplotlib as mpl
import xarray as xr

import ipywidgets
import plotly.subplots
import plotly.graph_objs as go

from typySANS.ImageWidget import ImageWidget
from typySANS.MVC import Fit_DataView


class Fit1DWidget:
    '''MVC Controller for 1D Data Fitters'''
    def __init__(self,x,y,fit_model,fit_params):
        self.data_model = Fit1DWidget_DataModel(x,y,fit_model,fit_params)
        
        subplot_kw = dict( rows=1, cols=1,)
        self.data_view = Fit1DWidget_DataView(subplot_kw)
        self.data_view.widget.update_layout(dragmode='select')
        
    def get_fit_param(self,name):
        return self.data_model.fit_result.params[name]
        
    def run(self):
        
        x = self.data_model.data.x.values
        y = self.data_model.data.values
        x_fit = self.data_model.data_fit.x.values
        y_fit = self.data_model.data_fit.values
        
        self.data_view.add_trace(x,y,'SANS',row=1,col=1,mode='markers',color='blue')
        self.data_view.add_trace(x_fit,y_fit,'Fit',row=1,col=1,mode='lines',color='red')
        
        self.data_view.change_output(self.data_model.fit_result.fit_report())
        self.data_view.widget.data[0].on_selection(self.update_fit)
        
        return self.data_view.run()
    
    def update_fit(self,trace,points,state):
        self.data_model.update_mask(points.point_inds)
        self.data_model.fit()
        
        x = self.data_model.x_fit
        y = self.data_model.y_fit
        self.data_view.update_trace(1,x,y)
        self.data_view.change_output(self.data_model.fit_result.fit_report())
    
    
class Fit1DWidget_DataModel:
    '''MVC DataModel for 1D Data Fitters'''
    def __init__(self,x,y,model,params):
        self.model  = model
        self.params = params
        self.fit_params = None
        
        self.data  = xr.DataArray(y,dims=['x'],coords={'x':x})
        self.mask  = np.ones_like(y,dtype=bool)
        self.fit()
    
    def update_mask(self,indices):
        self.mask = np.in1d(range(self.data.shape[0]),indices)
        
    @property
    def x(self):
        return self.data.x.values[self.mask]
    
    @property
    def y(self):
        return self.data.values[self.mask]
    
    @property
    def x_fit(self):
        return self.data_fit.x.values[self.mask]
    
    @property
    def y_fit(self):
        return self.data_fit.values[self.mask]
        
    def fit(self):
        fit = self.model.fit(self.y,x=self.x,params=self.params)
        self.fit_result = fit
        
        x_fit = self.data.x.values
        y_fit = self.model.eval(x=x_fit,params=self.fit_result.params)
        self.data_fit = xr.DataArray(y_fit,dims=['x'],coords={'x':x_fit})
        
            
class Fit1DWidget_DataView(Fit_DataView):
    def update_trace(self,trace_number,x,y):
        self.widget.data[trace_number].x = x
        self.widget.data[trace_number].y = y

