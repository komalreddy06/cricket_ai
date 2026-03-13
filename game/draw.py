"""
game/draw.py  —  All drawing functions (ground, players, ball, HUD)
"""
import pygame, math, random
from constants import *


def draw_stadium_backdrop(surf, horizon_y, t=0.0):
    """Draw a sky gradient, crowd band, and floodlights for a richer scene."""
    sky_top = (18, 48, 84)
    sky_bottom = (110, 150, 190)
    for y in range(horizon_y):
        f = y / max(horizon_y, 1)
        col = (
            int(sky_top[0] + (sky_bottom[0] - sky_top[0]) * f),
            int(sky_top[1] + (sky_bottom[1] - sky_top[1]) * f),
            int(sky_top[2] + (sky_bottom[2] - sky_top[2]) * f),
        )
        pygame.draw.line(surf, col, (0, y), (WIN_W, y))

    # Subtle clouds
    for i in range(5):
        cx = int((i + 0.5) * WIN_W / 5 + math.sin(t * 0.15 + i) * 30)
        cy = int(horizon_y * 0.25 + (i % 2) * 35)
        cl = pygame.Surface((150, 56), pygame.SRCALPHA)
        pygame.draw.ellipse(cl, (255, 255, 255, 38), (0, 10, 120, 34))
        pygame.draw.ellipse(cl, (255, 255, 255, 45), (35, 0, 110, 40))
        surf.blit(cl, (cx - 75, cy))

    # Crowd tiers + tiny seats
    pygame.draw.rect(surf, (42, 45, 58), (0, horizon_y, WIN_W, 46))
    pygame.draw.rect(surf, (28, 32, 42), (0, horizon_y + 46, WIN_W, 22))
    for x in range(0, WIN_W, 9):
        col = (95 + (x % 30), 95 + (x % 60), 112 + (x % 40))
        pygame.draw.rect(surf, col, (x, horizon_y + 6 + ((x // 9) % 2), 5, 3))

    # Floodlights
    for lx in (75, WIN_W - 75):
        pygame.draw.rect(surf, (155, 165, 185), (lx - 3, horizon_y - 135, 6, 135))
        pygame.draw.rect(surf, (225, 225, 210), (lx - 22, horizon_y - 150, 44, 12), border_radius=4)
        glow = pygame.Surface((160, 180), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (255, 255, 200, 42), (0, 15, 160, 165))
        surf.blit(glow, (lx - 80, horizon_y - 5))

def draw_ground(surf, cx, cy, rx, ry):
    """Draw cricket oval ground with pitch, crease, boundary."""
    # Turf base
    pygame.draw.ellipse(surf, (16, 48, 20),
        (int(cx-rx), int(cy-ry), int(rx*2), int(ry*2)))

    # Outer field gradient via concentric ellipses
    for i in range(12, 0, -1):
        f  = i / 12
        g  = int(22 + f*12), int(55 + f*30), int(22 + f*12)
        pygame.draw.ellipse(surf, g,
            (int(cx-rx*f), int(cy-ry*f), int(rx*f*2), int(ry*f*2)))

    # Mowing stripes (alternate brightness)
    for i in range(8):
        band_h = int((ry * 2) / 8)
        y = int(cy - ry + i * band_h)
        shade = 18 if i % 2 == 0 else -10
        stripe_col = (max(0, 40 + shade), max(0, 95 + shade), max(0, 44 + shade))
        stripe = pygame.Surface((int(rx * 2), band_h), pygame.SRCALPHA)
        stripe.fill((*stripe_col, 70))
        mask = pygame.Surface((int(rx * 2), int(ry * 2)), pygame.SRCALPHA)
        pygame.draw.ellipse(mask, (255, 255, 255, 255), (0, 0, int(rx * 2), int(ry * 2)))
        stripe.blit(mask, (0, -int(i * band_h)), special_flags=pygame.BLEND_RGBA_MULT)
        surf.blit(stripe, (int(cx-rx), y))

    # Boundary rope
    pygame.draw.ellipse(surf, (255,255,255,60),
        (int(cx-rx+4), int(cy-ry+4), int(rx*2-8), int(ry*2-8)), 2)
    pygame.draw.ellipse(surf, (230, 200, 145),
        (int(cx-rx+10), int(cy-ry+10), int(rx*2-20), int(ry*2-20)), 1)

    # 30-yard inner circle
    pygame.draw.ellipse(surf, (255,255,255,30),
        (int(cx-rx*.52), int(cy-ry*.52),
         int(rx*1.04), int(ry*1.04)), 1)

    # Pitch strip
    pw, ph = 26, int(ry*.56)
    pygame.draw.rect(surf, C_PITCH_STRIP,
        (cx-pw//2, cy-ph//2, pw, ph), border_radius=3)
    # Crease lines
    pygame.draw.rect(surf, C_WHITE,
        (cx-pw//2-2, cy-ph//2+8, pw+4, 4))
    pygame.draw.rect(surf, C_WHITE,
        (cx-pw//2-2, cy+ph//2-12, pw+4, 4))
    # Stumps
    for sx in [cx-6, cx, cx+6]:
        pygame.draw.line(surf, C_STUMPS, (sx, cy-ph//2+2), (sx, cy-ph//2+12), 2)
        pygame.draw.line(surf, C_STUMPS, (sx, cy+ph//2-12),(sx, cy+ph//2-2),  2)


def draw_batsman(surf, x, y, color=C_GOLD, swing=0.0, scale=1.0):
    """Draw stick-figure batsman with bat swing animation."""
    s = scale
    # Shadow
    pygame.draw.ellipse(surf, (0,0,0,60),
        (int(x-18*s), int(y+28*s), int(36*s), int(10*s)))
    # Body
    pygame.draw.line(surf, color, (int(x), int(y-20*s)), (int(x), int(y+10*s)), int(3*s))
    # Head
    pygame.draw.circle(surf, color, (int(x), int(y-26*s)), int(8*s))
    # Helmet
    pygame.draw.arc(surf, (80,80,80),
        (int(x-9*s), int(y-36*s), int(18*s), int(18*s)), 0, math.pi, int(3*s))
    # Legs
    pygame.draw.line(surf, color, (int(x), int(y+10*s)),
                     (int(x-10*s), int(y+28*s)), int(3*s))
    pygame.draw.line(surf, color, (int(x), int(y+10*s)),
                     (int(x+8*s),  int(y+28*s)), int(3*s))
    # Arms & bat
    bat_angle = math.radians(-40 + swing * 100)
    arm_end_x = x + math.cos(bat_angle) * 22*s
    arm_end_y = y - 5*s + math.sin(bat_angle) * 22*s
    bat_end_x = x + math.cos(bat_angle) * 42*s
    bat_end_y = y - 5*s + math.sin(bat_angle) * 42*s
    pygame.draw.line(surf, color,   (int(x), int(y-5*s)),
                     (int(arm_end_x), int(arm_end_y)), int(3*s))
    pygame.draw.line(surf, (200,160,80),
                     (int(arm_end_x), int(arm_end_y)),
                     (int(bat_end_x), int(bat_end_y)), int(5*s))
    # Pads
    pygame.draw.rect(surf, (240,240,200),
        (int(x-12*s), int(y+10*s), int(8*s), int(16*s)), border_radius=3)
    pygame.draw.rect(surf, (240,240,200),
        (int(x+4*s),  int(y+10*s), int(8*s), int(16*s)), border_radius=3)


def draw_bowler(surf, x, y, color=C_BLUE, run_phase=0.0, scale=1.0):
    """Draw stick-figure bowler with run-up animation."""
    s   = scale
    bob = math.sin(run_phase * math.pi * 2) * 4 * s
    # Shadow
    pygame.draw.ellipse(surf, (0,0,0,60),
        (int(x-16*s), int(y+28*s), int(32*s), int(8*s)))
    # Body
    pygame.draw.line(surf, color,
        (int(x), int(y-20*s+bob)), (int(x), int(y+10*s+bob)), int(3*s))
    # Head
    pygame.draw.circle(surf, color, (int(x), int(y-27*s+bob)), int(7*s))
    # Legs (animated)
    leg_swing = math.sin(run_phase*math.pi*4)*12*s
    pygame.draw.line(surf, color, (int(x), int(y+10*s+bob)),
                     (int(x-10*s+leg_swing), int(y+28*s+bob)), int(3*s))
    pygame.draw.line(surf, color, (int(x), int(y+10*s+bob)),
                     (int(x+10*s-leg_swing), int(y+28*s+bob)), int(3*s))
    # Bowling arm (raised)
    arm_angle = math.radians(-110 + run_phase*60)
    ax = x + math.cos(arm_angle)*20*s
    ay = y - 10*s + bob + math.sin(arm_angle)*20*s
    pygame.draw.line(surf, color,
        (int(x), int(y-10*s+bob)), (int(ax), int(ay)), int(3*s))
    pygame.draw.line(surf, color,
        (int(x), int(y-10*s+bob)),
        (int(x-15*s), int(y+0*s+bob)), int(3*s))


def draw_fielder(surf, x, y, color=(100,180,100), scale=0.7):
    s = scale
    pygame.draw.ellipse(surf, (0,0,0,65), (int(x-8*s), int(y+6*s), int(16*s), int(5*s)))
    pygame.draw.circle(surf, color, (int(x), int(y)), int(10*s))
    pygame.draw.circle(surf, (200,200,200), (int(x), int(y-14*s)), int(5*s))
    pygame.draw.line(surf, color, (int(x), int(y-9*s)), (int(x), int(y+4*s)), int(2*s))


def draw_ball(surf, x, y, r=BALL_R, trail=None):
    """Draw cricket ball with seam, shine, and optional motion trail."""
    if trail:
        for i, (tx, ty) in enumerate(trail):
            alpha = int(80 * (i+1)/len(trail))
            tr = max(2, int(r * (i+1)/len(trail) * 0.6))
            col = (200, 40, 40, alpha)
            s2  = pygame.Surface((tr*2, tr*2), pygame.SRCALPHA)
            pygame.draw.circle(s2, (200,40,40,alpha), (tr,tr), tr)
            surf.blit(s2, (int(tx)-tr, int(ty)-tr))
    # Main ball
    pygame.draw.circle(surf, C_BALL, (int(x), int(y)), r)
    # Seam
    pygame.draw.arc(surf, C_BALL_SEAM,
        (int(x-r+2), int(y-r), r*2-4, r*2), 0.3, math.pi-0.3, 2)
    # Shine
    pygame.draw.circle(surf, C_BALL_SHINE,
        (int(x-r//3), int(y-r//3)), r//3)


def rounded_rect(surf, color, rect, radius=12, border=0, border_color=None):
    pygame.draw.rect(surf, color, rect, border_radius=radius)
    if border and border_color:
        pygame.draw.rect(surf, border_color, rect, border, border_radius=radius)


def draw_panel(surf, rect, title=None, font=None, title_color=C_GOLD):
    rounded_rect(surf, C_CARD, rect, radius=14,
                 border=1, border_color=(42,70,100))
    if title and font:
        t = font.render(title, True, title_color)
        surf.blit(t, (rect[0]+14, rect[1]+10))


def draw_text(surf, text, font, color, x, y, center=False, shadow=False):
    if shadow:
        s = font.render(text, True, (0,0,0))
        surf.blit(s, (x+2, y+2) if not center else
                  (x - s.get_width()//2 + 2, y - s.get_height()//2 + 2))
    t = font.render(text, True, color)
    if center:
        surf.blit(t, (x - t.get_width()//2, y - t.get_height()//2))
    else:
        surf.blit(t, (x, y))
    return t.get_width()


def draw_button(surf, rect, text, font, hover=False, active=False,
                color=C_GOLD, text_color=C_BG):
    c = color if not hover else tuple(min(255,v+40) for v in color)
    if active:
        c = C_GREEN
    rounded_rect(surf, c, rect, radius=10)
    # Inner highlight
    hi_rect = (rect[0]+2, rect[1]+2, rect[2]-4, rect[3]//2)
    hi_surf  = pygame.Surface((hi_rect[2], hi_rect[3]), pygame.SRCALPHA)
    hi_surf.fill((255,255,255,30))
    surf.blit(hi_surf, (hi_rect[0], hi_rect[1]))
    draw_text(surf, text, font, text_color,
              rect[0]+rect[2]//2, rect[1]+rect[3]//2, center=True)


def draw_progress_bar(surf, x, y, w, h, value, max_val, color=C_GOLD, bg=C_DARK):
    pygame.draw.rect(surf, bg,    (x, y, w, h), border_radius=h//2)
    fw = int(w * min(value/max(max_val,1), 1.0))
    if fw > 0:
        pygame.draw.rect(surf, color, (x, y, fw, h), border_radius=h//2)
    pygame.draw.rect(surf, C_GREY, (x, y, w, h), 1, border_radius=h//2)


def draw_ball_dots(surf, balls, x, y, font_small):
    """Draw over dots for ball-by-ball scorecard."""
    for i, b in enumerate(balls):
        bx = x + i * 30
        col = (220,50,50) if b["wicket"] else \
              ((255,215,0) if b["runs"]==6 else \
              ((76,200,80) if b["runs"]==4 else \
              ((150,150,150) if b["runs"]==0 else C_CREAM)))
        pygame.draw.circle(surf, col, (bx+12, y+12), 12)
        pygame.draw.circle(surf, (0,0,0), (bx+12, y+12), 12, 1)
        txt = "W" if b["wicket"] else str(b["runs"])
        t   = font_small.render(txt, True, C_BG)
        surf.blit(t, (bx+12-t.get_width()//2, y+12-t.get_height()//2))


def particle_burst(particles, x, y, color, count=20):
    """Add explosion particles to list."""
    for _ in range(count):
        angle = random.uniform(0, math.pi*2)
        speed = random.uniform(2, 8)
        particles.append({
            "x": x, "y": y,
            "vx": math.cos(angle)*speed,
            "vy": math.sin(angle)*speed,
            "life": 1.0,
            "color": color,
            "size": random.randint(3,8),
        })

def update_draw_particles(surf, particles):
    """Update and draw all particles. Removes dead ones."""
    alive = []
    for p in particles:
        p["x"]  += p["vx"]
        p["y"]  += p["vy"]
        p["vy"] += 0.3   # gravity
        p["life"] -= 0.04
        if p["life"] > 0:
            alpha = int(255 * p["life"])
            col   = p["color"]
            s2    = pygame.Surface((p["size"]*2, p["size"]*2), pygame.SRCALPHA)
            pygame.draw.circle(s2, (*col[:3], alpha),
                               (p["size"], p["size"]), p["size"])
            surf.blit(s2, (int(p["x"])-p["size"], int(p["y"])-p["size"]))
            alive.append(p)
    particles[:] = alive
