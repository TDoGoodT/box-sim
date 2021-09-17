import pandas as pd
import utils
import networkx as nx
import matplotlib.pyplot as plt
from clickplot import AnnoteFinder
from pylab import *


class OptionsTree(object):
    colors = [
        "black",
        "red",
        "blue",
        "green",
        "gold",
        "violet",
        "aqua",
        "blue",
        "pink",
        "purple",
        "indigo",
        "pink",
        "gold",
        "peru",
        "navy",
        "blue",
        "purple",
        "aqua",
        "blue",
        "pink",
        "purple",
        "indigo",
        "pink",
        "indigo",
        "pink",
        "gold",
        "peru",
        "navy",
        "blue",
        "purple",
    ]

    def __init__(self, plot_option_func=None, def_arr=None):
        self.DB = pd.DataFrame({"source":[],"target":[],"color":[]})
        self.plot_option_func = plot_option_func
        self.def_arr = def_arr

    def addEdge(self, a, b):
        self.DB = self.DB.append({"source":a,"target":b,"color":self.colors[len(a)]}, ignore_index=True)
        
    def plot_graph(self,name=""):
        G = nx.from_pandas_edgelist(self.DB, 'source', 'target')#, edge_attr=True)
        pos = nx.kamada_kawai_layout(G)
        x, y, annotes = [], [], []
        for key in pos:
            d = pos[key]
            annotes.append(key)
            x.append(d[0])
            y.append(d[1])
        fig = plt.figure(figsize=(10,10))
        ax = fig.add_subplot(111)
        ax.set_title(name) # 'Valid Options Tree')
        # print(self.DB.color[:-1])
        # input()
        nx.draw(G, pos, font_size=6,width=1,#edge_color=self.DB.color,#, edge_color='#BB0000', 
                        node_size=4, with_labels=False)


        af = AnnoteFinder(x, y, annotes, func=self.plot_option_func, def_arr=self.def_arr)
        connect('button_press_event', af)

        show()
