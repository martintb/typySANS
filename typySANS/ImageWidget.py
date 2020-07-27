import numpy as np
import ipywidgets
import matplotlib as mpl
from scipy.interpolate import interp2d
import xarray as xr

import plotly.subplots
import plotly.graph_objs as go

class ImageWidget:
    def __init__(self,img,cmap='viridis',lognorm=True,norm_min=1):
        
        if lognorm:
            self.norm = mpl.colors.LogNorm(norm_min,img.max())
        else:
            self.norm = mpl.colors.Normalize(norm_min,img.max())
            
        self.cmapper = mpl.cm.ScalarMappable(norm=self.norm,cmap=cmap).to_rgba
        self.img = img
        self.z = self.cmapper(img)*256
        self.widget = go.FigureWidget(
            go.Image(z=self.z)
        )
    def run(self):
        return self.widget
