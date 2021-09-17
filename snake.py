import itertools 
from utils import *

B = {
    "x": np.array([1, 0, 0], int),
    "y": np.array([0, 1, 0], int),
    "z": np.array([0, 0, 1], int),
}

rots = {"0": 0, "1": 90, "2": 180, "3": 270}


class Snake(object):

    class CollidingBlocks(Exception):
        pass


    def __init__(self, def_arr, option="0"):
        self.def_arr = def_arr
        self.option = option
        self.dir = B["x"]
        self.state = []
        self.state, _ = self.calc_states(option)
        #print(f"-I- Initial state: {self.state}")


    def pop_last_block(self):
        self.state.pop(-1)
        self.reset_dir()
    
    @staticmethod
    def plot_option(option : str, def_arr: str):
        for i in plt.get_fignums()[1:]:
            plt.close(i)
        Snake(def_arr,option).plot_snake()


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

    def save_snake_img(self,fname,dpi):

        fig = plt.figure()
        ax = plt.axes(projection="3d")

        # Data for a three-dimensional line
        xline = [state[0] for state in self.state]
        yline = [state[1] for state in self.state]
        zline = [state[2] for state in self.state]
        ax.plot3D(xline, yline, zline, "gray")
        ax.scatter3D(xline, yline, zline, "black", marker="s")
        plt.savefig(fname,dpi=dpi)
        plt.close()

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
    def dist_from_init(block):
        # print(f"-I- calcing distance from {type(block)}:{block} to init")
        if all(block == np.array([0,0,0],int)):
            return 0
        return np.linalg.norm(np.array([0,0,0],int)-block)

    def rank_option(self, option):
        self.calc_states(option)
        return self.rank()

    def bbox_vol(self):
        max_x=max_y=max_z=0
        min_x=min_y=min_z=None
        for state in self.state:
            if max_x < state[0]:
                max_x = state[0]
            if not min_x or min_x > state[0]:
                min_x = state[0]

            if max_y < state[1]:
                max_y = state[1]
            if not min_y or min_y > state[1]:
                min_y = state[1]

            if max_z < state[2]:
                max_z = state[2]
            if not min_z or min_z > state[2]:
                min_z = state[2]
            
            
        return (max_x-min_x)*(max_y-min_y)*(max_z-min_z)

    def density(self):
        body = np.zeros((27, 27, 27),int)
        score = 0
        for state in self.state:
            body[tuple(state)] = 1
        for state in itertools.product(range(3,27),repeat=3):
            score += sum(state) * body[tuple(state)] 
        return score
        
    def rank(self):
        if not self.check_if_colliding():
            rank = -1
        else:
            rank = self.density()
            # rank = self.bbox_vol()
        if self.check_if_valid():
            raise Exception("Success")
        # return sum([self.dist_from_init(block) for block in self.state])
        # print(f"-I- {rank} ")
        return rank
        
        
    def check_if_colliding(self) -> bool:
        body = np.zeros((27, 27, 27), int)
        for idx, state in enumerate(self.state, start=1):
            # print(f"-I- {state=}")
            if any([x < 0 for x in state]) or int(body[tuple(state)]) != 0:
                print(f"-I- validation failed skipping")
                return False
            else:
                body[tuple(state)] = idx
        return True

    
    def check_if_valid(self) -> bool:
        body = np.zeros((27, 27, 27), int)
        for idx, state in enumerate(self.state, start=1):
            if any([(x < 0 or x > 2) for x in state]):
                return False
            elif int(body[tuple(state)]) != 0:
                return False
            else:
                body[tuple(state)] = idx
        return True


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
        if not self.option:
            self.option = option
        else:
            self.option += option

        try:
            if self.def_arr[len(self.state)-1] == 1:
                self.rotate_dir(self.get_perpendicular_dir(), rots[option])
            self.state.append(self.state[-1] + self.dir)

        except IndexError:
            block = np.array([0, 0, 0], int)
            self.state.append(block)

    def calc_states(self, option: str) -> list:
        self.option = option
        self.state = []
        self.reset_dir()
        for op in option:
            self.build_next_option(op)
        return self.state.copy(), self.dir
