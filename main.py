import sys

import numpy
from box import Box
def_arr = numpy.array([1,1,1,1,0,1,0,1,1,1,1,1,1,1,1,1,1,1,0,1,0,1,1,1,1])
def main():
    x = Box(def_arr)
    x.solve()
    
if __name__=="__main__":
    sys.exit(main())