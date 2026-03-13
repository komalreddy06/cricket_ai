"""Dataset-driven cricket probability engine using IPL ball-by-ball deliveries."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv
import random
from typing import Dict

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
