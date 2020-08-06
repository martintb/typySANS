import numpy as np
import matplotlib as mpl
import xarray as xr

import ipywidgets
import plotly.subplots
import plotly.graph_objs as go

from typySANS.FitUtil import init_image_mesh
from typySANS.ImageWidget import ImageWidget
from typySANS.MVC import Fit_DataView


class Fit2DWidget:
    '''MVC Controller for 2D Data Fitters'''
    def __init__(self,img,fit_model,fit_params):
        self.data_model = Fit2DWidget_DataModel(img,fit_model,fit_params)
        
        subplot_kw = dict(
            rows=2,
            cols=2,
            shared_xaxes=True,
            shared_yaxes=True,
            horizontal_spacing=0,
            vertical_spacing=0
        )
        self.data_view = Fit2DWidget_DataView(subplot_kw)
    
    def get_fit_param(self,name):
        return self.data_model.fit_result.params[name]
        
    def run(self):
        img = self.data_model.data.values
        y0 = self.data_model.fit_result.params['y0'].value
        x0 = self.data_model.fit_result.params['x0'].value
        self.data_model.make_slice('xslice','x',x0)
        self.data_model.make_slice('yslice','y',y0)
        
        self.data_view.add_image(img,row=2,col=1)
        self.data_view.add_horizontal_line(y0,row=2,col=1)
        self.data_view.add_vertical_line(x0,row=2,col=1)
        self.data_view.change_output(self.data_model.fit_result.fit_report())
        
        x,y = self.data_model.get_slice('xslice','y',fit=False)
        x_fit,y_fit = self.data_model.get_slice('xslice','y',fit=True)
        self.data_view.add_trace(x,y,'SANS Y',row=2,col=2,mode='markers',color='blue')
        self.data_view.add_trace(x_fit,y_fit,'Fit Y',row=2,col=2,mode='lines',color='red')
        
        y,x = self.data_model.get_slice('yslice','x',fit=False)
        y_fit,x_fit = self.data_model.get_slice('yslice','x',fit=True)
        self.data_view.add_trace(x,y,'SANS X',row=1,col=1,mode='markers',color='blue')
        self.data_view.add_trace(x_fit,y_fit,'Fit X',row=1,col=1,mode='lines',color='red')
        
        self.data_view.update_legend(
            dict(
                yanchor="bottom", 
                xanchor="left", 
                y=0.5, 
                x=0.5
            )
        )
        
        return self.data_view.run()
    
    
class Fit2DWidget_DataModel:
    '''MVC DataModel for 2D Data Fitters'''
    def __init__(self,data,model,params,fit_now=True):
        self.model  = model
        self.params = params
        self.slices = {}
        
        Nx,Ny = np.shape(data)
        x,y,X,Y,self.XY = init_image_mesh(Nx,Ny)
        self.data    = xr.DataArray(data,dims=['y','x'],coords={'x':x,'y':y})
        
        if fit_now:
            self.fit()
        
    def fit(self):
        fit = self.model.fit(self.data.values.ravel(),XY=self.XY,params=self.params)
        self.fit_result = fit
        
        x_fit,y_fit,X_fit,Y_fit,XY_fit = init_image_mesh(*np.shape(self.data),step=0.25)
        data_fit = self.model.eval(XY=XY_fit,params=self.fit_result.params).reshape(512,-1)
        self.data_fit = xr.DataArray(data_fit,dims=['y','x'],coords={'x':x_fit,'y':y_fit})
        
    def make_slice(self,name,dim,value):
        self.slices[name] = {
            'data': self.data.interp(**{dim:value}),
            'data_fit': self.data_fit.interp(**{dim:value}),
        }
    def get_slice(self,name,index,fit=False):
        if fit:
            name2 = 'data_fit'
        else:
            name2 = 'data'
        
        x = self.slices[name][name2].values
        y = getattr(self.slices[name][name2],index).values
        return x,y
            
class Fit2DWidget_DataView(Fit_DataView):
    def change_output(self,value):
        self.output.clear_output()
        with self.output:
            print('Warning: Pixel coordinates are one less than Igor due to zero-based indexing!')
            print()
            print(value)

