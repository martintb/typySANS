import numpy as np
import lmfit
import pyFAI,pyFAI.azimuthalIntegrator
import ipywidgets
import plotly.subplots
import plotly.graph_objs as go
import matplotlib as mpl
from scipy.interpolate import interp2d
import xarray as xr

class ImageWidget:
    def __init__(self,img,cmap='viridis',lognorm=True,norm_min=1):
        
        if lognorm:
            self.norm = mpl.colors.LogNorm(norm_min,img.max())
        else:
            self.norm = mpl.colors.Normalize(norm_min,img.max())
            
        self.cmapper = mpl.cm.ScalarMappable(norm=self.norm,cmap=cmap).to_rgba
        self.img = img
        self.z = self.cmapper(img)*256
        self.widget = go.FigureWidget(
            go.Image(z=self.z)
        )
    def run(self):
        return self.widget
    

class InteractiveFit1D:
    def __init__(self,x,y,model,params):
        self.model = model
        self.params = params
        self.output = ipywidgets.Output()
        self.output.layout = ipywidgets.Layout(
            height='300px',
            overflow_y='auto',
            border = '1px solid black',
            
        )
        
        sans_data = go.Scatter(type='scatter',
                            x=x,
                            y=y,
                            mode='markers',
                            name = 'SANS',
                            marker=dict(color='blue',
                                        size=10, 
                                        showscale=False)
                    )
        xfit,yfit =  self.fit(x,y)
        fit_data = go.Scatter(type='scatter',
                      x=xfit,
                      y=yfit,
                      name = 'Gaussian Fit',
                      mode='lines',
                            
                   )
        
        self.widget = go.FigureWidget(data=[sans_data,fit_data], 
                              layout = dict(
                                           #autosize=True,
                                           dragmode='select',
                                           xaxis=dict(zeroline=False),
                                           hovermode='closest')
                                      
                             )
        #
        self.sans_data = self.widget.data[0]
        self.fit_data = self.widget.data[1]
        self.widget.update_layout(legend=dict( yanchor="top", y=0.99, xanchor="left", x=0.01 )) 
        
        #set up callbacks
        self.sans_data.on_selection(self.update_fit)
    
    def run(self):
        vstack = ipywidgets.VBox([self.widget,self.output])
        return vstack
    
    def update_fit(self,trace,points,state):
        inds = points.point_inds
        x = trace['x'][inds]
        y = trace['y'][inds]
        xfit,yfit = self.fit(x,y)
        
        self.fit_data.x = xfit
        self.fit_data.y = yfit
        
    def fit(self,x,y):
        fit1D = self.model.fit(y,x=x,params=self.params)
        yfit  = self.model.eval(x=x,params=fit1D.params)
        self.fit_result = fit1D
        
        self.output.clear_output()
        with self.output:
            print(self.fit_result.fit_report())
        return x,yfit


class InteractiveFit2D:
    def __init__(self,img,model,params):
        self.img = img
        self.model = model
        self.params = params
        self.output = ipywidgets.Output()
        self.output.layout = ipywidgets.Layout(
            height='300px',
            overflow_y='auto',
            border = '1px solid black',
            
        )
        
        self.fit(self.img)
        self.img_fit = self.model.eval(dummy=None,params=self.fit_result.params).reshape(128,-1)
        x0 = self.x0.value
        y0 = self.y0.value
        
        da = xr.DataArray(self.img,dims=['y','x'],coords={'x':x,'y':y})
        da_fit = xr.DataArray(self.img_fit,dims=['y','x'],coords={'x':x,'y':y})
        xslice = da.interp(x=x0).values
        yslice = da.interp(y=y0).values
        xslice_fit = da_fit.interp(x=x0).values
        yslice_fit = da_fit.interp(y=y0).values
        
        
        self.norm = mpl.colors.LogNorm(1,self.img.max())
        self.cmapper = mpl.cm.ScalarMappable(norm=self.norm,cmap='viridis').to_rgba
        self.z = self.cmapper(img)*256
        
        self.widget = go.FigureWidget(
            plotly.subplots.make_subplots(rows=2,cols=2,
                                         shared_xaxes=True,
                                         shared_yaxes=True,
                                         horizontal_spacing=0,
                                         vertical_spacing=0,
                                         )
        )
        self.widget.add_image(z=self.z,row=2,col=1)
        self.widget.add_trace(
            go.Scatter(
                x=x, 
                y=yslice, 
                mode='markers', 
                marker={'color':'blue'},
                name='SANS Slice X'),
            row=1, 
            col=1
        )
        self.widget.add_trace(
            go.Scatter(
                x=x, 
                y=yslice_fit, 
                mode='lines', 
                line={'color':'red'},
                name='Fit X'),
            row=1, 
            col=1
        )
        self.widget.add_trace(
            go.Scatter(
                x=xslice, 
                y=y, 
                mode='markers', 
                marker={'color':'blue'},
                name='SANS Slice Y'),
            row=2, 
            col=2
        )
        self.widget.add_trace(
            go.Scatter(
                x=xslice_fit, 
                y=y, 
                mode='lines', 
                line={'color':'red'},
                name='Fit Y'),
            row=2, 
            col=2
        )
        
        self.widget.add_shape(
            xref='paper',
            x0=0, x1=128, y0=y0, y1=y0,
            line=dict(color='red',dash='dot',width=0.3),
            row=2,col=1,
        )
        self.widget.add_shape(
            yref='paper',
            x0=x0, x1=x0, y0=0, y1=128,
            line=dict(color='red', dash='dot',width=0.3),
            row=2,col=1,
        )
        self.widget.update_layout(
            height=600,
            width=600, 
            legend=dict(
                yanchor="bottom", 
                xanchor="left", 
                y=0.5, 
                x=0.5 )
        ) 
        
        # self.draw_center(nsigmas=[5,10,15])
    
    def run(self):
        vstack = ipywidgets.VBox([self.widget,self.output])
        return vstack
    
    def draw_center(self,nsigmas):
        x0 = self.fit_result.params['x0'].value
        y0 = self.fit_result.params['y0'].value
        sig_x = self.fit_result.params['sig_x']
        sig_y = self.fit_result.params['sig_y']
        for n in nsigmas:
            self.ImageWidget.widget.add_shape(type='circle',
                                  xref='x',
                                  yref='y',
                                  x0=x0-n*sig_x/2.0,
                                  y0=y0-n*sig_y/2.0,
                                  x1=x0+n*sig_x/2.0,
                                  y1=y0+n*sig_y/2.0,
                                  line_color='green',
                                  )
    def update_fit(self,trace,points,state):
        inds = points.point_inds
        x = trace['x'][inds]
        y = trace['y'][inds]
        xfit,yfit = self.fit(x,y)
        
        self.fit_data.x = xfit
        self.fit_data.y = yfit
        
    def fit(self,img):
        fit = self.model.fit(img.ravel(),dummy=None,params=self.params)
        self.fit_result = fit
        self.x0 = fit.params['x0']
        self.y0 = fit.params['y0']
        
        self.output.clear_output()
        with self.output:
            print(self.fit_result.fit_report())
            
class AgBehFitter:
    def __init__(self,df):
        self.df = df
        self.built = False
        self.tab_children = {}
        self.fitter1D = {}
        self.fitter2D = {}
        self.wavelengths = sorted(self.df.wavelength.unique())
        self.check()
        self.model1D,self.param1D = init_gaussian1D_lmfit()
        self.model2D,self.param2D = init_gaussian2D_lmfit()
        self.integrator = init_integrator()
    def check(self):
        for i,(index,sdf) in enumerate(self.df.groupby('wavelength')):
            if not (len(sdf)==2):
                raise ValueError('There should be one transmission and one scattering file for each wavelength.')
    def build_tabs(self):
        if self.built:
            return
        
        for i,(wavelength,sdf) in enumerate(self.df.groupby('wavelength')):
            self.progress.children[0].value = i
            self.progress.children[1].value = f'{i}/{len(self.wavelengths)} Wavelengths Processed'
            
            sdf_trans = sdf.query('transmission==True').squeeze()
            sdf_scatt = sdf.query('transmission==False').squeeze()
            transFitter = InteractiveFit2D(
                    img = sdf_trans.img,
                    model =self.model2D,
                    params=self.param2D
            )
            self.fitter2D[wavelength] = transFitter
            
            self.integrator.set_poni1(
                self.integrator.get_pixel1()*(128-transFitter.y0)
            )
            self.integrator.set_poni2(
                self.integrator.get_pixel2()*transFitter.x0
            )
            self.integrator.set_wavelength(sdf_scatt.wavelength*1e-10)
            self.integrator.set_dist(sdf_scatt.SDD/100.0)
            azim = self.integrator.integrate1d(data=sdf_scatt.img,
                                          unit='q_A^-1',
                                          method='csr_ocl',
                                          correctSolidAngle=True,
                                          npt=500)
            
            azimFitter = InteractiveFit1D(
                    x=azim.radial,
                    y=azim.intensity,
                    model =self.model1D,
                    params=self.param1D)
            self.fitter1D[wavelength] = azimFitter
            
            
            AgBeh2D = ImageWidget(sdf_scatt.img)
            

            self.tab_children[wavelength] = {
                'trans':transFitter,
                'AgBeh2D':AgBeh2D,
                'AgBeh1D':azimFitter
            }
        self.progress.children[0].value = i+1
        self.progress.children[1].value = f'{i+1}/{len(self.wavelengths)} Wavelengths Processed'
        self.built = True
        
    def make_summary(self):
        y = [self.fitter1D[k].fit_result.params['center'].value for k in self.wavelengths]
        yerr = [self.fitter1D[k].fit_result.params['center'].stderr for k in self.wavelengths]
        fig = go.FigureWidget()
        fig.add_scatter(y=y,error_y={'array':yerr})
        
        yval = 0.1076
        fig.add_shape(
            xref='paper',
            x0=0, x1=1, y0=yval, y1=yval,
            line=dict(
                dash='dash'
            )
        )
        
        yval = 0.1076*1.01
        fig.add_shape(
            xref='paper',
            x0=0, x1=1, y0=yval, y1=yval,
            line=dict(
                dash='dot',
                color='red'
            )
        )
        
        yval = 0.1076*0.99
        fig.add_shape(
            xref='paper',
            x0=0, x1=1, y0=yval, y1=yval,
            line=dict(
                dash='dot',
                color='red'
            )
        )

        fig.update_layout(
            xaxis_title = 'Wavelength',
            yaxis_title = 'AgBeh Peak q',
            xaxis=dict(
                tickmode='array',
                tickvals=[i for i,_ in enumerate(self.wavelengths)],
                ticktext=self.wavelengths,
            )
        )
        fig.add_annotation(x=0.5,y=yval,text='1% Error')
        self.summary = fig
        
    def update_summary(self,dummy):
        y = [self.fitter1D[k].fit_result.params['center'].value for k in self.wavelengths]
        yerr = [self.fitter1D[k].fit_result.params['center'].stderr for k in self.wavelengths]
        self.summary.data[0]['y'] = y
        self.summary.data[0]['error_y']['array'] = yerr
        
    def run(self):
        self.progress = ipywidgets.HBox([
            ipywidgets.IntProgress(min=0,max=len(self.wavelengths)),
            ipywidgets.Label(f'0/{len(self.wavelengths)} Wavelengths Processed')
        ])
        display(self.progress)
        self.build_tabs()
        
        tabs = ipywidgets.Tab()
        children = []
        for i,wavelength in enumerate(self.wavelengths):
            sub_tab = ipywidgets.Tab()
            trans = self.tab_children[wavelength]['trans'].run()
            AgBeh1D = self.tab_children[wavelength]['AgBeh1D'].run()
            
            output = ipywidgets.Output(
                layout=ipywidgets.Layout(
                    height='300px', 
                    overflow_y='auto', 
                    border = '1px solid black',
                )
            )
            with output:
                print(self.integrator)
            AgBeh2D = ipywidgets.VBox([self.tab_children[wavelength]['AgBeh2D'].run(),output])
                
            
            sub_tab.children = [trans,AgBeh2D,AgBeh1D]
            sub_tab.set_title(0,'Trans Beam Center')
            sub_tab.set_title(1,'AgBeh 2D')
            sub_tab.set_title(2,'AgBeh 1D')
            children.append(sub_tab)
            tabs.set_title(i,'λ={}'.format(wavelength))
        
        self.make_summary()
        children.append(self.summary)
        tabs.set_title(i+1,'Summary')
        tabs.children = children
        
        button1 = ipywidgets.Button(description='Open Beam Center')
        button2 = ipywidgets.Button(description='Open AgBeh 2D')
        button3 = ipywidgets.Button(description='Open AgBeh 1D')
        button4 = ipywidgets.Button(description='Update Summary')
        
        def select_tab(i):
            for t in tabs.children[:-1]:
                t.selected_index=i
            
        button1.on_click(lambda x: select_tab(0))
        button2.on_click(lambda x: select_tab(1))
        button3.on_click(lambda x: select_tab(2))
        button4.on_click(self.update_summary)
        
        buttons = ipywidgets.HBox([button1,button2,button3,button4])
        vbox = ipywidgets.VBox([buttons,tabs])
        return vbox
