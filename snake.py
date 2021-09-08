from utils import *

B = {
    "x": np.array([1, 0, 0], int),
    "y": np.array([0, 1, 0], int),
    "z": np.array([0, 0, 1], int),
}

rots = {"0": 0, "1": 90, "2": 180, "3": 270}


class Snake(object):
    def __init__(self, def_arr, option="0"):
        self.def_arr = def_arr
        self.option = option
        self.dir = B["x"]
        self.state = []
        self.state, _ = self.calc_states(option)
        #print(f"-I- Initial state: {self.state}")

    def plot_snake(self):

        fig = plt.figure()
        ax = plt.axes(projection="3d")

        # Data for a three-dimensional line
        xline = [state[0] for state in self.state]
        yline = [state[1] for state in self.state]
        zline = [state[2] for state in self.state]
        ax.plot3D(xline, yline, zline, "gray")
        ax.scatter3D(xline, yline, zline, "black", marker="s")
        plt.show()

    def get_perpendicular_dir(self):
        if abs(np.dot(self.dir, B["x"])) == 1:
            v = B["y"]
        elif abs(np.dot(self.dir, B["y"])) == 1:
            v = B["z"]
        elif abs(np.dot(self.dir, B["z"])) == 1:
            v = B["x"]
        else:
            assert False
        return v

    def reset_dir(self):
        try:
            self.dir = self.state[-1] - self.state[-2]
        except IndexError as e:
            #print(f"-D- reset_dir: catched {e}")
            self.dir = B["x"]
        #print(f"-D- reset_dir: new direction is {self.dir}")
        

    def rotate_dir(self, rotation_axis, rotation):
        self.dir = self.rotate_v(rotation_axis, self.dir, rotation)
        return

    @staticmethod
    def rotate_v(v, rotation_axis, rotation):
        #print(f"-D- rotate_v: {v=},{rotation_axis=},{rotation=}")
        if rotation != 0:
            rotation_radians = np.radians(rotation)
            rotation_vector = rotation_radians * rotation_axis
            rotation = R.from_rotvec(rotation_vector)
            v = np.array([round(x) for x in (rotation.apply(v))], int)
        #print(f"-D- rotate_v: result: {v=}")
        return v

    def build_next_option(self, option):
        x = self.def_arr[len(self.state)-1]
        #print(f"-D- build_next_option: {x=}")

        try:
            if x == 0:
                self.state.append(self.state[-1] + self.dir)
            elif x == 1:
                self.rotate_dir(self.get_perpendicular_dir(), rots[option])
                self.state.append(self.state[-1] + self.dir)
            #print(f"-D- build_next_option: {self.state=}")
        except IndexError:
            block = np.array([0, 0, 0], int)
            print(f"-W- build_next_option: Placing first block at {block}")
            self.state.append(block)

    def calc_states(self, options: str) -> list:
        self.state = []
        for op in options:
            self.build_next_option(op)
        return self.state.copy(), self.dir
