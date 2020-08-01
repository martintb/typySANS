import pathlib
import pandas as pd
import numpy as np 

import ipywidgets
import ipyaggrid
import h5py

import shutil
import warnings

from typySANS.ProgressWidget import ProgressWidget
from typySANS.ImageWidget import ImageWidget

class NexusDataSetWidget:
    def __init__(self):
        self.data_model = NexusDataSetWidget_DataModel()
        self.data_view = NexusDataSetWidget_DataView()
        self.selected_img = None
        self.selected_row = None
    
    def load_files(self,*args):
        data_path = self.data_view.data_path.value
        filedata = self.data_model.get_filedata(data_path)
        self.data_view.update_grid(filedata)
        
    def plot_data(self,*args):
        try:
            selected_rows =  self.data_view.grid.grid_data_out['rows']
        except KeyError:
            #no rows selected
            return
        
        filename = selected_rows.iloc[0]['filename']#.squeeze()
        self.selected_row = self.data_view.grid.grid_data_out['rows'].iloc[0].name[0]
            
            
        data_path = pathlib.Path(self.data_view.data_path.value)
        filepath = data_path/filename
        with h5py.File(filepath,'r') as h5:
            self.selected_img = h5['entry/data/y'][()].T
        self.data_view.image.update_widget_image(self.selected_img)
        
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
        
        data_path = pathlib.Path(self.data_view.data_path.value)
        for fname in selected_rows['filename']:
            old_path = data_path/fname
            new_path = move_path/fname
            
            old_path.replace(new_path)#actually does the move
        
        self.load_files()
        
         
    def run(self):
        widget = self.data_view.run()
        self.data_view.load_button.on_click(self.load_files)
        self.data_view.move_button.on_click(self.move)
        self.data_view.plot_button.on_click(self.plot_data)
        return widget
        
                
        
class NexusDataSetWidget_DataModel:
    def __init__(self):
        self.path = None
    def get_filedata(self,path):
        self.path = pathlib.Path(path)
        
        filedata = []
        for fname in self.path.glob('*nxs*'):
            with h5py.File(fname,'r') as h5:
                filedata.append({
                    'filename':str(fname.parts[-1]),
                    'label':h5['entry/sample/description'][()][0].decode('utf8'),
                    'countTime':'{:.2f}'.format(float(h5['entry/collection_time'][()][0])),
                    'detectorDistance':'{:5.2f}'.format(h5['entry/DAS_logs/detectorPosition/softPosition'][()][0]),
                    'wavelength':float(h5['entry/DAS_logs/wavelength/wavelength'][()][0]),
                })
        return filedata
        
        
    
class NexusDataSetWidget_DataView:
    def update_grid(self,data):
        self.grid.update_grid_data(data)
        
    def run(self):
        column_defs = [
            {'field':'filename'},
            {'field':'label'},
            {'field':'countTime'},
            {'field':'detectorDistance'},
            {'field':'wavelength'},
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
            theme='ag-theme-balham', 
        )
        self.load_button = ipywidgets.Button(description='LOAD FILES')
        self.data_path     = ipywidgets.Text(value='./')
        self.move_button   = ipywidgets.Button(description='MOVE SELECTED')
        self.move_path     = ipywidgets.Text(value='./junk/')
        
        self.plot_button   = ipywidgets.Button(description='PLOT SELECTED')
        self.plot_next_button   = ipywidgets.Button(description='PLOT NEXT')
        self.plot_prev_button   = ipywidgets.Button(description='PLOT PREV')
        
        self.image = ImageWidget(2.0*np.ones((128,128)))
        
        down_hbox = ipywidgets.HBox([self.load_button,self.data_path])
        move_hbox = ipywidgets.HBox([self.move_button,self.move_path])
        plot_hbox = ipywidgets.HBox([self.plot_button,self.plot_prev_button,self.plot_next_button])
        vbox = ipywidgets.VBox([
            self.grid,
            down_hbox,
            move_hbox,
            plot_hbox,
            self.image.run(),
        ])
        
        return vbox
        
    
    
        
        