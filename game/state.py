"""
game/state.py  —  Complete game state
"""
from engine.ai import QLearner

class GameState:
    def __init__(self):
        # Toss
        self.human_call   = None
        self.coin_result  = None
        self.toss_winner  = None
        self.human_role   = None   # "BAT" | "BOWL"
        self.ai_role      = None

        # Match config
        self.overs = 1

        # Innings
        self.innings1_batting = None   # "human"|"ai"
        self.innings2_batting = None
        self.innings          = 1
        self.scores           = {"human": 0, "ai": 0}
        self.wickets          = {"human": 0, "ai": 0}
        self.balls            = {1: [], 2: []}

        # Field
        self.field_positions  = {}

        # Bayesian context
        self.pitch = "Flat"
        self.mood  = "Aggressive"
        self.shot_probs = {}

        # Q-Learner
        self.ql = QLearner()

        # Last ball AI reasoning
        self.ai_reasoning = {}
        self.last_shot    = "None"
        self.last_result  = None

        # Winner
        self.winner         = None
        self.result_message = ""

    def set_toss(self, human_call, coin_result, toss_winner, human_role):
        self.human_call  = human_call
        self.coin_result = coin_result
        self.toss_winner = toss_winner
        self.human_role  = human_role
        self.ai_role     = "BOWL" if human_role=="BAT" else "BAT"
        self.innings1_batting = "human" if human_role=="BAT" else "ai"
        self.innings2_batting = "ai"    if human_role=="BAT" else "human"

    def current_batting(self):
        return self.innings1_batting if self.innings==1 else self.innings2_batting

    def record_ball(self, runs, wicket):
        entry = {"runs": runs, "wicket": wicket}
        self.balls[self.innings].append(entry)
        batter = self.current_batting()
        self.scores[batter]  += runs
        self.wickets[batter] += int(wicket)

    def balls_done(self):
        return len(self.balls[self.innings])

    def balls_left(self):
        return max(0, 6 - self.balls_done())

    def target(self):
        return (self.scores["human"] if self.innings1_batting=="human"
                else self.scores["ai"]) + 1

    def chasing_score(self):
        return self.scores["human"] if self.innings2_batting=="human" \
               else self.scores["ai"]

    def determine_winner(self):
        h = self.scores["human"]
        a = self.scores["ai"]
        if h > a:
            self.winner = "human"
            self.result_message = f"🎉 You win by {h-a} run{'s' if h-a!=1 else ''}!"
        elif a > h:
            self.winner = "ai"
            self.result_message = f"🤖 AI wins by {a-h} run{'s' if a-h!=1 else ''}!"
        else:
            self.winner = "tie"
            self.result_message = "🤝 It's a tie — Super Over needed!"
        return self.winner
