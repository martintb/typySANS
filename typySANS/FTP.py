import ftplib
import threading
import queue
import pathlib
from concurrent.futures import ProcessPoolExecutor

def download_file(paths,url='ncnr.nist.gov'):
    src_path,dest_path = paths
    filename = src_path.parts[-1] #assumed src_path is a pathlib.Path object!
    with ftplib.FTP(url) as ftp:
        ftp.login()
        with open(dest_path/filename,'wb') as f:
            ftp.retrbinary(f'RETR {str(src_path)}',f.write)
            
def get_file_list(src_path,url='ncnr.nist.gov'):
    with ftplib.FTP(url) as ftp:
        ftp.login()
        src_path_list = ftp.nlst(str(src_path))
    return src_path_list
            
def download_all_files(src_path,dest_path,select_key='nxs',progress=None):
    
    src_path_list = get_file_list(src_path)
    
    dest_path = pathlib.Path(dest_path)
    paths = []
    for src_path in get_file_list(src_path):
        if not (select_key in src_path):
            continue
        src_path = pathlib.Path(src_path)
        paths.append((src_path,dest_path))
        
    if progress is not None:
        progress.set(0,len(paths))
        
    with ProcessPoolExecutor(max_workers=5) as executor:
        results = executor.map(download_file,paths)
        for result in results:
            if progress is not None:
                progress.increment()