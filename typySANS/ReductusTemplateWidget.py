import numpy as np
import copy
import ipywidgets
import matplotlib.colors
import matplotlib.cm
import xarray as xr
import warnings
import json

import plotly.subplots
import plotly.graph_objs as go

class ReductusTemplateWidget:
    def __init__(self,template_path):
        self.selected_node = 0
        self.data_model = ReductusTemplateWidget_DataModel(template_path)
        self.data_view = ReductusTemplateWidget_DataView()
        self.data_view.init_graph(
            self.data_model.nodes_x,
            self.data_model.nodes_y,
            self.data_model.edges_x,
            self.data_model.edges_y,
            self.data_model.labels,
            self.data_model.modules,
        )
    
    def set_template(self,path):
        self.data_model.set_template(path)
        
    def update_point(self,trace,points,selector):
        try:
            self.selected_node = points.point_inds[0]
        except IndexError:
            return
        
        with self.data_view.graph.batch_update():
            self.data_view.node_select.x = [self.data_model.nodes_x[self.selected_node]]
            self.data_view.node_select.y = [self.data_model.nodes_y[self.selected_node]]
        
        self.data_view.show_module(
            self.data_model.modules_meta[self.selected_node],
            update_callback=self.update_template_config
        )
    
    def update_template_config(self,update):
        if update['type']!='change':
            return
        print(update)
        
        value = update['new']
        param = update['owner'].description
        
        self.data_model.modules_meta[self.selected_node]['config'][param] = value
            
    def run(self):
        widget = self.data_view.run()
        self.data_view.nodes.on_click(self.update_point)
        self.data_view.show_module(
            self.data_model.modules_meta[self.selected_node],
            update_callback=self.update_template_config
        )
        
        return widget

class ReductusTemplateWidget_DataModel:
    def __init__(self,path):
        self.set_template(path)
    
    def set_template(self,path):
        with open(path, 'rt') as f: 
            self.template = json.loads(f.read())
        self.modules_meta = self.template['modules']
        self.wires   = self.template['wires']
        
        for m in self.modules_meta:
            m['y']*=-1
            
        self.nodes_x = [m['x'] for m in self.modules_meta]
        self.nodes_y = [m['y'] for m in self.modules_meta]
        self.labels = [m['title'].split('.')[-1].replace(' ','\n') for m in self.modules_meta]
        self.modules = [m['module'] for m in self.modules_meta]
        
        
        
        self.edges_x = []
        self.edges_y = []
        for w in self.wires:
            i0 = w['source'][0]
            i1 = w['target'][0]
            x0 = self.modules_meta[i0]['x']
            x1 = self.modules_meta[i1]['x']
            y0 = self.modules_meta[i0]['y']
            y1 = self.modules_meta[i1]['y']
            self.edges_x.extend([x0,x1,None])
            self.edges_y.extend([y0,y1,None])
    
class ReductusTemplateWidget_DataView:
    def __init__(self):
        self.widget = None
    def init_graph(self,nodes_x,nodes_y,edges_x,edges_y,labels,modules):
        modules_u = np.unique(modules)
        cmap = matplotlib.cm.get_cmap('jet',modules_u.shape[0])
        cmap = {m:matplotlib.colors.to_hex(cmap(i)) for i,m in enumerate(modules_u)}
        colors = [cmap[m] for m in modules]
        
        nodes = go.Scatter(
            x=nodes_x, y=nodes_y,
            mode='markers',
            hoverinfo='text',
            marker=dict(
                showscale=False,
                size=20,
                line_width=2,
            )
        )
        nodes.text = labels
        nodes.marker.color = colors
        
        node_select = go.Scatter(
            x=[nodes_x[0]],y=[nodes_y[0]],
            mode='markers',
            hoverinfo='skip',
            marker=dict(
                showscale=False,
                color='red',
                size=35,
                line_width=4,
                symbol='circle-open',
            ),
            
        )
        
        edges = go.Scatter(
            x=edges_x, y=edges_y,
            mode='lines',
            line=dict(
                width=0.5, 
                color='black',
                shape='spline',
                
            ),
            hoverinfo='none',
        )
        
        xrange = [min(nodes_x)-40,max(nodes_x)+40]
        yrange = [min(nodes_y)-30,max(nodes_y)+30]
        self.graph = go.FigureWidget(
            data=[edges,nodes,node_select],
            layout = dict(
                width=500,
                height=350,
                margin=dict(b=20,l=5,r=5,t=40),
                xaxis=dict(range=xrange,showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(range=yrange,showgrid=False, zeroline=False, showticklabels=False),
                showlegend=False,
                plot_bgcolor='white',
            ),
        )
        self.nodes = self.graph.data[1]
        self.node_select = self.graph.data[2]
        self.edges = self.graph.data[0]
        
        
    def show_module(self,module,update_callback=None):
        self.module_title.value = module['title'].split('.')[-1].replace(' ','\n') 
        self.module_name.value = module['module']
        
        if 'config' not in module:
            return
        
        config_widgets = []
        hbox = []
        for i,(k,v) in enumerate(module['config'].items()):
            if k == 'filelist':
                continue
                
            if type(v) is bool:
                widget = ipywidgets.Checkbox(description=k,value=v)
            elif type(v) in [list,tuple]:
                v = str(v)[1:-1]#remove brackets/paren
                widget = ipywidgets.Text(description=k,value=str(v))
            hbox.append(widget)
            
            if update_callback is not None:
                widget.observe(update_callback,names='value')
            
            if (i%2)==0:
                config_widgets.append(ipywidgets.HBox(hbox))
                hbox = []
                
        
        
        if 'filelist' in module['config']:
            config_widgets.append(
                ipywidgets.Textarea(description='filelist',value='')
            )
        self.config_vbox.children = config_widgets
                
            
            
    def run(self):
        self.module_name = ipywidgets.Text(description='Module',value='',disabled=True)
        self.module_title = ipywidgets.Text(description='Title',value='',disabled=True)
        self.config_vbox = ipywidgets.VBox([])
        self.output = ipywidgets.VBox([
            ipywidgets.HBox([self.module_title,self.module_name]),
            self.config_vbox,
            
        ])
        
        self.widget = ipywidgets.VBox(
            [
                self.graph,
                self.output,
            ],
            layout={ 'align_items':'center', 'justify_content':'center' }
        )
        return self.widget