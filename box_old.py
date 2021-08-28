import itertools as itr
import numpy as np
from scipy.spatial.transform import Rotation as R

B = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
rots = [0, 90, 180, 270]


class Box:
    def __init__(self, def_arr):
        self.def_arr = def_arr
        self.body = np.array([[0, 0, 0] for i in range(27)])
        self.solution = None

    def solve(self):
        c = 0
        options = itr.product([0, 1, 2, 3], repeat=25)
        for op in options:
            dir = np.array([1, 0, 0])
            for idx, x in enumerate(self.def_arr, start=1):
                if x == 0:
                    self.body[idx] = self.body[idx - 1] + dir
                    if any([t > 2 for t in self.body[idx]]):
                        c += 1
                        print(f"Bad {c}")
                        break
                elif x == 1:
                    for v in B:
                        if np.dot(dir, v) == 0:
                            break
                    rotation = op[idx]
                    rotation_radians = np.radians(rotation)
                    rotation_axis = dir

                    rotation_vector = rotation_radians * rotation_axis
                    rotation = R.from_rotvec(rotation_vector)
                    dir = rotation.apply(v)
                    self.body[idx] = self.body[idx - 1] + dir

                    if any([t > 2 for t in self.body[idx]]):
                        c += 1
                        print(f"Bad {c}")
                        break
        print(self.body)
        return
