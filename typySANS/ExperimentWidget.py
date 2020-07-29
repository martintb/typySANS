import ipywidgets
import ipyaggrid
import pathlib
import ftplib
import requests
import datetime
import pandas as pd
import copy
from concurrent.futures import ProcessPoolExecutor


class ExperimentWidget:
    def __init__(self):
        self.data_model = ExperimentWidget_DataModel()
        self.data_view = ExperimentWidget_DataView()
        
    def run(self):
        self.data_model.build_experiments()
        widget = self.data_view.run(self.data_model.experiments)
        self.data_view.download_button.on_click(self.download_all_files)
        return widget
    
                
    def get_file_list(self,src_path):
        with ftplib.FTP('ncnr.nist.gov') as ftp:
            ftp.login()
            src_path_list = ftp.nlst(src_path)
        return src_path_list
            
    def download_all_files(self,*args):
        
        src_path = self.data_view.grid.grid_data_out['rows'].squeeze().paths
        src_path_list = self.get_file_list(src_path[0])
        dest_path = pathlib.Path(self.data_view.download_loc.value)
        
        paths = []
        for src_path in src_path_list:
            if not ('nxs' in src_path):
                continue
            src = pathlib.Path(src_path)
            paths.append((src,dest_path))
            
        self.data_view.update_progress(0,len(src_path_list))
        with ProcessPoolExecutor(max_workers=5) as executor:
            results = executor.map(download_file,paths)
            for result in results:
                self.data_view.increment_progress()
                
def download_file(paths):
    src,dest = paths
    with ftplib.FTP('ncnr.nist.gov') as ftp:
        ftp.login()
        with open(dest/src.parts[-1],'wb') as f:
            ftp.retrbinary(f'RETR {src}',f.write)
        
        
class ExperimentWidget_DataModel:
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
        
    
    
        
        
        
    
class ExperimentWidget_DataView:
    def increment_progress(self):
        self.update_progress(self.progress.value+1,self.progress.max)
        
    def update_progress(self,i,N):
        self.progress.max = N
        self.progress.value = i
        self.progress_label.value = f'{i}/{N} Downloaded'
        
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
            theme='ag-theme-excel', 
        )
        self.download_button    = ipywidgets.Button(description='DOWNLOAD')
        self.download_loc       = ipywidgets.Text(value='./test/')
        self.progress           = ipywidgets.IntProgress(value=0,min=0,max=10)
        self.progress_label              = ipywidgets.Label(value='')
        
        down_hbox = ipywidgets.HBox([self.download_button,self.download_loc])
        prog_hbox = ipywidgets.HBox([self.progress,self.progress_label])
        vbox = ipywidgets.VBox([self.grid,down_hbox,prog_hbox])
        return vbox
        
    
    
        
        