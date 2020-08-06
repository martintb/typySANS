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
    
    def update_widget_label(self,label):
        self.data_view.data_label.value = label
        
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
            
        else:
            img = self.data_model.img
            
        minval = img[~np.isinf(img)].min()
        maxval = img.max()
        self.data_view.image.data[0].update(dict(z=img,zmin=minval,zmax=maxval))
        self.data_view.slider.max = maxval#order of max/min setting is important
        self.data_view.slider.min = minval
        self.data_view.slider.value = [minval,maxval]
        
    def run(self):
        widget = self.data_view.run(self.data_model.img)
        self.data_view.slider.observe(self.update_colorbar,names='value')
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
        
        self.checkbox = ipywidgets.Checkbox(
            value=False,
            description='log scale',
        )
        
        self.data_label = ipywidgets.Label(value='')
        self.vbox = ipywidgets.VBox(
            [self.data_label,self.slider,self.checkbox],
            layout={'align_items':'center','justify_content':'center'}
        )
        self.widget = ipywidgets.VBox(
            [self.image,self.vbox],
            layout={'align_items':'center'},
        )
        return self.widget