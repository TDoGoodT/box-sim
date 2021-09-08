from utils import *

class OptionsTree(object):
    def __init__(self):
        self.options = {}
        self.graph = GraphVisualization()
    def addEdge(self, a, b):
        try:
            self.options[a].append(b)
        except KeyError:
            self.options[a] = [b]
        self.graph.addEdge(a,b)
    #TODO: add removeEdge method
    