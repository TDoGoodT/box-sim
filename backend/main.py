from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
import sys, os, json, asyncio, logging

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


def states_to_json(states):
    return [{"x": int(s[0]), "y": int(s[1]), "z": int(s[2])} for s in states]


async def dfs_stream(def_arr, depth=27):
    """
    DFS solver that yields partial states as it finds valid positions.
    Yields dicts: {step, option, positions, valid, done, iterations}
    """
    snake = Snake(def_arr, "0")
    op = "0"
    visited = {op: True}
    Q = [0, 1, 2, 3]
    count = 0
    current_depth = 1

    # Yield initial state
    yield {"step": 1, "option": op, "positions": states_to_json(snake.state),
           "valid": snake.check_if_valid(), "done": False, "iterations": 0}

    while count < 2_000_000:
        # Yield control to event loop occasionally so SSE can flush
        if count % 500 == 0:
            await asyncio.sleep(0)

        try:
            next_dir = Q.pop(0)
            next_option = op + str(next_dir)
            if visited.get(next_option):
                continue
            visited[next_option] = True
            snake.build_next_option(str(next_dir))
            count += 1

            if snake.check_if_valid():
                op = next_option
                Q = [0, 1, 2, 3]
                new_depth = len(op)

                # Yield every time we place a new block (go deeper)
                yield {
                    "step": new_depth,
                    "option": op,
                    "positions": states_to_json(snake.state),
                    "valid": snake.check_if_valid(),
                    "done": new_depth >= depth,
                    "iterations": count,
                }

                if new_depth >= depth:
                    logger.info(f"DFS solved in {count} iterations, solution={op}")
                    return
            else:
                snake.pop_last_block()

        except IndexError:
            # Backtrack
            Q = [0, 1, 2, 3]
            if len(op) <= 1:
                yield {"error": "No solution found", "done": True, "iterations": count}
                return
            op = op[:-1]
            try:
                snake.pop_last_block()
            except Exception:
                yield {"error": "No solution found", "done": True, "iterations": count}
                return


# ── API routes ───────────────────────────────────────────────

@app.get("/api/solve/stream")
async def solve_stream():
    """SSE endpoint — streams DFS progress as blocks are placed."""
    async def event_gen():
        async for state in dfs_stream(def_arr):
            yield {"data": json.dumps(state)}

    return EventSourceResponse(event_gen())


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
