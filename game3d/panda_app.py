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
        self.balls = 0
        self.runs = 0
        self.wickets = 0

        self.btns = []
        self.hud_nodes = []

        self._set_camera_toss()
        self._build_lights()
        self._build_stadium()
        self._build_players()
        self._build_broadcast_hud()
        self._build_toss_ui()

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

        # mowing stripes
        self.stripes = []
        for i in range(10):
            shade = 0.26 if i % 2 == 0 else 0.20
            stripe = self._box((0, -55 + i * 11, -0.52), (120, 10.5, 0.08), (0.18, shade, 0.19, 1))
            self.stripes.append(stripe)

        self.pitch = self._box((0, 0, 0.1), (4.2, 28, 0.18), (0.72, 0.62, 0.42, 1))

        # 360 stands + crowd
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

        # floodlights
        self.floodlights = []
        for x, y in [(-56, -56), (56, -56), (-56, 56), (56, 56)]:
            pole = self._box((x, y, 14), (0.7, 0.7, 28), (0.65, 0.68, 0.75, 1))
            lamp = self._box((x, y, 28.8), (7.0, 2.6, 1.0), (0.97, 0.95, 0.8, 1))
            self.floodlights.extend([pole, lamp])

    def _build_players(self):
        # Toss scene lineup
        self.presenter = self._box((-8, -2, 2.4), (1.1, 1.1, 4.8), (0.15, 0.16, 0.2, 1))
        self.human_cap = self._box((-2.6, 0, 2.3), (1.15, 1.15, 4.6), (0.95, 0.4, 0.1, 1))
        self.ai_cap = self._box((2.6, 0, 2.3), (1.15, 1.15, 4.6), (0.8, 0.85, 0.95, 1))
        self.umpire = self._box((8, -1.5, 2.3), (1.1, 1.1, 4.6), (0.68, 0.77, 0.9, 1))

        self.ball = self.loader.loadModel("models/smiley")
        self.ball.reparentTo(self.render)
        self.ball.setScale(0.42)
        self.ball.setColor(0.88, 0.26, 0.14, 1)
        self.ball.setPos(0, 2, 5.0)

        # Match players
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
        self.hud_nodes.append(self.top_bar)

        self.team_left = OnscreenText(text="SRH 0/0", pos=(-0.95, 0.86), scale=0.07, fg=(1, 0.65, 0.2, 1), align=TextNode.ALeft)
        self.team_mid = OnscreenText(text="Overs", pos=(0, 0.86), scale=0.055, fg=(1, 1, 0.9, 1))
        self.team_right = OnscreenText(text="AI XI 0/0", pos=(0.95, 0.86), scale=0.07, fg=(0.78, 0.9, 1, 1), align=TextNode.ARight)
        self.msg = OnscreenText(text="MAKE YOUR CALL", pos=(0, 0.72), scale=0.08, fg=(1, 1, 1, 1))

        loaded = f"IPL dataset loaded: {self.model.rows:,} balls" if self.model.loaded else "No IPL CSV found (using fallback priors)"
        self.data_label = OnscreenText(text=loaded, pos=(-1.33, 0.96), scale=0.043, fg=(0.8, 1, 0.85, 1), align=TextNode.ALeft)

    def _clear_buttons(self):
        for b in self.btns:
            b.destroy()
        self.btns = []

    def _btn(self, text, x, y, scale, color, cmd):
        b = DirectButton(text=text, text_scale=0.65, scale=scale, pos=(x, 0, y),
                         frameColor=color, relief=1, command=cmd)
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
        self.msg.setText(f"COIN: {coin}  |  {'YOU WON TOSS' if coin == call else 'AI WON TOSS'}")
        self.mode = "choice"
        self._show_choice_buttons()

    def _show_choice_buttons(self):
        self._clear_buttons()
        self._btn("BAT", -0.36, -0.82, 0.10, (0.95, 0.45, 0.1, 1), lambda: self._start_match("BAT"))
        self._btn("BOWL", 0.36, -0.82, 0.10, (0.2, 0.45, 0.9, 1), lambda: self._start_match("BOWL"))

    def _start_match(self, role):
        self.mode = "match"
        self._clear_buttons()
        self._set_camera_match()

        self.presenter.hide(); self.human_cap.hide(); self.ai_cap.hide(); self.umpire.hide()
        self.batsman.show(); self.bowler.show()
        for f in self.fielders:
            f.show()

        self.msg.setText(f"You chose {role}. Select SHOT + DIRECTION")

        for i, shot in enumerate(["DEFEND", "PUSH", "STROKE", "LOFT"]):
            x = -0.78 + i * 0.52
            self._btn(shot, x, -0.84, 0.072, (0.14, 0.3, 0.56, 1), lambda s=shot: self._play_ball(s))

        for i, d in enumerate(["LEG", "STRAIGHT", "OFF"]):
            x = -0.40 + i * 0.40
            self._btn(d, x, -0.68, 0.062, (0.36, 0.55, 0.76, 1), lambda dd=d: self._set_direction(dd))

        self.balls = 0
        self.runs = 0
        self.wickets = 0
        self._update_score()

    def _set_direction(self, direction):
        self.current_direction = direction
        self.msg.setText(f"Direction: {direction} | choose shot")

    def _update_score(self):
        over_txt = f"{self.balls // 6}.{self.balls % 6}"
        self.team_left.setText(f"SRH {self.runs}/{self.wickets}")
        self.team_mid.setText(f"Overs {over_txt}")
        self.team_right.setText("AI XI 0/0")

    def _play_ball(self, shot):
        if self.mode != "match":
            return

        self.balls += 1
        out = self.model.sample_ball(self.balls - 1, shot, self.current_direction)
        if out.wicket:
            self.wickets += 1
        else:
            self.runs += out.runs

        self._update_score()
        self.msg.setText(out.desc)
        self.ball.setPos(*out.landing)

        if self.balls >= 6 or self.wickets >= 1:
            self.msg.setText(out.desc + " | INNINGS COMPLETE")
            for b in self.btns:
                b["state"] = "disabled"
