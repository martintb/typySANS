if __name__ == '__main__':
  from lib import *
  import ipdb; ist = ipdb.set_trace
  import numpy as np
  
  fpath = '../nSoftData/Snyder/June 30/SCPOL018.SA4_CRS_E692'
  nfile = NCNRFile(fpath)
  nfile.readFile()
  nfile.readHeader()
  nfile.printHeader()
  nfile.readDetector()
  
  rawDet = nfile['rawCounts']
  
   
  import matplotlib.pyplot as plt
  import matplotlib.colors as mplcolors
  plt.figure()
  plt.imshow(rawDet)
  plt.figure()
  plt.imshow(rawDet,norm=mplcolors.LogNorm(vmin=0.01,vmax=rawDet.max()))
  plt.show()
