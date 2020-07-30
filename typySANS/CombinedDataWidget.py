import ipywidgets
import ipyaggrid
import pathlib
import ftplib
import requests
import datetime
import pandas as pd
import copy
from concurrent.futures import ProcessPoolExecutor

from typySANS.NICEExperimentWidget import NICEExperimentWidget
from typySANS.NICEFileWidget import NICEFileWidget
from typySANS.NexusDataWidget import NexusDataWidget


class CombinedDataWidget:
    def __init__(self):
        self.experiment_widget = NICEExperimentWidget()
        self.file_widget = NICEFileWidget()
        self.nexus_widget = NexusDataWidget()
        self.data_view = CombinedDataWidget_DataView()
        
    def update_remote_filelist(self,*args):
        if not self.data_view.tabs.selected_index==1:
            return
        
        try:
            selected_rows =  self.experiment_widget.data_view.grid.grid_data_out['rows']
        except KeyError:
            #no rows selected
            return
         
        src_paths = selected_rows.squeeze().paths
        if len(src_paths)>0:
            #need to trip 'pub' and 'data' portions of path
            src_path = pathlib.Path(src_paths[0]).parts[1:-1]
            src_path = pathlib.Path(*src_path)
        else:
            print('No data paths')
            return
        self.file_widget.data_view.update_loc.value = str(src_path)
        
    def run(self):
        experiment_widget = self.experiment_widget.run()
        file_widget = self.file_widget.run()
        nexus_widget = self.nexus_widget.run()
        widget = self.data_view.run(experiment_widget,file_widget,nexus_widget)
        
        self.data_view.tabs.on_trait_change(self.update_remote_filelist,name='selected_index')
        
        return widget
    
class CombinedDataWidget_DataView:
    def run(self,experiment_widget,file_widget,nexus_widget):
        self.tabs = ipywidgets.Tab()
        self.tabs.children = [experiment_widget,file_widget,nexus_widget]
        self.tabs.set_title(0,'Experiments')
        self.tabs.set_title(1,'Remote Files')
        self.tabs.set_title(2,'Local Files')
        return self.tabs
        
        
    
    
        
        