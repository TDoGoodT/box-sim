from utils import *
import numpy as np

class Box(object):
    def __init__(self):
        self.body = np.zeros((3, 3, 3), int)

    def validate_snake(self, snake) -> bool:
        self.body = np.zeros((3, 3, 3), int)
        for idx, state in enumerate(snake.state, start=1):
            if any([(x < 0 or x > 2) for x in state]):
                self.body = np.zeros((3, 3, 3), int)
                # print(f"-I- validate_snake: state is not valid.")
                #print(f"-D- validate_snake: {snake.state=}.")
                #print(f"-D- validate_snake: {[(x < 0 or x > 2) for x in state]=}, {idx=}")
                return False
            elif int(self.body[tuple(state)]) != 0:
                # print(f"-I- validate_snake: state is not valid.")
                #print(f"-D- validate_snake: {snake.state=}.")
                #print(
                #     f"-I- validate_snake: {state=}\n-I- validate_snake: {self.body[tuple(state)]=}\n-I- validate_snake: {idx=}"
                # )
                self.body = np.zeros((3, 3, 3), int)
                return False
            else:
                self.body[tuple(state)] = idx
        return True

