"""Dataset-driven cricket probability engine using IPL ball-by-ball deliveries."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv
import random
from typing import Dict, Tuple

RUN_VALUES = [0, 1, 2, 3, 4, 6]
PHASES = ["powerplay", "middle", "death"]


@dataclass
class BallOutcome:
    runs: int
    wicket: bool
    desc: str
    landing: tuple[float, float, float]


class IPLDataModel:
    def __init__(self) -> None:
        self.loaded = False
        self.rows = 0
        self.phase_run_dist: Dict[str, Dict[int, float]] = {
            p: {rv: 1.0 for rv in RUN_VALUES} for p in PHASES
        }
        self.phase_wicket: Dict[str, float] = {p: 0.06 for p in PHASES}
        self.direction_boost = {
            "LEG": {4: 1.12, 6: 1.08, 0: 0.9},
            "STRAIGHT": {1: 1.1, 2: 1.08, 6: 1.02},
            "OFF": {4: 1.15, 0: 0.92, 6: 1.05},
        }
        self.ai_shots = ["DEFEND", "PUSH", "STROKE", "LOFT"]
        self.ai_dirs = ["LEG", "STRAIGHT", "OFF"]

    def train_from_kaggle_csv(self) -> None:
        for p in [Path("data/deliveries.csv"), Path("data/ipl_deliveries.csv"), Path("deliveries.csv")]:
            if p.exists():
                self._load_csv(p)
                return

    def _load_csv(self, path: Path) -> None:
        run_counts = {p: {rv: 1 for rv in RUN_VALUES} for p in PHASES}
        wicket_counts = {p: 1 for p in PHASES}
        ball_counts = {p: 2 for p in PHASES}

        with path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                over = self._safe_int(r.get("over") or r.get("Over"), 1)
                phase = "powerplay" if over <= 6 else ("middle" if over <= 15 else "death")

                batsman_runs = self._safe_int(
                    r.get("batsman_runs") or r.get("batter_runs") or r.get("runs_batter"),
                    0,
                )
                run_counts[phase][batsman_runs if batsman_runs in RUN_VALUES else 0] += 1

                is_wicket = self._safe_int(
                    r.get("is_wicket") or r.get("player_dismissed") or r.get("wicket") or 0,
                    0,
                )
                wicket_counts[phase] += 1 if is_wicket else 0
                ball_counts[phase] += 1
                self.rows += 1

        for phase in PHASES:
            total = sum(run_counts[phase].values())
            self.phase_run_dist[phase] = {rv: run_counts[phase][rv] / total for rv in RUN_VALUES}
            self.phase_wicket[phase] = wicket_counts[phase] / ball_counts[phase]

        self.loaded = True

    @staticmethod
    def _safe_int(v, default=0):
        try:
            return int(v)
        except Exception:
            return default

    def sample_ball(self, over_ball: int, shot: str, direction: str) -> BallOutcome:
        over = max(1, (over_ball // 6) + 1)
        phase = "powerplay" if over <= 6 else ("middle" if over <= 15 else "death")

        dist = dict(self.phase_run_dist[phase])
        for rv, mul in self.direction_boost.get(direction, {}).items():
            if rv in dist:
                dist[rv] *= mul

        shot_boost = {
            "DEFEND": {0: 1.3, 1: 1.1, 4: 0.7, 6: 0.55},
            "PUSH": {1: 1.2, 2: 1.15, 0: 0.9},
            "STROKE": {2: 1.05, 4: 1.2, 6: 1.1},
            "LOFT": {0: 0.85, 4: 1.2, 6: 1.45},
        }.get(shot, {})
        for rv, mul in shot_boost.items():
            dist[rv] *= mul

        wicket_p = min(0.45, max(0.02, self.phase_wicket[phase]))
        if shot == "LOFT":
            wicket_p *= 1.45
        elif shot == "DEFEND":
            wicket_p *= 0.75

        if random.random() < wicket_p:
            lx, ly, lz = self._landing_from_direction(direction, 2.0)
            return BallOutcome(0, True, f"{shot} to {direction}: WICKET!", (lx, ly, lz))

        runs = self._sample_runs(dist)
        lx, ly, lz = self._landing_from_direction(direction, 7 + runs * 1.2)
        return BallOutcome(runs, False, f"{shot} to {direction}: {runs} run(s)", (lx, ly, lz))

    def expected_value(self, over_ball: int, shot: str, direction: str) -> Tuple[float, float]:
        """Return expected runs and wicket probability for a candidate action."""
        over = max(1, (over_ball // 6) + 1)
        phase = "powerplay" if over <= 6 else ("middle" if over <= 15 else "death")

        dist = dict(self.phase_run_dist[phase])
        for rv, mul in self.direction_boost.get(direction, {}).items():
            if rv in dist:
                dist[rv] *= mul

        shot_boost = {
            "DEFEND": {0: 1.3, 1: 1.1, 4: 0.7, 6: 0.55},
            "PUSH": {1: 1.2, 2: 1.15, 0: 0.9},
            "STROKE": {2: 1.05, 4: 1.2, 6: 1.1},
            "LOFT": {0: 0.85, 4: 1.2, 6: 1.45},
        }.get(shot, {})
        for rv, mul in shot_boost.items():
            if rv in dist:
                dist[rv] *= mul

        total = sum(dist.values())
        exp_runs = sum((rv * p) for rv, p in dist.items()) / total if total else 0.0
        wicket_p = min(0.45, max(0.02, self.phase_wicket[phase]))
        if shot == "LOFT":
            wicket_p *= 1.45
        elif shot == "DEFEND":
            wicket_p *= 0.75
        return exp_runs, min(0.7, wicket_p)

    def minimax_ai_batting(self, over_ball: int, target_needed: int, balls_left: int, wickets_left: int) -> tuple[str, str]:
        """Choose AI batting action using a shallow minimax search with alpha-beta pruning."""

        def evaluate_state(runs_needed: int, b_left: int, w_left: int) -> float:
            if runs_needed <= 0:
                return 100.0
            if b_left <= 0 or w_left <= 0:
                return -100.0 - runs_needed
            return -(runs_needed * 5) + (b_left * 1.2) + (w_left * 3.0)

        def value_for_action(shot: str, direction: str) -> float:
            exp_runs, wicket_p = self.expected_value(over_ball, shot, direction)
            next_runs_needed = max(0, target_needed - exp_runs)
            survive = evaluate_state(next_runs_needed, balls_left - 1, wickets_left)
            out = evaluate_state(target_needed, balls_left - 1, wickets_left - 1)
            return (1 - wicket_p) * survive + wicket_p * out

        def min_node(shot: str, alpha: float, beta: float) -> tuple[float, str]:
            best_val = float("inf")
            best_dir = "STRAIGHT"
            for direction in self.ai_dirs:
                score = value_for_action(shot, direction)
                if score < best_val:
                    best_val = score
                    best_dir = direction
                beta = min(beta, best_val)
                if beta <= alpha:
                    break
            return best_val, best_dir

        best_shot = "PUSH"
        best_dir = "STRAIGHT"
        alpha = float("-inf")
        beta = float("inf")
        best_score = float("-inf")
        for shot in self.ai_shots:
            score, direction = min_node(shot, alpha, beta)
            if score > best_score:
                best_score = score
                best_shot = shot
                best_dir = direction
            alpha = max(alpha, best_score)
            if beta <= alpha:
                break
        return best_shot, best_dir

    @staticmethod
    def _sample_runs(dist: Dict[int, float]) -> int:
        total = sum(dist.values())
        r = random.random() * total
        c = 0.0
        for run, p in sorted(dist.items()):
            c += p
            if r <= c:
                return run
        return 0

    @staticmethod
    def _landing_from_direction(direction: str, distance: float):
        if direction == "LEG":
            return (-distance * 0.55, 0.25, -distance)
        if direction == "OFF":
            return (distance * 0.55, 0.25, -distance)
        return (0.0, 0.25, -distance)
