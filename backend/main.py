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


async def replay_solution(solution_option, def_arr, iterations, algo, delay=0.06):
    """
    Yield a clean 27-step replay of the solution, one block at a time.
    The first event has done=False (search done marker), then steps 1..27,
    with the final step having done=True (solution complete).
    Called by every algo after finding the solution.
    """
    for i in range(1, len(solution_option) + 1):
        partial = solution_option[:i]
        s = Snake(def_arr, partial)
        await asyncio.sleep(delay)
        yield make_event(i, partial, s, i == len(solution_option), iterations, algo)


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
                if done:
                    logger.info(f"DFS solved in {count} iters, solution={op}")
                    async for frame in replay_solution(op, def_arr, count, "dfs"):
                        yield frame
                    return
                yield make_event(len(op), op, snake, False, count, "dfs")
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
                if done:
                    logger.info(f"DFS+pruning solved in {count} iters ({pruned} pruned), solution={op}")
                    async for frame in replay_solution(op, def_arr, count, "dfs_pruned"):
                        yield frame
                    return
                yield make_event(len(op), op, snake, False, count, "dfs_pruned")
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
                        if level >= depth:
                            logger.info(f"BFS solved in {count} iters, solution={new_option}")
                            async for frame in replay_solution(new_option, def_arr, count, "bfs"):
                                yield frame
                            return
                        yield make_event(level, new_option, snake, False, count, "bfs")

        if not next_frontier:
            yield {"error": "No solution at this depth", "done": True, "iterations": count}
            return
        frontier = next_frontier
        logger.info(f"BFS level {level}: {len(frontier)} valid paths, {count} checks")


# ── A* guided search ─────────────────────────────────────────

# ── Warnsdorff DFS ───────────────────────────────────────────

def _count_free_neighbors(pos, occupied):
    """Count in-bounds, unoccupied neighbors of pos (tuple)."""
    x, y, z = pos
    count = 0
    for dx, dy, dz in [(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]:
        nx, ny, nz = x+dx, y+dy, z+dz
        nb = (nx, ny, nz)
        if nb not in occupied and 0 <= nx <= 2 and 0 <= ny <= 2 and 0 <= nz <= 2:
            count += 1
    return count

def _leaf_prune(occupied, remaining):
    """
    Fast O(27) check: any free cell with 0 free neighbors = isolated = prune.
    More than 1 free cell with exactly 1 free neighbor = two dead-end leaves = prune
    (Hamiltonian path can only have ONE endpoint / dead-end).
    """
    if remaining == 0:
        return False
    ALL = frozenset((x,y,z) for x in range(3) for y in range(3) for z in range(3))
    free = ALL - occupied
    leaves = 0
    for cell in free:
        x, y, z = cell
        nbr = 0
        for dx, dy, dz in [(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]:
            if (x+dx, y+dy, z+dz) in free:
                nbr += 1
        if nbr == 0:
            return True   # isolated cell
        if nbr == 1:
            leaves += 1
            if leaves > 1:
                return True  # two dead-end leaves → impossible
    return False

async def warnsdorff_stream(def_arr, depth=27):
    """
    DFS with Warnsdorff move ordering + leaf pruning.
    Only yields on forward progress (new max depth), then replays solution.
    At each step, sort rotation choices 0-3 by how many free neighbors
    the resulting next cell has (fewest = try first — Warnsdorff rule).
    """
    ALL = frozenset((x,y,z) for x in range(3) for y in range(3) for z in range(3))
    count = [0]
    pruned = [0]
    best_depth = [0]

    def warnsdorff_key(next_pos_t, occupied):
        """Free neighbor count of next_pos, excluding occupied. Fewest = best."""
        x, y, z = next_pos_t
        n = 0
        for dx, dy, dz in [(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]:
            nb = (x+dx, y+dy, z+dz)
            if nb not in occupied and 0 <= x+dx <= 2 and 0 <= y+dy <= 2 and 0 <= z+dz <= 2:
                n += 1
        return n

    DONE = object()  # sentinel

    async def dfs(op, occupied):
        count[0] += 1
        if count[0] % 300 == 0:
            await asyncio.sleep(0)

        # Pruning: bbox
        snake_now = Snake(def_arr, op)
        pos_list = snake_now.state
        if not bbox_fits(pos_list):
            pruned[0] += 1
            return

        remaining = depth - len(op)

        # Pruning: leaf/degree-1
        if _leaf_prune(occupied, remaining):
            pruned[0] += 1
            return

        # Pruning: flood fill
        if remaining > 0 and not free_cells_reachable(pos_list, remaining):
            pruned[0] += 1
            return

        if len(op) >= depth:
            yield op  # solution string
            return

        # Try all 4 rotations, sorted by Warnsdorff key of next cell
        candidates = []
        for r in range(4):
            test = Snake(def_arr, op + str(r))
            if test.check_if_valid():
                next_pos = tuple(test.state[-1])
                if next_pos not in occupied:
                    key = warnsdorff_key(next_pos, occupied | {next_pos})
                    candidates.append((key, r, next_pos))

        # Sort: fewest free neighbors first (Warnsdorff)
        candidates.sort(key=lambda x: x[0])

        for _, r, next_pos in candidates:
            child_op = op + str(r)
            child_occ = occupied | {next_pos}

            # Yield on forward depth progress
            d = len(child_op)
            if d > best_depth[0]:
                best_depth[0] = d
                child_snake = Snake(def_arr, child_op)
                yield make_event(d, child_op, child_snake, False, count[0], "warnsdorff")

            found = False
            async for event in dfs(child_op, child_occ):
                if isinstance(event, str):
                    yield event  # pass solution up
                    found = True
                    break
                else:
                    yield event
            if found:
                return

    yield make_event(1, "0", Snake(def_arr, "0"), False, 0, "warnsdorff")

    start_occ = frozenset({(0,0,0)})
    solution = None
    async for event in dfs("0", start_occ):
        if isinstance(event, str):
            solution = event
        else:
            yield event

    if solution:
        logger.info(f"Warnsdorff solved in {count[0]} iters ({pruned[0]} pruned), solution={solution}")
        async for frame in replay_solution(solution, def_arr, count[0], "warnsdorff"):
            yield frame
    else:
        yield {"error": "Warnsdorff exhausted", "done": True, "iterations": count[0]}


async def astar_stream(def_arr, depth=27):
    """
    A* search guided by a heuristic:
      f(n) = -depth + penalty if not reachable
    Yields EVERY valid state popped from the heap (not just new max depth),
    so user sees continuous block placement including backtracking.
    At the end, replays the full solution path step by step.
    """
    counter = 0

    def heuristic(positions):
        score = 0
        for p in positions:
            score += (2 - p[0]) + (2 - p[1]) + (2 - p[2])
        return score

    def priority(option, positions):
        d = len(positions)
        remaining = depth - d
        h = heuristic(positions)
        if remaining > 0 and not free_cells_reachable(positions, remaining):
            return (1000 - d, -h)
        return (-d, -h)

    init_snake = Snake(def_arr, "0")
    heap = []
    heapq.heappush(heap, (priority("0", init_snake.state), counter, "0"))
    visited = {"0": True}
    iterations = 0

    while heap and iterations < 2_000_000:
        if iterations % 100 == 0:
            await asyncio.sleep(0)

        prio, _, option = heapq.heappop(heap)
        iterations += 1

        snake = Snake(def_arr, option)
        if not snake.check_if_valid():
            continue

        d = len(option)

        # Yield EVERY state so user sees continuous progress
        done = d >= depth
        yield make_event(d, option, snake, False, iterations, "astar")

        if done:
            logger.info(f"A* solved in {iterations} iters, solution={option}")
            async for frame in replay_solution(option, def_arr, iterations, "astar"):
                yield frame
            return

        for j in range(4):
            child = option + str(j)
            if visited.get(child):
                continue
            visited[child] = True
            child_snake = Snake(def_arr, child)
            if not child_snake.check_if_valid():
                continue
            p = priority(child, child_snake.state)
            counter += 1
            heapq.heappush(heap, (p, counter, child))


# ── API ──────────────────────────────────────────────────────

ALGOS = {"dfs", "bfs", "dfs_pruned", "astar", "warnsdorff"}

@app.get("/api/solve/stream")
async def solve_stream(algo: str = Query(default="dfs", pattern="^(dfs|bfs|dfs_pruned|astar|warnsdorff)$")):
    """SSE endpoint — streams solver progress."""
    async def event_gen():
        gen = {
            "dfs":         dfs_stream(def_arr),
            "bfs":         bfs_stream(def_arr),
            "dfs_pruned":  dfs_pruned_stream(def_arr),
            "astar":       astar_stream(def_arr),
            "warnsdorff":  warnsdorff_stream(def_arr),
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
