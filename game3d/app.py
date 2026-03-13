from ursina import *
import math
import random
from engine.ipl_ai import IPLDataModel


class Cricket3DApp:
    def __init__(self):
        self.app = Ursina(borderless=False)
        window.title = "Cricket AI vs Human Cricket (3D)"
        window.color = color.rgb(98, 160, 225)

        self.mode = "toss"
        self.toss_phase = "call"
        self.current_direction = "STRAIGHT"

        self.model = IPLDataModel()
        self.model.train_from_kaggle_csv()

        self.message = Text(text="", y=0.40, origin=(0, 0), scale=1.2, color=color.white)
        self.data_badge = Text(text="", y=0.46, x=-0.62, origin=(0, 0), scale=0.9, color=color.azure)

        self.score_text = None
        self.status_text = None
        self.shot_btns = []
        self.dir_btns = []

        self._build_360_stadium()
        self._build_toss_ui()

    def _build_360_stadium(self):
        DirectionalLight(y=4, z=-2)
        AmbientLight(color=color.rgba(160, 160, 160, 0.8))

        self.ground = Entity(model='plane', scale=(110, 1, 110), color=color.rgb(74, 142, 75), collider='box')
        self.pitch = Entity(model='cube', scale=(3.0, 0.08, 20), y=0.05, color=color.rgb(190, 155, 108))

        self.boundary = Entity(model='circle', scale=72, rotation_x=90, y=0.09, color=color.rgba(255, 255, 255, 210))

        self.stands = []
        self.crowd = []
        for ring in [45, 52, 59]:
            h = 1.0 + (ring - 45) * 0.12
            for i in range(70):
                ang = (360 / 70) * i
                x = ring * math.sin(math.radians(ang))
                z = ring * math.cos(math.radians(ang))
                b = Entity(model='cube', scale=(2.2, 1.1, 2.2), position=(x, h, z), color=color.rgb(40, 45, 55))
                b.look_at((0, h, 0))
                self.stands.append(b)

                c = Entity(model='cube', scale=(0.42, 0.65, 0.42), position=(x * 0.98, h + 0.82, z * 0.98),
                           color=color.rgb(120 + (i * 3) % 120, 80 + (i * 5) % 140, 90 + (i * 7) % 140))
                self.crowd.append(c)

        self.ad_ring = Text(text="  CRICKET AI LEAGUE  " * 9, y=0.48, origin=(0, 0), scale=1.0, color=color.white)

        self.presenter = Entity(model='cube', scale=(1, 2.2, 0.65), position=(-4.2, 1.1, 2), color=color.rgb(58, 61, 70))
        self.captain_human = Entity(model='cube', scale=(1, 2.2, 0.65), position=(-1.15, 1.1, 1.8), color=color.rgb(53, 130, 226))
        self.captain_ai = Entity(model='cube', scale=(1, 2.2, 0.65), position=(1.3, 1.1, 1.8), color=color.rgb(240, 188, 70))
        self.umpire = Entity(model='cube', scale=(1, 2.2, 0.65), position=(4.0, 1.1, 2), color=color.rgb(174, 210, 233))

        self.ball = Entity(model='sphere', scale=0.28, position=(0, 2.8, 1.8), color=color.red)
        self.batsman = Entity(model='cube', scale=(0.85, 2.1, 0.6), position=(0.4, 1.05, -7), color=color.rgb(60, 140, 240), enabled=False)
        self.bowler = Entity(model='cube', scale=(0.85, 2.1, 0.6), position=(0.0, 1.05, 9), color=color.rgb(236, 188, 66), enabled=False)

        self.fielders = []
        for ang in [20, 60, 105, 150, 210, 250, 300, 335]:
            x = 22 * math.sin(math.radians(ang))
            z = 22 * math.cos(math.radians(ang))
            f = Entity(model='cube', scale=(0.72, 1.75, 0.5), position=(x, 0.9, z), color=color.rgb(235, 193, 80), enabled=False)
            self.fielders.append(f)

        camera.position = (0, 15, -29)
        camera.rotation_x = 28

    def _clear_buttons(self):
        for key in ("heads_btn", "tails_btn", "bat_btn", "bowl_btn"):
            obj = getattr(self, key, None)
            if obj:
                destroy(obj)
                setattr(self, key, None)

        for b in self.shot_btns:
            destroy(b)
        for b in self.dir_btns:
            destroy(b)
        self.shot_btns = []
        self.dir_btns = []

    def _build_toss_ui(self):
        self._clear_buttons()
        self.toss_phase = "call"
        self.message.text = "MAKE YOUR CALL: HEADS OR TAILS"

        if self.model.loaded:
            self.data_badge.text = f"IPL dataset loaded: {self.model.rows:,} balls"
            self.data_badge.color = color.lime
        else:
            self.data_badge.text = "Dataset not found (using fallback priors). Place Kaggle deliveries.csv in /data"
            self.data_badge.color = color.orange

        self.heads_btn = Button(text='HEADS', scale=(0.2, 0.08), position=(-0.24, -0.37), color=color.azure)
        self.tails_btn = Button(text='TAILS', scale=(0.2, 0.08), position=(0.24, -0.37), color=color.azure)
        self.heads_btn.on_click = lambda: self._resolve_toss('HEADS')
        self.tails_btn.on_click = lambda: self._resolve_toss('TAILS')

    def _resolve_toss(self, call):
        if self.toss_phase != "call":
            return
        self.toss_phase = "resolved"

        coin = "HEADS" if random.random() < 0.5 else "TAILS"
        human_won = coin == call
        self.message.text = f"COIN: {coin} | {'YOU WON TOSS' if human_won else 'AI WON TOSS'}"

        self.heads_btn.enabled = False
        self.tails_btn.enabled = False
        invoke(self._show_innings_choice, delay=0.08)

    def _show_innings_choice(self):
        destroy(self.heads_btn)
        destroy(self.tails_btn)
        self.heads_btn = None
        self.tails_btn = None

        self.message.text = "CHOOSE INNINGS"
        self.bat_btn = Button(text='BAT', scale=(0.2, 0.08), position=(-0.22, -0.37), color=color.rgb(35, 55, 95))
        self.bowl_btn = Button(text='BOWL', scale=(0.2, 0.08), position=(0.22, -0.37), color=color.rgb(35, 55, 95))
        self.bat_btn.on_click = lambda: self._start_match('BAT')
        self.bowl_btn.on_click = lambda: self._start_match('BOWL')

    def _start_match(self, role):
        self.mode = "match"
        self._clear_buttons()

        self.presenter.enabled = False
        self.captain_human.enabled = False
        self.captain_ai.enabled = False
        self.umpire.enabled = False

        self.batsman.enabled = True
        self.bowler.enabled = True
        for f in self.fielders:
            f.enabled = True

        camera.position = (0, 18, -34)
        camera.rotation_x = 30

        if self.score_text:
            destroy(self.score_text)
        if self.status_text:
            destroy(self.status_text)

        self.score_text = Text(text='IND 0/0 | OVER 0.0', x=-0.61, y=0.40, scale=1.05)
        self.status_text = Text(text=f'You chose {role}. Select shot + direction.', x=-0.28, y=-0.23, scale=1.0)

        for i, shot in enumerate(['DEFEND', 'PUSH', 'STROKE', 'LOFT']):
            btn = Button(text=shot, scale=(0.14, 0.07), position=(-0.36 + i * 0.24, -0.37), color=color.rgb(31, 67, 99))
            btn.on_click = lambda s=shot: self._play_ball(s)
            self.shot_btns.append(btn)

        for i, d in enumerate(['LEG', 'STRAIGHT', 'OFF']):
            btn = Button(text=d, scale=(0.16, 0.06), position=(-0.24 + i * 0.24, -0.28), color=color.rgb(72, 116, 162))
            btn.on_click = lambda direction=d: self._set_direction(direction)
            self.dir_btns.append(btn)

        self.balls = 0
        self.runs = 0
        self.wickets = 0

    def _set_direction(self, direction: str):
        self.current_direction = direction
        self.status_text.text = f"Direction set: {direction}. Now play shot."

    def _play_ball(self, shot: str):
        self.balls += 1
        outcome = self.model.sample_ball(self.balls - 1, shot, self.current_direction)

        if outcome.wicket:
            self.wickets += 1
        else:
            self.runs += outcome.runs

        over_txt = f"{self.balls // 6}.{self.balls % 6}"
        self.score_text.text = f'IND {self.runs}/{self.wickets} | OVER {over_txt}'
        self.status_text.text = outcome.desc

        self.ball.enabled = True
        self.ball.position = outcome.landing

        if self.balls >= 6 or self.wickets >= 1:
            for b in self.shot_btns + self.dir_btns:
                b.disabled = True
            self.status_text.text += " | INNINGS COMPLETE"

    def run(self):
        self.app.run()
