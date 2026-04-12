from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import sys, os, logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from snake import Snake
from utils import def_arr

logger = logging.getLogger("snake2box")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Snake2Box API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── DFS solver — runs once at startup ───────────────────────

def solve_dfs(def_arr, depth=27):
    """Depth-first search through rotation space. Returns solution option string."""
    snake = Snake(def_arr, "0")
    op = "0"
    visited = {op: True}
    Q = [0, 1, 2, 3]
    count = 0

    while count < 2_000_000:
        try:
            next_dir = Q.pop(0)
            next_option = op + str(next_dir)
            if visited.get(next_option):
                continue
            visited[next_option] = True
            snake.build_next_option(str(next_dir))
            count += 1
            if snake.check_if_valid():
                # Valid = all 27 blocks within [0,2]^3, no overlaps
                op = next_option
                Q = [0, 1, 2, 3]
                if len(op) >= depth:
                    logger.info(f"DFS solved in {count} iterations, solution={op}")
                    return op, snake
            else:
                snake.pop_last_block()
        except IndexError:
            # Dead end — backtrack
            Q = [0, 1, 2, 3]
            if len(op) <= 1:
                raise RuntimeError("Puzzle has no solution")
            op = op[:-1]
            try:
                snake.pop_last_block()
            except Exception:
                raise RuntimeError("Puzzle has no solution")

    raise RuntimeError(f"DFS exceeded iteration limit ({count})")


logger.info("Running DFS solver at startup...")
_solution_option, _solution_snake = solve_dfs(def_arr)
logger.info(f"Solution found: {_solution_option}")


def states_to_json(states):
    return [{"x": int(s[0]), "y": int(s[1]), "z": int(s[2])} for s in states]


# ── API routes ───────────────────────────────────────────────

@app.get("/api/snake/{option}")
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


@app.post("/api/solve")
def solve():
    """Return all 27 steps of the DFS solution."""
    steps = []
    for i in range(1, len(_solution_option) + 1):
        partial = _solution_option[:i]
        snake = Snake(def_arr, partial)
        steps.append({
            "step": i,
            "option": partial,
            "positions": states_to_json(snake.state),
            "valid": snake.check_if_valid(),
        })
    return {
        "solution": _solution_option,
        "steps": steps,
        "total_steps": len(steps),
        "def_arr": def_arr,
        "algo": "dfs",
    }


@app.get("/api/def_arr")
def get_def_arr():
    return {"def_arr": def_arr}


# ── Serve React frontend ─────────────────────────────────────

DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")

if os.path.isdir(DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(DIST, "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        return FileResponse(os.path.join(DIST, "index.html"))
