import pathlib
import requests
import datetime
import copy
import json


import pandas as pd

import ipywidgets
import ipyaggrid

from typySANS.FTP import FTP
from typySANS.ProgressWidget import ProgressWidget


class NICEFileWidget:
    def __init__(self):
        self.data_model = NICEFileWidget_DataModel()
        self.data_view = NICEFileWidget_DataView()
        self.ftp = FTP()
    
    def download_all_files(self,*args):
        
        src_paths = self.data_view.grid.grid_data_out['rows'].squeeze().path
        dest_path = pathlib.Path(self.data_view.download_loc.value)
        
        self.ftp.download_filelist(
            src_paths.values,
            dest_path,
            select_key='nxs',
            progress=self.data_view.progress
        )
    
    def update_grid(self,*args):
        path = pathlib.Path(self.data_view.update_loc.value)/'data'
        file_list = self.data_model.get_file_list(path)
        
        data = []
        for file in file_list['files']:
            data.append({'file':file,'path':str('pub'/path/file)})
        self.data_view.update(data)
        
    def run(self):
        widget = self.data_view.run()
        self.data_view.download_button.on_click(self.download_all_files)
        self.data_view.update_button.on_click(self.update_grid)
        return widget
        
                
        
class NICEFileWidget_DataModel:
        
    def get_file_list(self,path):
        path = pathlib.Path(path)
        result = requests.post(
            url='https://ncnr.nist.gov/ncnrdata/listftpfiles.php',
            data={'pathlist[]':path.parts},
        )
        return json.loads(result.content)
    
class NICEFileWidget_DataView:
        
    def update(self,data):
        self.grid.update_grid_data(data)
        
    def run(self):
        column_defs = [
            {'field':'file'},
            {'field':'path'},
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
        self.update_button      = ipywidgets.Button(description='UPDATE')
        self.update_loc         = ipywidgets.Text(value='ncnrdata/ngbsans/202007/nonims288')
        self.download_button    = ipywidgets.Button(description='DOWNLOAD')
        self.stop_button        = ipywidgets.Button(description='STOP')
        self.download_loc       = ipywidgets.Text(value='./test/')
        self.progress           = ProgressWidget()
        
        update_hbox = ipywidgets.HBox([self.update_button,self.update_loc])
        down_hbox = ipywidgets.HBox([self.download_button,self.stop_button,self.download_loc])
        vbox = ipywidgets.VBox([self.grid,update_hbox,down_hbox,self.progress.run()])
        return vbox
        
    
    
        
        