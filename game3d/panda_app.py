"""Panda3D-based 3D cricket prototype (non-Ursina)."""
from __future__ import annotations

import random
import math

from direct.showbase.ShowBase import ShowBase
from direct.gui.DirectGui import DirectButton, OnscreenText
from panda3d.core import AmbientLight, DirectionalLight, LVector3, TextNode

from engine.ipl_ai import IPLDataModel


class Cricket3DPandaApp(ShowBase):
    def __init__(self):
        super().__init__()
        self.disableMouse()

        self.model = IPLDataModel()
        self.model.train_from_kaggle_csv()

        self.mode = "toss"
        self.current_direction = "STRAIGHT"
        self.balls = 0
        self.runs = 0
        self.wickets = 0

        self._set_camera_toss()
        self._build_lights()
        self._build_ground_and_stands()
        self._build_characters()
        self._build_ui()

    def _build_lights(self):
        amb = AmbientLight("amb")
        amb.setColor((0.58, 0.58, 0.58, 1))
        self.render.setLight(self.render.attachNewNode(amb))

        sun = DirectionalLight("sun")
        sun.setColor((0.85, 0.85, 0.8, 1))
        sun_np = self.render.attachNewNode(sun)
        sun_np.setHpr(-35, -50, 0)
        self.render.setLight(sun_np)

    def _set_camera_toss(self):
        self.camera.setPos(0, -58, 24)
        self.camera.lookAt(0, 0, 5)

    def _set_camera_match(self):
        self.camera.setPos(0, -72, 30)
        self.camera.lookAt(0, 2, 2)

    def _make_box(self, pos, scale, color):
        m = self.loader.loadModel("models/box")
        m.reparentTo(self.render)
        m.setPos(*pos)
        m.setScale(*scale)
        m.setColor(*color)
        return m

    def _build_ground_and_stands(self):
        self.ground = self._make_box((0, 0, -0.6), (120, 120, 1), (0.25, 0.48, 0.24, 1))
        self.pitch = self._make_box((0, 0, 0.1), (4, 26, 0.2), (0.72, 0.62, 0.42, 1))

        self.stands = []
        self.crowd = []
        for ring, h in [(50, 2), (58, 4), (66, 6)]:
            for i in range(72):
                a = math.radians((360 / 72) * i)
                x = ring * math.cos(a)
                y = ring * math.sin(a)
                b = self._make_box((x, y, h), (2.5, 2.5, 1.1), (0.18, 0.2, 0.26, 1))
                b.lookAt(0, 0, h)
                self.stands.append(b)

                cc = (
                    (90 + (i * 3) % 150) / 255,
                    (80 + (i * 5) % 150) / 255,
                    (100 + (i * 7) % 140) / 255,
                    1,
                )
                c = self._make_box((x * 0.985, y * 0.985, h + 1.0), (0.32, 0.32, 0.8), cc)
                self.crowd.append(c)

    def _build_characters(self):
        self.presenter = self._make_box((-7, -2, 2.3), (1.2, 1.2, 4.5), (0.2, 0.2, 0.25, 1))
        self.human_cap = self._make_box((-2, 0, 2.2), (1.2, 1.2, 4.4), (0.22, 0.53, 0.9, 1))
        self.ai_cap = self._make_box((2.5, 0, 2.2), (1.2, 1.2, 4.4), (0.94, 0.76, 0.29, 1))
        self.umpire = self._make_box((7, -1, 2.2), (1.2, 1.2, 4.4), (0.73, 0.83, 0.92, 1))

        self.ball = self.loader.loadModel("models/smiley")
        self.ball.reparentTo(self.render)
        self.ball.setScale(0.4)
        self.ball.setColor(0.85, 0.2, 0.2, 1)
        self.ball.setPos(0, 2, 4.5)

        self.batsman = self._make_box((1, -15, 2.1), (1.1, 1.1, 4.2), (0.25, 0.57, 0.95, 1))
        self.bowler = self._make_box((0, 14, 2.1), (1.1, 1.1, 4.2), (0.94, 0.74, 0.26, 1))
        self.batsman.hide(); self.bowler.hide()

        self.fielders = []
        for ang in [25, 65, 110, 160, 200, 245, 300, 335]:
            a = math.radians(ang)
            f = self._make_box((24 * math.cos(a), 24 * math.sin(a), 1.7), (0.9, 0.9, 3.4), (0.93, 0.76, 0.28, 1))
            f.hide()
            self.fielders.append(f)

    def _build_ui(self):
        loaded_txt = f"IPL data loaded: {self.model.rows:,} balls" if self.model.loaded else "No IPL CSV found (fallback priors)"
        self.data_label = OnscreenText(text=loaded_txt, pos=(-1.3, 0.92), scale=0.05, fg=(0.8, 1, 0.85, 1), align=TextNode.ALeft)
        self.msg = OnscreenText(text="MAKE YOUR CALL", pos=(0, 0.78), scale=0.08, fg=(1, 1, 1, 1))

        self.btns = []
        self._show_toss_buttons()

    def _clear_buttons(self):
        for b in self.btns:
            b.destroy()
        self.btns = []

    def _show_toss_buttons(self):
        self._clear_buttons()
        self.btns.append(DirectButton(text="HEADS", scale=0.085, pos=(-0.42, 0, -0.82), command=lambda: self._resolve_toss("HEADS")))
        self.btns.append(DirectButton(text="TAILS", scale=0.085, pos=(0.42, 0, -0.82), command=lambda: self._resolve_toss("TAILS")))

    def _resolve_toss(self, call):
        if self.mode != "toss":
            return
        coin = random.choice(["HEADS", "TAILS"])
        self.msg.setText(f"COIN: {coin} | {'YOU WON TOSS' if coin == call else 'AI WON TOSS'}")
        self.mode = "choice"
        self._show_choice_buttons()

    def _show_choice_buttons(self):
        self._clear_buttons()
        self.btns.append(DirectButton(text="BAT", scale=0.085, pos=(-0.36, 0, -0.82), command=lambda: self._start_match("BAT")))
        self.btns.append(DirectButton(text="BOWL", scale=0.085, pos=(0.36, 0, -0.82), command=lambda: self._start_match("BOWL")))

    def _start_match(self, role):
        self.mode = "match"
        self._clear_buttons()
        self._set_camera_match()

        self.presenter.hide(); self.human_cap.hide(); self.ai_cap.hide(); self.umpire.hide()
        self.batsman.show(); self.bowler.show()
        for f in self.fielders:
            f.show()

        self.msg.setText(f"You chose {role}. Pick shot + direction")
        self.score_label = OnscreenText(text="IND 0/0 | OVER 0.0", pos=(-1.25, 0.82), scale=0.06, fg=(1, 1, 1, 1), align=TextNode.ALeft)

        for i, shot in enumerate(["DEFEND", "PUSH", "STROKE", "LOFT"]):
            x = -0.76 + i * 0.5
            self.btns.append(DirectButton(text=shot, scale=0.065, pos=(x, 0, -0.82), command=lambda s=shot: self._play_ball(s)))

        for i, d in enumerate(["LEG", "STRAIGHT", "OFF"]):
            x = -0.4 + i * 0.4
            self.btns.append(DirectButton(text=d, scale=0.055, pos=(x, 0, -0.66), command=lambda dd=d: self._set_direction(dd)))

        self.balls = 0
        self.runs = 0
        self.wickets = 0

    def _set_direction(self, direction):
        self.current_direction = direction
        self.msg.setText(f"Direction: {direction} | Choose shot")

    def _play_ball(self, shot):
        if self.mode != "match":
            return
        self.balls += 1
        out = self.model.sample_ball(self.balls - 1, shot, self.current_direction)
        if out.wicket:
            self.wickets += 1
        else:
            self.runs += out.runs

        over_txt = f"{self.balls // 6}.{self.balls % 6}"
        self.score_label.setText(f"IND {self.runs}/{self.wickets} | OVER {over_txt}")
        self.msg.setText(out.desc)
        self.ball.setPos(*out.landing)

        if self.balls >= 6 or self.wickets >= 1:
            self.msg.setText(out.desc + " | INNINGS COMPLETE")
            for b in self.btns:
                b["state"] = "disabled"
