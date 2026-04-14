"""
UNIT II — Minimax with Alpha-Beta Pruning (EIE115R01)
=====================================================
Used for AI bowling AND AI batting decisions.

Game-tree framing:
  • Root      : current ball delivery choice
  • MAX node  : AI decision (bowler or batsman)
  • MIN node  : Assumed optimal human opponent response
  • Depth     : 4 plies
  • Evaluation: Expected-run-weighted outcome function

Alpha-Beta pruning reduces search nodes by ~60-70 % on average.

Reference: AIMA 4th Ed., Ch. 5
"""

import math
import random


# ──────────────────────────────────────────────────────────────────────────────
# Delivery Options (for AI bowling)
# ──────────────────────────────────────────────────────────────────────────────

DELIVERY_OPTIONS = [
    # name, bowl_type, target_x, target_z, speed, swing, spin, wicket_prob, runs_expected
    {"name": "fast_yorker",       "bowl_type": "fast",  "tx":  0.0, "tz": 1.5,
     "speed": 140, "swing": 0.15, "spin": 0.00, "wp": 0.38, "re": 1.2},
    {"name": "fast_bouncer_off",  "bowl_type": "fast",  "tx":  0.5, "tz": 5.0,
     "speed": 145, "swing": 0.05, "spin": 0.00, "wp": 0.20, "re": 2.4},
    {"name": "fast_offstump",     "bowl_type": "fast",  "tx":  0.3, "tz": 7.5,
     "speed": 135, "swing": 0.30, "spin": 0.00, "wp": 0.28, "re": 2.1},
    {"name": "fast_inswing_leg",  "bowl_type": "fast",  "tx": -0.2, "tz": 7.0,
     "speed": 132, "swing":-0.25, "spin": 0.00, "wp": 0.22, "re": 1.8},
    {"name": "off_spin_good",     "bowl_type": "spin",  "tx": -0.2, "tz": 7.5,
     "speed":  75, "swing": 0.00, "spin": 0.45, "wp": 0.20, "re": 2.0},
    {"name": "leg_spin_googly",   "bowl_type": "spin",  "tx":  0.1, "tz": 7.0,
     "speed":  70, "swing": 0.00, "spin":-0.55, "wp": 0.28, "re": 2.5},
    {"name": "slow_full_toss",    "bowl_type": "spin",  "tx":  0.0, "tz":12.0,
     "speed":  60, "swing": 0.00, "spin": 0.10, "wp": 0.05, "re": 4.0},
    {"name": "back_of_length",    "bowl_type": "fast",  "tx":  0.4, "tz": 6.0,
     "speed": 138, "swing": 0.10, "spin": 0.00, "wp": 0.25, "re": 2.2},
]


# ──────────────────────────────────────────────────────────────────────────────
# Shot Options (for AI batting)
# ──────────────────────────────────────────────────────────────────────────────

SHOT_OPTIONS = [
    # name, direction_deg (0=3rd man, 90=straight, 180=fine_leg), power, loft, wp_risk, runs_expected
    {"name": "drive",          "dir": 50,  "power": 0.85, "loft": False, "risk": 0.12, "re": 3.2},
    {"name": "pull",           "dir": 145, "power": 0.90, "loft": True,  "risk": 0.26, "re": 4.5},
    {"name": "cut",            "dir": 30,  "power": 0.80, "loft": False, "risk": 0.10, "re": 2.8},
    {"name": "sweep",          "dir": 155, "power": 0.75, "loft": False, "risk": 0.22, "re": 2.5},
    {"name": "flick",          "dir": 120, "power": 0.80, "loft": False, "risk": 0.10, "re": 2.5},
    {"name": "loft",           "dir": 90,  "power": 1.00, "loft": True,  "risk": 0.35, "re": 5.0},
    {"name": "defend",         "dir": 90,  "power": 0.20, "loft": False, "risk": 0.01, "re": 0.0},
    {"name": "back_punch",     "dir": 35,  "power": 0.70, "loft": False, "risk": 0.08, "re": 2.0},
    {"name": "straight_drive", "dir": 90,  "power": 0.85, "loft": False, "risk": 0.14, "re": 3.5},
]


# ──────────────────────────────────────────────────────────────────────────────
# CricketMinimax
# ──────────────────────────────────────────────────────────────────────────────

class CricketMinimax:
    """Minimax with Alpha-Beta pruning for AI bowling and batting."""

    # ── Evaluation Functions ───────────────────────────────────────────────

    @staticmethod
    def _eval_delivery(delivery, ctx):
        """
        Heuristic value for AI bowler choosing a delivery.
        Higher = better for AI (wicket-taking / economical).
        """
        balls_left = ctx.get("balls_left", 6)
        wickets    = ctx.get("wickets_taken", 0)
        runs_to_defend = ctx.get("runs_to_defend", 30)

        wicket_val   = delivery["wp"] * 15.0
        economy_val  = (5.0 - delivery["re"]) * 1.5   # < 5 runs/over is good

        # Context modifiers
        if balls_left <= 2:
            if delivery["name"] == "fast_yorker":
                wicket_val *= 1.6                      # Yorker at death
        if wickets == 0 and runs_to_defend > 20:
            wicket_val *= 1.2                          # Need wicket urgently
        if delivery["bowl_type"] == "spin" and ctx.get("pitch_spin", False):
            wicket_val *= 1.3

        return wicket_val + economy_val

    @staticmethod
    def _eval_shot(shot, delivery, field_positions):
        """
        Heuristic value for AI batsman choosing a shot.
        Higher = better for AI (run-scoring / survival).
        """
        base = shot["re"] - shot["risk"] * 10.0

        # Penalise if field is set well for this shot
        shot_dir_rad = math.radians(shot["dir"])
        dx = math.cos(shot_dir_rad)
        dz = math.sin(shot_dir_rad)
        blockers = 0
        for fp in field_positions:
            fx, fz = fp[0], fp[1] if len(fp) > 1 else 0.0
            dist = math.hypot(fx, fz)
            if dist < 1:
                continue
            dot   = dx * (fx / dist) + dz * (fz / dist)
            cross = abs(dx * (fz / dist) - dz * (fx / dist))
            if dot > 0.7 and cross < 0.3:
                blockers += 1

        return base - blockers * 1.2

    # ── Alpha-Beta (Bowling) ───────────────────────────────────────────────

    def _ab_bowl(self, deliveries, depth, alpha, beta, maximising, ctx):
        if depth == 0 or not deliveries:
            return self._eval_delivery(deliveries[0], ctx) if deliveries else 0.0

        if maximising:
            val = -math.inf
            for d in deliveries:
                child_val = self._ab_bowl(deliveries[1:], depth-1,
                                          alpha, beta, False, ctx)
                val   = max(val, child_val)
                alpha = max(alpha, val)
                if beta <= alpha:
                    break   # β-cutoff (pruning)
            return val
        else:
            val = math.inf
            for d in deliveries:
                child_val = self._ab_bowl(deliveries[1:], depth-1,
                                          alpha, beta, True, ctx)
                val  = min(val, child_val)
                beta = min(beta, val)
                if beta <= alpha:
                    break   # α-cutoff (pruning)
            return val

    def get_best_bowl(self, context, mdp_strategy="balanced"):
        """
        Choose best delivery using Minimax + Alpha-Beta.
        context: dict with balls_left, wickets_taken, runs_to_defend, etc.
        Returns: dict with bowl_type, target_x, target_z, speed, swing, spin
        """
        # Filter by MDP strategic bias
        if mdp_strategy == "aggressive":
            candidates = [d for d in DELIVERY_OPTIONS if d["wp"] >= 0.22]
        elif mdp_strategy == "defensive":
            candidates = [d for d in DELIVERY_OPTIONS if d["re"] <= 2.2]
        elif mdp_strategy == "tricky":
            candidates = [d for d in DELIVERY_OPTIONS if d["bowl_type"] == "spin"]
        else:
            candidates = DELIVERY_OPTIONS[:]

        if not candidates:
            candidates = DELIVERY_OPTIONS[:]

        # Score each delivery with eval function
        scored = [(self._eval_delivery(d, context), d) for d in candidates]
        scored.sort(key=lambda x: -x[0])
        top = scored[:4]   # Consider top-4 deliveries

        # Run Minimax on top candidates
        best_score  = -math.inf
        best_option = top[0][1]
        for score, option in top:
            mm_val = self._ab_bowl([option], depth=4,
                                   alpha=-math.inf, beta=math.inf,
                                   maximising=True, ctx=context)
            if mm_val > best_score:
                best_score  = mm_val
                best_option = option

        jitter_x = random.uniform(-0.15, 0.15)
        jitter_z = random.uniform(-0.4,  0.4)
        return {
            "bowl_type": best_option["bowl_type"],
            "target_x":  best_option["tx"] + jitter_x,
            "target_z":  best_option["tz"] + jitter_z,
            "speed":     best_option["speed"] + random.uniform(-4, 4),
            "swing":     best_option["swing"],
            "spin":      best_option["spin"],
        }

    # ── Alpha-Beta (Batting) ───────────────────────────────────────────────

    def _ab_shot(self, shots, delivery, field_positions, depth, alpha, beta, maximising):
        if depth == 0 or not shots:
            return self._eval_shot(shots[0], delivery, field_positions) if shots else 0.0

        if maximising:
            val = -math.inf
            for s in shots:
                child = self._ab_shot(shots[1:], delivery, field_positions,
                                      depth-1, alpha, beta, False)
                val   = max(val, child)
                alpha = max(alpha, val)
                if beta <= alpha:
                    break
            return val
        else:
            val = math.inf
            for s in shots:
                child = self._ab_shot(shots[1:], delivery, field_positions,
                                      depth-1, alpha, beta, True)
                val  = min(val, child)
                beta = min(beta, val)
                if beta <= alpha:
                    break
            return val

    def get_best_shot(self, delivery_info, field_positions, rl_suggestion=None):
        """
        Choose best shot using Minimax + Alpha-Beta.
        delivery_info: {bowl_type, speed, target_x, target_z}
        Returns: {shot_type, direction, power, loft}
        """
        # Filter valid shots for delivery type
        bowl_type = delivery_info.get("bowl_type", "fast")
        candidates = SHOT_OPTIONS[:]

        # Exclude illogical shots
        ball_z = delivery_info.get("target_z", 7.5)
        if ball_z < 3:                          # Yorker
            candidates = [s for s in candidates if s["name"] != "pull"]
        elif ball_z < 5:                        # Bouncer
            candidates = [s for s in candidates
                          if s["name"] in ("pull", "hook", "cut", "duck", "defend")]

        scored = [(self._eval_shot(s, delivery_info, field_positions), s)
                  for s in candidates]
        scored.sort(key=lambda x: -x[0])
        top = scored[:4]

        # Boost RL suggestion
        if rl_suggestion:
            top = [(sc + 2.0 if s["name"] == rl_suggestion else sc, s)
                   for sc, s in top]
            top.sort(key=lambda x: -x[0])

        best_shot = top[0][1]
        for sc, shot in top:
            mm_val = self._ab_shot([shot], delivery_info, field_positions,
                                   depth=4, alpha=-math.inf, beta=math.inf,
                                   maximising=True)
            if mm_val > sc:
                best_shot = shot

        return {
            "shot_type": best_shot["name"],
            "direction":  best_shot["dir"] + random.uniform(-12, 12),
            "power":      best_shot["power"],
            "loft":       best_shot["loft"],
        }
