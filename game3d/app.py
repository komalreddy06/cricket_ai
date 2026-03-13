from ursina import *
import random
import math


class Cricket3DApp:
    def __init__(self):
        self.app = Ursina(borderless=False)
        window.title = "Cricket AI vs Human (3D Python Prototype)"
        window.color = color.rgb(120, 180, 235)

        self.mode = "toss"
        self.message = Text(text="", y=0.35, origin=(0, 0), scale=1.4, color=color.white)

        self._build_world()
        self._build_toss_ui()

    def _build_world(self):
        self.sun = DirectionalLight(y=2, z=3)
        self.sun.look_at(Vec3(1, -1, -1))
        AmbientLight(color=color.rgba(140, 140, 140, 0.8))

        self.ground = Entity(model='plane', scale=(80, 1, 50), color=color.rgb(88, 155, 84), collider='box')
        self.pitch = Entity(model='cube', scale=(2.6, 0.1, 18), y=0.05, color=color.rgb(198, 166, 120))

        self.stands = []
        for i in range(24):
            angle = (360 / 24) * i
            e = Entity(
                model='cube',
                scale=(3.4, 2, 2),
                color=color.rgb(65, 70, 80),
                position=(28 * math.sin(math.radians(angle)), 1, 14 * math.cos(math.radians(angle)))
            )
            e.look_at((0, 1, 0))
            self.stands.append(e)

        self.boundary = Entity(model='torus', scale=(31, 1, 19), y=0.06, color=color.rgba(255, 255, 255, 180))

        # Toss scene characters
        self.presenter = Entity(model='cube', scale=(1, 2.2, 0.6), position=(-4, 1.1, 2), color=color.rgb(60, 60, 65))
        self.captain_aus = Entity(model='cube', scale=(1, 2.1, 0.6), position=(-1.1, 1.05, 1.8), color=color.rgb(245, 190, 65))
        self.captain_ind = Entity(model='cube', scale=(1, 2.1, 0.6), position=(1.3, 1.05, 1.6), color=color.rgb(57, 120, 230))
        self.umpire = Entity(model='cube', scale=(1, 2.1, 0.6), position=(4, 1.05, 1.9), color=color.rgb(170, 210, 235))

        self.ball = Entity(model='sphere', scale=0.25, position=(0, 2.5, 1.8), color=color.red)

        self.batsman = Entity(model='cube', scale=(0.8, 2, 0.5), position=(0.5, 1, -6), color=color.rgb(65, 130, 235), enabled=False)
        self.bowler = Entity(model='cube', scale=(0.8, 2, 0.5), position=(0.2, 1, 8), color=color.rgb(235, 188, 65), enabled=False)

        camera.position = (0, 8.5, -17)
        camera.rotation_x = 22

    def _clear_buttons(self):
        for key in ("heads_btn", "tails_btn", "bat_btn", "bowl_btn", "shot_btns", "next_ball_btn"):
            obj = getattr(self, key, None)
            if obj is None:
                continue
            if isinstance(obj, list):
                for b in obj:
                    destroy(b)
            else:
                destroy(obj)
            setattr(self, key, None)

    def _build_toss_ui(self):
        self._clear_buttons()
        self.message.text = "MAKE YOUR CALL"

        self.heads_btn = Button(text='HEADS', scale=(0.2, 0.08), position=(-0.28, -0.36), color=color.azure)
        self.tails_btn = Button(text='TAILS', scale=(0.2, 0.08), position=(0.28, -0.36), color=color.azure)

        self.heads_btn.on_click = lambda: self._resolve_toss('HEADS')
        self.tails_btn.on_click = lambda: self._resolve_toss('TAILS')

    def _resolve_toss(self, call):
        coin = random.choice(['HEADS', 'TAILS'])
        human_won = coin == call
        self.message.text = f"COIN: {coin}  |  {'YOU WON THE TOSS' if human_won else 'AI WON THE TOSS'}"

        destroy(self.heads_btn)
        destroy(self.tails_btn)
        self.heads_btn = None
        self.tails_btn = None

        self.bat_btn = Button(text='BAT', scale=(0.2, 0.08), position=(-0.22, -0.36), color=color.rgb(35, 55, 95))
        self.bowl_btn = Button(text='BOWL', scale=(0.2, 0.08), position=(0.22, -0.36), color=color.rgb(35, 55, 95))

        self.bat_btn.on_click = lambda: self._start_match('BAT')
        self.bowl_btn.on_click = lambda: self._start_match('BOWL')

    def _start_match(self, role):
        self.mode = 'match'
        self.message.text = f"YOU CHOSE TO {role} FIRST"

        destroy(self.bat_btn)
        destroy(self.bowl_btn)

        self.presenter.enabled = False
        self.captain_aus.enabled = False
        self.captain_ind.enabled = False
        self.umpire.enabled = False
        self.ball.enabled = False

        self.batsman.enabled = True
        self.bowler.enabled = True

        camera.position = (0, 11, -21)
        camera.rotation_x = 28

        self.score_text = Text(text='IND 0/0   |   OVER 0.0', x=-0.43, y=0.45, scale=1.2)
        self.status_text = Text(text='Select your shot', x=-0.1, y=-0.25, scale=1.1)

        shots = ['DEFEND', 'PUSH', 'STROKE', 'LOFT']
        self.shot_btns = []
        x0 = -0.36
        for i, shot in enumerate(shots):
            btn = Button(text=shot, scale=(0.16, 0.07), position=(x0 + i * 0.24, -0.38), color=color.rgb(40, 70, 100))
            btn.on_click = lambda s=shot: self._play_ball(s)
            self.shot_btns.append(btn)

        self.balls = 0
        self.runs = 0
        self.wickets = 0

    def _play_ball(self, shot):
        self.balls += 1
        wicket = random.random() < 0.14
        if wicket:
            self.wickets += 1
            result = 'WICKET'
        else:
            gained = random.choice([0, 1, 2, 3, 4, 6])
            self.runs += gained
            result = f'{gained} RUNS'

        over = f"{self.balls // 6}.{self.balls % 6}"
        self.score_text.text = f'IND {self.runs}/{self.wickets}   |   OVER {over}'
        self.status_text.text = f'{shot} -> {result}'

        self.ball.enabled = True
        self.ball.position = (random.uniform(-1.2, 1.2), 1.1, random.uniform(-6.8, -4.8))

        if self.balls >= 6 or self.wickets >= 1:
            for btn in self.shot_btns:
                btn.disabled = True
            self.status_text.text = self.status_text.text + '  |  INNINGS COMPLETE'

    def run(self):
        self.app.run()
