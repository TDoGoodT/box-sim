#!/usr/local/bin/python3
import argparse
from utils import *
from snake import Snake
from option_tree import OptionsTree
import os
import matplotlib.pyplot as plt
import imageio
import random as rand
import itertools as itr
class Puzzle:
    next = \
    {
        '0':'1',
        '1':'2',
        '2':'3',
        '3':'0'
    }
    def __init__(self, def_arr, starting_option="0"):
        self.snake = Snake(def_arr,starting_option)
        self.tree = OptionsTree(Snake.plot_option, def_arr)

    @staticmethod
    def visited(visited, x):
        try:
            if visited[x] == True:
                return True
        except KeyError:
            return False

    def explore_bfs(self, depth= 27, validate=True):
        options = ['0']
        new_options = []
        count = 0

        for i in range(1,depth):
            for option in options:
                for j in range(4):
                    new_option = option + str(j)
                    if validate: 
                        self.snake.calc_states(new_option)
                        count += 1
                        if self.snake.check_if_valid():
                            new_options.append(new_option)
                            self.tree.addEdge(option, new_option)
                    elif not validate:
                        new_options.append(new_option)
                        count += 1
                        self.tree.addEdge(option, new_option)
            options = new_options
            new_options = []
        print(f"-I- explore_bfs: done in {count} steps")





    def explore_dfs(self, depth = 27):
        longest = 0
        Q = [0, 1, 2, 3]
        op = self.snake.option[0]
        visited = {op: True}
        done = False
        count = 0
        while not done:
            try:
                next_option = op + str(Q.pop(0))
                if self.visited(visited, next_option):
                    continue
                visited[next_option] = True
                self.snake.build_next_option(next_option[-1])
                count += 1
                if self.snake.check_if_valid():
                    self.tree.addEdge(op, next_option)
                    op = next_option
                    Q = [0, 1, 2, 3]
                    if len(op) >= depth:
                        print(f"-I- explore_dfs: done in {count} steps")
                        done = True
                else:
                    self.snake.pop_last_block()

            except IndexError as e1:
                Q = [0, 1, 2, 3]
                op = op[:-1]
                try:
                    self.snake.pop_last_block()
                    
                except Exception as e2:
                    print(f"-E- explore_dfs: Snake is not solvable")
                    return

    def fold_snake(self, option: str="0"*27,visited=set()):
        assert len(option) == 27
        self.snake.calc_states(option)
        relevant_idx = [i for i in range(27) if self.snake.def_arr[i] == 1]
        count = 0

        while True:
            for i in relevant_idx:
                try:
                    visited.add(option)
                    ranks = [
                                (
                                    option[:i] + Puzzle.next[str(op)]  + option[i+1:],
                                    self.snake.rank_option(option[:i] + Puzzle.next[str(op)] + option[i+1:])
                                )
                                    for op in range(4) if (option[:i] + Puzzle.next[str(op)]  + option[i+1:]) not in visited  or rand.randint(0,3)==0
                            ]
                    # next_option = min([rank for rank in ranks if rank[1] > 0 and rand.randint(0,100) > 50],key=lambda item:item[1])[0]
                    ranks = [rank for rank in ranks if rank[1] != -1 ]
                    # print(ranks)
                    # input()
                    try:
                        next_option = ranks[0][0]
                        _min = ranks[0][1] 
                        for idx, (op, rank) in enumerate(ranks):
                            if rank != -1 and (rank < _min):
                                next_option = op
                            

                    except ValueError:
                        continue
                    except IndexError:
                        continue
                    except TypeError:
                        continue
                    print(f"-I- going from {option} to {next_option}")
                    # assert next_option not in visited
                    count += 1

                    if count % 1000 == 0:
                        self.snake.plot_snake()

                    option = next_option            
                except Exception as e:
                    self.snake.plot_snake()
                    plt.close()
                    raise e
                

    def explore_heuristicly(self):
        op = self.snake.option
        visited = {op: True}
        done = False
        while not done:
            try:
                options = {}
                for x in range(4):
                    next_option = op + str(x)
                    if not self.visited(visited, next_option):
                        self.snake.build_next_option(next_option[-1])
                        options[next_option] = self.snake.rank()
                        self.snake.pop_last_block()
                        
                op = max(options, key=options.get)
                visited[op] = True

            except IndexError as e1:
                Q = [0, 1, 2, 3]
                op = op[:-1]
                try:
                    self.snake.pop_last_block()

                except Exception:
                    print(f"-E- explore_dfs: Snake is not solvable")
                    return



if __name__ == "__main__":


    parser = argparse.ArgumentParser(description='Solve Snake2Box and display solution.')
    parser.add_argument('--algo', metavar='a', type=str, required=True,
                        help='The algorithem to solve with current option [dfs, bfs]')
    parser.add_argument('--depth', metavar='d', type=int, default=27,
                        help='The max depth to traverse')
    parser.add_argument('--viz_snake', default=False, action='store_true',
                        help='Visualize the snake when done.')
    parser.add_argument('--viz_tree', default=False, action='store_true',
                        help='Visualize the traversed tree when done.')

    args = parser.parse_args()
    puz = Puzzle(def_arr)
    if args.algo=='dfs': 
        puz.explore_dfs(args.depth)
    elif args.algo=='bfs':
        puz.explore_bfs(args.depth)
    else:
        raise Exception
    if args.viz_snake: puz.snake.plot_snake()
    if args.viz_tree: puz.tree.plot_graph()
