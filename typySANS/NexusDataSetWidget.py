import pathlib
import pandas as pd
import numpy as np 

import ipywidgets
from ipywidgets import HBox,VBox

import ipyaggrid
import h5py

import shutil
import warnings

from typySANS.ProgressWidget import ProgressWidget
from typySANS.ImageWidget import ImageWidget
from typySANS.IntegratorWidget import IntegratorWidget

import plotly.graph_objects as go

class NexusDataSetWidget:
    def __init__(self):
        self.data_model = NexusDataSetWidget_DataModel()
        self.data_view = NexusDataSetWidget_DataView()
        
        self.integrator = IntegratorWidget(np.ones((128,128)))
        self.selected_img = None
    
    def load_files(self,*args):
        load_path = self.data_view.load_path.value
        filedata = self.data_model.get_filedata(load_path)
        self.data_view.update_grid(filedata)
        
    def plot_increment(self,button):
        grid_data_out = self.data_view.grid.grid_data_out
        try:
            selected_rows =  grid_data_out['rows'].iloc[0]
        except KeyError:
            selected_rows =  grid_data_out['grid'].iloc[0]
        
        if button.description == 'PLOT NEXT':
            index = selected_rows.name[0]+1
        elif button.description == 'PLOT PREV':
            index = selected_rows.name[0]-1
        if index>grid_data_out['grid'].index.max()[0]:
            index = grid_data_out['grid'].index.min()[0]
        elif index<grid_data_out['grid'].index.min()[0]:
            index = grid_data_out['grid'].index.max()[0]
        
        grid_data_out['rows'] = grid_data_out['grid'].loc[[index]]
        self.plot_data()
            
    def plot_data(self,*args):
        #initialize 
        if self.data_view.accordion.children[0].children[1] is self.data_view.dummy:
            vbox = self.data_view.accordion.children[0]
            children = list(vbox.children)
            children[1] = self.integrator.run()
            vbox.children = children
            
        try:
            selected_row =  self.data_view.grid.grid_data_out['rows'].iloc[0]
        except KeyError:
            return
        
        filename = selected_row['filename']#.squeeze()
            
        load_path = pathlib.Path(self.data_view.load_path.value)
        filepath = load_path/filename
        with h5py.File(filepath,'r') as h5:
            sample_label = h5['entry/sample/description'][()][0].decode('utf8')
            self.selected_img = h5['entry/data/y'][()].T
            
        
        self.integrator.update_image(self.selected_img)
        self.integrator.update_integrator(
            SDD = float(selected_row['detectorDistance']),
            wavelength = float(selected_row['wavelength']),
            x0 = float(selected_row['beamCenterX']),
            y0 = float(selected_row['beamCenterY']),
        )
        self.integrator.integrate()
        
        label = f'Filename: {filename}' 
        label+= '\n' 
        label+= f'Sample Label: {sample_label}'  
        label+= '\n' 
        label+= '\n' 
        label+= str(self.integrator.data_model.integrator)
        self.integrator.data_view.change_output(label)
        
    def move(self,*args):
        try:
            selected_rows =  self.data_view.grid.grid_data_out['rows']
        except KeyError:
            #no rows selected
            return
        
        move_path = pathlib.Path(self.data_view.move_path.value)
        if move_path.is_file():
            warnings.warn('Skipping move as destination is a file!')
        move_path.mkdir(exist_ok=True)
        
        load_path = pathlib.Path(self.data_view.load_path.value)
        for fname in selected_rows['filename']:
            old_path = load_path/fname
            new_path = move_path/fname
            
            old_path.replace(new_path)#actually does the move
        
        self.load_files()
        
         
    def run(self):
        widget = self.data_view.run()
        self.data_view.load_button.on_click(self.load_files)
        self.data_view.move_button.on_click(self.move)
        self.data_view.plot_button.on_click(self.plot_data)
        self.data_view.plot_next_button.on_click(self.plot_increment)
        self.data_view.plot_prev_button.on_click(self.plot_increment)
        return widget
        
                
        
class NexusDataSetWidget_DataModel:
    def __init__(self):
        self.path = None
    def get_filedata(self,path):
        self.path = pathlib.Path(path)
        
        filedata = []
        for file in sorted(self.path.glob('*nxs*')):
            with h5py.File(file,'r') as h5:
                filedata.append({
                    'filename':str(file.parts[-1]),
                    'label':h5['entry/sample/description'][()][0].decode('utf8'),
                    'countTime':'{:.2f}'.format(float(h5['entry/collection_time'][()][0])),
                    'detectorDistance':'{:5.2f}'.format(h5['entry/DAS_logs/detectorPosition/softPosition'][()][0]),
                    'wavelength':float(h5['entry/DAS_logs/wavelength/wavelength'][()][0]),
                    'beamCenterX':float(h5['entry/instrument/detector/beam_center_x'][()][0]),
                    'beamCenterY':float(h5['entry/instrument/detector/beam_center_y'][()][0]),
                })
        filedata = pd.DataFrame(filedata)
        return filedata
        
        
    
class NexusDataSetWidget_DataView:
    def __init__(self):
        self.image = None
        self.integrated_trace = None
        self.dummy = ipywidgets.Label() #sentinel for not loaded
        
    def update_grid(self,data):
        self.grid.update_grid_data(data)
        
    def build_grid(self):
        column_defs = [
            {'field':'filename'},
            {'field':'label'},
            {'field':'countTime'},
            {'field':'detectorDistance'},
            {'field':'wavelength'},
            {'field':'beamCenterX'},
            {'field':'beamCenterY'},
        ]
        
        grid_options = {
            'columnDefs':column_defs,
            'enableSorting': True,
            'enableFilter': True,
            'enableColResize': True,
            'rowSelection':'multiple',
        }
        self.grid = ipyaggrid.Grid(
            grid_data=[],
            grid_options=grid_options,
            index=True,
            quick_filter=True, 
            export_mode='auto',
            show_toggle_edit=True,
            sync_grid=True,
            sync_on_edit=True,
            theme='ag-theme-balham', 
        )
        
    def build_grid_buttons(self):
        self.load_button = ipywidgets.Button(description='LOAD FILES')
        self.load_path     = ipywidgets.Text(value='./')
        self.move_button   = ipywidgets.Button(description='MOVE SELECTED')
        self.move_path     = ipywidgets.Text(value='./junk/')
        
        self.plot_button   = ipywidgets.Button(description='PLOT SELECTED')
        self.plot_next_button   = ipywidgets.Button(description='PLOT NEXT')
        self.plot_prev_button   = ipywidgets.Button(description='PLOT PREV')
        
    def run(self):
        self.build_grid()
        self.build_grid_buttons()
        
        load_hbox = ipywidgets.HBox([self.load_button,self.load_path])
        move_hbox = ipywidgets.HBox([self.move_button,self.move_path])
        button_vbox = ipywidgets.VBox([load_hbox,move_hbox])
        
        plot_hbox = ipywidgets.HBox(
            [self.plot_button,self.plot_prev_button,self.plot_next_button],
            layout={ 'align_items':'center', 'justify_content':'center' }
        )
        raw_data_vbox = ipywidgets.VBox([plot_hbox,self.dummy])
        
        self.accordion = ipywidgets.Accordion([raw_data_vbox])
        self.accordion.set_title(0,'Raw Data')
        self.accordion.selected_index = None
        
        vbox = ipywidgets.VBox([
            self.grid,
            button_vbox,
            self.accordion,
        ])
        
        return vbox
        
    
    
