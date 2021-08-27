import itertools as itr
import numpy as np
from scipy.spatial.transform import Rotation as R
B = {
        'x':np.array([1,0,0]),
        'y':np.array([0,1,0]),
        'z':np.array([0,0,1]),
    }
rots = [0,90,180,270]
class Box:
    def __init__(self, def_arr):
        self.def_arr = def_arr
        self.body = np.array([[0,0,0] for i in range(27)])
        self.solution = None
    
    def validate_options(self, op):
        dir = B['x']
        for idx, x in enumerate(self.def_arr[:len(op)-1], start=1):
            if x == 0:
                self.body[idx] = self.body[idx-1] + dir
                if any([t > 2 for t in self.body[idx]]):
                    return False
            elif x == 1:
                if np.dot(dir,B['x']) == 1:
                    v = B['y']
                elif np.dot(dir,B['y']) == 1:
                    v = B['z']
                elif np.dot(dir,B['z']) == 1:
                    v = B['x']
                
                rotation = rots[op[idx]]
                rotation_radians = np.radians(rotation)

                rotation_vector = rotation_radians * dir
                rotation = R.from_rotvec(rotation_vector)
                dir = np.array([round(x) for x in (rotation.apply(v))])
                self.body[idx] = self.body[idx-1] + dir

                if any([t > 2 for t in self.body[idx]]):
                    return False
        return True

    def solve(self):
        options = [[0],[1],[2],[3]]
        for op_size in range(1,26):
            next_options = []
            for op in options:
                for i in range(4):
                    if self.validate_options(op + [i]):
                        next_options.append(op + [i])
            options = next_options
            print(op_size)
            print(len(options))
            # print(options)
        print(len(options))
        print(options)