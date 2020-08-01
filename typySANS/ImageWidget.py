import numpy as np
import ipywidgets
import matplotlib as mpl
from scipy.interpolate import interp2d
import xarray as xr
import warnings

import plotly.subplots
import plotly.graph_objs as go

class ImageWidget:
    def __init__(self,img):
        self.data_model = ImageWidget_DataModel(img)
        self.data_view = ImageWidget_DataView()
    
    def update_widget_image(self,img):
        self.data_model.img = img
        self.data_view.image.data[0].update(dict(z=img,zmin=img.min(),zmax=img.max()))
        self.update_logscale({'owner':self.data_view.checkbox})
        
    
    def update_colorbar(self,update):
        zmin,zmax = update['owner'].value
        self.data_view.image.data[0].update(dict(zmin=zmin,zmax=zmax))
        
    def update_logscale(self,update):
        logscale = update['owner'].value
        if logscale:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                img = np.log10(self.data_model.img)
            
            minval = img[~np.isinf(img)].min()
            maxval = img.max()
            self.data_view.image.data[0].update(dict(z=img,zmin=minval,zmax=maxval))
            self.data_view.log_slider.max = maxval#order of max/min setting is important
            self.data_view.log_slider.min = minval
            self.data_view.log_slider.value = [minval,maxval]
            self.data_view.slider.layout.visibility = 'hidden'
            self.data_view.log_slider.layout.visibility = 'visible'
        else:
            img = self.data_model.img
            self.data_view.image.data[0].update(dict(z=img,zmin=img.min(),zmax=img.max()))
            self.data_view.slider.min = img.min()
            self.data_view.slider.max = img.max()
            self.data_view.slider.value = [img.min(),img.max()]
            self.data_view.slider.layout.visibility = 'visible'
            self.data_view.log_slider.layout.visibility = 'hidden'
        
    def run(self):
        widget = self.data_view.run(self.data_model.img)
        self.data_view.slider.observe(self.update_colorbar,names='value')
        self.data_view.log_slider.observe(self.update_colorbar,names='value')
        self.data_view.checkbox.observe(self.update_logscale,names='value')
        return widget

class ImageWidget_DataModel:
    def __init__(self,img):
        self.img = img
    
class ImageWidget_DataView:
    def __init__(self):
        self.widget = None
    def run(self,img):
        self.image = go.FigureWidget(
            go.Heatmap(
                z=img,
            ),
            layout=dict(
                height=300,
                width=400,
                modebar=dict(orientation='h'),
                margin =dict(pad=0,r=150,l=0,t=30,b=0),
            ),
        )
        
        self.slider = ipywidgets.FloatRangeSlider(
            description='Colorscale',
            value=[img.min(),img.max()],
            min=img.min(),
            max=img.max(),
            readout_format='.0f',
            #orientation='vertical',
            #readout=False,
        )
        self.log_slider = ipywidgets.FloatRangeSlider(
            description='LogColorscale',
            value=[0.0,np.log10(img.max())],
            min=np.log10(img[img>0.0].min()),
            max=np.log10(img.max()),
            readout_format='.1f',
            #orientation='vertical',
            #readout=False,
            layout = {
                'visibility':'hidden'
            }
        
        )
        
        self.checkbox = ipywidgets.Checkbox(
            value=False,
            description='log scale',
        )
        
        self.hbox = ipywidgets.VBox(
            [self.slider,self.log_slider],
        )
        self.vbox = ipywidgets.VBox(
            [self.hbox,self.checkbox],
            layout={'align_items':'center','justify_content':'center'}
        )
        self.widget = ipywidgets.HBox(
            [self.image,self.vbox],
            layout={'align_items':'center'},
        )
        return self.widget