import ipywidgets
import ipyaggrid
import pathlib
import ftplib
import requests
import datetime
import pandas as pd
import copy
from concurrent.futures import ProcessPoolExecutor

from typySANS.NCNRExperimentWidget import NCNRExperimentWidget


class NCNRDataWidget:
    def __init__(self):
        self.data_view = NCNRDataWidget_DataView()
        
    def run(self):
        self.data_model.build_experiments()
        widget = self.data_view.run(self.data_model.experiments)
        self.data_view.download_button.on_click(self.download_all_files)
        return widget
    
class NCNRDataWidget_DataView:
    def __init__(self):
        self.experiment_widget = NCNRExperimentWidget()
        self.init_file_grid()
    
    def init_file_grid(self)
        column_defs = [
            {'field':'id'},
            {'field':'title'},
            {'field':'participants'},
            {'field':'localContact'},
            {'field':'creationDate'},
            {'field':'paths'},
        ]
        
        grid_options = {
            'columnDefs':[{'field':'filename'},{'field':'path'}],
            'enableSorting': True,
            'enableFilter': True,
            'enableColResize': True,
            'rowSelection':'multiple',
        }
        self.file_grid = ipyaggrid.Grid(
            grid_data=[],
            grid_options=grid_options,
            quick_filter=True, 
            export_mode='auto')
    
    def run(self):
        widget = self.experiment_widget.run()
        
        tabs = ipywidgets.Tab()
        
        tabs.children = [experiment_widget,file_widget]
                
        
    
    
        
        