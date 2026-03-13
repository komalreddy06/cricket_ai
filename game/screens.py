"""
game/screens.py  —  All game screens
Each screen has: handle_event(e), update(dt), draw(surf)
"""
import pygame, math, random
from constants import *
from game.draw  import *
from engine.ai  import (astar_place_fielders, ai_bowl, bayesian_sample_shot,
                         resolve_ball, SHOTS, DELIVERIES,
                         OUTCOME, SHOT_IDX, minimax_choose)


# ═══════════════════════════════════════════════════════════════════════════
#  BASE SCREEN
# ═══════════════════════════════════════════════════════════════════════════
class Screen:
    def __init__(self, manager):
        self.mgr   = manager
        self.state = manager.state
        self.fonts = manager.fonts

    def on_enter(self): pass
    def handle_event(self, e): pass
    def update(self, dt): pass
    def draw(self, surf): pass


# ═══════════════════════════════════════════════════════════════════════════
#  SPLASH SCREEN
# ═══════════════════════════════════════════════════════════════════════════
class SplashScreen(Screen):
    def on_enter(self):
        self._t    = 0.0
        self._stars= [(random.randint(0,WIN_W), random.randint(0,WIN_H),
                        random.uniform(0.3,1.0)) for _ in range(120)]
        self._particles = []

    def handle_event(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN:
            mx, my = e.pos
            if self._btn_rect.collidepoint(mx, my):
                particle_burst(self._particles, mx, my, C_GOLD, 30)
                self.mgr.goto("toss")
        if e.type == pygame.KEYDOWN and e.key == pygame.K_RETURN:
            self.mgr.goto("toss")

    def update(self, dt):
        self._t += dt

    def draw(self, surf):
        surf.fill(C_BG)
        # Stars
        for sx, sy, br in self._stars:
            twinkle = 0.5 + 0.5*math.sin(self._t*2 + sx)
            r = max(1, int(2*br*twinkle))
            pygame.draw.circle(surf, (255,255,255), (sx,sy), r)

        # Big cricket ground preview (background)
        pygame.draw.ellipse(surf, (20,50,20),
            (WIN_W//2-300, WIN_H//2-160, 600, 320))
        pygame.draw.ellipse(surf, (255,255,255),
            (WIN_W//2-300, WIN_H//2-160, 600, 320), 1)

        # Title
        pulse = 1 + 0.04*math.sin(self._t*2)
        f = self.fonts["huge"]
        draw_text(surf, "🏏  AI vs HUMAN CRICKET", f, C_GOLD,
                  WIN_W//2, 140, center=True, shadow=True)

        # Subtitle
        draw_text(surf, "INTELLIGENCE  vs  HUMAN  ·  1-OVER MATCH",
                  self.fonts["small"], C_GREY, WIN_W//2, 195, center=True)

        # Algorithm badges
        algos = [
            ("A* Search",       "Field Placement", C_GREEN,   "Unit I"),
            ("Minimax + α-β",   "AI Bowler",       C_BLUE,    "Unit II"),
            ("Bayesian Network","Uncertainty",      C_ORANGE,  "Unit III"),
            ("Q-Learning",      "Adaptive AI",     C_PINK,    "Unit IV"),
        ]
        bw, bh = 230, 90
        total_w = len(algos)*bw + (len(algos)-1)*16
        bx0 = WIN_W//2 - total_w//2
        for i,(algo,role,col,unit) in enumerate(algos):
            bx = bx0 + i*(bw+16)
            by = 230
            rounded_rect(surf, C_CARD, (bx,by,bw,bh), radius=12,
                         border=2, border_color=col)
            # Left accent bar
            pygame.draw.rect(surf, col, (bx,by+10,4,bh-20), border_radius=2)
            draw_text(surf, unit, self.fonts["tiny"], col, bx+16, by+10)
            draw_text(surf, algo, self.fonts["med"],  C_WHITE, bx+16, by+30)
            draw_text(surf, role, self.fonts["small"],C_GREY,  bx+16, by+54)

        # How to play
        how_y = 345
        rounded_rect(surf, C_CARD, (WIN_W//2-380, how_y, 760, 120), radius=14,
                     border=1, border_color=(42,70,100))
        draw_text(surf, "HOW TO PLAY", self.fonts["small"], C_GOLD,
                  WIN_W//2-360, how_y+10)
        steps = [
            "1. Win the toss → choose to BAT or BOWL",
            "2. If BATTING: Pick your shot each ball. Score as many runs as possible!",
            "3. If BOWLING: Pick your delivery. Get the AI out or limit their runs!",
            "4. 6 balls each. Highest score wins. AI uses 4 algorithms to beat you!",
        ]
        for i, s in enumerate(steps):
            draw_text(surf, s, self.fonts["small"], C_CREAM,
                      WIN_W//2-360, how_y+32+i*20)

        # Start button
        bw2, bh2 = 280, 56
        self._btn_rect = pygame.Rect(WIN_W//2-bw2//2, 490, bw2, bh2)
        mx, my = pygame.mouse.get_pos()
        hover  = self._btn_rect.collidepoint(mx, my)
        draw_button(surf, self._btn_rect, "▶  START MATCH",
                    self.fonts["med"], hover=hover)

        # Pulse ring on button
        ring_r = int(34 + 8*math.sin(self._t*3))
        pygame.draw.circle(surf, (*C_GOLD, 60),
            (WIN_W//2, 518), ring_r, 2)

        draw_text(surf, "Press ENTER or click to start",
                  self.fonts["tiny"], C_GREY, WIN_W//2, 558, center=True)

        update_draw_particles(surf, self._particles)


# ═══════════════════════════════════════════════════════════════════════════
#  TOSS SCREEN
# ═══════════════════════════════════════════════════════════════════════════
class TossScreen(Screen):
    def on_enter(self):
        self._phase     = "call"   # call→flipping→choose→done
        self._t         = 0.0
        self._coin_t    = 0.0
        self._result    = None
        self._particles = []
        self._human_call= None

    def handle_event(self, e):
        if e.type != pygame.MOUSEBUTTONDOWN: return
        mx, my = e.pos

        if self._phase == "call":
            if self._heads_btn.collidepoint(mx,my):
                self._human_call = "HEADS"
                self._phase = "flipping"
                self._coin_t = 0
            elif self._tails_btn.collidepoint(mx,my):
                self._human_call = "TAILS"
                self._phase = "flipping"
                self._coin_t = 0

        elif self._phase == "choose":
            if self._bat_btn.collidepoint(mx,my):
                self._finalise("BAT")
            elif self._bowl_btn.collidepoint(mx,my):
                self._finalise("BOWL")

        elif self._phase == "done":
            if self._next_btn.collidepoint(mx,my):
                self.mgr.goto("field")

    def _finalise(self, human_choice):
        self.state.set_toss(
            self._human_call,
            self._result["coin"],
            self._result["winner"],
            human_choice)
        self._phase = "done"

    def update(self, dt):
        self._t += dt
        if self._phase == "flipping":
            self._coin_t += dt
            if self._coin_t > 2.2:
                import random
                coin = random.choice(["HEADS","TAILS"])
                winner = "human" if coin==self._human_call else "ai"
                self._result = {"coin":coin, "winner":winner}
                self._phase  = "landed"
                particle_burst(self._particles, WIN_W//2, WIN_H//2-60,
                    C_GOLD if winner=="human" else C_BLUE, 40)
                if winner == "ai":
                    from engine.ai import bayesian_sample_shot
                    import random as rnd
                    ai_ch = "BAT" if rnd.random()<0.65 else "BOWL"
                    self._ai_choice = ai_ch
                    # auto proceed after delay
                    self._auto_timer = 2.0

    def draw(self, surf):
        surf.fill(C_BG)

        ground_y = int(WIN_H * 0.58)
        draw_stadium_backdrop(surf, ground_y - 170, self._t)
        draw_ad_ribbon(surf, max(10, ground_y - 204))

        # outfield
        pygame.draw.ellipse(surf, (55, 122, 58), (-90, ground_y - 30, WIN_W + 180, 330))
        pygame.draw.ellipse(surf, (180, 160, 110), (WIN_W//2 - 110, ground_y + 18, 220, 72))

        # toss group (presenter, captains, umpire)
        base_y = ground_y + 72
        draw_toss_character(surf, WIN_W//2 - 210, base_y, (58, 62, 74), role="presenter", facing=1, scale=1.7)
        draw_toss_character(surf, WIN_W//2 - 35, base_y - 2, (240, 186, 58), role="captain", facing=1, scale=1.75)
        draw_toss_character(surf, WIN_W//2 + 95, base_y - 2, (54, 128, 224), role="captain", facing=-1, scale=1.68)
        draw_toss_character(surf, WIN_W//2 + 220, base_y + 2, (166, 196, 225), role="umpire", facing=-1, scale=1.65)

        draw_text(surf, "MATCH TOSS", self.fonts["big"], C_GOLD,
                  WIN_W//2, 56, center=True, shadow=True)
        draw_text(surf, "Broadcast toss view · choose quickly and start the action",
                  self.fonts["small"], C_CREAM, WIN_W//2, 92, center=True)

        # coin area + phase text
        cx, cy = WIN_W//2, ground_y + 10
        if self._phase == "call":
            bob = math.sin(self._t*2.6) * 5
            pygame.draw.circle(surf, C_GOLD_DARK, (cx, int(cy+bob)), 40)
            pygame.draw.circle(surf, C_GOLD, (cx, int(cy+bob)-2), 38)
            draw_text(surf, "CALL THE TOSS", self.fonts["med"], C_WHITE, WIN_W//2, cy+48, center=True)

            self._heads_btn = pygame.Rect(WIN_W//2-300, cy+88, 240, 58)
            self._tails_btn = pygame.Rect(WIN_W//2+60,  cy+88, 240, 58)
            msg_rect = pygame.Rect(WIN_W//2-130, cy+84, 260, 62)
            rounded_rect(surf, (17, 39, 66), msg_rect, radius=8, border=2, border_color=(236, 121, 38))
            draw_text(surf, "MAKE YOUR CALL", self.fonts["med"], C_WHITE, msg_rect.centerx, msg_rect.y+18, center=True)

            mx,my = pygame.mouse.get_pos()
            draw_button(surf, self._heads_btn, "HEADS", self.fonts["big"],
                        hover=self._heads_btn.collidepoint(mx,my), color=(30, 43, 62), text_color=C_CREAM)
            draw_button(surf, self._tails_btn, "TAILS", self.fonts["big"],
                        hover=self._tails_btn.collidepoint(mx,my), color=(30, 43, 62), text_color=C_CREAM)

        elif self._phase == "flipping":
            spin = self._coin_t * 10
            squish = max(0.16, abs(math.cos(spin)))
            ry = int(38 * squish)
            bob = -abs(math.sin(self._coin_t * 4)) * 65
            col = C_GOLD if math.cos(spin) > 0 else C_GREY
            pygame.draw.ellipse(surf, col, (cx-38, int(cy+bob)-ry, 76, ry*2))
            draw_text(surf, "TOSS IN AIR...", self.fonts["med"], C_CREAM, WIN_W//2, cy+55, center=True)

        elif self._phase in ("landed", "choose", "done"):
            coin = self._result["coin"]
            winner = self._result["winner"]
            col = C_GOLD if coin == "HEADS" else C_GREY
            pygame.draw.circle(surf, col, (cx, cy), 38)
            pygame.draw.circle(surf, C_WHITE, (cx, cy), 38, 2)
            draw_text(surf, "H" if coin=="HEADS" else "T", self.fonts["big"], C_BG, cx, cy, center=True)

            win_txt = "YOU WON THE TOSS" if winner == "human" else "AI WON THE TOSS"
            win_col = C_GOLD if winner == "human" else C_BLUE
            draw_text(surf, win_txt, self.fonts["big"], win_col, WIN_W//2, cy+52, center=True, shadow=True)

            if self._phase == "choose":
                banner = pygame.Rect(WIN_W//2-230, cy+88, 460, 62)
                rounded_rect(surf, (17, 39, 66), banner, radius=10, border=2, border_color=(236, 121, 38))
                draw_text(surf, "WHAT WOULD YOU LIKE TO DO?", self.fonts["med"], C_WHITE, banner.centerx, banner.y+19, center=True)
                self._bat_btn = pygame.Rect(WIN_W//2-300, cy+170, 240, 58)
                self._bowl_btn = pygame.Rect(WIN_W//2+60, cy+170, 240, 58)
                mx,my = pygame.mouse.get_pos()
                draw_button(surf, self._bat_btn, "BAT", self.fonts["big"],
                            hover=self._bat_btn.collidepoint(mx,my), color=(30, 43, 62), text_color=C_CREAM)
                draw_button(surf, self._bowl_btn, "BOWL", self.fonts["big"],
                            hover=self._bowl_btn.collidepoint(mx,my), color=(30, 43, 62), text_color=C_CREAM)

            elif self._phase == "done":
                hr = self.state.human_role
                ar = self.state.ai_role
                draw_text(surf, f"YOU: {hr} FIRST  ·  AI: {ar} FIRST", self.fonts["med"], C_CREAM, WIN_W//2, cy+100, center=True)
                self._next_btn = pygame.Rect(WIN_W//2-150, cy+146, 300, 54)
                mx,my = pygame.mouse.get_pos()
                draw_button(surf, self._next_btn, "CONTINUE TO FIELD SETUP", self.fonts["med"],
                            hover=self._next_btn.collidepoint(mx,my))

        if self._phase == "landed" and hasattr(self, "_auto_timer"):
            self._auto_timer -= 0.016
            if self._auto_timer <= 0:
                self._finalise(self._ai_choice)
                del self._auto_timer

        update_draw_particles(surf, self._particles)


# ═══════════════════════════════════════════════════════════════════════════
#  FIELD PLACEMENT SCREEN (A*)
# ═══════════════════════════════════════════════════════════════════════════
class FieldScreen(Screen):
    def on_enter(self):
        self._t = 0.0
        self._anim_done  = False
        self._reveal_idx = 0
        self._fielders   = {}
        self._reveal_t   = 0.0
        # Run A*
        self.state.field_positions = astar_place_fielders()
        self._fielder_list = list(self.state.field_positions.items())

    def handle_event(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN:
            if hasattr(self,"_next_btn") and self._next_btn.collidepoint(e.pos):
                self.mgr.goto("minimax_demo")
            if hasattr(self,"_skip_btn") and self._skip_btn.collidepoint(e.pos):
                self._reveal_idx = len(self._fielder_list)

    def update(self, dt):
        self._t += dt
        self._reveal_t += dt
        if self._reveal_t > 0.25 and self._reveal_idx < len(self._fielder_list):
            self._reveal_idx += 1
            self._reveal_t = 0

    def draw(self, surf):
        surf.fill(C_BG)
        # Ground
        gw, gh = 480, 420
        gx, gy = 80, WIN_H//2 - gh//2
        gcx, gcy = gx + gw//2, gy + gh//2
        draw_stadium_backdrop(surf, gy-42, self._t)
        draw_ad_ribbon(surf, max(8, gy-74))
        draw_ground(surf, gcx, gcy, gw//2-10, gh//2-10)

        # Batsman at crease
        draw_batsman(surf, gcx, gcy+20, C_GOLD, scale=0.85)

        # Revealed fielders
        for i in range(self._reveal_idx):
            zid, info = self._fielder_list[i]
            fx = gx + int(info["x"] * gw)
            fy = gy + int(info["y"] * gh)
            # Risk halo
            risk_col = (200,60,60) if info["risk"]>=0.70 else \
                       (210,140,30) if info["risk"]>=0.60 else (60,160,80)
            s2 = pygame.Surface((50,50), pygame.SRCALPHA)
            pygame.draw.circle(s2, (*risk_col, 60), (25,25), 22)
            surf.blit(s2, (fx-25, fy-25))
            draw_fielder(surf, fx, fy, color=risk_col)
            draw_text(surf, info["name"], self.fonts["tiny"],
                      C_CREAM, fx, fy+16, center=True)

        # Title panel
        draw_text(surf, "FIELD PLACEMENT  —  A* SEARCH",
                  self.fonts["big"], C_GOLD, WIN_W//2+80, 28, center=True, shadow=True)
        draw_text(surf, "Unit I  ·  Informed Search  ·  h(n) = uncovered run probability",
                  self.fonts["small"], C_GREY, WIN_W//2+80, 65, center=True)

        # Info panel right
        px, py, pw, ph = 590, 95, 560, 460
        rounded_rect(surf, C_CARD, (px,py,pw,ph), radius=14,
                     border=1, border_color=(42,70,100))

        draw_text(surf, "HOW A* WORKS", self.fonts["med"], C_GOLD, px+20, py+14)
        concepts = [
            ("State",    "Each zone = a node in search space"),
            ("g(n)",     "Zones already covered (cost so far)"),
            ("h(n)",     "Uncovered run probability (heuristic)"),
            ("f(n)",     "g(n) + h(n)  →  total cost estimate"),
            ("Goal",     "Place 8 fielders, minimise total h(n)"),
            ("Result",   "Optimal field for current batsman!"),
        ]
        for i,(key,val) in enumerate(concepts):
            iy = py+46+i*34
            rounded_rect(surf, C_CARD2, (px+14,iy,pw-28,28), radius=6)
            draw_text(surf, key+":", self.fonts["small"], C_BLUE,   px+22, iy+6)
            draw_text(surf, val,     self.fonts["small"], C_CREAM,  px+90, iy+6)

        # Fielder assignments
        draw_text(surf, "FIELDER ASSIGNMENTS", self.fonts["med"],
                  C_GOLD, px+20, py+260)
        for i in range(min(self._reveal_idx, 8)):
            zid, info = self._fielder_list[i]
            iy = py+290+i*22
            risk_col = (200,80,80) if info["risk"]>=0.70 else \
                       (210,160,30) if info["risk"]>=0.60 else (80,200,80)
            pygame.draw.circle(surf, risk_col, (px+28, iy+8), 6)
            draw_text(surf, f"Fielder {i+1}  →  {info['name']}  ({info['risk']:.0%} risk)",
                      self.fonts["small"], C_CREAM, px+42, iy)

        # Legend
        for lx,col,lbl in [(px+20,  (200,80,80),"High risk ≥70%"),
                            (px+160, (210,160,30),"Medium risk ≥60%"),
                            (px+310, (80,200,80), "Low risk <60%")]:
            pygame.draw.circle(surf, col, (lx, py+ph-22), 7)
            draw_text(surf, lbl, self.fonts["tiny"], C_CREAM, lx+12, py+ph-28)

        # Buttons
        self._next_btn = pygame.Rect(px+pw-240, py+ph-55, 220, 44)
        self._skip_btn = pygame.Rect(px+20, py+ph-55, 120, 44)
        mx,my = pygame.mouse.get_pos()
        draw_button(surf, self._skip_btn, "Skip Anim",
                    self.fonts["small"], hover=self._skip_btn.collidepoint(mx,my),
                    color=C_GREY, text_color=C_WHITE)
        draw_button(surf, self._next_btn, "NEXT: Minimax →",
                    self.fonts["med"], hover=self._next_btn.collidepoint(mx,my))


# ═══════════════════════════════════════════════════════════════════════════
#  MINIMAX DEMO SCREEN
# ═══════════════════════════════════════════════════════════════════════════
class MinimaxDemoScreen(Screen):
    def on_enter(self):
        self._t    = 0.0
        from engine.ai import minimax_choose
        self._delivery, self._tree = minimax_choose()
        self._build_layout()

    def _build_layout(self):
        """Pre-compute node positions for tree drawing."""
        self._positions = {}
        root = self._tree
        # Level 0: root centered
        # Level 1: delivery children
        # Level 2: shot children per delivery
        children = [c for c in root.children]
        n = len(children)
        margin = 100
        avail  = WIN_W - 2*margin
        for i, child in enumerate(children):
            cx = margin + int(avail * i/(max(n-1,1)))
            cy = 200
            self._positions[id(child)] = (cx, cy)
            gchildren = child.children
            gn = len(gchildren)
            slot_w = avail//max(n,1)
            slot_x = margin + i*slot_w
            for j, gc in enumerate(gchildren):
                gx = slot_x + int(slot_w * j/max(gn-1,1)) if gn>1 else slot_x+slot_w//2
                self._positions[id(gc)] = (gx, 360)
        self._positions["root"] = (WIN_W//2, 90)

    def handle_event(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN:
            if hasattr(self,"_next_btn") and self._next_btn.collidepoint(e.pos):
                self.mgr.goto("match")
            if hasattr(self,"_regen_btn") and self._regen_btn.collidepoint(e.pos):
                self.on_enter()

    def update(self, dt): self._t += dt

    def _node_color(self, node):
        if node.pruned:    return C_GREY
        if node.is_ai:     return C_BLUE
        return C_GOLD

    def draw(self, surf):
        surf.fill(C_BG)
        draw_text(surf, "MINIMAX + ALPHA-BETA PRUNING  —  Game Tree",
                  self.fonts["big"], C_GOLD, WIN_W//2, 28, center=True, shadow=True)
        draw_text(surf, "Unit II  ·  AI bowler (MIN) vs Human batter (MAX)  ·  α-β cuts irrelevant branches ✂️",
                  self.fonts["small"], C_GREY, WIN_W//2, 62, center=True)

        root = self._tree
        rx, ry = self._positions["root"]

        # Draw edges first
        for child in root.children:
            if id(child) not in self._positions: continue
            cx2, cy2 = self._positions[id(child)]
            col = (200,50,50) if child.pruned else \
                  (C_GREEN if child.label==self._delivery else C_GREY)
            pygame.draw.line(surf, col, (rx, ry+22), (cx2, cy2-22), 2)
            for gc in child.children:
                if id(gc) not in self._positions: continue
                gx2, gy2 = self._positions[id(gc)]
                col2 = (200,50,50) if gc.pruned else (80,100,120)
                pygame.draw.line(surf, col2, (cx2, cy2+22), (gx2, gy2-18), 1)

        # Root node
        pygame.draw.circle(surf, C_GREEN, (rx, ry), 26)
        pygame.draw.circle(surf, C_WHITE, (rx, ry), 26, 2)
        draw_text(surf, "MIN", self.fonts["tiny"], C_BG, rx, ry-7, center=True)
        score_str = f"{root.score:.1f}" if root.score else "?"
        draw_text(surf, score_str, self.fonts["small"], C_BG, rx, ry+5, center=True)

        # Level 1: deliveries
        for child in root.children:
            if id(child) not in self._positions: continue
            cx2, cy2 = self._positions[id(child)]
            is_best  = (child.label == self._delivery and not child.pruned)
            col = C_GREEN if is_best else (C_GREY if child.pruned else C_BLUE)
            r   = 24 if is_best else 20
            pygame.draw.circle(surf, col, (cx2, cy2), r)
            pygame.draw.circle(surf, C_WHITE, (cx2, cy2), r, 2 if is_best else 1)

            short = child.label.replace("Out-Swinger","O-Sw").replace("In-Swinger","I-Sw")
            draw_text(surf, short, self.fonts["tiny"],
                      C_BG if not child.pruned else C_GREY,
                      cx2, cy2-5, center=True)
            if not child.pruned and child.score is not None:
                sc_col = C_GREEN if child.score<=1 else (C_ORANGE if child.score<=3 else C_RED)
                draw_text(surf, f"{child.score:.1f}", self.fonts["tiny"],
                          sc_col, cx2, cy2+38, center=True)

            if child.pruned:
                draw_text(surf, "✂️", self.fonts["small"], C_RED,
                          cx2, cy2+28, center=True)
            elif is_best:
                draw_text(surf, "← BEST", self.fonts["tiny"], C_GREEN,
                          cx2+28, cy2-6)

            # Level 2: shots
            for gc in child.children:
                if id(gc) not in self._positions: continue
                gx2, gy2 = self._positions[id(gc)]
                gcol = C_GREY if gc.pruned else C_GOLD
                gr   = 16
                pygame.draw.circle(surf, gcol, (gx2, gy2), gr)
                pygame.draw.circle(surf, C_WHITE, (gx2, gy2), gr, 1)
                gl = gc.label[:3]
                draw_text(surf, gl, self.fonts["tiny"],
                          C_BG if not gc.pruned else C_GREY,
                          gx2, gy2-4, center=True)
                if not gc.pruned and gc.score is not None:
                    draw_text(surf, str(int(gc.score)), self.fonts["tiny"],
                              C_CREAM, gx2, gy2+22, center=True)
                if gc.pruned:
                    draw_text(surf, "✂", self.fonts["tiny"], C_RED,
                              gx2, gy2+20, center=True)

        # Legend
        legend_items = [
            (C_GREEN, "Best delivery (AI chooses)"),
            (C_BLUE,  "MIN node (AI delivery)"),
            (C_GOLD,  "MAX node (Human shot)"),
            (C_GREY,  "Pruned by α-β  ✂️"),
        ]
        lx = 30
        for i,(col,lbl) in enumerate(legend_items):
            pygame.draw.circle(surf, col, (lx, 430+i*24), 8)
            draw_text(surf, lbl, self.fonts["tiny"], C_CREAM, lx+16, 424+i*24)

        # Formula box
        rounded_rect(surf, C_CARD, (WIN_W-300, 90, 280, 260), radius=12,
                     border=1, border_color=C_BLUE)
        draw_text(surf, "KEY CONCEPTS", self.fonts["small"], C_GOLD, WIN_W-286, 100)
        formulas = [
            "AI = MIN player",
            "Human = MAX player",
            "Depth = 2 levels",
            "Prune: β ≤ α",
            f"Best delivery:",
            f"  {self._delivery}",
            f"Score: {root.score:.2f}" if root.score else "",
            "Nodes saved by",
            "α-β pruning!",
        ]
        for i,f in enumerate(formulas):
            col = C_GREEN if "Best" in f or self._delivery in f else C_CREAM
            draw_text(surf, f, self.fonts["tiny"], col, WIN_W-286, 124+i*22)

        # Buttons
        self._regen_btn = pygame.Rect(WIN_W-300, 370, 130, 40)
        self._next_btn  = pygame.Rect(WIN_W-155, 370, 135, 40)
        mx,my = pygame.mouse.get_pos()
        draw_button(surf, self._regen_btn, "🔄 Regenerate",
                    self.fonts["small"], hover=self._regen_btn.collidepoint(mx,my),
                    color=C_GREY, text_color=C_WHITE)
        draw_button(surf, self._next_btn,  "PLAY MATCH →",
                    self.fonts["small"], hover=self._next_btn.collidepoint(mx,my))


# ═══════════════════════════════════════════════════════════════════════════
#  MATCH SCREEN  —  with Timing Bar + Shot Direction Joystick
# ═══════════════════════════════════════════════════════════════════════════
class MatchScreen(Screen):

    IDLE    = "idle"
    TIMING  = "timing"     # timing bar running — press SPACE to hit
    RUNNING = "running"    # bowler run-up animation
    BOWLING = "bowling"    # ball in flight
    IMPACT  = "impact"
    RESULT  = "result"

    # Shot direction zones (angle in degrees from center)
    SHOT_DIRS = {
        "Drive" : (0,   -1.0),   # straight
        "Loft"  : (0,   -0.8),   # straight up
        "Pull"  : (-130, 0.9),   # leg side behind square
        "Cut"   : (130,  0.9),   # off side behind square
        "Sweep" : (-110, 0.7),   # fine leg
        "Defend": (0,    0.1),   # back to bowler
    }

    def on_enter(self):
        self._t          = 0.0
        self._phase      = self.IDLE
        self._ball_phase = 0.0
        self._run_phase  = 0.0
        self._bat_swing  = 0.0
        self._particles  = []
        self._result_txt = ""
        self._result_col = C_WHITE
        self._result_t   = 0.0
        self._pending    = None

        # Timing bar state
        self._timing_val   = 0.0    # 0→1→0 oscillating
        self._timing_dir   = 1.0
        self._timing_speed = 1.4    # how fast bar moves
        self._timing_zone  = None   # "early"/"perfect"/"late"/None
        self._selected_shot= None   # chosen shot type
        self._shot_pending = None   # shot chosen, waiting for timing

        # Joystick state
        self._joystick_x   = 0.0   # -1 to +1
        self._joystick_y   = 0.0
        self._dragging     = False
        self._drag_start   = None
        self._joy_center   = None

        # Ground layout
        gw, gh  = 500, 420
        self._gx = 50; self._gy = (WIN_H-gh)//2
        self._gcx= self._gx+gw//2; self._gcy = self._gy+gh//2
        self._ball_x = float(self._gcx)
        self._ball_y = float(self._gcy - gh*0.22)
        self._ball_tx= float(self._gcx)
        self._ball_ty= float(self._gcy + gh*0.20)
        self._ball_trail = []

        self._human_is_batting = (self.state.current_batting()=="human")
        self._setup_buttons()
        self._show_switch = False

    def _setup_buttons(self):
        """Shot/delivery selection buttons on right panel."""
        options = SHOTS if self._human_is_batting else DELIVERIES
        self._action_btns = []
        bw, bh = 158, 42
        startx = WIN_W - 530
        starty = 310
        cols = 3
        for i, opt in enumerate(options):
            r = i // cols; c = i % cols
            rect = pygame.Rect(startx + c*(bw+6), starty + r*(bh+6), bw, bh)
            self._action_btns.append((rect, opt))

    # ── Events ────────────────────────────────────────────────────────────
    def handle_event(self, e):
        if self._show_switch:
            if e.type == pygame.MOUSEBUTTONDOWN:
                if hasattr(self,"_switch_btn") and self._switch_btn.collidepoint(e.pos):
                    self.state.innings = 2
                    self._show_switch  = False
                    self._human_is_batting = (self.state.current_batting()=="human")
                    self._setup_buttons()
                    self._phase = self.IDLE
            return

        # ── BATTING: select shot → show timing bar → SPACE to hit ─────────
        if self._human_is_batting:
            if e.type == pygame.MOUSEBUTTONDOWN:
                mx, my = e.pos
                if self._phase == self.IDLE:
                    for rect, opt in self._action_btns:
                        if rect.collidepoint(mx, my):
                            self._shot_pending = opt
                            self._phase = self.TIMING
                            self._timing_val = 0.0
                            self._timing_dir = 1.0
                            return
                    # Joystick drag start
                    if hasattr(self,"_joy_center"):
                        jx, jy = self._joy_center
                        if math.hypot(mx-jx, my-jy) < 60:
                            self._dragging   = True
                            self._drag_start = (mx, my)

                elif self._phase == self.TIMING:
                    # Click anywhere also triggers timing
                    self._fire_timing()

                if e.type == pygame.MOUSEBUTTONDOWN and self._phase == self.IDLE:
                    if hasattr(self,"_joy_center"):
                        self._dragging = True
                        self._drag_start = e.pos

            if e.type == pygame.MOUSEBUTTONUP:
                self._dragging = False
                self._joystick_x = 0.0
                self._joystick_y = 0.0

            if e.type == pygame.MOUSEMOTION and self._dragging and self._drag_start:
                dx = e.pos[0] - self._drag_start[0]
                dy = e.pos[1] - self._drag_start[1]
                dist = math.hypot(dx, dy)
                if dist > 0:
                    self._joystick_x = max(-1, min(1, dx/50))
                    self._joystick_y = max(-1, min(1, dy/50))

            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_SPACE and self._phase == self.TIMING:
                    self._fire_timing()

        # ── BOWLING: just pick delivery ────────────────────────────────────
        else:
            if e.type == pygame.MOUSEBUTTONDOWN:
                mx, my = e.pos
                if self._phase == self.IDLE:
                    for rect, opt in self._action_btns:
                        if rect.collidepoint(mx, my):
                            self._selected_shot = opt
                            self._start_ball(opt)
                            return

    def _fire_timing(self):
        """Called when player presses SPACE/clicks during timing bar."""
        val = self._timing_val
        if 0.38 <= val <= 0.62:
            zone = "perfect"
        elif 0.22 <= val < 0.38 or 0.62 < val <= 0.78:
            zone = "good"
        else:
            zone = "early" if val < 0.5 else "late"
        self._timing_zone = zone
        self._start_ball(self._shot_pending, timing=zone)

    def _start_ball(self, human_action: str, timing: str = "perfect"):
        """Resolve ball outcome + start animation."""
        balls_left  = self.state.balls_left()
        balls_done  = self.state.balls_done()
        runs_needed = max(1, self.state.target()-self.state.chasing_score()) \
                      if self.state.innings==2 else 10

        if self._human_is_batting:
            delivery, reasoning = ai_bowl(
                balls_left, runs_needed, self.state.last_shot,
                self.state.ql, balls_done)
            shot = human_action
            self.state.ai_reasoning = reasoning
            self.state.pitch = reasoning["pitch"]
            self.state.mood  = reasoning["mood"]
            self.state.shot_probs = reasoning["shot_probs"]

            # Timing affects runs: perfect=full, good=75%, early/late=50%
            result = resolve_ball(delivery, shot)
            if not result["wicket"]:
                mult = {"perfect":1.0, "good":0.75,
                        "early":0.5, "late":0.5}.get(timing, 1.0)
                result["runs"] = max(0, int(result["runs"] * mult))
                if timing in ("early","late") and result["runs"] > 0:
                    result["desc"] += f"  ({timing.upper()} — mistimed!)"
        else:
            delivery = human_action
            from engine.ai import infer_pitch, infer_mood
            pitch = infer_pitch(balls_done)
            mood  = infer_mood(balls_left, runs_needed)
            shot  = bayesian_sample_shot(pitch, mood)
            self.state.pitch = pitch; self.state.mood = mood
            self.state.ai_reasoning = {
                "final":delivery,"bayesian":delivery,
                "minimax":delivery,"qlearn":delivery,
                "pitch":pitch,"mood":mood,"shot_probs":{}}
            result = resolve_ball(delivery, shot)

        self.state.last_result = result
        self._pending    = result
        self._phase      = self.RUNNING
        self._run_phase  = 0.0
        self._ball_phase = 0.0
        self._timing_zone= timing if self._human_is_batting else None

        gcy = self._gcy; gh = 420
        self._ball_x = float(self._gcx + random.randint(-8,8))
        self._ball_y = float(gcy - gh*0.22)
        # Shot direction from joystick
        jx = self._joystick_x
        self._ball_tx = float(self._gcx + jx*120 + random.randint(-6,6))
        self._ball_ty = float(gcy + gh*0.18)
        self._ball_trail = []
        self._joystick_x = 0.0; self._joystick_y = 0.0

    # ── Update ────────────────────────────────────────────────────────────
    def update(self, dt):
        self._t += dt

        # Timing bar oscillation
        if self._phase == self.TIMING:
            self._timing_val += dt * self._timing_speed * self._timing_dir
            if self._timing_val >= 1.0:
                self._timing_val = 1.0; self._timing_dir = -1.0
            elif self._timing_val <= 0.0:
                self._timing_val = 0.0; self._timing_dir = 1.0

        if self._phase == self.RUNNING:
            self._run_phase += dt * 2.5
            if self._run_phase >= 1.0:
                self._phase = self.BOWLING
                self._ball_phase = 0.0

        elif self._phase == self.BOWLING:
            self._ball_phase += dt * 2.6
            prog = min(self._ball_phase, 1.0)
            self._ball_trail.append((self._ball_x, self._ball_y))
            if len(self._ball_trail) > 14: self._ball_trail.pop(0)
            # Arc
            arc_y = -70 * math.sin(prog * math.pi)
            self._ball_x = self._gcx + (self._ball_tx-self._gcx)*prog
            self._ball_y = self._ball_ty + \
                (self._ball_y - self._ball_ty) * (1-0.1) + \
                arc_y * (1-prog) * 0.3
            self._ball_x = self._gcx + (self._ball_tx-self._gcx)*prog
            self._ball_y = self._ball_ty + \
                (1-prog)**2 * (self._ball_y - self._ball_ty) + arc_y*prog*(1-prog)

            if self._ball_phase >= 1.0:
                self._phase = self.IMPACT
                result = self._pending
                col = C_RED if result["wicket"] else \
                    ((255,215,0) if result["runs"]==6 else
                    (C_GREEN if result["runs"]==4 else C_WHITE))
                particle_burst(self._particles,
                    int(self._ball_tx), int(self._ball_ty), col, 35)
                self._bat_swing = 1.0

        elif self._phase == self.IMPACT:
            self._bat_swing = max(0, self._bat_swing - dt*3)
            self._phase = self.RESULT
            result = self._pending
            self.state.record_ball(result["runs"], result["wicket"])
            self.state.last_shot = result["shot"]
            bl2 = self.state.balls_left()
            rn2 = max(0, self.state.target()-self.state.chasing_score()) \
                  if self.state.innings==2 else 10
            self.state.ql.update(result["runs"], result["wicket"],
                                  bl2, rn2, result["shot"])
            self._result_txt = result["desc"]
            self._result_col = C_RED if result["wicket"] else \
                ((255,215,0) if result["runs"]==6 else
                (C_GREEN if result["runs"]==4 else C_CREAM))
            self._result_t = 0.0

        elif self._phase == self.RESULT:
            self._result_t += dt
            self._bat_swing = max(0, self._bat_swing-dt*2)
            if self._result_t > 2.2:
                done = self.state.balls_done()
                if done >= 6 or self._pending["wicket"]:
                    if self.state.innings == 1:
                        self._show_switch = True; self._phase = self.IDLE
                    else:
                        self.state.determine_winner()
                        self.mgr.goto("result")
                else:
                    self._phase = self.IDLE
                    self._selected_shot = None
                    self._shot_pending  = None
                    self._timing_zone   = None

        # update particles
        alive = []
        for p in self._particles:
            p["x"] += p["vx"]; p["y"] += p["vy"]
            p["vy"] += 0.3; p["life"] -= 0.04
            if p["life"] > 0: alive.append(p)
        self._particles[:] = alive

    # ── Draw ──────────────────────────────────────────────────────────────
    def draw(self, surf):
        surf.fill(C_BG)
        gw, gh = 500, 420
        gx, gy = self._gx, self._gy
        gcx, gcy = self._gcx, self._gcy

        draw_stadium_backdrop(surf, gy-46, self._t)
        draw_ad_ribbon(surf, max(8, gy-78), text="AI VS HUMAN CUP")

        # Ground
        draw_ground(surf, gcx, gcy, gw//2-10, gh//2-12)

        # Fielders
        for zid, info in self.state.field_positions.items():
            fx = gx + int(info["x"]*gw)
            fy = gy + int(info["y"]*gh)
            draw_fielder(surf, fx, fy)

        # Bowler
        bowl_y = gcy - gh*0.22 - 30
        draw_bowler(surf, gcx, int(bowl_y),
                    run_phase=self._run_phase if self._phase==self.RUNNING else 0)

        # Batsman
        draw_batsman(surf, gcx, int(gcy+gh*0.18),
                     color=C_GOLD, swing=self._bat_swing)

        # Ball
        if self._phase in (self.BOWLING, self.IMPACT, self.RESULT):
            draw_ball(surf, self._ball_x, self._ball_y,
                      trail=self._ball_trail)

        # Particles
        for p in self._particles:
            alpha = int(255 * p["life"])
            s2 = pygame.Surface((p["size"]*2, p["size"]*2), pygame.SRCALPHA)
            pygame.draw.circle(s2, (*p["color"][:3], alpha),
                               (p["size"], p["size"]), p["size"])
            surf.blit(s2, (int(p["x"])-p["size"], int(p["y"])-p["size"]))

        # ── RIGHT PANEL ───────────────────────────────────────────────────
        px = gx + gw + 18
        pw = WIN_W - px - 14

        # ── Scoreboard ────────────────────────────────────────────────────
        rounded_rect(surf, C_CARD, (px, gy, pw, 118), radius=14,
                     border=1, border_color=(42,70,100))
        draw_text(surf, f"INNINGS {self.state.innings}",
                  self.fonts["tiny"], C_GOLD, px+14, gy+8)
        h_sc = self.state.scores["human"]; h_wk = self.state.wickets["human"]
        a_sc = self.state.scores["ai"];    a_wk = self.state.wickets["ai"]
        draw_text(surf, "👤 YOU", self.fonts["small"], C_GOLD, px+14, gy+28)
        draw_text(surf, f"{h_sc}/{h_wk}", self.fonts["big"], C_GOLD, px+110, gy+20)
        draw_text(surf, "🤖 AI",  self.fonts["small"], C_BLUE, px+14, gy+68)
        draw_text(surf, f"{a_sc}/{a_wk}", self.fonts["big"], C_BLUE, px+110, gy+60)
        for i in range(6):
            done = self.state.balls_done()
            col  = C_GREEN if i < done else C_DARK
            pygame.draw.circle(surf, col, (px+pw-16-i*20, gy+62), 7)
            pygame.draw.circle(surf, C_GREY, (px+pw-16-i*20, gy+62), 7, 1)

        if self.state.innings == 2:
            tgt  = self.state.target()
            need = max(0, tgt - self.state.chasing_score())
            bl   = self.state.balls_left()
            draw_text(surf, f"🎯 Need {need} off {bl} balls  (Target:{tgt})",
                      self.fonts["small"], C_ORANGE, px+14, gy+124)

        # ── Commentary bar ────────────────────────────────────────────────
        com_y = gy + 148 if self.state.innings==1 else gy+158
        if self._phase == self.RESULT and self._result_txt:
            rounded_rect(surf, (20,45,25), (px, com_y, pw, 42), radius=10)
            draw_text(surf, self._result_txt, self.fonts["small"],
                      self._result_col, px+pw//2, com_y+14, center=True)

        # Ball dots
        bd_y = gy + 202 if self.state.innings==1 else gy+212
        draw_text(surf, "OVER:", self.fonts["tiny"], C_GREY, px+10, bd_y+2)
        draw_ball_dots(surf, self.state.balls[self.state.innings],
                       px+60, bd_y-2, self.fonts["tiny"])

        # ── TIMING BAR (when batting and timing phase) ────────────────────
        tb_y = gy + 240
        if self._human_is_batting:
            # Always show timing bar area
            tb_w = pw - 20; tb_h = 28
            tb_x = px + 10

            # Background zones: early | good | PERFECT | good | late
            zone_colors = [
                (0.00, 0.22, (180,60,60)),    # early (red)
                (0.22, 0.38, (220,160,40)),   # good (orange)
                (0.38, 0.62, (60,200,80)),    # PERFECT (green)
                (0.62, 0.78, (220,160,40)),   # good (orange)
                (0.78, 1.00, (180,60,60)),    # late (red)
            ]
            for z_start, z_end, z_col in zone_colors:
                zx = tb_x + int(z_start * tb_w)
                zw = int((z_end-z_start) * tb_w)
                pygame.draw.rect(surf, z_col, (zx, tb_y, zw, tb_h), border_radius=4)

            # Zone labels
            for label, frac, col in [
                ("EARLY", 0.11, (255,120,120)),
                ("GOOD",  0.30, (255,200,80)),
                ("PERFECT",0.50,(100,255,120)),
                ("GOOD",  0.70, (255,200,80)),
                ("LATE",  0.89, (255,120,120)),
            ]:
                lx = tb_x + int(frac * tb_w)
                draw_text(surf, label, self.fonts["tiny"], col, lx, tb_y+6, center=True)

            # Moving indicator
            if self._phase == self.TIMING:
                ind_x = tb_x + int(self._timing_val * tb_w)
                pygame.draw.rect(surf, C_WHITE,
                    (ind_x-3, tb_y-4, 6, tb_h+8), border_radius=3)
                # Glow
                s2 = pygame.Surface((20, tb_h+16), pygame.SRCALPHA)
                pygame.draw.rect(s2, (255,255,255,60), (0,0,20,tb_h+16), border_radius=4)
                surf.blit(s2, (ind_x-10, tb_y-8))

            # Timing result flash
            if self._phase in (self.RUNNING, self.BOWLING, self.RESULT):
                if self._timing_zone:
                    zone_col = {"perfect":(60,220,80),"good":(220,160,40),
                                "early":(200,60,60),"late":(200,60,60)}
                    tc = zone_col.get(self._timing_zone, C_CREAM)
                    draw_text(surf, self._timing_zone.upper()+"!",
                              self.fonts["med"], tc,
                              tb_x+tb_w//2, tb_y-18, center=True)

            draw_text(surf, "TIMING  (SPACE or click to hit)",
                      self.fonts["tiny"], C_GREY, tb_x, tb_y+tb_h+4)

            # ── Shot selection buttons ─────────────────────────────────────
            sh_y = tb_y + tb_h + 28
            draw_text(surf, "SELECT SHOT:", self.fonts["small"],
                      C_GOLD, px+10, sh_y)
            mx2, my2 = pygame.mouse.get_pos()
            enabled = (self._phase == self.IDLE)
            for rect, opt in self._action_btns:
                rect2 = pygame.Rect(rect.x, rect.y+40, rect.w, rect.h)
                is_sel = (opt == self._shot_pending)
                hover  = rect2.collidepoint(mx2,my2) and enabled
                bg_col = C_GREEN if is_sel else \
                         ((80,160,80) if self._phase==self.TIMING and is_sel
                          else (C_GOLD if enabled else C_GREY))
                draw_button(surf, rect2, opt, self.fonts["tiny"],
                            hover=hover, active=is_sel,
                            color=bg_col, text_color=C_BG)
                # Emoji label
                from constants import SHOT_EMOJIS
                em = SHOT_EMOJIS.get(opt,"")
                draw_text(surf, em, self.fonts["small"], C_GOLD,
                          rect2.x+4, rect2.y+10)

            # ── Shot direction joystick ────────────────────────────────────
            joy_x = px + pw//2
            joy_y = sh_y + 185
            self._joy_center = (joy_x, joy_y)
            joy_r = 52

            # Outer ring
            pygame.draw.circle(surf, (30,50,70), (joy_x, joy_y), joy_r)
            pygame.draw.circle(surf, C_GREY, (joy_x, joy_y), joy_r, 2)

            # Direction labels
            for lbl, dx2, dy2 in [
                ("LEG", -joy_r-18, 0),
                ("MID", 0, -joy_r-14),
                ("OFF", joy_r+18, 0),
            ]:
                draw_text(surf, lbl, self.fonts["tiny"], C_GREY,
                          joy_x+dx2, joy_y+dy2-5, center=True)

            # Knob
            kx = joy_x + int(self._joystick_x * (joy_r-14))
            ky = joy_y + int(self._joystick_y * (joy_r-14))
            pygame.draw.circle(surf, C_GOLD, (kx, ky), 18)
            pygame.draw.circle(surf, C_WHITE, (kx, ky), 18, 2)
            draw_text(surf, "🏏", self.fonts["small"], C_BG,
                      kx, ky, center=True)

            draw_text(surf, "DRAG to aim shot direction",
                      self.fonts["tiny"], C_GREY, joy_x, joy_y+joy_r+10, center=True)

        else:
            # ── BOWLING mode buttons ───────────────────────────────────────
            draw_text(surf, "🎯 YOUR DELIVERY:", self.fonts["med"],
                      C_GOLD, px+10, tb_y-22)
            mx2, my2 = pygame.mouse.get_pos()
            enabled = (self._phase == self.IDLE)
            for rect, opt in self._action_btns:
                rect2 = pygame.Rect(rect.x, rect.y, rect.w, rect.h)
                is_sel = (opt == self._selected_shot)
                hover  = rect2.collidepoint(mx2,my2) and enabled
                draw_button(surf, rect2, opt, self.fonts["small"],
                            hover=hover, active=is_sel,
                            color=C_GREEN if is_sel else (C_GOLD if enabled else C_GREY),
                            text_color=C_BG)

        # ── AI Reasoning panel ────────────────────────────────────────────
        ry_start = WIN_H - 190
        rounded_rect(surf, C_CARD, (px, ry_start, pw, 178), radius=12,
                     border=1, border_color=(42,70,100))
        draw_text(surf, "🤖 AI REASONING", self.fonts["small"],
                  C_GOLD, px+12, ry_start+8)
        ar = self.state.ai_reasoning
        if ar:
            items = [
                (C_GREEN,  "A*",      "8 fielders optimal ✓"),
                (C_BLUE,   "Minimax", f"→ {ar.get('minimax','?')}"),
                (C_ORANGE, "Bayes",   f"{ar.get('pitch','?')} · {ar.get('mood','?')} → {ar.get('bayesian','?')}"),
                (C_PINK,   "Q-Learn", f"→ {ar.get('qlearn','?')}"),
                (C_GREEN,  "FINAL",   f"→ {ar.get('final','?')} (vote)"),
            ]
            for i,(col,algo,val) in enumerate(items):
                iy = ry_start+30+i*26
                pygame.draw.rect(surf, col, (px+8, iy+3, 3, 18))
                draw_text(surf, f"{algo}:", self.fonts["tiny"], col, px+18, iy+4)
                draw_text(surf, val,        self.fonts["tiny"], C_CREAM, px+100, iy+4)

            # Bayesian prob mini bars
            probs = ar.get("shot_probs", {})
            if probs:
                by0 = ry_start+162
                for i,(shot,prob) in enumerate(list(probs.items())[:4]):
                    bx2 = px+10+i*int(pw/4)
                    bw2 = int(pw/4)-4
                    pygame.draw.rect(surf, C_DARK, (bx2, by0, bw2, 8), border_radius=4)
                    fw2 = int(bw2*prob)
                    if fw2>0:
                        pygame.draw.rect(surf, C_ORANGE,
                                         (bx2, by0, fw2, 8), border_radius=4)
                    draw_text(surf, f"{shot[:3]}", self.fonts["tiny"],
                              C_CREAM, bx2, by0-12)

        # ── Innings switch overlay ────────────────────────────────────────
        if self._show_switch:
            ov = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
            ov.fill((0,0,0,170))
            surf.blit(ov, (0,0))
            sw2, sh2 = 620, 270
            sx2 = WIN_W//2-sw2//2; sy2 = WIN_H//2-sh2//2
            rounded_rect(surf, C_CARD, (sx2,sy2,sw2,sh2), radius=18,
                         border=2, border_color=C_GOLD)
            draw_text(surf, "⚡ END OF INNINGS 1", self.fonts["big"],
                      C_GOLD, WIN_W//2, sy2+36, center=True)
            sc1 = self.state.scores[self.state.innings1_batting]
            wk1 = self.state.wickets[self.state.innings1_batting]
            btr = "You scored" if self.state.innings1_batting=="human" else "AI scored"
            draw_text(surf, f"{btr}  {sc1}/{wk1}",
                      self.fonts["med"], C_CREAM, WIN_W//2, sy2+88, center=True)
            draw_text(surf, f"Target:  {self.state.target()} runs in 6 balls",
                      self.fonts["big"], C_ORANGE, WIN_W//2, sy2+122, center=True)
            self._switch_btn = pygame.Rect(WIN_W//2-140, sy2+sh2-72, 280, 52)
            mx3,my3 = pygame.mouse.get_pos()
            draw_button(surf, self._switch_btn, "START INNINGS 2  ▶",
                        self.fonts["med"],
                        hover=self._switch_btn.collidepoint(mx3,my3))


# ═══════════════════════════════════════════════════════════════════════════
#  RESULT SCREEN
# ═══════════════════════════════════════════════════════════════════════════
class ResultScreen(Screen):
    def on_enter(self):
        self._t = 0.0
        self._particles = []
        col = C_GOLD if self.state.winner=="human" else C_BLUE
        particle_burst(self._particles, WIN_W//2, WIN_H//2, col, 80)

    def handle_event(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN:
            if hasattr(self,"_play_btn") and self._play_btn.collidepoint(e.pos):
                from game.state import GameState
                self.mgr.state = GameState()
                self.mgr.screens["toss"].state    = self.mgr.state
                self.mgr.screens["field"].state   = self.mgr.state
                self.mgr.screens["minimax_demo"].state = self.mgr.state
                self.mgr.screens["match"].state   = self.mgr.state
                self.mgr.screens["result"].state  = self.mgr.state
                self.mgr.goto("toss")
            if hasattr(self,"_quit_btn") and self._quit_btn.collidepoint(e.pos):
                pygame.quit(); import sys; sys.exit()

    def update(self, dt):
        self._t += dt
        if self._t < 3.0:
            if random.random() < 0.3:
                col = C_GOLD if self.state.winner=="human" else C_BLUE
                particle_burst(self._particles,
                    random.randint(0,WIN_W), random.randint(0,WIN_H//2),
                    col, 8)

    def draw(self, surf):
        surf.fill(C_BG)
        update_draw_particles(surf, self._particles)

        winner = self.state.winner
        emoji  = "🏆" if winner=="human" else ("🤖" if winner=="ai" else "🤝")
        col    = C_GOLD if winner=="human" else (C_BLUE if winner=="ai" else C_GREY)

        draw_text(surf, emoji,  self.fonts["huge"], col, WIN_W//2, 100, center=True)
        draw_text(surf, self.state.result_message, self.fonts["big"], col,
                  WIN_W//2, 195, center=True, shadow=True)

        # Scorecard
        sw, sh = 700, 260
        sx, sy = WIN_W//2-sw//2, 240
        rounded_rect(surf, C_CARD, (sx,sy,sw,sh), radius=16,
                     border=1, border_color=(42,70,100))
        draw_text(surf, "MATCH SCORECARD", self.fonts["med"], C_GOLD, sx+20, sy+14)

        for inn, batting, label in [
            (1, self.state.innings1_batting, "Innings 1"),
            (2, self.state.innings2_batting, "Innings 2"),
        ]:
            iy = sy+52+(inn-1)*80
            rounded_rect(surf, C_CARD2, (sx+14, iy, sw-28, 64), radius=10)
            sc  = self.state.scores[batting]
            wk  = self.state.wickets[batting]
            who = "👤 YOU" if batting=="human" else "🤖 AI"
            wcol= C_GOLD if batting=="human" else C_BLUE
            draw_text(surf, f"{label}  —  {who} batting",
                      self.fonts["small"], wcol, sx+28, iy+8)
            draw_text(surf, f"{sc}/{wk}", self.fonts["big"], wcol, sx+28, iy+28)
            draw_ball_dots(surf, self.state.balls[inn],
                           sx+130, iy+30, self.fonts["tiny"])

        # Algorithm summary
        rounded_rect(surf, C_CARD, (sx, sy+sh+14, sw, 80), radius=12,
                     border=1, border_color=(42,70,100))
        draw_text(surf, "Algorithms used: A* · Minimax+α-β · Bayesian Network · Q-Learning",
                  self.fonts["small"], C_GREY, WIN_W//2, sy+sh+30, center=True)
        ql_hist = self.state.ql.history
        if ql_hist:
            avg_r = sum(h["reward"] for h in ql_hist)/len(ql_hist)
            draw_text(surf,
                f"Q-Learning: {len(ql_hist)} balls learned  ·  avg reward {avg_r:+.2f}  ·  Q-states: {len(self.state.ql.Q)}",
                self.fonts["tiny"], C_PINK, WIN_W//2, sy+sh+52, center=True)

        # Buttons
        self._play_btn = pygame.Rect(WIN_W//2-260, sy+sh+110, 240, 52)
        self._quit_btn = pygame.Rect(WIN_W//2+20,  sy+sh+110, 240, 52)
        mx,my = pygame.mouse.get_pos()
        draw_button(surf, self._play_btn, "🔄  PLAY AGAIN",
                    self.fonts["med"], hover=self._play_btn.collidepoint(mx,my))
        draw_button(surf, self._quit_btn, "✖  QUIT",
                    self.fonts["med"], hover=self._quit_btn.collidepoint(mx,my),
                    color=C_RED, text_color=C_WHITE)