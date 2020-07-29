import numpy as np
import matplotlib as mpl
import xarray as xr

import ipywidgets
import plotly.subplots
import plotly.graph_objs as go

from typySANS.FitUtil import init_image_mesh
from typySANS.MVC import Fit_DataView

import pyFAI,pyFAI.azimuthalIntegrator

import warnings


class IntegratorWidget:
    '''MVC Controller for 2D-1D Integrators'''
    def __init__(self,data,**integrator_kwargs):
        self.data_model = IntegratorWidget_DataModel(data)
        
        subplot_kw = dict(
            rows=1,
            cols=2,
            shared_xaxes=False,
            shared_yaxes=False,
        )
        self.data_view = IntegratorWidget_DataView(height=600,width=100,subplot_kw=subplot_kw)
        self.data_model.update_integrator(**integrator_kwargs)
        self.data_model.integrate()
        
    def update_integrator(self,**kwargs):
        self.data_model.update_integrator(**kwargs)
    
    def get_integrated_data(self):
        return  self.data_model.x, self.data_model.y
        
    def run(self):
        data2D = self.data_model.data2D
        data1D = self.data_model.data1D
        
        self.data_view.add_image(data2D.values,row=1,col=1)
        self.data_view.change_output(self.data_model.integrator)
        
        self.data_view.add_trace(
            data1D.x.values,
            data1D.values,
            'SANS X',
            col=2,
            mode='markers',
            color='blue')
        self.data_view.widget.update_layout(height=400,width=800)
        
        return self.data_view.run()
    
    
class IntegratorWidget_DataModel:
    '''MVC DataModel for 2D->1D Integrator'''
    def __init__(self,data):
        Nx,Ny = np.shape(data)
        x,y,X,Y,self.XY = init_image_mesh(Nx,Ny)
        self.data2D    = xr.DataArray(data,dims=['y','x'],coords={'x':x,'y':y})
        self.init_integrator()
        
    @property
    def x(self):
        return self.data1D.x.values
    
    @property
    def y(self):
        return self.data1D.values
    
    def init_integrator(self,Nx=128,Ny=128,pixel_dx=0.00508,pixel_dy=0.00508):
        SDD = 5.0 # in m
        dx = dy = 0.00508 #pixel size in m
        poni1 = 64.5*dy  #dummy
        poni2 = 64.5*dx #dummy 
        wavelength = 5*1e-10 #dummy (in m)
        detector = pyFAI.detectors.Detector(dx,dy,max_shape=(Ny,Nx))
        self.integrator = pyFAI.azimuthalIntegrator.AzimuthalIntegrator(
                                                     dist=SDD, #meter
                                                     poni1=poni1,
                                                     poni2=poni2,
                                                     wavelength=wavelength, #meters
                                                     detector=detector,
                                                )                   
    def update_integrator(self,**kwargs):
        ''' 
        x0,y0: [pixels]
            beam center location
        
        wavelength: [angstroms]
            wavelength of neutron beam
        
        SDD: [cm]
            sample to detector distance
        '''
        dy = self.integrator.get_pixel1()
        dx = self.integrator.get_pixel2()
        for k,v in kwargs.items():
            if k=='y0':
                self.integrator.set_poni1(dy*v)
            elif k=='x0':
                self.integrator.set_poni2(dx*v)
            elif k=='wavelength':
                self.integrator.set_wavelength(v*1e-10)
            elif k=='SDD':
                self.integrator.set_dist(v/100.0)
            else:
                raise ValueError(f'Integrator parameter not understood: {k}={v}')
        
    def integrate(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            pf_result = self.integrator.integrate1d(
                data=self.data2D.values,
                unit='q_A^-1',
                method='csr_ocl_1,3',
                correctSolidAngle=False,
                npt=500,
            )
        self.data1D = xr.DataArray(
            pf_result.intensity,
            dims=['x'],
            coords={'x':pf_result.radial}
        )
        
            
class IntegratorWidget_DataView(Fit_DataView):
    pass
