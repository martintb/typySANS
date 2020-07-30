import ftplib
import threading
import queue
import pathlib
from concurrent.futures import ProcessPoolExecutor

# needs to be free function
def download_file(paths,url='ncnr.nist.gov'):
    src_path,dest_path = paths
    filename = src_path.parts[-1] #assumed src_path is a pathlib.Path object!
    with ftplib.FTP(url) as ftp:
        ftp.login()
        with open(dest_path/filename,'wb') as f:
            ftp.retrbinary(f'RETR {str(src_path)}',f.write)
            
class FTP:
    def __init__(self,url='ncnr.nist.gov'):
        self.url = url
        self.executor = None
            
    def stop(self,*args):#*args makes this callable
        if self.executor is not None:
            self.executor.shutdown(wait=False)
            self.executor = None
            
    def get_file_list(self,src_path):
        with ftplib.FTP(self.url) as ftp:
            ftp.login()
            src_path_list = ftp.nlst(str(src_path))
        return src_path_list
                
    def download_all_files(self,src_path,dest_path,select_key='nxs',progress=None):
        src_paths = self.get_file_list(src_path)
        self.download_filelist(src_paths,dest_path,select_key,progress)
        
    def download_filelist(self,src_paths,dest_path,select_key='nxs',progress=None):
        dest_path = pathlib.Path(dest_path)
        paths = []
        for src_path in src_paths:
            if not (select_key in str(src_path)):
                continue
            src_path = pathlib.Path(src_path)
            paths.append((src_path,dest_path))
            
        if progress is not None:
            progress.set(0,len(paths))
            
        if self.executor is None:
            self.executor =  ProcessPoolExecutor(max_workers=5)
            
        for result in self.executor.map(download_file,paths):
            if progress is not None:
                progress.increment()