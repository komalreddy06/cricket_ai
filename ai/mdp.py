"""
UNIT III — Markov Decision Process + Value Iteration (EIE115R01)
================================================================
Defines the AI bowling STRATEGY as an MDP:

  States  : (balls_remaining ∈ {1..6},
             runs_bucket ∈ {0,5,10,…,50},
             wickets_taken ∈ {0,1,2})
             → 6 × 11 × 3 = 198 states

  Actions : {fast_yorker, fast_bouncer, off_stump,
             leg_spin_googly, wide_line_spin}  (5 actions)

  Transition: Stochastic outcomes {wicket, dot, single, four, six}
              with P(outcome | action) defined below

  Reward  : wicket=+10, dot=+3, single=+0, four=-3, six=-7
            + context bonuses at end-state

  Solution: Value Iteration (Policy Iteration alternative also shown)

Reference: AIMA 4th Ed., Ch. 17
"""

import math
import itertools
import random


# ── MDP Parameters ────────────────────────────────────────────────────────────

ACTIONS = ["fast_yorker", "fast_bouncer", "off_stump", "leg_spin_googly", "wide_line"]

# P(outcome | action)
TRANSITION = {
    "fast_yorker":    {"wicket": 0.38, "dot": 0.30, "single": 0.18, "four": 0.10, "six": 0.04},
    "fast_bouncer":   {"wicket": 0.20, "dot": 0.22, "single": 0.24, "four": 0.20, "six": 0.14},
    "off_stump":      {"wicket": 0.28, "dot": 0.30, "single": 0.24, "four": 0.14, "six": 0.04},
    "leg_spin_googly":{"wicket": 0.26, "dot": 0.26, "single": 0.24, "four": 0.14, "six": 0.10},
    "wide_line":      {"wicket": 0.05, "dot": 0.28, "single": 0.34, "four": 0.24, "six": 0.09},
}

# R(outcome)
REWARDS = {"wicket": 10, "dot": 3, "single": 0, "four": -3, "six": -7}

# Run values for transition (how many runs scored)
RUN_VALUES = {"wicket": 0, "dot": 0, "single": 1, "four": 4, "six": 6}

BALLS_RANGE   = list(range(1, 7))       # 1..6
RUNS_BUCKET   = list(range(0, 55, 5))   # 0,5,10,…,50
WICKETS_RANGE = [0, 1, 2]


class CricketMDP:
    """
    MDP bowling strategy with Value Iteration.
    After calling value_iteration(), use get_optimal_action() per ball.
    """

    def __init__(self, gamma=0.95):
        self.gamma = gamma
        self.states = list(itertools.product(BALLS_RANGE, RUNS_BUCKET, WICKETS_RANGE))
        self.V      = {s: 0.0 for s in self.states}
        self.policy = {s: "off_stump" for s in self.states}
        self._solved = False

    # ── State Helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _next_state(state, outcome):
        balls, runs_bucket, wkts = state
        new_balls = max(0, balls - 1)
        new_wkts  = min(2, wkts + (1 if outcome == "wicket" else 0))
        runs_given = RUN_VALUES[outcome]
        new_runs   = max(0, runs_bucket - runs_given)
        new_runs   = (new_runs // 5) * 5            # discretise
        return (new_balls, new_runs, new_wkts)

    @staticmethod
    def _reward(state, outcome):
        balls, runs_bucket, wkts = state
        r = REWARDS[outcome]
        # Bonus: wicket when few runs remain to defend
        if outcome == "wicket" and runs_bucket <= 10:
            r += 5
        # Penalty: boundary when runs buffer is small
        if outcome in ("four", "six") and runs_bucket <= 10:
            r -= 4
        return r

    # ── Value Iteration ────────────────────────────────────────────────────

    def value_iteration(self, theta=1e-4, max_iter=500):
        """
        Standard value iteration:
        V(s) ← max_a Σ_o P(o|a) · [R(s,o) + γ·V(s')]
        Runs until max |ΔV| < theta.
        """
        for iteration in range(max_iter):
            delta = 0.0
            new_V = {}
            new_policy = {}

            for s in self.states:
                balls, runs_bucket, wkts = s
                if balls == 0:
                    new_V[s] = 0.0
                    new_policy[s] = "off_stump"
                    continue

                best_val    = -math.inf
                best_action = ACTIONS[0]
                for action in ACTIONS:
                    q = 0.0
                    for outcome, prob in TRANSITION[action].items():
                        r  = self._reward(s, outcome)
                        ns = self._next_state(s, outcome)
                        q += prob * (r + self.gamma * self.V.get(ns, 0.0))
                    if q > best_val:
                        best_val    = q
                        best_action = action

                new_V[s]      = best_val
                new_policy[s] = best_action
                delta = max(delta, abs(best_val - self.V.get(s, 0.0)))

            self.V.update(new_V)
            self.policy.update(new_policy)

            if delta < theta:
                print(f"[MDP] Value iteration converged in {iteration+1} steps (delta={delta:.6f})")
                break

        self._solved = True

    # ── Policy Iteration (Alternative) ────────────────────────────────────

    def policy_iteration(self, max_iter=100):
        """Alternative to value_iteration using policy iteration."""
        for _ in range(max_iter):
            # Policy Evaluation
            for _ in range(30):
                for s in self.states:
                    balls = s[0]
                    if balls == 0:
                        self.V[s] = 0.0
                        continue
                    a = self.policy[s]
                    q = 0.0
                    for outcome, prob in TRANSITION[a].items():
                        r  = self._reward(s, outcome)
                        ns = self._next_state(s, outcome)
                        q += prob * (r + self.gamma * self.V.get(ns, 0.0))
                    self.V[s] = q

            # Policy Improvement
            stable = True
            for s in self.states:
                old_action = self.policy[s]
                best_val   = -math.inf
                best_a     = old_action
                for a in ACTIONS:
                    q = sum(p * (self._reward(s, o) + self.gamma * self.V.get(self._next_state(s, o), 0.0))
                            for o, p in TRANSITION[a].items())
                    if q > best_val:
                        best_val = q
                        best_a   = a
                self.policy[s] = best_a
                if best_a != old_action:
                    stable = False

            if stable:
                break

        self._solved = True

    # ── Public API ─────────────────────────────────────────────────────────

    def _discretise(self, balls_remaining, runs_to_defend, wickets_taken):
        b = max(1, min(6, int(balls_remaining)))
        r = min(50, (int(runs_to_defend) // 5) * 5)
        w = min(2, int(wickets_taken))
        return (b, r, w)

    def get_optimal_action(self, balls_remaining, runs_to_defend, wickets_taken):
        """
        Returns strategy string for Minimax to use.
        Possible: "aggressive", "balanced", "tricky", "defensive"
        """
        if not self._solved:
            self.value_iteration()

        s = self._discretise(balls_remaining, runs_to_defend, wickets_taken)
        optimal = self.policy.get(s, "off_stump")

        strategy_map = {
            "fast_yorker":     "aggressive",
            "fast_bouncer":    "aggressive",
            "off_stump":       "balanced",
            "leg_spin_googly": "tricky",
            "wide_line":       "defensive",
        }
        return strategy_map.get(optimal, "balanced")

    def get_state_value(self, balls_remaining, runs_to_defend, wickets_taken):
        """Query the value of a state (useful for debugging)."""
        s = self._discretise(balls_remaining, runs_to_defend, wickets_taken)
        return self.V.get(s, 0.0)
