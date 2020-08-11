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
        
    def update_colorbar(self,update):
        zmin,zmax = update['owner'].value
        self.data_view.widget.data[0].update(dict(zmin=zmin,zmax=zmax))
        # self.data_view.slider.max = zmax#order of max/min setting is important
        # self.data_view.slider.min = zmin
        # self.data_view.slider.value = [zmin,zmax]
        
    def update_trace_logscale(self,update):
        checkbox = update['owner']
        if checkbox.value==True:
            typ='log'
        else:
            typ='linear'
            
        if 'log x' in checkbox.description:
            self.data_view.widget.update_xaxes(type=typ,row=1,col=2)
        elif 'log y' in checkbox.description:
            self.data_view.widget.update_yaxes(type=typ,row=1,col=2)
                
        
    def update_image_logscale(self,update):
        logscale = update['owner'].value
        if logscale:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                img = np.log10(self.data_model.data2D.values)
            
        else:
            img = self.data_model.data2D.values
            
        minval = img[~np.isinf(img)].min()
        maxval = img.max()
        self.data_view.widget.data[0].update(dict(z=img,zmin=minval,zmax=maxval))
        self.data_view.slider.max = maxval#order of max/min setting is important
        self.data_view.slider.min = minval
        self.data_view.slider.value = [minval,maxval]
        
    def update_image(self,image):
        self.data_model.set_image(image)
        self.data_view.widget.data[0].z=image
        zmin,zmax = image.min(),image.max()
        self.data_view.widget.data[0].update(dict(zmin=zmin,zmax=zmax))
        self.data_view.slider.max = zmax#order of max/min setting is important
        self.data_view.slider.min = zmin
        self.data_view.slider.value = [zmin,zmax]
        
    def update_integrator(self,**kwargs):
        self.data_model.update_integrator(**kwargs)
        
    def integrate(self):
        self.data_model.integrate()
        data1D = self.data_model.data1D
        self.data_view.widget.data[1].update(x=data1D.x.values,y=data1D.values)
    
    def get_integrated_data(self):
        return  self.data_model.x, self.data_model.y
        
    def run(self):
        data1D = self.data_model.data1D
        data2D = self.data_model.data2D
        
        self.data_view.add_image(data2D.values,row=1,col=1)
        self.data_view.change_output(self.data_model.integrator)
        
        self.data_view.add_trace(
            data1D.x.values,
            data1D.values,
            'SANS',
            col=2,
            mode='markers',
            color='blue')
        self.data_view.widget.update_layout(height=400,width=800)
        widget = self.data_view.run(data2D.values)
        
        self.data_view.slider.observe(self.update_colorbar,names='value')
        self.data_view.checkbox_z.observe(self.update_image_logscale,names='value')
        self.data_view.checkbox_y.observe(self.update_trace_logscale,names='value')
        self.data_view.checkbox_x.observe(self.update_trace_logscale,names='value')
        
        return widget
    
    
class IntegratorWidget_DataModel:
    '''MVC DataModel for 2D->1D Integrator'''
    def __init__(self,data=None):
        self.init_integrator() 
        if data is not None:
            self.set_image(data) 
    
    def set_image(self,data):
        Nx,Ny = np.shape(data)
        x,y,X,Y,self.XY = init_image_mesh(Nx,Ny)
        self.data2D    = xr.DataArray(data,dims=['y','x'],coords={'x':x,'y':y})
        
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
        #print('Integrator Args:')
        for k,v in kwargs.items():
            #print(k,v)
            if k=='y0':
                self.integrator.set_poni1(dy*float(v))
            elif k=='x0':
                self.integrator.set_poni2(dx*float(v))
            elif k=='wavelength':
                self.integrator.set_wavelength(float(v)*1e-10)
            elif k=='SDD':
                self.integrator.set_dist(float(v)/100.0)
            else:
                raise ValueError(f'Integrator parameter not understood: {k}={v}')
        
    def integrate(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            pf_result = self.integrator.integrate1d(
                data=self.data2D.values,
                unit='q_A^-1',
                #method='csr_ocl_1,3',
                method='csr_ocl',
                correctSolidAngle=False,
                npt=200,
            )
        self.data1D = xr.DataArray(
            pf_result.intensity,
            dims=['x'],
            coords={'x':pf_result.radial}
        )
        
            
class IntegratorWidget_DataView(Fit_DataView):
    def run(self,img):
        
        self.slider = ipywidgets.FloatRangeSlider(
            description='Colorscale',
            value=[img.min(),img.max()],
            min=img.min(),
            max=img.max(),
            readout_format='.0f',
        )
        
        self.checkbox_z = ipywidgets.Checkbox(
            value=False,
            description='log z',
        )
        
        self.checkbox_x = ipywidgets.Checkbox(
            value=True,
            description='log x',
        )
        
        self.checkbox_y = ipywidgets.Checkbox(
            value=True,
            description='log y',
        )
        
        self.widget.update_xaxes(type='log',row=1,col=2)
        self.widget.update_yaxes(type='log',row=1,col=2)
        self.widget.update_layout(height=250,width=600,margin=dict(t=30,b=30))
        
        vbox = ipywidgets.VBox(
            [
                self.widget,
                self.slider,
                ipywidgets.HBox([
                    self.checkbox_z,
                    self.checkbox_y,
                    self.checkbox_x,
                ],layout=dict(width='500px')),
                self.output
            ],
            layout={ 'align_items':'center', 'justify_content':'center'}
        )
        return vbox
