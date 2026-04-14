"""
UNIT I — Search Algorithms (EIE115R01)
======================================
BFS  : Breadth-First Search  → fielder coverage zone exploration
DFS  : Depth-First Search    → shot decision-tree traversal
A*   : A* Search             → optimal fielder path to ball landing zone

Reference: AIMA 4th Ed., Ch. 3
"""

import heapq
import math
from collections import deque


# ──────────────────────────────────────────────────────────────────────────────
# A* SEARCH  — Optimal Fielder Pathfinding
# ──────────────────────────────────────────────────────────────────────────────

class AStarFielder:
    """A* search to find the shortest path for a fielder to reach a ball."""

    FIELD_RADIUS = 35.0   # metres from centre
    STEP = 2.0            # grid resolution in metres

    def _h(self, a, b):
        """Euclidean distance heuristic."""
        return math.hypot(a[0] - b[0], a[1] - b[1])

    def _in_field(self, x, z):
        return x * x + z * z <= self.FIELD_RADIUS ** 2

    def _neighbors(self, pos):
        x, z = pos
        dirs = [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]
        result = []
        for dx, dz in dirs:
            nx, nz = round(x + dx * self.STEP, 1), round(z + dz * self.STEP, 1)
            if self._in_field(nx, nz):
                result.append((nx, nz))
        return result

    def find_path(self, start, goal):
        """
        A* from start=(x,z) to goal=(x,z).
        Returns list of waypoints [[x,z], ...].
        """
        start = (round(start[0], 1), round(start[1], 1))
        goal  = (round(goal[0],  1), round(goal[1],  1))

        open_heap = []          # (f, g, node)
        heapq.heappush(open_heap, (0.0, 0.0, start))
        came_from = {}
        g_score   = {start: 0.0}

        while open_heap:
            f, g, current = heapq.heappop(open_heap)

            if self._h(current, goal) < self.STEP:
                # Reconstruct path
                path = [list(current)]
                while current in came_from:
                    current = came_from[current]
                    path.append(list(current))
                path.reverse()
                return path

            for nb in self._neighbors(current):
                cost = self.STEP
                tentative_g = g + cost
                if tentative_g < g_score.get(nb, math.inf):
                    came_from[nb] = current
                    g_score[nb] = tentative_g
                    f_new = tentative_g + self._h(nb, goal)
                    heapq.heappush(open_heap, (f_new, tentative_g, nb))

        # No path — return direct line
        return [list(start), list(goal)]


# ──────────────────────────────────────────────────────────────────────────────
# BFS  — Fielder Coverage Zone Exploration
# ──────────────────────────────────────────────────────────────────────────────

class BFSCoverage:
    """BFS to find all zones reachable by a fielder within a time limit."""

    STEP = 2.0
    FIELD_RADIUS = 35.0

    def reachable_zone(self, start, max_steps=8):
        """
        BFS from start position.
        Returns set of (x,z) grid cells reachable within max_steps moves.
        """
        start = (round(start[0], 1), round(start[1], 1))
        visited = {start}
        queue   = deque([(start, 0)])

        while queue:
            pos, depth = queue.popleft()
            if depth >= max_steps:
                continue
            x, z = pos
            for dx, dz in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]:
                nx = round(x + dx * self.STEP, 1)
                nz = round(z + dz * self.STEP, 1)
                npos = (nx, nz)
                if npos not in visited and nx*nx + nz*nz <= self.FIELD_RADIUS**2:
                    visited.add(npos)
                    queue.append((npos, depth + 1))

        return visited

    def find_uncovered_zones(self, fielder_positions, ball_landing=None):
        """Return approximate field zones NOT covered by any fielder."""
        covered = set()
        for fp in fielder_positions:
            covered |= self.reachable_zone(fp, max_steps=6)

        # Check if ball landing is uncovered
        if ball_landing:
            bl = (round(ball_landing[0], 1), round(ball_landing[1], 1))
            return bl not in covered

        return len(covered)


# ──────────────────────────────────────────────────────────────────────────────
# DFS  — Shot Selection Decision Tree
# ──────────────────────────────────────────────────────────────────────────────

class DFSShotTree:
    """DFS over a shot decision tree given delivery characteristics."""

    # Decision tree: delivery → situation → recommended shot
    TREE = {
        "yorker": {
            "leg":  {"attack": "flick",      "defend": "jam_down",   "neutral": "squeeze"},
            "off":  {"attack": "drive",      "defend": "jam_down",   "neutral": "push"},
            "mid":  {"attack": "flick",      "defend": "block",      "neutral": "push"},
        },
        "bouncer": {
            "leg":  {"attack": "pull",       "defend": "duck",       "neutral": "hook"},
            "off":  {"attack": "cut",        "defend": "duck",       "neutral": "back_punch"},
            "mid":  {"attack": "pull",       "defend": "duck",       "neutral": "hook"},
        },
        "good_length": {
            "off":  {"attack": "drive",      "defend": "defend",     "neutral": "push"},
            "leg":  {"attack": "flick",      "defend": "pad",        "neutral": "sweep"},
            "mid":  {"attack": "straight_drive","defend":"defend",   "neutral": "push"},
        },
        "full": {
            "off":  {"attack": "drive",      "defend": "defend",     "neutral": "push"},
            "leg":  {"attack": "sweep",      "defend": "pad",        "neutral": "flick"},
            "mid":  {"attack": "loft",       "defend": "defend",     "neutral": "drive"},
        },
        "short": {
            "off":  {"attack": "cut",        "defend": "defend",     "neutral": "back_punch"},
            "leg":  {"attack": "pull",       "defend": "duck",       "neutral": "hook"},
            "mid":  {"attack": "pull",       "defend": "defend",     "neutral": "hook"},
        },
    }

    def _classify_length(self, z):
        if z <= 2:   return "yorker"
        if z <= 5:   return "bouncer"
        if z <= 8:   return "good_length"
        if z <= 12:  return "full"
        return "short"

    def _classify_line(self, x):
        if x > 0.3:  return "off"
        if x < -0.3: return "leg"
        return "mid"

    def dfs_select_shot(self, target_x, target_z, confidence, depth=0, max_depth=3):
        """
        DFS through decision tree to select shot.
        confidence=0..1 maps to defend/neutral/attack.
        """
        length = self._classify_length(target_z)
        line   = self._classify_line(target_x)

        if depth >= max_depth:
            return "defend"

        subtree = self.TREE.get(length, {}).get(line, {})
        if not subtree:
            return "defend"

        if confidence >= 0.65:
            return subtree.get("attack", "defend")
        elif confidence >= 0.35:
            return subtree.get("neutral", "defend")
        else:
            return subtree.get("defend", "defend")
