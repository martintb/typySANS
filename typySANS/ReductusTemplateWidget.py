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
import ipyaggrid

class ReductusTemplateWidget:
    def __init__(self,template_path):
        self.selected_node = 0
        self.data_model = ReductusTemplateWidget_DataModel(template_path)
        self.data_view = ReductusTemplateWidget_DataView()
    
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
            self.data_model.modules[self.selected_node],
            update_callback=self.update_template_config
        )
        
    def update_node_status(self,*args):
        colors = []
        for i,module in enumerate(self.data_model.modules):
            if (i in self.data_model.input_nodes) and (len(module['config']['filelist'])==0):
                colors.append('red')
            else:
                colors.append('green')
                
        #update plot
        with self.data_view.graph.batch_update():
            self.data_view.node_status.marker.color = colors
                
    def update_template_config(self,update):
        if update['type']!='change':
            return
        
        value = update['new']
        param = update['owner'].description
        
        self.data_model.modules[self.selected_node]['config'][param] = value
            
    def run(self):
        self.data_view.init_nodes(
            self.data_model.nodes_x,
            self.data_model.nodes_y,
            self.data_model.labels,
            self.data_model.module_names,
        )
        self.data_view.init_edges(
            self.data_model.edges_x,
            self.data_model.edges_y,
        )
        self.data_view.init_node_select(
            self.data_model.nodes_x[0],
            self.data_model.nodes_y[0],
        )
        self.data_view.init_node_status(
            self.data_model.nodes_x,
            self.data_model.nodes_y,
            self.data_model.input_nodes,
        )
        self.data_view.init_filelist()
        self.data_view.build_graph()
        
        widget = self.data_view.run()
        self.data_view.nodes.on_click(self.update_point)
        self.data_view.show_module(
            self.data_model.modules[self.selected_node],
            update_callback=self.update_template_config
        )
        
        return widget

class ReductusTemplateWidget_DataModel:
    def __init__(self,path):
        self.set_template(path)
    
    def set_template(self,path):
        with open(path, 'rt') as f: 
            self.template = json.loads(f.read())
        self.modules = self.template['modules']
        self.wires   = self.template['wires']
        
        # flip the coordinate system to make visualization easier
        for m in self.modules:
            m['y']*=-1
            
        self.nodes_x = [m['x'] for m in self.modules]
        self.nodes_y = [m['y'] for m in self.modules]
        self.labels = [m['title'].split('.')[-1].replace(' ','\n') for m in self.modules]
        self.module_names = [m['module'] for m in self.modules]
        
        self.edges_x = []
        self.edges_y = []
        self.input_nodes = np.ones(len(self.modules),dtype=bool)
        for w in self.wires:
            i0 = w['source'][0]
            i1 = w['target'][0]
            x0 = self.modules[i0]['x']
            x1 = self.modules[i1]['x']
            y0 = self.modules[i0]['y']
            y1 = self.modules[i1]['y']
            self.edges_x.extend([x0,x1,None])
            self.edges_y.extend([y0,y1,None])
            
            self.input_nodes[i1] = False 
        
        self.input_nodes = np.where(self.input_nodes)[0]
    
class ReductusTemplateWidget_DataView:
    def __init__(self):
        self.widget = None
        self.nodes = None
        self.edges = None
        self.node_select = None
        self.node_status = None
        
    def init_filelist(self):
        
        grid_options = {
            'columnDefs':[{'field':'InputFile'}],
            'enableSorting': False,
            'enableFilter': False,
            'enableColResize': False,
            'rowSelection':'multiple',
        }
        self.filelist = ipyaggrid.Grid(
            grid_data=[],
            height=100,
            grid_options=grid_options,
            index=False,
            quick_filter=False, 
            export_mode='auto',
            show_toggle_edit=False,
            sync_grid=True,
            sync_on_edit=True,
            theme='ag-theme-balham', 
        )
    
    def init_edges(self,edges_x,edges_y):
        self.edges = go.Scatter(
            x=edges_x, y=edges_y,
            mode='lines',
            line=dict(
                width=0.5, 
                color='black',
                shape='spline',
                
            ),
            hoverinfo='none',
        )
        
    def init_node_select(self,x,y):
        self.node_select = go.Scatter(
            x=[x],y=[y],
            mode='markers',
            hoverinfo='skip',
            marker=dict(
                showscale=False,
                color='black',
                size=30,
                line_width=2,
                symbol='circle-open',
            ),
            
        )
        
    def init_node_status(self,nodes_x,nodes_y,input_nodes):
        colors = ['red' if i in input_nodes else 'green' for i,_ in enumerate(nodes_x) ]
        self.node_status = go.Scatter(
            x=nodes_x,
            y=nodes_y,
            mode='markers',
            hoverinfo='skip',
            marker=dict(
                showscale=False,
                color=colors,
                size=25,
                line_width=4,
                symbol='circle-open',
            ),
            
        )
        
        
    def init_nodes(self,nodes_x,nodes_y,labels,module_names):
        module_names_u = np.unique(module_names)
        cmap = matplotlib.cm.get_cmap('jet',module_names_u.shape[0])
        cmap = {m:matplotlib.colors.to_hex(cmap(i)) for i,m in enumerate(module_names_u)}
        colors = [cmap[m] for m in module_names]
        
        self.nodes = go.Scatter(
            x=nodes_x, y=nodes_y,
            mode='markers',
            hoverinfo='text',
            marker=dict(
                showscale=False,
                size=20,
                line_width=2,
            )
        )
        self.nodes.text = labels
        self.nodes.marker.color = colors
        
        
    def build_graph(self):
        xrange = [min(self.nodes.x)-50,max(self.nodes.x)+50]
        yrange = [min(self.nodes.y)-30,max(self.nodes.y)+30]
        self.graph = go.FigureWidget(
            data=[self.edges,self.nodes,self.node_select,self.node_status],
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
        # need to reassign pointers because FigureWidget makes a copy...
        self.edges = self.graph.data[0]
        self.nodes = self.graph.data[1]
        self.node_select = self.graph.data[2]
        self.node_status = self.graph.data[3]
        
        
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
            self.filelist.update_grid_data([{'InputFile':v} for v in module['config']['filelist']])
            config_widgets.append(self.filelist)
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