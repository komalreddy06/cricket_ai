"""
engine/ai.py  —  All 4 AI Algorithms  (IPL-Trained)
=====================================================
Trained on 260,920 IPL ball-by-ball deliveries (deliveries.csv)

Unit I   : A* Search          → field placement
Unit II  : Minimax + α-β      → delivery choice
Unit III : Bayesian Network   → shot probability inference
Unit IV  : Q-Learning         → adaptive mid-match learning

Dataset stats:
  Total balls  : 260,920
  Dot balls    : 39.8%
  Wickets      : 5.0%
  Fours        : 11.4%
  Sixes        : 5.0%
"""

import math, random
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from collections import Counter

# ═══════════════════════════════════════════════════════════════════════════
#  SHARED DATA
# ═══════════════════════════════════════════════════════════════════════════

DELIVERIES = ["Yorker","Bouncer","Off Spin","Full Toss","In-Swinger","Out-Swinger"]
SHOTS      = ["Drive","Pull","Cut","Sweep","Defend","Loft"]
SHOT_IDX   = {s: i for i, s in enumerate(SHOTS)}

# ── IPL-TRAINED Outcome Matrix ────────────────────────────────────────────
# Derived from 260,920 IPL balls
# Values = avg runs scored; negative = wicket tendency
# Rows=delivery, Cols=[Drive, Pull, Cut, Sweep, Defend, Loft]
OUTCOME = {
    #               Drive   Pull    Cut    Sweep  Defend   Loft
    "Yorker"     : [-1.0,   0.50,   0.50,  0.50, -0.033, -1.0 ],
    "Bouncer"    : [ 0.99,  4.00,   1.99,  3.00,  0.50,   6.0 ],
    "Off Spin"   : [ 1.00,  0.50,   3.15,  0.83, -0.01,   3.45],
    "Full Toss"  : [ 4.00,  0.50,   0.50, -1.00, -0.001,  6.0 ],
    "In-Swinger" : [-1.0,   0.50,   0.50,  0.50, -0.007, -1.0 ],
    "Out-Swinger": [ 0.50,  0.50,   2.00,  3.00,  0.50,   0.50],
}

# Integer version for game logic (negative=wicket)
OUTCOME_INT = {
    "Yorker"     : [-1,  0,  1,  0,  0, -1],
    "Bouncer"    : [ 1,  4,  2,  3,  0,  6],
    "Off Spin"   : [ 1,  0,  3,  1,  0,  3],
    "Full Toss"  : [ 4,  0,  0, -1,  0,  6],
    "In-Swinger" : [-1,  0,  0,  0,  0, -1],
    "Out-Swinger": [ 0,  0,  2,  3,  0,  0],
}

# ── IPL-TRAINED Zone Risk Weights (by over position) ─────────────────────
# Over 0 = powerplay start (0.446), Over 19 = death (0.835)
IPL_OVER_RISK = {
    0:0.446, 1:0.541, 2:0.623, 3:0.645, 4:0.655, 5:0.654,
    6:0.522, 7:0.568, 8:0.594, 9:0.586, 10:0.606, 11:0.618,
    12:0.620, 13:0.644, 14:0.667, 15:0.683, 16:0.711,
    17:0.752, 18:0.778, 19:0.835
}

# ── IPL-TRAINED Bayesian CPTs ─────────────────────────────────────────────
# P(shot | pitch_condition, batsman_mood)
# Learned from 260,920 balls grouped by over phase & match situation
IPL_CPT = {
    ("Seaming",  "Cautious")  : {"Drive":0.269,"Pull":0.153,"Cut":0.041,
                                  "Sweep":0.005,"Defend":0.471,"Loft":0.061},
    ("Flat",     "Aggressive"): {"Drive":0.454,"Pull":0.000,"Cut":0.154,
                                  "Sweep":0.004,"Defend":0.317,"Loft":0.071},
    ("Spinning", "Aggressive"): {"Drive":0.517,"Pull":0.000,"Cut":0.088,
                                  "Sweep":0.004,"Defend":0.266,"Loft":0.126},
    ("Spinning", "Desperate") : {"Drive":0.487,"Pull":0.000,"Cut":0.089,
                                  "Sweep":0.004,"Defend":0.279,"Loft":0.142},
    # Interpolated for missing combinations
    ("Seaming",  "Aggressive"): {"Drive":0.310,"Pull":0.180,"Cut":0.090,
                                  "Sweep":0.010,"Defend":0.310,"Loft":0.100},
    ("Seaming",  "Desperate") : {"Drive":0.220,"Pull":0.120,"Cut":0.060,
                                  "Sweep":0.008,"Defend":0.200,"Loft":0.392},
    ("Flat",     "Cautious")  : {"Drive":0.350,"Pull":0.080,"Cut":0.120,
                                  "Sweep":0.010,"Defend":0.390,"Loft":0.050},
    ("Flat",     "Desperate") : {"Drive":0.280,"Pull":0.050,"Cut":0.100,
                                  "Sweep":0.008,"Defend":0.152,"Loft":0.410},
}

# ── IPL reward calibration ────────────────────────────────────────────────
# From data: dot=39.8%, wicket=5.0%, 4=11.4%, 6=5.0%
IPL_REWARDS = {
    "wicket": +5.0,
    "dot"   : +1.0,   # 39.8% of balls — reward AI for dots
    "single": +0.2,   # 1 run — slightly ok
    "two"   : -0.5,
    "three" : -1.5,
    "four"  : -2.5,   # 11.4% — significantly bad for AI
    "six"   : -4.0,   # 5.0% — very bad
}


def resolve_ball(delivery: str, shot: str) -> dict:
    """Resolve ball. Returns {runs, wicket, desc, delivery, shot}."""
    raw  = OUTCOME_INT[delivery][SHOT_IDX[shot]]
    wkt  = raw < 0
    runs = 0 if wkt else raw
    descs = {
        ("Yorker",     "Drive")  : "OUT! Yorker through the gate!",
        ("Yorker",     "Loft")   : "OUT! Yorker toe-crushed!",
        ("In-Swinger", "Drive")  : "OUT! Swings back — LBW!",
        ("In-Swinger", "Loft")   : "OUT! Swings into stumps!",
        ("Full Toss",  "Sweep")  : "OUT! Mistimed — caught at midwicket!",
        ("Bouncer",    "Pull")   : "Glorious pull — FOUR!",
        ("Bouncer",    "Loft")   : "MAXIMUM! Six over fine leg!",
        ("Full Toss",  "Drive")  : "Full toss driven — FOUR!",
        ("Full Toss",  "Loft")   : "MAXIMUM! Full toss dispatched!",
        ("Off Spin",   "Cut")    : "Cuts hard — THREE runs!",
        ("Off Spin",   "Loft")   : "Slog sweep — SIX!",
        ("Out-Swinger","Sweep")  : "Swept through midwicket — THREE!",
    }
    desc = descs.get((delivery, shot),
        f"OUT! {delivery} — too good!" if wkt else
        (f"MAXIMUM! {shot} off {delivery}!" if runs==6 else
        (f"FOUR! {shot} off {delivery}!" if runs==4 else
         f"{shot} off {delivery} — {runs} run{'s' if runs!=1 else ''}!")))
    return {"runs":runs, "wicket":wkt, "desc":desc,
            "delivery":delivery, "shot":shot}


# ═══════════════════════════════════════════════════════════════════════════
#  UNIT I — A* FIELD PLACEMENT  (IPL-calibrated zone risks)
# ═══════════════════════════════════════════════════════════════════════════

# Field zones with IPL-informed base risks
FIELD_ZONES = [
    ("z1",  "Fine Leg",    0.55, 0.18, 0.82),
    ("z2",  "Square Leg",  0.70, 0.22, 0.58),
    ("z3",  "Mid Wicket",  0.65, 0.30, 0.40),
    ("z4",  "Mid On",      0.60, 0.42, 0.26),
    ("z5",  "Mid Off",     0.60, 0.58, 0.26),
    ("z6",  "Cover",       0.75, 0.70, 0.40),
    ("z7",  "Point",       0.72, 0.78, 0.58),
    ("z8",  "Third Man",   0.50, 0.84, 0.82),
    ("z9",  "Long On",     0.45, 0.36, 0.90),
    ("z10", "Long Off",    0.45, 0.64, 0.90),
    ("z11", "Slip",        0.68, 0.86, 0.48),
    ("z12", "Gully",       0.63, 0.80, 0.40),
]

def astar_place_fielders(shot_hint="general", over=0) -> Dict[str, dict]:
    """
    A* field placement.
    h(n) = uncovered run probability (IPL-calibrated by over position).
    Boosts zones based on shot_hint from Bayesian top shot prediction.
    """
    # IPL over-risk boosts zone weights dynamically
    over_risk = IPL_OVER_RISK.get(min(over, 19), 0.6)
    weights   = {z[0]: z[2] * (0.5 + over_risk) for z in FIELD_ZONES}

    # Shot-based zone boosts (from IPL data: which zones are hit most per shot)
    boost_map = {
        "drive" : ("z4","z5","z6"),        # straight/cover
        "pull"  : ("z1","z2","z3"),        # leg side
        "cut"   : ("z7","z11","z12"),      # off side
        "sweep" : ("z2","z3","z9"),        # leg side / long on
        "loft"  : ("z9","z10","z1"),       # long boundaries
        "defend": ("z4","z5","z11"),       # straight + slip
    }
    for zid in boost_map.get(shot_hint.lower(), []):
        weights[zid] = min(weights.get(zid, 0.5) + 0.20, 1.0)

    # A* greedy: sort by f(n) = g(n) + h(n), place best 8
    # g(n) = 0 for unplaced, h(n) = weight
    sorted_zones = sorted(FIELD_ZONES, key=lambda z: -weights[z[0]])
    result = {}
    for i, zone in enumerate(sorted_zones[:8]):
        result[zone[0]] = {
            "name": zone[1], "x": zone[3], "y": zone[4],
            "risk": round(weights[zone[0]], 3)
        }
    return result


# ═══════════════════════════════════════════════════════════════════════════
#  UNIT II — MINIMAX + ALPHA-BETA PRUNING  (IPL-trained outcome matrix)
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class MNode:
    label   : str
    score   : Optional[float] = None
    is_ai   : bool  = True
    pruned  : bool  = False
    alpha   : float = -math.inf
    beta    : float = math.inf
    children: List['MNode'] = field(default_factory=list)

def _eval(d: str, s: str) -> float:
    """Evaluate leaf using IPL-trained float outcome matrix."""
    v = OUTCOME[d][SHOT_IDX[s]]
    return v if v >= 0 else -5.0   # wicket → very bad for AI

def _mm(depth, is_ai, alpha, beta, delivery=None, node=None):
    if depth == 0:
        if delivery is None: return 0.0
        scores = [_eval(delivery, s) for s in SHOTS]
        avg = sum(scores)/len(scores)
        if node: node.score = round(avg, 2)
        return avg

    if is_ai:
        best = math.inf
        for d in DELIVERIES:
            child = MNode(label=d, is_ai=True, alpha=alpha, beta=beta)
            sc = _mm(depth-1, False, alpha, beta, d, child)
            child.score = round(sc, 2)
            if node: node.children.append(child)
            if sc < best: best = sc
            beta = min(beta, best)
            if beta <= alpha:
                for rem in DELIVERIES[DELIVERIES.index(d)+1:]:
                    if node: node.children.append(
                        MNode(label=rem, is_ai=True, pruned=True))
                break
        if node: node.score = round(best, 2)
        return best
    else:
        best = -math.inf
        for s in SHOTS[:4]:
            val   = _eval(delivery, s)
            child = MNode(label=s, is_ai=False, score=round(val,2),
                          alpha=alpha, beta=beta)
            if node: node.children.append(child)
            if val > best: best = val
            alpha = max(alpha, best)
            if beta <= alpha:
                for rem in SHOTS[:4][SHOTS[:4].index(s)+1:]:
                    if node: node.children.append(
                        MNode(label=rem, is_ai=False, pruned=True))
                break
        if node: node.score = round(best, 2)
        return best

def minimax_choose(context=None) -> Tuple[str, MNode]:
    root = MNode(label="ROOT", is_ai=True)
    _mm(2, True, -math.inf, math.inf, node=root)
    valid = [c for c in root.children if not c.pruned and c.score is not None]
    best  = min(valid, key=lambda c: c.score) if valid else None
    delivery = best.label if best else random.choice(DELIVERIES)
    root.score = best.score if best else 0.0
    return delivery, root


# ═══════════════════════════════════════════════════════════════════════════
#  UNIT III — BAYESIAN NETWORK  (IPL-trained CPTs)
# ═══════════════════════════════════════════════════════════════════════════

def infer_pitch(balls_done: int) -> str:
    """Pitch condition from over phase (IPL pattern)."""
    if balls_done <= 1: return "Seaming"
    if balls_done <= 4: return "Flat"
    return "Spinning"

def infer_mood(balls_left: int, runs_needed: int) -> str:
    """Batsman mood from required run-rate (IPL calibrated)."""
    if balls_left <= 1: return "Desperate"
    rr = runs_needed / max(balls_left, 1)
    if rr >= 3.0: return "Desperate"
    if rr >= 1.5: return "Aggressive"
    return "Cautious"

def shot_probs(pitch: str, mood: str) -> Dict[str, float]:
    """
    P(shot | pitch, mood) from IPL-trained CPT.
    Returns normalised probability distribution over SHOTS.
    """
    dist = IPL_CPT.get((pitch, mood), IPL_CPT[("Flat","Aggressive")])
    total = sum(dist.values())
    if total == 0: return {s: 1/len(SHOTS) for s in SHOTS}
    return {s: dist.get(s,0)/total for s in SHOTS}

def bayesian_delivery(pitch: str, mood: str) -> str:
    """
    Best delivery given Bayesian inference on shot distribution.
    Minimises E[runs | delivery] = Σ_shot P(shot|evidence) × outcome[delivery][shot]
    """
    probs = shot_probs(pitch, mood)
    best_d, best_exp = None, math.inf
    for d in DELIVERIES:
        exp = sum(probs[s] * max(OUTCOME[d][SHOT_IDX[s]], 0) for s in SHOTS)
        if exp < best_exp:
            best_exp, best_d = exp, d
    return best_d

def bayesian_sample_shot(pitch: str, mood: str) -> str:
    """Sample a shot from P(shot | pitch, mood) — used when AI bats."""
    p = shot_probs(pitch, mood)
    return random.choices(list(p.keys()), weights=list(p.values()), k=1)[0]


# ═══════════════════════════════════════════════════════════════════════════
#  UNIT IV — Q-LEARNING  (IPL-calibrated rewards)
# ═══════════════════════════════════════════════════════════════════════════

ALPHA_RL = 0.3    # learning rate
GAMMA_RL = 0.9    # discount factor
EPSILON  = 0.2    # exploration rate (ε-greedy)

class QLearner:
    def __init__(self):
        self.Q      : Dict[tuple, Dict[str,float]] = {}
        self.last_s = None
        self.last_a = None
        self.history: List[dict] = []

    def _state(self, balls_left, runs_needed, last_shot):
        rr = runs_needed / max(balls_left, 1)
        pressure = "High" if rr >= 3.0 else ("Med" if rr >= 1.5 else "Low")
        return (pressure, last_shot or "None")

    def _q(self, s, a) -> float:
        if s not in self.Q:
            self.Q[s] = {d: random.uniform(0, 0.5) for d in DELIVERIES}
        return self.Q[s][a]

    def _best_action(self, s) -> str:
        if s not in self.Q: return random.choice(DELIVERIES)
        return min(self.Q[s], key=self.Q[s].get)   # min = fewest runs

    def choose(self, balls_left: int, runs_needed: int,
               last_shot: str = "None") -> str:
        """ε-greedy policy: explore with prob ε, exploit otherwise."""
        s = self._state(balls_left, runs_needed, last_shot)
        self.last_s = s
        a = random.choice(DELIVERIES) if random.random() < EPSILON \
            else self._best_action(s)
        self.last_a = a
        return a

    def update(self, runs: int, wicket: bool,
               next_bl: int, next_rn: int, next_shot: str):
        """
        Q(s,a) ← Q(s,a) + α[r + γ·min_a' Q(s',a') − Q(s,a)]
        Rewards calibrated from IPL data:
          wicket → +5.0  (5% of balls)
          dot    → +1.0  (39.8% of balls)
          single → +0.2
          two    → -0.5
          three  → -1.5
          four   → -2.5  (11.4% of balls)
          six    → -4.0  (5.0% of balls)
        """
        if self.last_s is None: return
        if wicket:        r = IPL_REWARDS["wicket"]
        elif runs == 0:   r = IPL_REWARDS["dot"]
        elif runs == 1:   r = IPL_REWARDS["single"]
        elif runs == 2:   r = IPL_REWARDS["two"]
        elif runs == 3:   r = IPL_REWARDS["three"]
        elif runs == 4:   r = IPL_REWARDS["four"]
        else:             r = IPL_REWARDS["six"]

        s, a = self.last_s, self.last_a
        s2   = self._state(next_bl, next_rn, next_shot)
        if s2 not in self.Q:
            self.Q[s2] = {d: random.uniform(0, 0.5) for d in DELIVERIES}
        old = self._q(s, a)
        new = old + ALPHA_RL * (r + GAMMA_RL * min(self.Q[s2].values()) - old)
        self.Q[s][a] = new
        self.history.append({
            "delivery": a, "reward": r,
            "old_q": round(old,3), "new_q": round(new,3),
            "delta": round(new-old, 3)
        })


# ═══════════════════════════════════════════════════════════════════════════
#  COMBINED AI DECISION  (majority vote of all 3 bowling algorithms)
# ═══════════════════════════════════════════════════════════════════════════

def ai_bowl(balls_left: int, runs_needed: int, last_shot: str,
            ql: QLearner, balls_done: int = 0) -> Tuple[str, dict]:
    """
    Combines Minimax + Bayesian + Q-Learning via majority vote.
    Returns (final_delivery, reasoning_dict).
    """
    pitch = infer_pitch(balls_done)
    mood  = infer_mood(balls_left, runs_needed)

    mm_d,  tree = minimax_choose()
    bay_d        = bayesian_delivery(pitch, mood)
    ql_d         = ql.choose(balls_left, runs_needed, last_shot)

    # Majority vote
    votes = Counter([mm_d, bay_d, ql_d])
    final = votes.most_common(1)[0][0]

    # Best child info for display
    valid = [c for c in tree.children if not c.pruned and c.score is not None]
    best_child = min(valid, key=lambda c: c.score) if valid else None
    pruned_count = sum(1 for c in tree.children if c.pruned)

    return final, {
        "minimax"      : mm_d,
        "bayesian"     : bay_d,
        "qlearn"       : ql_d,
        "final"        : final,
        "pitch"        : pitch,
        "mood"         : mood,
        "shot_probs"   : shot_probs(pitch, mood),
        "tree"         : tree,
        "mm_score"     : best_child.score if best_child else 0,
        "pruned_count" : pruned_count,
        "ipl_trained"  : True,
    }
