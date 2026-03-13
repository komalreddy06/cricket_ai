"""
main.py  —  AI vs Human Cricket  (Pygame edition)
==================================================
Run:  python main.py
Req:  pip install pygame
"""
import pygame, sys
from constants  import *
from game.state   import GameState
from game.screens import (SplashScreen, TossScreen, FieldScreen,
                           MinimaxDemoScreen, MatchScreen, ResultScreen)


class GameManager:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(TITLE)
        self.surf  = pygame.display.set_mode((WIN_W, WIN_H))
        self.clock = pygame.time.Clock()
        self.state = GameState()

        # Load fonts (system fonts — no file needed)
        self.fonts = {
            "huge" : pygame.font.SysFont("segoeuiemoji,segoeui,arial", 52, bold=True),
            "big"  : pygame.font.SysFont("segoeuiemoji,segoeui,arial", 34, bold=True),
            "med"  : pygame.font.SysFont("segoeuiemoji,segoeui,arial", 22, bold=True),
            "small": pygame.font.SysFont("segoeuiemoji,segoeui,arial", 16),
            "tiny" : pygame.font.SysFont("segoeuiemoji,segoeui,arial", 12),
        }

        self.screens = {
            "splash"      : SplashScreen(self),
            "toss"        : TossScreen(self),
            "field"       : FieldScreen(self),
            "minimax_demo": MinimaxDemoScreen(self),
            "match"       : MatchScreen(self),
            "result"      : ResultScreen(self),
        }
        self._current = "splash"
        self.screens["splash"].on_enter()

    def goto(self, name: str):
        self._current = name
        self.screens[name].state = self.state
        self.screens[name].on_enter()

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit(); sys.exit()
                self.screens[self._current].handle_event(event)

            self.screens[self._current].update(dt)
            self.screens[self._current].draw(self.surf)
            pygame.display.flip()


if __name__ == "__main__":
    GameManager().run()
