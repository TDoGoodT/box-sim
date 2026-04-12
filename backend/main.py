from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from snake import Snake
from utils import def_arr

app = FastAPI(title="Snake2Box API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SOLUTION = "000120020010310231120202033"

def states_to_json(states):
    return [{"x": int(s[0]), "y": int(s[1]), "z": int(s[2])} for s in states]


@app.get("/snake/{option}")
def get_snake(option: str):
    if len(option) > 27 or not all(c in "0123" for c in option):
        raise HTTPException(status_code=400, detail="Invalid option string")
    snake = Snake(def_arr, option)
    return {
        "option": option,
        "positions": states_to_json(snake.state),
        "valid": snake.check_if_valid(),
        "def_arr": def_arr,
    }


@app.post("/solve")
def solve():
    """Return all 27 steps of the solution, each showing block positions."""
    steps = []
    for i in range(1, len(SOLUTION) + 1):
        partial = SOLUTION[:i]
        snake = Snake(def_arr, partial)
        steps.append({
            "step": i,
            "option": partial,
            "positions": states_to_json(snake.state),
            "valid": snake.check_if_valid(),
        })
    return {
        "solution": SOLUTION,
        "steps": steps,
        "total_steps": len(steps),
        "def_arr": def_arr,
    }


@app.get("/def_arr")
def get_def_arr():
    return {"def_arr": def_arr}
