"""
UNIT II — Constraint Satisfaction Problem (EIE115R01)
======================================================
Variables : 9 fielder slots (F1..F9)
Domains   : Named field zones (slip, cover, mid-on, etc.)
Constraints:
  1. No two fielders in the same zone
  2. At least one fielder in slip cordon
  3. Field covers the highest-probability shot direction(s)
  4. No fielder beyond boundary (>35 m)

Solution algorithm: Backtracking search with
  - MRV  (Minimum Remaining Values) for variable ordering
  - LCV  (Least Constraining Value) for value ordering

Reference: AIMA 4th Ed., Ch. 6
"""

import random


# ──────────────────────────────────────────────────────────────────────────────
# Field Zone Definitions  (x, z) in cricket pitch coords
#   • x = 0 is centre of pitch; positive = off-side, negative = on-side
#   • z = 0 is batting crease; z > 0 is towards bowler (field)
# ──────────────────────────────────────────────────────────────────────────────

ZONES = {
    # Cordon (behind-the-bat)
    "1st_slip":         (3.0,  -3.0),
    "2nd_slip":         (4.5,  -3.5),
    "gully":            (6.0,  -1.0),
    # Off-side
    "point":            (14.0,  2.0),
    "cover_point":      (18.0,  8.0),
    "cover":            (16.0, 14.0),
    "extra_cover":      (13.0, 18.0),
    "mid_off":          (6.0,  20.0),
    "long_off":         (10.0, 32.0),
    "deep_cover":       (25.0, 14.0),
    "deep_point":       (28.0,  3.0),
    "third_man":        (12.0,-28.0),
    # On-side
    "mid_on":           (-6.0, 20.0),
    "mid_wicket":       (-15.0,12.0),
    "square_leg":       (-8.0,  0.0),
    "fine_leg":         (-8.0,-28.0),
    "deep_fine_leg":    (-15.0,-30.0),
    "deep_mid_wicket":  (-27.0,10.0),
    "deep_square_leg":  (-28.0, 1.0),
    "long_on":          (-12.0,30.0),
    # Straight
    "silly_mid_on":     (-3.0, 10.0),
    "silly_mid_off":    ( 3.0, 10.0),
    "short_leg":        (-2.0,  2.0),
}

ALL_ZONES = list(ZONES.keys())

# Shot → zones where the ball typically goes
SHOT_ZONE_MAP = {
    "drive":        ["cover", "extra_cover", "mid_off", "long_off"],
    "pull":         ["mid_wicket", "deep_mid_wicket", "square_leg", "deep_square_leg"],
    "cut":          ["point", "cover_point", "deep_point", "gully"],
    "sweep":        ["mid_wicket", "square_leg", "fine_leg", "deep_fine_leg"],
    "flick":        ["mid_wicket", "fine_leg", "deep_fine_leg"],
    "hook":         ["square_leg", "fine_leg", "deep_mid_wicket"],
    "loft":         ["long_on", "long_off", "deep_mid_wicket", "deep_cover"],
    "defend":       ["1st_slip", "2nd_slip", "gully"],
    "straight_drive":["mid_on", "mid_off", "long_on", "long_off"],
    "back_punch":   ["point", "cover_point", "gully"],
    "squeeze":      ["1st_slip", "gully", "third_man"],
    "jam_down":     ["mid_wicket", "mid_on"],
}


class FieldPlacementCSP:
    """
    CSP to place 9 fielders optimally given predicted shot distribution.
    """

    NUM_FIELDERS = 9

    def __init__(self):
        self.variables = [f"F{i+1}" for i in range(self.NUM_FIELDERS)]
        self.all_zones  = ALL_ZONES

    # ── Constraint Checks ──────────────────────────────────────────────────

    def _no_overlap(self, assignment, zone):
        """Constraint: no two fielders in the same zone."""
        return zone not in assignment.values()

    def _slip_present(self, assignment):
        """Constraint: at least one slip in assignment (only enforced at end)."""
        slip_zones = {"1st_slip", "2nd_slip"}
        return bool(slip_zones & set(assignment.values()))

    def _is_consistent(self, assignment, var, zone):
        """Returns True if adding var=zone to assignment is consistent."""
        return self._no_overlap(assignment, zone)

    # ── Variable & Value Ordering ──────────────────────────────────────────

    def _select_unassigned(self, assignment):
        """MRV: pick variable with fewest remaining legal values."""
        unassigned = [v for v in self.variables if v not in assignment]
        # Count legal zones per variable
        def remaining(v):
            return sum(1 for z in self.all_zones
                       if self._is_consistent(assignment, v, z))
        return min(unassigned, key=remaining)

    def _order_domain(self, var, assignment, priority_zones):
        """LCV: prefer zones that appear in priority_zones (shot coverage)."""
        def score(z):
            base = priority_zones.get(z, 0.0)
            # Penalise: assigning this zone to var should leave other vars options
            future_conflict = sum(
                1 for other in self.variables
                if other != var and other not in assignment and z in self.all_zones
            )
            return base - future_conflict * 0.01
        return sorted(self.all_zones, key=score, reverse=True)

    # ── Backtracking Search ────────────────────────────────────────────────

    def _backtrack(self, assignment, priority_zones):
        if len(assignment) == len(self.variables):
            # Final constraint: ensure slip is covered
            if not self._slip_present(assignment):
                # Force last slot to slip
                last_var = list(assignment.keys())[-1]
                if "1st_slip" not in assignment.values():
                    assignment[last_var] = "1st_slip"
            return assignment

        var = self._select_unassigned(assignment)

        for zone in self._order_domain(var, assignment, priority_zones):
            if self._is_consistent(assignment, var, zone):
                assignment[var] = zone
                result = self._backtrack(assignment, priority_zones)
                if result is not None:
                    return result
                del assignment[var]

        return None  # No solution from this branch

    # ── Public API ────────────────────────────────────────────────────────

    def build_priority_map(self, shot_distribution):
        """
        shot_distribution: dict {shot_name: probability}
        Returns zone priority map {zone_name: coverage_score}
        """
        priority = {}
        for shot, prob in shot_distribution.items():
            for zone in SHOT_ZONE_MAP.get(shot, []):
                priority[zone] = priority.get(zone, 0.0) + prob
        return priority

    def solve(self, shot_distribution):
        """
        Main entry: solve CSP and return list of [x,z] fielder positions.
        shot_distribution e.g. {"drive":0.4, "pull":0.3, "cut":0.3}
        """
        priority_zones = self.build_priority_map(shot_distribution)

        assignment = self._backtrack({}, priority_zones)

        if assignment is None:
            # Fallback: sensible default field
            assignment = {
                "F1": "1st_slip", "F2": "gully",       "F3": "point",
                "F4": "cover",    "F5": "mid_off",      "F6": "mid_on",
                "F7": "mid_wicket","F8": "square_leg",  "F9": "fine_leg",
            }

        positions = []
        for var in self.variables:
            zone = assignment[var]
            x, z = ZONES[zone]
            # Small random jitter for realism
            positions.append([x + random.uniform(-1, 1), z + random.uniform(-1, 1)])

        return positions, assignment
