import numpy as np
import lmfit
import pyFAI,pyFAI.azimuthalIntegrator
import matplotlib as mpl
import xarray as xr

def init_integrator():
    SDD = 5.0 # in m
    dx = dy = 0.005 #pixel size in m
    poni1      = 63*dy  #dummy
    poni2      = 63*dx #dummy 
    wavelength = 5*1e-10 #dummy (in m)
    detector = pyFAI.detectors.Detector(dx,dy,max_shape=(128,128))
    
    integrator = pyFAI.azimuthalIntegrator.AzimuthalIntegrator(
                                                 dist=SDD, #meter
                                                 poni1=poni1,
                                                 poni2=poni2,
                                                 wavelength=wavelength, #meters
                                                 detector=detector,
                                            )                   
    return integrator


def init_image_mesh(Nx=128,Ny=128,step=1):
    x = np.arange(0,Nx,step)
    y = np.arange(0,Ny,step)
    X,Y = np.meshgrid(x,y,indexing='xy')
    XY = np.vstack((X.ravel(),Y.ravel())).T
    return x,y,X,Y,XY

def gaussian2D(XY,x0, y0, sig_x, sig_y, A, B):
    x,y = XY.T
    z = A*np.exp(-(((x-x0)/sig_x)**2 + ((y-y0)/sig_y)**2)/2.0) + B
    return z

def init_gaussian2D_lmfit():
    model = lmfit.Model(gaussian2D)
    
    params = lmfit.Parameters()
    params.add('x0', 113.0,min=1,max=128)
    params.add('y0', 63.0,min=1,max=128)
    params.add('sig_x',5.0,min=0.1,max=25)
    params.add('sig_y',5.0,min=0.1,max=25)
    params.add('B',0.0,min=0.0,vary=True)
    params.add('A',5000.0)
    return model,params

def init_gaussian1D_lmfit():
    model = lmfit.models.GaussianModel() + lmfit.models.LinearModel()
    
    params = lmfit.Parameters()
    params.add('amplitude', 20)
    params.add('center', 0.1076)
    params.add('sigma',0.1)
    params.add('slope',0.0, vary=False)
    params.add('intercept',20)
    return model,params

