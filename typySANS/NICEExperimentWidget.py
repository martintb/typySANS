import pathlib
import requests
import datetime
import copy


import pandas as pd

import ipywidgets
import ipyaggrid

from typySANS.FTP import FTP
from typySANS.ProgressWidget import ProgressWidget


class NICEExperimentWidget:
    def __init__(self):
        self.data_model = NICEExperimentWidget_DataModel()
        self.data_view = NICEExperimentWidget_DataView()
        self.ftp = FTP()
    
    def download_all_files(self,*args):
        
        src_paths = self.data_view.grid.grid_data_out['rows'].squeeze().paths
        dest_path = pathlib.Path(self.data_view.download_loc.value)
        
        if len(src_paths)>0:
            src_path = pathlib.Path(src_paths[0])
        else:
            print('No data paths')
            return
        
        self.ftp.download_all_files(
            src_path,
            dest_path,
            select_key='nxs',
            progress=self.data_view.progress
        )
        
    def run(self):
        self.data_model.build_experiments()
        widget = self.data_view.run(self.data_model.experiments)
        
        self.data_view.download_button.on_click(self.download_all_files)
        self.data_view.stop_button.on_click(self.ftp.stop)
        return widget
        
                
        
class NICEExperimentWidget_DataModel:
    def __init__(self):
        self.manifest=None
        self.path_lookup=None
        self.experiments = None
    def get_manifest(self):
        self.manifest = requests.get(
            'https://ncnr.nist.gov/pub/ncnrdata/ngbsans/experiment_manifest.json'
        ).json()
    def get_path_lookup(self):
        self.path_lookup = requests.get(
            'https://ncnr.nist.gov/ipeek/experiment_lookup.json'
        ).json()
    def build_experiments(self):
        if self.manifest is None:
            self.get_manifest()
        if self.path_lookup is None:
            self.get_path_lookup()
        
        df = pd.DataFrame(self.manifest['experiments'])
        df['creationDate'] = df['creationTimeStamp'].apply(
            lambda x: datetime.datetime.fromtimestamp(x/1000)
        )
        df['paths'] = df.apply(
            lambda x: self.path_lookup['ngbsans']
            .get(x['id'],{})
            .get('paths',[]),
            axis=1
        
        )
        base_path = pathlib.Path('pub/ncnrdata')
        df['paths'] = df.apply(
            lambda x: [str(base_path / p / x.id / 'data') for p in x.paths],
            axis=1
        )
        
        self.experiments = df
        
    
class NICEExperimentWidget_DataView:
        
    def run(self,experiments):
        column_defs = [
            {'field':'id'},
            {'field':'title'},
            {'field':'participants'},
            {'field':'localContact'},
            {'field':'creationDate'},
            {'field':'paths'},
        ]
        
        grid_options = {
            'columnDefs':column_defs,
            'enableSorting': True,
            'enableFilter': True,
            'enableColResize': True,
            'rowSelection':'single',
        }
        self.grid = ipyaggrid.Grid(
            grid_data=experiments,
            grid_options=grid_options,
            index=True,
            quick_filter=True, 
            export_mode='auto',
            theme='ag-theme-balham', 
        )
        self.download_button    = ipywidgets.Button(description='DOWNLOAD ALL')
        self.download_loc       = ipywidgets.Text(value='./test/')
        self.stop_button        = ipywidgets.Button(description='STOP')
        self.progress           = ProgressWidget()
        
        down_hbox = ipywidgets.HBox([self.download_button,self.stop_button,self.download_loc])
        vbox = ipywidgets.VBox([self.grid,down_hbox,self.progress.run()])
        return vbox
        
    
    
        
        