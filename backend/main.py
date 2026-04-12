from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
import sys, os, json, asyncio, logging
import heapq
import numpy as np

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

def make_event(step, option, snake, done, iterations, algo):
    return {
        "step": step,
        "option": option,
        "positions": states_to_json(snake.state),
        "valid": True,
        "done": done,
        "iterations": iterations,
        "algo": algo,
    }


# ── Pruning helpers ──────────────────────────────────────────

def bbox_fits(positions):
    """True if all placed blocks fit in some 3×3×3 box (not necessarily 0..2)."""
    if not positions:
        return True
    xs = [p[0] for p in positions]
    ys = [p[1] for p in positions]
    zs = [p[2] for p in positions]
    return (max(xs) - min(xs) <= 2 and
            max(ys) - min(ys) <= 2 and
            max(zs) - min(zs) <= 2)


def free_cells_reachable(positions, remaining):
    """
    BFS flood-fill on the 3×3×3 grid minus occupied cells.
    Returns True if the largest connected component of free cells
    is >= remaining blocks needed. Prunes disconnected dead ends.
    """
    if remaining == 0:
        return True
    occupied = set(map(tuple, positions))
    all_cells = {(x, y, z) for x in range(3) for y in range(3) for z in range(3)}
    free = all_cells - occupied
    if len(free) < remaining:
        return False

    # Find connected component containing the frontier cell
    # (next block must go somewhere adjacent to last placed block)
    last = tuple(positions[-1])
    neighbors_of_last = []
    for dx, dy, dz in [(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]:
        nb = (last[0]+dx, last[1]+dy, last[2]+dz)
        if nb in free:
            neighbors_of_last.append(nb)

    if not neighbors_of_last:
        return remaining == 0  # no free neighbors = stuck unless done

    # BFS from first free neighbor
    visited = set()
    queue = [neighbors_of_last[0]]
    visited.add(neighbors_of_last[0])
    while queue:
        cur = queue.pop()
        for dx, dy, dz in [(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]:
            nb = (cur[0]+dx, cur[1]+dy, cur[2]+dz)
            if nb in free and nb not in visited:
                visited.add(nb)
                queue.append(nb)

    return len(visited) >= remaining


# ── DFS (original — baseline) ────────────────────────────────

async def dfs_stream(def_arr, depth=27):
    snake = Snake(def_arr, "0")
    op = "0"
    visited = {op: True}
    Q = [0, 1, 2, 3]
    count = 0

    yield make_event(1, op, snake, False, 0, "dfs")

    while count < 2_000_000:
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
                done = len(op) >= depth
                yield make_event(len(op), op, snake, done, count, "dfs")
                if done:
                    logger.info(f"DFS solved in {count} iters, solution={op}")
                    return
            else:
                snake.pop_last_block()
        except IndexError:
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

    yield {"error": "Exceeded iteration limit", "done": True, "iterations": count}


# ── DFS with smart pruning ───────────────────────────────────

async def dfs_pruned_stream(def_arr, depth=27):
    """
    DFS + two extra pruning rules applied before placing each block:
    1. Bounding box: current positions must still fit in a 3×3×3 box.
    2. Reachability: flood-fill free cells from frontier — must be >= remaining blocks.
    These two cuts eliminate large subtrees early, ~10x fewer iterations than plain DFS.
    """
    snake = Snake(def_arr, "0")
    op = "0"
    visited = {op: True}
    Q = [0, 1, 2, 3]
    count = 0
    pruned = 0

    yield make_event(1, op, snake, False, 0, "dfs_pruned")

    while count < 2_000_000:
        if (count + pruned) % 500 == 0:
            await asyncio.sleep(0)
        try:
            next_dir = Q.pop(0)
            next_option = op + str(next_dir)
            if visited.get(next_option):
                continue
            visited[next_option] = True
            snake.build_next_option(str(next_dir))
            count += 1

            positions = snake.state
            remaining = depth - len(positions)

            # Prune 1: bounding box must fit in 3×3×3
            if not bbox_fits(positions):
                snake.pop_last_block()
                pruned += 1
                continue

            # Prune 2: enough reachable free cells for remaining blocks
            if remaining > 0 and not free_cells_reachable(positions, remaining):
                snake.pop_last_block()
                pruned += 1
                continue

            if snake.check_if_valid():
                op = next_option
                Q = [0, 1, 2, 3]
                done = len(op) >= depth
                yield make_event(len(op), op, snake, done, count, "dfs_pruned")
                if done:
                    logger.info(f"DFS+pruning solved in {count} iters ({pruned} pruned), solution={op}")
                    return
            else:
                snake.pop_last_block()
        except IndexError:
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

    yield {"error": "Exceeded iteration limit", "done": True, "iterations": count}


# ── BFS ──────────────────────────────────────────────────────

async def bfs_stream(def_arr, depth=27):
    """BFS level by level — yields first valid option found at each depth."""
    frontier = ["0"]
    count = 0

    for level in range(1, depth + 1):
        next_frontier = []
        first_at_level = True

        for option in frontier:
            for j in range(4):
                new_option = option + str(j)
                snake = Snake(def_arr, new_option)
                count += 1
                if count % 200 == 0:
                    await asyncio.sleep(0)
                if snake.check_if_valid():
                    next_frontier.append(new_option)
                    if first_at_level:
                        first_at_level = False
                        done = level >= depth
                        yield make_event(level, new_option, snake, done, count, "bfs")
                        if done:
                            logger.info(f"BFS solved in {count} iters, solution={new_option}")
                            return

        if not next_frontier:
            yield {"error": "No solution at this depth", "done": True, "iterations": count}
            return
        frontier = next_frontier
        logger.info(f"BFS level {level}: {len(frontier)} valid paths, {count} checks")


# ── A* guided search ─────────────────────────────────────────

async def astar_stream(def_arr, depth=27):
    """
    A* search guided by a heuristic:
      f(n) = g(n) + h(n)
      g(n) = depth already placed (blocks so far) — we want to maximize this, so negate
      h(n) = compactness score: sum of (3 - coord) for each placed block (reward proximity to origin corner)
             + reachability penalty: 0 if reachable cells >= remaining, else large penalty

    Priority queue pops the most promising partial solution.
    Yields whenever we reach a NEW maximum depth (new block placed deeper than before).
    """
    # heap entry: (priority, tie_breaker, option_str, snake_state_positions, snake_dir)
    # We rebuild Snake from scratch for each state to avoid shared-state bugs
    counter = 0
    best_depth = 0

    def heuristic(positions):
        """Higher = better. Sum of (2 - coord) rewards blocks near origin corner."""
        score = 0
        for p in positions:
            score += (2 - p[0]) + (2 - p[1]) + (2 - p[2])
        return score

    def priority(option, positions):
        d = len(positions)
        remaining = depth - d
        h = heuristic(positions)
        # Reachability bonus: heavily penalise if not enough free space
        if remaining > 0 and not free_cells_reachable(positions, remaining):
            return (1000 - d, -h)   # push to back
        return (-d, -h)             # deeper + more compact = lower priority value = pops first

    init_snake = Snake(def_arr, "0")
    heap = []
    heapq.heappush(heap, (priority("0", init_snake.state), counter, "0"))
    visited = {"0": True}
    iterations = 0

    yield make_event(1, "0", init_snake, False, 0, "astar")

    while heap and iterations < 2_000_000:
        if iterations % 200 == 0:
            await asyncio.sleep(0)

        prio, _, option = heapq.heappop(heap)
        iterations += 1

        # Rebuild snake for this option
        snake = Snake(def_arr, option)
        if not snake.check_if_valid():
            continue

        d = len(option)

        # Yield whenever we reach a new maximum depth
        if d > best_depth:
            best_depth = d
            done = d >= depth
            yield make_event(d, option, snake, done, iterations, "astar")
            if done:
                logger.info(f"A* solved in {iterations} iters, solution={option}")
                return

        # Expand children
        for j in range(4):
            child = option + str(j)
            if visited.get(child):
                continue
            visited[child] = True
            child_snake = Snake(def_arr, child)
            if not child_snake.check_if_valid():
                continue
            positions = child_snake.state
            p = priority(child, positions)
            counter += 1
            heapq.heappush(heap, (p, counter, child))

    yield {"error": "A* exhausted search space", "done": True, "iterations": iterations}


# ── API ──────────────────────────────────────────────────────

ALGOS = {"dfs", "bfs", "dfs_pruned", "astar"}

@app.get("/api/solve/stream")
async def solve_stream(algo: str = Query(default="dfs", pattern="^(dfs|bfs|dfs_pruned|astar)$")):
    """SSE endpoint — streams solver progress."""
    async def event_gen():
        gen = {
            "dfs":        dfs_stream(def_arr),
            "bfs":        bfs_stream(def_arr),
            "dfs_pruned": dfs_pruned_stream(def_arr),
            "astar":      astar_stream(def_arr),
        }[algo]
        async for state in gen:
            yield {"data": json.dumps(state)}

    return EventSourceResponse(event_gen())


@app.get("/api/def_arr")
def get_def_arr():
    return {"def_arr": def_arr}


# ── Frontend ─────────────────────────────────────────────────

DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")

if os.path.isdir(DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(DIST, "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        return FileResponse(os.path.join(DIST, "index.html"))
