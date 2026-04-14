"""
UNIT IV — Q-Learning for AI Batting (EIE115R01)
================================================
The AI batsman learns an optimal shot-selection policy by interacting
with the bowling environment (trial-and-error, no supervisor).

State  : (bowl_type, line, length)  e.g. ("fast", "off_stump", "good_length")
Action : shot type string           e.g. "drive", "pull", "defend" …
Reward : runs_scored − wicket_penalty

Update rule  (Bellman equation):
  Q(s,a) ← Q(s,a) + α · [r + γ · max_a' Q(s',a') − Q(s,a)]

Exploration : ε-greedy with exponential decay (more exploit over time)
Persistence : Q-table saved to JSON so the AI improves across sessions.

Reference: AIMA 4th Ed., Ch. 22;  Graesser & Keng, Ch. 2
"""

import random
import math
import json
import os
from collections import defaultdict


ACTIONS = [
    "drive", "pull", "cut", "sweep", "flick",
    "loft", "defend", "back_punch", "straight_drive",
]

# Reward signal helpers
ACTION_BASE_RUNS = {
    "drive": 2.8, "pull": 4.0, "cut": 2.5, "sweep": 2.2,
    "flick": 2.4, "loft": 5.0, "defend": 0.0,
    "back_punch": 1.8, "straight_drive": 3.2,
}
ACTION_WICKET_RISK = {
    "drive": 0.12, "pull": 0.28, "cut": 0.08, "sweep": 0.20,
    "flick": 0.10, "loft": 0.38, "defend": 0.01,
    "back_punch": 0.06, "straight_drive": 0.14,
}

BOWL_TYPES  = ["fast", "spin"]
LINES       = ["off_stump", "middle", "leg_stump", "wide_off"]
LENGTHS     = ["short", "good_length", "full", "yorker"]

Q_TABLE_FILE = "q_table_batting.json"


class CricketQLearning:
    """
    Q-Learning agent for AI batting shot selection.
    Supports persistence (saves/loads Q-table between sessions).
    """

    def __init__(self, alpha=0.12, gamma=0.90, epsilon=0.35, epsilon_min=0.05):
        self.alpha       = alpha
        self.gamma       = gamma
        self.epsilon     = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = 0.92     # decay per over (6 balls)

        # Q-table: state_key → {action: Q-value}
        self._q: dict[str, dict[str, float]] = defaultdict(
            lambda: {a: 0.0 for a in ACTIONS}
        )

        # Episode stats
        self.episode        = 0
        self.reward_history = []

        self._load()

    # ── State Encoding ─────────────────────────────────────────────────────

    @staticmethod
    def encode_state(bowl_type, line, length):
        """Convert state components to hashable key."""
        return f"{bowl_type}|{line}|{length}"

    @staticmethod
    def classify_delivery(tx, tz, bowl_type):
        """Map raw delivery coords → (bowl_type, line, length) state."""
        if tz <= 2.0:  length = "yorker"
        elif tz <= 5.0: length = "short"
        elif tz <= 9.5: length = "good_length"
        else:           length = "full"

        if tx > 0.32:   line = "off_stump"
        elif tx > 0.80: line = "wide_off"
        elif tx < -0.32: line = "leg_stump"
        else:            line = "middle"

        return bowl_type, line, length

    # ── Action Selection ───────────────────────────────────────────────────

    def get_action(self, bowl_type, line, length):
        """
        ε-greedy action selection.
        • With prob ε  → explore: random action
        • With prob 1-ε → exploit: argmax Q(s, ·)
        """
        state_key = self.encode_state(bowl_type, line, length)

        # ── Validity filter: some shots don't make sense ────────────────
        valid = list(ACTIONS)
        if length == "yorker":
            valid = [a for a in valid if a not in ("pull",)]
        elif length == "short":
            valid = [a for a in valid if a not in ("drive", "sweep")]

        if random.random() < self.epsilon:
            return random.choice(valid)

        q_vals = self._q[state_key]
        # Filter Q-vals to valid actions
        valid_q = {a: q_vals.get(a, 0.0) for a in valid}
        return max(valid_q, key=valid_q.get)

    # ── Q-Learning Update ──────────────────────────────────────────────────

    def update(self, bowl_type, line, length,
               action, reward,
               next_bowl_type, next_line, next_length):
        """
        Q(s,a) ← Q(s,a) + α·[r + γ·max_a' Q(s',a') − Q(s,a)]
        """
        s_key  = self.encode_state(bowl_type, line, length)
        ns_key = self.encode_state(next_bowl_type, next_line, next_length)

        current_q  = self._q[s_key].get(action, 0.0)
        max_next_q = max(self._q[ns_key].values()) if self._q[ns_key] else 0.0

        td_target = reward + self.gamma * max_next_q
        td_error  = td_target - current_q
        self._q[s_key][action] = current_q + self.alpha * td_error

        self.episode        += 1
        self.reward_history.append(reward)

        # Decay exploration every 6 balls (one over)
        if self.episode % 6 == 0:
            self.epsilon = max(self.epsilon_min,
                               self.epsilon * self.epsilon_decay)
            self._save()

    # ── Reward Calculator ──────────────────────────────────────────────────

    @staticmethod
    def compute_reward(runs_scored, got_out):
        """
        Reward shaping:
          +runs_scored (1..6)
          −10 for wicket
          −0.5 for dot ball
        """
        if got_out:
            return -10.0
        if runs_scored == 0:
            return -0.5
        return float(runs_scored)

    # ── Q-table Utilities ──────────────────────────────────────────────────

    def best_action_for(self, bowl_type, line, length):
        """Return greedy best action for a state (no exploration)."""
        key = self.encode_state(bowl_type, line, length)
        return max(self._q[key], key=self._q[key].get)

    def get_q_values(self, bowl_type, line, length):
        """Return full Q-value dict for inspection."""
        return dict(self._q[self.encode_state(bowl_type, line, length)])

    def softmax_probs(self, bowl_type, line, length, temperature=1.0):
        """Return softmax probability distribution over actions."""
        q_vals = self.get_q_values(bowl_type, line, length)
        exp_vals = {a: math.exp(v / temperature) for a, v in q_vals.items()}
        total = sum(exp_vals.values())
        return {a: v / total for a, v in exp_vals.items()} if total else {}

    # ── Persistence ────────────────────────────────────────────────────────

    def _save(self):
        try:
            data = {k: dict(v) for k, v in self._q.items()}
            with open(Q_TABLE_FILE, "w") as f:
                json.dump({"q_table": data,
                           "epsilon": self.epsilon,
                           "episode": self.episode}, f)
        except Exception:
            pass

    def _load(self):
        try:
            if os.path.exists(Q_TABLE_FILE):
                with open(Q_TABLE_FILE) as f:
                    data = json.load(f)
                for k, v in data.get("q_table", {}).items():
                    self._q[k] = v
                self.epsilon = data.get("epsilon", self.epsilon)
                self.episode = data.get("episode", 0)
                print(f"[QL] Loaded Q-table: {len(self._q)} states, "
                      f"ε={self.epsilon:.3f}, ep={self.episode}")
        except Exception:
            pass
