import numpy as np
import matplotlib.pyplot as plt

import sasmodels.data
import sasmodels.core
import sasmodels.direct_model

from ipywidgets import Dropdown,Button,\
                       HBox,VBox,Tab,\
                       Output,Label,\
                       Text,FloatText,IntText

from ipyfilechooser import FileChooser
from typySANS.misc import for_all_methods


debug_output = Output()
@for_all_methods(debug_output.capture())
class SasViewPlot(object):
    def __init__(self):
        self.Data1D = None
        self.model_info = None
        self.model = None
        self.calculator = None

        self.theory_y = None

    def _update_model(self,event):

        qmin = float(self.qmin.value)
        qmax = float(self.qmax.value)
        numq = int(self.numq.value)
        if (self.Data1D is None) or (self.Data1D.y is None):
            self.Data1D        = sasmodels.data.empty_data1D(np.geomspace(qmin,qmax,numq))
        else: # SANS data is present, can only mask
            mask = np.logical_not((self.Data1D.x>qmin) & (self.Data1D.x<qmax))
            self.Data1D.mask = mask
        self.model_info    = sasmodels.core.load_model_info(self.model_select.value)
        self.model         = sasmodels.core.build_model(self.model_info)
        self.calculator    = sasmodels.direct_model.DirectModel(self.Data1D,self.model)
        
        parms = self.model_info.parameters.common_parameters
        parms += self.model_info.parameters.kernel_parameters
        prev_parms = [i.description for i in self.parameters.children]
        text_list = []
        for parm in parms:
            if parm.id in prev_parms:
                idx = prev_parms.index(parm.id)
                t = self.parameters.children[idx]
            else:
                t = Text(description=parm.id)
                t.value = str(parm.default)
                t.style = {'description_width':'initial'}
                t.on_submit(self._update_plot)
            text_list.append(t)
        self.parameters.children = tuple(text_list)
        
        text_list = []
        defaults = {'_pd':0.0,'_pd_type':'gaussian','_pd_n':'10','_pd_nsigma':3}
        prev_parms = [i.description for i in self.parameters_pd.children]
        for i in self.model_info.parameters.pd_1d:
            for pd in ['_pd','_pd_type','_pd_n','_pd_nsigma']:
                parm_id = i + pd

                if parm_id in prev_parms:
                    idx = prev_parms.index(parm_id)
                    t = self.parameters_pd.children[idx]
                else:
                    t = Text(description=parm_id)
                    t.value = str(defaults[pd])
                    t.style = {'description_width':'initial'}
                    t.on_submit(self._update_plot)
                text_list.append(t)
        self.parameters_pd.children = tuple(text_list)
            
        
        self._update_plot(None)
        
        self.docs.clear_output()
        with self.docs:
            print(self.model_info.docs)
    
    def _update_plot(self,event):
        parms = {}
        parm_list = list(self.parameters.children)
        parm_list += list(self.parameters_pd.children)
        for i in parm_list:
            try:
                parms[i.description] = float(i.value)
            except ValueError:
                parms[i.description] = i.value
            
        self.theory_y = self.calculator(**parms)
        self.theory.set_xdata(self.Data1D.x[~self.Data1D.mask.astype(bool)])
        self.theory.set_ydata(self.theory_y)

        if (self.Data1D is not None) and (self.Data1D.y is not None):
            self.data.set_xdata(self.Data1D.x)
            self.data.set_ydata(self.Data1D.y)
            
        self.ax.relim()
        self.ax.autoscale()
        
    def _load_data(self,event):
        data_path = self.file_chooser.selected
        if data_path is None:
            return

        self.Data1D = sasmodels.data.load_data(data_path)
        self.numq.value = str(self.Data1D.x.shape[0])
        self.numq.disabled = True

        self._update_model(None)
        
    def _init_widget(self):

        self.model_select = Dropdown(options = sasmodels.core.list_models())
        self.model_select.value = 'sphere'
        self.model_select.observe(self._update_model,names='value')
        
        self.qmin = Text(description='qmin',value='0.001')
        self.qmax = Text(description='qmax',value='0.5')
        self.numq = Text(description='numq',value='150')
        self.qrange = VBox([self.qmin,self.qmax,self.numq])
        for i in (self.qmin,self.qmax,self.numq):
            i.on_submit(self._update_model)
        
        self.file_chooser = FileChooser()
        self.load_data = Button(description='Load Data')
        self.load_data.on_click(self._load_data)

        self.parameters = VBox([])
        self.parameters_pd = VBox([])
        self.docs = Output()
        
        self.tabs = Tab([self.parameters,self.parameters_pd,self.qrange,VBox([self.file_chooser,self.load_data]),self.docs])
        self.tabs.set_title(0,'Model Params')
        self.tabs.set_title(1,'Dispersity')
        self.tabs.set_title(2,'Q-Range')
        self.tabs.set_title(3,'Load Data')
        self.tabs.set_title(4,'Documentation')
        self.tabs.layout = {'height':'300px','width':'600px'}
        
        self.output = Output()
        
        widget = VBox([self.model_select,self.tabs,self.output,debug_output])
        return widget
    
    def _init_plot(self):
        self.fig = plt.figure(0)
        self.fig.set_figwidth(6)
        self.fig.set_figheight(3)
        self.fig.clear()
        if not self.fig.get_axes():
            self.ax = self.fig.add_subplot(111)
        else:
            self.ax = self.fig.get_axes()[0]
        
        
        self.data = plt.Line2D([0.001,0.5],[np.nan,np.nan])
        self.data.set_marker('.')
        self.data.set_linestyle('None')
        self.ax.add_line(self.data)
        
        self.theory = plt.Line2D([0.001,0.5],[np.nan,np.nan])
        self.data.set_color('red')
        self.ax.add_line(self.theory)
        
        self.ax.set(xlim=(0.001,0.5),xscale='log',yscale='log')
        self.ax.set_ylabel('dΣ/dΩ [$cm^{-1}$]')
        self.ax.set_xlabel('q [$Å^{-1}$]')
    
    def run_widget(self):
        self._init_plot()
        widget = self._init_widget()
        widget.children = tuple([self.fig.canvas] + list(widget.children))
        # widget = HBox([self.fig.canvas,widget])
        self._update_model(None)
        
        return widget
