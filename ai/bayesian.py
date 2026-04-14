"""
UNIT III — Bayesian Networks (EIE115R01)
========================================
Network structure:
  DeliveryType ──► ShotType ──► ShotDirection
        ▲
  BatsmanHistory  (prior updates via belief update)

Conditional Probability Tables (CPTs) are initialised from cricket domain
knowledge and updated after each observed ball using Bayesian belief update:

  P(Shot|Delivery, History) ∝ P(History|Shot) · P(Shot|Delivery)

Reference: AIMA 4th Ed., Ch. 13-14
"""

import math
import random
from collections import defaultdict


class CricketBayesianNetwork:
    """
    Bayesian shot-prediction network.
    Predicts what shot a human batsman will play given a delivery.
    Updates its beliefs every ball based on observed outcomes.
    """

    # ── Initial CPT: P(ShotType | DeliveryType) ───────────────────────────
    _PRIOR_CPT = {
        "yorker": {
            "flick": 0.35, "drive": 0.18, "defend": 0.28, "sweep": 0.10,
            "pull": 0.04, "cut": 0.05,
        },
        "bouncer": {
            "pull": 0.48, "hook": 0.22, "cut": 0.12, "defend": 0.10,
            "drive": 0.08,
        },
        "good_length_off": {
            "drive": 0.38, "cut": 0.22, "defend": 0.26, "back_punch": 0.10,
            "pull": 0.04,
        },
        "good_length_mid": {
            "drive": 0.28, "pull": 0.18, "defend": 0.32, "flick": 0.14,
            "sweep": 0.08,
        },
        "good_length_leg": {
            "flick": 0.38, "sweep": 0.28, "defend": 0.22, "pull": 0.12,
        },
        "full_off": {
            "drive": 0.52, "loft": 0.18, "defend": 0.18, "cut": 0.06,
            "pull": 0.06,
        },
        "full_leg": {
            "flick": 0.48, "sweep": 0.32, "drive": 0.10, "defend": 0.10,
        },
        "short_off": {
            "cut": 0.48, "back_punch": 0.28, "pull": 0.14, "defend": 0.10,
        },
        "short_leg": {
            "pull": 0.52, "hook": 0.28, "flick": 0.10, "defend": 0.10,
        },
        "wide_off": {
            "cut": 0.60, "drive": 0.22, "back_punch": 0.10, "let_go": 0.08,
        },
    }

    # ── CPT: P(DirectionZone | ShotType) ─────────────────────────────────
    _DIR_CPT = {
        "drive":        {"cover": 0.40, "extra_cover": 0.25, "mid_off": 0.20, "long_off": 0.15},
        "pull":         {"mid_wicket": 0.38, "square_leg": 0.32, "deep_mid_wicket": 0.20, "fine_leg": 0.10},
        "cut":          {"point": 0.48, "gully": 0.28, "third_man": 0.14, "cover_point": 0.10},
        "sweep":        {"mid_wicket": 0.30, "square_leg": 0.38, "fine_leg": 0.22, "deep_fine_leg": 0.10},
        "flick":        {"mid_wicket": 0.50, "fine_leg": 0.28, "square_leg": 0.22},
        "loft":         {"long_on": 0.34, "long_off": 0.34, "deep_mid_wicket": 0.18, "deep_cover": 0.14},
        "defend":       {"1st_slip": 0.30, "mid_on": 0.25, "mid_off": 0.25, "gully": 0.20},
        "back_punch":   {"point": 0.40, "cover_point": 0.30, "gully": 0.20, "cover": 0.10},
        "hook":         {"fine_leg": 0.40, "square_leg": 0.38, "deep_fine_leg": 0.22},
        "straight_drive":{"mid_on": 0.40, "mid_off": 0.35, "long_on": 0.15, "long_off": 0.10},
    }

    def __init__(self):
        # Mutable CPT copy for belief updates
        self.cpt = {k: dict(v) for k, v in self._PRIOR_CPT.items()}
        self.dir_cpt = {k: dict(v) for k, v in self._DIR_CPT.items()}

        # Observation counts for Bayesian update
        self.obs = defaultdict(lambda: defaultdict(int))   # delivery_type → shot → count
        self.dir_obs = defaultdict(lambda: defaultdict(int))

    # ── Delivery Classifier ────────────────────────────────────────────────

    def _classify_delivery(self, tx, tz):
        """Map (target_x, target_z) → CPT row key."""
        if tz <= 2.0:
            return "yorker"
        if tz <= 4.5:
            return "bouncer"

        length = "good_length" if tz <= 9.0 else ("full" if tz <= 13 else "short")
        if tx > 0.30:   line = "off"
        elif tx < -0.30: line = "leg"
        else:            line = "mid"

        return f"{length}_{line}"

    # ── Prediction ────────────────────────────────────────────────────────

    def predict_shot(self, tx, tz, shot_history=None):
        """
        Returns P(Shot | delivery, history) as a probability dict.
        Uses Bayesian belief update to incorporate observed history.
        """
        delivery_type = self._classify_delivery(tx, tz)

        prior = self.cpt.get(delivery_type, {"defend": 1.0})
        shots = list(prior.keys())

        # Observe counts for this delivery type
        total_obs = sum(self.obs[delivery_type].values())

        posterior = {}
        for shot in shots:
            p_prior = prior[shot]
            obs_count = self.obs[delivery_type].get(shot, 0)
            # Bayesian update with Laplace smoothing
            p_likelihood = (obs_count + 1) / (total_obs + len(shots))
            posterior[shot] = p_prior * p_likelihood

        # Normalise
        total = sum(posterior.values())
        if total > 0:
            posterior = {k: v / total for k, v in posterior.items()}

        # Recency bias: shots in last 2 balls are 30 % more likely
        if shot_history:
            for recent in shot_history[-2:]:
                if recent in posterior:
                    posterior[recent] *= 1.30
            total = sum(posterior.values())
            posterior = {k: v / total for k, v in posterior.items()}

        return posterior   # {shot_name: probability}

    def predict_direction(self, shot_type):
        """
        Returns most likely field zone the ball will travel to.
        P(zone | shot) from dir_cpt.
        """
        dist = self.dir_cpt.get(shot_type, {"mid_on": 0.5, "mid_off": 0.5})
        zones = list(dist.keys())
        probs = list(dist.values())
        # Weighted sample
        r = random.random()
        cumul = 0.0
        for z, p in zip(zones, probs):
            cumul += p
            if r <= cumul:
                return z
        return zones[-1]

    def estimate_timing(self, bowl_type, speed):
        """
        Estimate AI batsman's timing score (0..1).
        Faster deliveries are harder to time → lower mean, higher variance.
        """
        if bowl_type == "fast":
            mu    = max(0.3, 0.75 - (speed - 120) * 0.003)
            sigma = 0.10
        else:
            mu    = 0.72
            sigma = 0.08
        return round(max(0.05, min(1.0, random.gauss(mu, sigma))), 3)

    # ── Belief Update ─────────────────────────────────────────────────────

    def update(self, tx, tz, actual_shot, actual_direction_deg=None):
        """
        Bayesian belief update after observing a real ball outcome.
        Updates both the shot CPT and direction CPT.
        """
        delivery_type = self._classify_delivery(tx, tz)
        if actual_shot:
            self.obs[delivery_type][actual_shot] += 1

            # Soft update to CPT (EMA-style)
            prior = self.cpt.get(delivery_type, {})
            if actual_shot not in prior:
                prior[actual_shot] = 0.01
            for s in prior:
                if s == actual_shot:
                    prior[s] = min(0.95, prior[s] * 1.1)
                else:
                    prior[s] = max(0.01, prior[s] * 0.95)
            # Renormalise
            t = sum(prior.values())
            self.cpt[delivery_type] = {k: v / t for k, v in prior.items()}

        if actual_shot and actual_direction_deg is not None:
            zone = self._angle_to_zone(actual_direction_deg)
            self.dir_obs[actual_shot][zone] += 1
            # Update dir CPT
            d = self.dir_cpt.get(actual_shot, {})
            d[zone] = d.get(zone, 0.0) + 0.15
            t = sum(d.values())
            self.dir_cpt[actual_shot] = {k: v / t for k, v in d.items()}

    # ── Utility ───────────────────────────────────────────────────────────

    @staticmethod
    def _angle_to_zone(angle_deg):
        a = angle_deg % 360
        if a < 22:   return "third_man"
        if a < 55:   return "point"
        if a < 85:   return "cover"
        if a < 105:  return "mid_off"
        if a < 130:  return "straight"
        if a < 160:  return "mid_on"
        if a < 200:  return "mid_wicket"
        if a < 240:  return "square_leg"
        if a < 280:  return "fine_leg"
        return "deep_fine_leg"
