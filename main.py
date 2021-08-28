import sys

import numpy
from box import Box
from box import plot_option

def_arr = numpy.array(
    [0, 1, 1, 1, 1, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 0, 1, 1, 1, 1, 0],int
)


def main():
    x = Box(def_arr)
    body, option = x.solve()
    plot_option(body,option)


if __name__ == "__main__":
    sys.exit(main())
