"""Panda3D-based 3D cricket prototype with broadcast-style UI."""
from __future__ import annotations

import math
import random

from direct.gui.DirectGui import DirectButton, DirectFrame, OnscreenText
from direct.showbase.ShowBase import ShowBase
from panda3d.core import AmbientLight, DirectionalLight, TextNode

from engine.ipl_ai import IPLDataModel


class Cricket3DPandaApp(ShowBase):
    def __init__(self):
        super().__init__()
        self.disableMouse()
        self.setBackgroundColor(0.08, 0.13, 0.32, 1)

        self.model = IPLDataModel()
        self.model.train_from_kaggle_csv()

        self.mode = "toss"
        self.current_direction = "STRAIGHT"
        self.human_role = "BAT"
        self.innings = 1
        self.chasing = False
        self.game_over = False

        self.balls = 0
        self.runs = 0
        self.wickets = 0
        self.target = 0
        self.innings_scores = {"human": 0, "ai": 0}
        self.innings_wickets = {"human": 0, "ai": 0}

        self.btns = []
        self.pending_ai_ball = False

        self._set_camera_toss()
        self._build_lights()
        self._build_stadium()
        self._build_players()
        self._build_broadcast_hud()
        self._build_toss_ui()

        self.taskMgr.add(self._update_task, "cricket_update")

    # ── Scene ─────────────────────────────────────────────────────────────
    def _build_lights(self):
        amb = AmbientLight("amb")
        amb.setColor((0.55, 0.55, 0.60, 1))
        self.render.setLight(self.render.attachNewNode(amb))

        sun = DirectionalLight("sun")
        sun.setColor((0.92, 0.9, 0.82, 1))
        sun_np = self.render.attachNewNode(sun)
        sun_np.setHpr(-25, -55, 0)
        self.render.setLight(sun_np)

    def _set_camera_toss(self):
        self.camera.setPos(0, -64, 23)
        self.camera.lookAt(0, 0, 5)

    def _set_camera_match(self):
        self.camera.setPos(0, -78, 31)
        self.camera.lookAt(0, 2, 2)

    def _box(self, pos, scale, color):
        m = self.loader.loadModel("models/box")
        m.reparentTo(self.render)
        m.setPos(*pos)
        m.setScale(*scale)
        m.setColor(*color)
        return m

    def _build_stadium(self):
        self.ground = self._box((0, 0, -0.6), (126, 126, 1), (0.2, 0.43, 0.2, 1))

        self.stripes = []
        for i in range(10):
            shade = 0.26 if i % 2 == 0 else 0.20
            stripe = self._box((0, -55 + i * 11, -0.52), (120, 10.5, 0.08), (0.18, shade, 0.19, 1))
            self.stripes.append(stripe)

        self.pitch = self._box((0, 0, 0.1), (4.2, 28, 0.18), (0.72, 0.62, 0.42, 1))

        self.stands = []
        self.crowd = []
        for ring, h in [(52, 2), (61, 4), (70, 6)]:
            for i in range(88):
                a = math.radians((360 / 88) * i)
                x = ring * math.cos(a)
                y = ring * math.sin(a)
                b = self._box((x, y, h), (2.3, 2.3, 1.05), (0.13, 0.14, 0.20, 1))
                b.lookAt(0, 0, h)
                self.stands.append(b)

                crowd_col = (
                    (120 + (i * 7) % 120) / 255,
                    (80 + (i * 3) % 150) / 255,
                    (95 + (i * 5) % 150) / 255,
                    1,
                )
                c = self._box((x * 0.986, y * 0.986, h + 0.95), (0.28, 0.28, 0.72), crowd_col)
                self.crowd.append(c)

        self.floodlights = []
        for x, y in [(-56, -56), (56, -56), (-56, 56), (56, 56)]:
            pole = self._box((x, y, 14), (0.7, 0.7, 28), (0.65, 0.68, 0.75, 1))
            lamp = self._box((x, y, 28.8), (7.0, 2.6, 1.0), (0.97, 0.95, 0.8, 1))
            self.floodlights.extend([pole, lamp])

    def _build_players(self):
        self.presenter = self._box((-8, -2, 2.4), (1.1, 1.1, 4.8), (0.15, 0.16, 0.2, 1))
        self.human_cap = self._box((-2.6, 0, 2.3), (1.15, 1.15, 4.6), (0.95, 0.4, 0.1, 1))
        self.ai_cap = self._box((2.6, 0, 2.3), (1.15, 1.15, 4.6), (0.8, 0.85, 0.95, 1))
        self.umpire = self._box((8, -1.5, 2.3), (1.1, 1.1, 4.6), (0.68, 0.77, 0.9, 1))

        self.ball = self.loader.loadModel("models/smiley")
        self.ball.reparentTo(self.render)
        self.ball.setScale(0.42)
        self.ball.setColor(0.88, 0.26, 0.14, 1)
        self.ball.setPos(0, 2, 5.0)

        self.batsman = self._box((1, -16, 2.1), (1.2, 1.2, 4.3), (0.95, 0.4, 0.1, 1))
        self.bowler = self._box((0, 15, 2.1), (1.2, 1.2, 4.3), (0.9, 0.86, 0.92, 1))
        self.batsman.hide(); self.bowler.hide()

        self.fielders = []
        for ang in [20, 58, 100, 150, 205, 245, 300, 336]:
            a = math.radians(ang)
            f = self._box((26 * math.cos(a), 26 * math.sin(a), 1.8), (0.92, 0.92, 3.5), (0.9, 0.86, 0.92, 1))
            f.hide()
            self.fielders.append(f)

    # ── HUD / UI ─────────────────────────────────────────────────────────
    def _build_broadcast_hud(self):
        self.top_bar = DirectFrame(frameColor=(0.02, 0.09, 0.28, 0.9), frameSize=(-1.36, 1.36, -0.12, 0.12), pos=(0, 0, 0.88))

        self.team_left = OnscreenText(text="HUMAN 0/0", pos=(-0.95, 0.86), scale=0.07, fg=(1, 0.65, 0.2, 1), align=TextNode.ALeft)
        self.team_mid = OnscreenText(text="Over 0.0", pos=(0, 0.86), scale=0.055, fg=(1, 1, 0.9, 1))
        self.team_right = OnscreenText(text="AI 0/0", pos=(0.95, 0.86), scale=0.07, fg=(0.78, 0.9, 1, 1), align=TextNode.ARight)
        self.msg = OnscreenText(text="MAKE YOUR CALL", pos=(0, 0.72), scale=0.08, fg=(1, 1, 1, 1))

        loaded = f"IPL dataset loaded: {self.model.rows:,} balls" if self.model.loaded else "No IPL CSV found (using fallback priors)"
        self.data_label = OnscreenText(text=loaded, pos=(-1.33, 0.96), scale=0.043, fg=(0.8, 1, 0.85, 1), align=TextNode.ALeft)

    def _clear_buttons(self):
        for b in self.btns:
            b.destroy()
        self.btns = []

    def _btn(self, text, x, y, scale, color, cmd):
        b = DirectButton(text=text, text_scale=0.65, scale=scale, pos=(x, 0, y), frameColor=color, relief=1, command=cmd)
        self.btns.append(b)

    def _build_toss_ui(self):
        self.mode = "toss"
        self._clear_buttons()
        self.msg.setText("MAKE YOUR CALL")
        self._btn("HEADS", -0.45, -0.82, 0.10, (0.95, 0.45, 0.1, 1), lambda: self._resolve_toss("HEADS"))
        self._btn("TAILS", 0.45, -0.82, 0.10, (0.2, 0.45, 0.9, 1), lambda: self._resolve_toss("TAILS"))

    def _resolve_toss(self, call):
        if self.mode != "toss":
            return
        coin = random.choice(["HEADS", "TAILS"])
        human_won = coin == call
        if human_won:
            self.msg.setText(f"COIN: {coin} | YOU WON TOSS")
            self.mode = "choice"
            self._show_choice_buttons()
            return

        self.human_role = random.choice(["BAT", "BOWL"])
        self.msg.setText(f"COIN: {coin} | AI WON TOSS and chose {'BAT' if self.human_role == 'BOWL' else 'BOWL'}")
        self._start_match(self.human_role)

    def _show_choice_buttons(self):
        self._clear_buttons()
        self._btn("BAT", -0.36, -0.82, 0.10, (0.95, 0.45, 0.1, 1), lambda: self._start_match("BAT"))
        self._btn("BOWL", 0.36, -0.82, 0.10, (0.2, 0.45, 0.9, 1), lambda: self._start_match("BOWL"))

    def _start_match(self, role):
        self.human_role = role
        self.mode = "match"
        self._clear_buttons()
        self._set_camera_match()

        self.presenter.hide(); self.human_cap.hide(); self.ai_cap.hide(); self.umpire.hide()
        self.batsman.show(); self.bowler.show()
        for f in self.fielders:
            f.show()

        self.innings = 1
        self.game_over = False
        self.innings_scores = {"human": 0, "ai": 0}
        self.innings_wickets = {"human": 0, "ai": 0}
        self.target = 0
        self._setup_innings(1)

    def _setup_innings(self, innings_no: int):
        self.innings = innings_no
        self.balls = 0
        self.runs = 0
        self.wickets = 0
        self.pending_ai_ball = False

        self._clear_buttons()
        human_batting = (self.human_role == "BAT" and innings_no == 1) or (self.human_role == "BOWL" and innings_no == 2)
        self.chasing = innings_no == 2

        if human_batting:
            self.msg.setText("Your innings: Select SHOT + DIRECTION")
            for i, shot in enumerate(["DEFEND", "PUSH", "STROKE", "LOFT"]):
                x = -0.78 + i * 0.52
                self._btn(shot, x, -0.84, 0.072, (0.14, 0.3, 0.56, 1), lambda s=shot: self._play_human_ball(s))

            for i, d in enumerate(["LEG", "STRAIGHT", "OFF"]):
                x = -0.40 + i * 0.40
                self._btn(d, x, -0.68, 0.062, (0.36, 0.55, 0.76, 1), lambda dd=d: self._set_direction(dd))
        else:
            self.msg.setText("AI innings in progress...")
            self.pending_ai_ball = True

        self._update_scoreboard()

    def _set_direction(self, direction):
        if self.game_over:
            return
        self.current_direction = direction
        self.msg.setText(f"Direction: {direction} | choose shot")

    def _update_scoreboard(self):
        over_txt = f"{self.balls // 6}.{self.balls % 6}"
        human_batting = (self.human_role == "BAT" and self.innings == 1) or (self.human_role == "BOWL" and self.innings == 2)
        if human_batting:
            human_runs, human_wkts = self.runs, self.wickets
            ai_runs, ai_wkts = self.innings_scores["ai"], self.innings_wickets["ai"]
        else:
            human_runs, human_wkts = self.innings_scores["human"], self.innings_wickets["human"]
            ai_runs, ai_wkts = self.runs, self.wickets

        self.team_left.setText(f"HUMAN {human_runs}/{human_wkts}")
        self.team_mid.setText(f"Over {over_txt} | Innings {self.innings}/2")
        self.team_right.setText(f"AI {ai_runs}/{ai_wkts}")

    def _apply_ball(self, shot: str, direction: str, prefix: str):
        self.balls += 1
        out = self.model.sample_ball(self.balls - 1, shot, direction)
        if out.wicket:
            self.wickets += 1
        else:
            self.runs += out.runs
        self.ball.setPos(*out.landing)
        self._update_scoreboard()
        self.msg.setText(f"{prefix}: {out.desc}")

        if self.chasing and self.target and self.runs >= self.target:
            self._finish_innings(chased=True)
            return

        if self.balls >= 6 or self.wickets >= 1:
            self._finish_innings(chased=False)

    def _play_human_ball(self, shot):
        if self.mode != "match" or self.game_over:
            return
        human_batting = (self.human_role == "BAT" and self.innings == 1) or (self.human_role == "BOWL" and self.innings == 2)
        if not human_batting:
            return
        self._apply_ball(shot, self.current_direction, "YOU")

    def _play_ai_ball(self):
        if self.mode != "match" or self.game_over:
            return
        ai_batting = not ((self.human_role == "BAT" and self.innings == 1) or (self.human_role == "BOWL" and self.innings == 2))
        if not ai_batting:
            return

        balls_left = max(0, 6 - self.balls)
        wickets_left = max(0, 1 - self.wickets)
        target_needed = self.target - self.runs if self.chasing else 999
        shot, direction = self.model.minimax_ai_batting(self.balls, target_needed, balls_left, wickets_left)
        self._apply_ball(shot, direction, "AI")

    def _finish_innings(self, chased: bool):
        human_batting = (self.human_role == "BAT" and self.innings == 1) or (self.human_role == "BOWL" and self.innings == 2)
        if human_batting:
            self.innings_scores["human"] = self.runs
            self.innings_wickets["human"] = self.wickets
        else:
            self.innings_scores["ai"] = self.runs
            self.innings_wickets["ai"] = self.wickets

        if self.innings == 1:
            self.target = self.runs + 1
            self.msg.setText(f"Innings break: Target is {self.target}. Starting second innings...")
            self._setup_innings(2)
            return

        self.game_over = True
        self.pending_ai_ball = False
        self._clear_buttons()
        h = self.innings_scores["human"]
        a = self.innings_scores["ai"]
        if h > a:
            result = f"HUMAN WINS by {h - a} run(s)!"
        elif a > h:
            result = f"AI WINS by {a - h} run(s)!"
        else:
            result = "MATCH TIED"
        suffix = " (CHASE COMPLETED)" if chased else ""
        self.msg.setText(f"{result}{suffix} | Final: HUMAN {h} - AI {a}")
        self.team_mid.setText("Match Complete")

    def _update_task(self, task):
        if self.pending_ai_ball and not self.game_over and self.mode == "match":
            self.pending_ai_ball = False
            self.doMethodLater(0.8, self._delayed_ai_ball, "ai_ball")
        return task.cont

    def _delayed_ai_ball(self, task):
        self._play_ai_ball()
        ai_batting = not ((self.human_role == "BAT" and self.innings == 1) or (self.human_role == "BOWL" and self.innings == 2))
        if ai_batting and not self.game_over and self.mode == "match":
            self.pending_ai_ball = True
        return task.done
