import matplotlib
from mpl_toolkits import mplot3d
import matplotlib.pyplot as plt
import itertools as itr
import numpy as np
from scipy.spatial.transform import Rotation as R
from tqdm import tqdm
import matplotlib.pyplot as plt
from subprocess import call


B = {
    "x": np.array([1, 0, 0]),
    "y": np.array([0, 1, 0]),
    "z": np.array([0, 0, 1]),
}
rots = [0, 90, 180, 270]


def plot_option(body, op):
    fig = plt.figure()
    ax = plt.axes(projection="3d")

    # Data for a three-dimensional line
    xline = body[: len(op), 0]
    yline = body[: len(op), 1]
    zline = body[: len(op), 2]
    ax.plot3D(xline, yline, zline, "gray")
    ax.scatter3D(xline, yline, zline, "black", marker="s")
    plt.show()


class Box:
    def __init__(self, def_arr):
        self.def_arr = def_arr
        self.body = np.array([[0, 0, 0] for i in range(27)])
        self.solution = None
        self.body_db = {}
        self.dir_db = {}

    def plot_init(self):
        op = np.zeros(27, int)
        self.build_body(op)
        plot_option(self.body, op)
        return

    def build_body(self, op):
        dir = B["x"]
        for idx, x in enumerate(self.def_arr):
            if x == 0:
                self.body[idx] = self.body[idx - 1] + dir
                if any([t > 2 or t < 0 for t in self.body[idx]]):
                    raise Exception("Error")

                for cell in self.body[:idx]:
                    if all(x == y for (x, y) in zip(cell, self.body[idx])):
                        raise Exception("Error")

            elif x == 1:
                if abs(np.dot(dir, B["x"])) == 1:
                    v = B["y"]
                elif abs(np.dot(dir, B["y"])) == 1:
                    v = B["z"]
                elif abs(np.dot(dir, B["z"])) == 1:
                    v = B["x"]
                rotation = rots[op[idx]]
                rotation_radians = np.radians(rotation)
                rotation_vector = rotation_radians * dir
                rotation = R.from_rotvec(rotation_vector)
                dir = np.array([round(x) for x in (rotation.apply(v))])
                self.body[idx] = self.body[idx - 1] + dir
                if any([t > 2 or t < 0 for t in self.body[idx]]):
                    raise Exception("Error")

                for cell in self.body[:idx]:
                    if all(x == y for (x, y) in zip(cell, self.body[idx])):
                        raise Exception("Error")

                return self.body.copy(), dir

    def validate_option(self, op):
        if len(op) <= 2:
            try:
                body, dir = self.build_body(op)
                self.body_db[str(op)] = body.copy()
                self.dir_db[str(op)] = dir
                return True
            except Exception:
                return False
        elif len(op) > 2:
            dir = self.dir_db[str(op[:-1])]
            self.body = self.body_db[str(op[:-1])].copy()
            x = self.def_arr[len(op) - 1]
            idx = len(op) - 1
            try:
                body, dir = self.build_next_step(x, idx, dir, op)
                self.body_db[str(op)] = body.copy()
                self.dir_db[str(op)] = dir
                return True
            except Exception:
                return False

    def build_next_step(self, x, idx, dir, op):
        if x == 0:
            self.body[idx] = self.body[idx - 1] + dir
            if any([t > 2 or t < 0 for t in self.body[idx]]):
                raise Exception("Error")
            for cell in self.body[:idx]:
                if all(x == y for (x, y) in zip(cell, self.body[idx])):
                    raise Exception("Error")
        elif x == 1:
            if abs(np.dot(dir, B["x"])) == 1:
                v = B["y"]
            elif abs(np.dot(dir, B["y"])) == 1:
                v = B["z"]
            elif abs(np.dot(dir, B["z"])) == 1:
                v = B["x"]

            rotation = rots[op[idx]]
            rotation_radians = np.radians(rotation)
            rotation_vector = rotation_radians * dir
            rotation = R.from_rotvec(rotation_vector)
            dir = np.array([round(x) for x in (rotation.apply(v))])
            self.body[idx] = self.body[idx - 1] + dir

            if any([t > 2 or t < 0 for t in self.body[idx]]):
                raise Exception("Error")

            for cell in self.body[:idx]:
                if all(x == y for (x, y) in zip(cell, self.body[idx])):
                    raise Exception("Error")
        return self.body.copy(), dir

    def solve(self):
        # self.plot_init()
        options = [[0]]
        for _ in range(1, 27):
            next_options = []
            call("clear")
            print(len(options[0]))
            for op in tqdm(options):
                for i in range(4):
                    if self.validate_option(op + [i]):
                        next_options.append(op + [i])
            options = next_options
            if len(op) > 2:
                try:
                    op = options[0]
                except Exception:
                    break
                print(len(op) + 1)
        try:
            op = options[0]
        except Exception:
            return
        return self.body_db[str(op)], op