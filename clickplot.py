import utils
import networkx as nx
import matplotlib.pyplot as plt
from utils import *
from pylab import *

class AnnoteFinder:  # thanks to http://www.scipy.org/Cookbook/Matplotlib/Interactive_Plotting
    """
    callback for matplotlib to visit a node (display an annotation) when points are clicked on.  The
    point which is closest to the click and within xtol and ytol is identified.
    """
    def __init__(self, xdata, ydata, annotes, axis=None, xtol=None, ytol=None, func=None, def_arr=None):
        self.data = list(zip(xdata, ydata, annotes))
        if xtol is None: xtol = ((max(xdata) - min(xdata))/float(len(xdata)))/2
        if ytol is None: ytol = ((max(ydata) - min(ydata))/float(len(ydata)))/2
        self.xtol = xtol
        self.ytol = ytol
        if axis is None: axis = gca()
        self.axis= axis
        self.drawnAnnotations = {}
        self.links = []
        self.func = func
        self.def_arr = def_arr

    def __call__(self, event):
        if event.inaxes:
            clickX = event.xdata
            clickY = event.ydata
            # print(dir(event),event.key)
            if self.axis is None or self.axis==event.inaxes:
                annotes = []
                smallest_x_dist = float('inf')
                smallest_y_dist = float('inf')

                for x,y,a in self.data:
                    if abs(clickX-x)**2 + abs(clickY-y)**2 <= smallest_x_dist**2 + smallest_y_dist**2:
                        smallest_x_dist=abs(clickX-x)
                        smallest_y_dist=abs(clickY-y)
                        _x = x
                        _y = y
                        annote = a
                if annote:
                    self.drawAnnote(event.inaxes, _x, _y, annote)


    def drawAnnote(self, axis, x, y, annote):
        if (x, y) in self.drawnAnnotations:
            markers = self.drawnAnnotations.pop((x, y))
            for m in markers:
                m.set_visible(not m.get_visible())
            self.axis.figure.canvas.draw()
        else:
            t = axis.text(x, y, "%s" % (annote), )
            m = axis.scatter([x], [y], marker='d', c='r', zorder=100)
            self.drawnAnnotations[(x, y)] = (t, m)
            self.func(annote, self.def_arr)
            self.axis.figure.canvas.draw()

