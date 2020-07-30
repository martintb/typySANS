import ipywidgets


class ProgressWidget:
    def __init__(self,min=0,max=10):
        self.bar = ipywidgets.IntProgress(value=0,min=min,max=max)
        self.label_str = '{}/{} Downloaded'
        self.label = ipywidgets.Label(value='')
    
    def increment(self):
        self.set(self.bar.value+1,self.bar.max)
        
    def set(self,i,N):
        self.bar.max = N
        self.bar.value = i
        self.label.value = self.label_str.format(i,N)
    
    def run(self):
        hbox = ipywidgets.HBox([self.bar,self.label])
        return hbox