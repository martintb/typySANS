import numpy as np
import matplotlib as mpl
import xarray as xr

import ipywidgets
import plotly.subplots
import plotly.graph_objs as go


class Fit_DataView:
    '''MVC Data Viewer for 2D Data Fitters'''
    def __init__(self,subplot_kw,height=600,width=600):
        
        self.output = ipywidgets.Output()
        self.output.layout = ipywidgets.Layout(
            height='300px',
            overflow_y='auto',
            border = '1px solid black',
            padding= '25px',
        )
        
        self.widget = go.FigureWidget(
            plotly.subplots.make_subplots(**subplot_kw)
        )
        self.widget.update_layout(height=height, width=width)
        
    
    def update_legend(self,legend_kw):
        self.widget.update_layout( legend=legend_kw ) 
        
    def add_image(self,img,row=1,col=1,lognorm=True,cmap='viridis',norm_min=1):
        self.widget.add_heatmap(z=img,row=row,col=col)
        
    def add_trace(self,x,y,name,row=1,col=1,mode='marker',color='blue'):
        
        self.widget.add_trace(
            go.Scatter(
                x=x, 
                y=y, 
                mode=mode, 
                marker={'color':color},
                line={'color':color},
                name=name),
            row=row,col=col
        )
        
    def add_horizontal_line(self,y,x0=0,x1=128,row=1,col=1,line_kw=None):
        if line_kw is None:
            line_kw=dict(color='red',dash='dot',width=0.3)
            
        self.widget.add_shape(
            xref='paper',
            yref='y',
            x0=x0, x1=x1, y0=y, y1=y,
            line=line_kw,
            row=row,
            col=col,
        )
        
    def add_vertical_line(self,x,y0=0,y1=128,row=1,col=1,line_kw=None):
        if line_kw is None:
            line_kw=dict(color='red',dash='dot',width=0.3)
        self.widget.add_shape(
            xref='x',
            yref='paper',
            x0=x, x1=x, y0=y0, y1=y1,
            line=line_kw,
            row=row,col=col,
        )
    
    def change_output(self,value):
        self.output.clear_output()
        with self.output:
            print(value)
    
    def run(self):
        vbox = ipywidgets.VBox([self.widget,self.output])
        return vbox
    