import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
from scipy.spatial.transform import Rotation as R

def get_full_states_tree(depth):
    G = GraphVisualization()
    options = ['0']
    new_options = []

    for i in range(1,depth-1):
        for option in options:
            for j in range(4):
                new_option = option + str(j)
                new_options.append(new_option)
                G.addEdge(option, new_option)
                # print(option +","+ new_option)

        options = new_options
        new_options = []
    for option in options:
            new_option = option + str(0)
            new_options.append(new_option)
            G.addEdge(option, new_option)
            # print(option +","+ new_option)


    return G

# Defining a Class
class GraphVisualization:
   
    def __init__(self,arr=[]):
          
        # visual is a list which stores all 
        # the set of edges that constitutes a
        # graph
        self.visual = []
        for x in arr:
            self.visual.append(x)
        self.G = nx.Graph()
        
          
    # addEdge function inputs the vertices of an
    # edge and appends it to the visual list
    def addEdge(self, a, b):
        temp = [a, b]
        self.visual.append(temp)
        self.G.add_edges_from([temp])

          
    # In visualize function G is an object of
    # class Graph given by networkx G.add_edges_from(visual)
    # creates a graph with a given list
    # nx.draw_networkx(G) - plots the graph
    # plt.show() - displays the graph
    def visualize(self):
        nx.draw_networkx(self.G,pos=nx.kamada_kawai_layout(self.G),node_size=10,with_labels=False)
        plt.show()

# G = get_full_states_tree(5)
# G.visualize()