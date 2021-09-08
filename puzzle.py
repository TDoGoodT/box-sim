from utils import *
from box import Box
from snake import Snake
from option_tree import OptionsTree
class Puzzle:
    def __init__(self, def_arr, starting_option="0"):
        self.box = Box()
        self.snake = Snake(def_arr,starting_option)
        self.tree = OptionsTree()

    def explore_dfs(self):
        longest = 0
        Q = [0, 1, 2, 3]
        op = self.snake.option
        visited = {op: True}
        done = False
        while not done:
            try:
                next_option = op + str(Q.pop(0))
                if next_option not in visited:
                    # print(
                        # f"-I- explore_dfs: trying to go from {op!r} to {next_option!r}"
                    # )
                    self.tree.addEdge(op, next_option)
                    visited[next_option] = True
                    self.snake.build_next_option(next_option[-1])
                    if self.box.validate_snake(self.snake):
                        #print(f"-I- explore_dfs: snake is valid")
                        op = next_option
                        if len(op) > longest:
                            longest = len(op)
                            # print(f"-I- explore_dfs: longest valid sanke is {longest} blocks.")
                            self.snake.plot_snake()
                        Q = [0, 1, 2, 3]
                        if len(op) == 27:
                            print(f"-I- explore_dfs: Done: {op=}")
                            done = True
                    else:
                        #print(f"-I- explore_dfs: Snake is not valid")
                        self.snake.state.pop(-1)
                        self.snake.reset_dir()

            except IndexError as e1:
                #print(f"-D- explore_dfs: catched {e1}")
                Q = [0, 1, 2, 3]
                op = op[:-1]
                try:
                    self.snake.state.pop(-1)
                    self.snake.reset_dir()

                except Exception as e2:
                    print(f"-E- explore_dfs: Snake is not solvable")
                    return

