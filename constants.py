"""
constants.py  —  All magic numbers, colours, fonts in one place
"""
import os

# ── Window ────────────────────────────────────────────────────────────────
WIN_W, WIN_H = 1200, 750
FPS          = 60
TITLE        = "🏏  AI vs Human Cricket"

# ── Colours ───────────────────────────────────────────────────────────────
C_BG          = (10,  20,  35)
C_PITCH_OUTER = (34,  85,  34)
C_PITCH_INNER = (22,  60,  22)
C_PITCH_STRIP = (180,140,  80)
C_STUMPS      = (240,220, 160)
C_WHITE       = (255,255, 255)
C_BLACK       = (  0,  0,   0)
C_GOLD        = (244,196,  48)
C_GOLD_DARK   = (180,130,   8)
C_BLUE        = ( 33,150, 243)
C_BLUE_DARK   = ( 13, 80, 160)
C_GREEN       = ( 76,175,  80)
C_RED         = (220, 50,  50)
C_ORANGE      = (255,152,   0)
C_PINK        = (233, 30,  99)
C_GREY        = (100,120, 140)
C_DARK        = ( 20, 35,  55)
C_CARD        = ( 26, 45,  64)
C_CARD2       = ( 15, 28,  45)
C_CREAM       = (240,225, 195)
C_SHADOW      = (  0,  0,   0, 120)
C_OVERLAY     = (  0,  0,   0, 180)

# ── Ball ──────────────────────────────────────────────────────────────────
BALL_R        = 11
C_BALL        = (200,  40,  40)
C_BALL_SEAM   = (240, 200, 200)
C_BALL_SHINE  = (255, 120, 120)

# ── Player colours ────────────────────────────────────────────────────────
C_HUMAN       = C_GOLD
C_AI          = C_BLUE

# ── Delivery & Shot emoji maps ────────────────────────────────────────────
DELIVERY_EMOJIS = {
    "Yorker"     : "🎯",
    "Bouncer"    : "⬆️",
    "Off Spin"   : "🔄",
    "Full Toss"  : "🎾",
    "In-Swinger" : "↩️",
    "Out-Swinger": "↪️",
}
SHOT_EMOJIS = {
    "Drive"  : "🏏",
    "Pull"   : "💥",
    "Cut"    : "✂️",
    "Sweep"  : "🌊",
    "Defend" : "🛡️",
    "Loft"   : "🚀",
}

# ── Run colours (for dot display) ────────────────────────────────────────
def run_color(runs, wicket):
    if wicket: return C_RED
    if runs == 6: return (255, 215, 0)
    if runs == 4: return C_GREEN
    if runs == 0: return C_GREY
    return C_CREAM
