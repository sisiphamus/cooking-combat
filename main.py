"""Cooking Combat - A Street Fighter-style dessert fighting game!

Controls:
    Arrow Keys / WASD  - Move & Jump
    J                  - Light Attack
    K                  - Heavy Attack
    L                  - Special Attack (costs meter)
    Down / S           - Block (hold) / Crouch
    Enter              - Confirm / Start
    Escape             - Pause / Back
"""

import sys
import os

# Ensure we can import from the game directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame
from config import SCREEN_WIDTH, SCREEN_HEIGHT, TITLE, FPS

# Pre-init mixer before pygame.init for better audio
pygame.mixer.pre_init(22050, -16, 1, 512)
pygame.init()
pygame.display.set_caption(TITLE)

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

# Show loading screen
font = pygame.font.Font(None, 36)
screen.fill((0, 0, 0))
text = font.render("LOADING COOKING COMBAT...", True, (255, 255, 255))
screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, SCREEN_HEIGHT // 2))
pygame.display.flip()

# Now import game (which triggers sound generation etc.)
from game import Game

def main():
    game = Game(screen)
    game.run()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
