"""Game state machine - menus, fight flow, transitions for Cooking Combat."""

import random
import pygame
from config import *

from engine import Fighter, Player, Enemy, Projectile, check_combat, ParticleEffect
from graphics import (
    draw_stage, draw_hud, draw_title_screen, draw_fight_intro,
    draw_ko_screen, draw_game_over, draw_character, draw_particles,
    draw_pixel_text
)
from sound import SoundManager


def _fighter_to_dict(f):
    """Convert a Fighter object to a dict for graphics.draw_hud."""
    return {
        "hp": f.hp,
        "max_hp": f.max_hp,
        "name": f.name,
        "special_meter": f.special_meter,
        "combo_count": f.combo_count,
    }


def _draw_projectile_simple(surface, proj):
    """Draw a projectile as a small colored rectangle."""
    if not proj.active:
        return
    color = YELLOW
    if hasattr(proj, 'owner') and hasattr(proj.owner, 'enemy_data'):
        ed = proj.owner.enemy_data
        color = ed.get("color_secondary", YELLOW)
    rect = proj.get_rect()
    pygame.draw.rect(surface, color, rect)
    pygame.draw.rect(surface, WHITE, rect, 1)


class Game:
    """Main game controller handling all state transitions and the core loop."""

    STATE_TITLE = "title"
    STATE_INTRO = "intro"
    STATE_FIGHT = "fight"
    STATE_KO = "ko"
    STATE_VICTORY = "victory"
    STATE_GAME_OVER = "game_over"
    STATE_PAUSE = "pause"

    def __init__(self, screen):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.sound = SoundManager()
        self.particles = ParticleEffect()
        self.projectiles = []

        self.state = self.STATE_TITLE
        self.state_timer = 0
        self.fight_index = 0
        self.anim_frame = 0

        self.player = None
        self.enemy = None

        self.round_timer = ROUND_TIME
        self.round_timer_accumulator = 0.0

        self.transition_alpha = 0
        self.transitioning = False
        self.next_state = None

        self.combo_display_timer = 0
        self.combo_display_count = 0
        self.combo_display_side = "player"

        self.screen_shake = 0
        self.key_events = []
        self.keys = pygame.key.get_pressed()

        self.sound.play_music("menu")

    def new_game(self):
        """Start a new game from fight 0."""
        self.fight_index = 0
        self.setup_fight()

    def setup_fight(self):
        """Initialize fighters for the current fight."""
        enemy_data = ENEMY_ORDER[self.fight_index]

        # Player constructor: (x, y, name)
        self.player = Player(x=200, y=GROUND_Y - CHAR_HEIGHT, name=PLAYER_NAME)

        # Enemy constructor: (x, y, enemy_data, difficulty)
        e_height = BOSS_HEIGHT if enemy_data.get("is_boss") else CHAR_HEIGHT
        self.enemy = Enemy(
            x=700, y=GROUND_Y - e_height,
            enemy_data=enemy_data,
            difficulty=self.fight_index + 1
        )

        # Set opponent references for facing logic
        self.player.opponent = self.enemy
        self.enemy.opponent = self.player

        self.projectiles = []
        self.particles = ParticleEffect()
        self.round_timer = ROUND_TIME
        self.round_timer_accumulator = 0.0
        self.combo_display_timer = 0
        self.screen_shake = 0

    def handle_events(self):
        """Process pygame events. Returns False to quit."""
        key_events = []
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                key_events.append(event)
                if event.key == pygame.K_ESCAPE:
                    if self.state == self.STATE_FIGHT:
                        self.state = self.STATE_PAUSE
                        self.sound.play_sound("menu_select")
                    elif self.state == self.STATE_PAUSE:
                        self.state = self.STATE_FIGHT
                        self.sound.play_sound("menu_select")
                    elif self.state == self.STATE_TITLE:
                        return False
        self.key_events = key_events
        self.keys = pygame.key.get_pressed()
        return True

    def update(self):
        """Update current game state."""
        self.anim_frame += 1

        if self.transitioning:
            self.update_transition()
            if self.transition_alpha < 255:
                return

        if self.state == self.STATE_TITLE:
            self.update_title()
        elif self.state == self.STATE_INTRO:
            self.update_intro()
        elif self.state == self.STATE_FIGHT:
            self.update_fight()
        elif self.state == self.STATE_KO:
            self.update_ko()
        elif self.state == self.STATE_PAUSE:
            self.update_pause()

        if self.screen_shake > 0:
            self.screen_shake = max(0, self.screen_shake - 0.5)
        if self.combo_display_timer > 0:
            self.combo_display_timer -= 1

    def update_transition(self):
        """Update fade transition."""
        if not self.transitioning:
            return
        self.transition_alpha += TRANSITION_SPEED
        if self.transition_alpha >= 255:
            self.state = self.next_state
            self.state_timer = 0
            self.transitioning = False
            self.transition_alpha = 255

    def update_title(self):
        for event in self.key_events:
            if event.key == pygame.K_RETURN:
                self.sound.play_sound("menu_confirm")
                self.new_game()
                self.state = self.STATE_INTRO
                self.state_timer = INTRO_DURATION
                self.sound.stop_music()

    def update_intro(self):
        self.state_timer -= 1
        if self.state_timer <= 0:
            self.state = self.STATE_FIGHT
            self.sound.play_sound("round_start")
            enemy_data = ENEMY_ORDER[self.fight_index]
            if enemy_data.get("is_boss"):
                self.sound.play_music("boss")
            else:
                self.sound.play_music("fight")

    def update_fight(self):
        """Main fight logic each frame."""
        # Round timer
        self.round_timer_accumulator += 1.0 / FPS
        if self.round_timer_accumulator >= 1.0:
            self.round_timer_accumulator -= 1.0
            self.round_timer -= 1

        # 1. Input & AI decisions (before physics)
        self.player.handle_input(self.keys, self.key_events)
        self.enemy.ai_update(self.player)

        # 2. Physics & state updates
        self.player.update()
        self.enemy.update()

        # 3. Combat resolution (after positions and hitboxes are current)
        hit_events = check_combat(self.player, self.enemy, self.projectiles)
        for hit in hit_events:
            self._on_hit(hit)

        # 4. Projectile update (after combat so hits register on current frame)
        self.projectiles = [p for p in self.projectiles if p.active]
        for proj in self.projectiles:
            proj.update()

        # 5. Keep fighters on screen
        self._clamp_fighter(self.player)
        self._clamp_fighter(self.enemy)

        # 6. Prevent fighters from overlapping (push apart)
        self._push_apart(self.player, self.enemy)

        # 7. Boss rage aura particles
        if hasattr(self.enemy, '_rage_active') and self.enemy._rage_active:
            cx = self.enemy.x + self.enemy.width / 2
            cy = self.enemy.y + self.enemy.height / 2
            for _ in range(2):
                self.particles.add_single(
                    cx + random.uniform(-30, 30),
                    cy + random.uniform(-40, 40),
                    random.uniform(-0.5, 0.5),
                    random.uniform(-2.0, -0.5),
                    (220, 30 + random.randint(0, 40), 30),
                    life=random.randint(8, 16), size=random.randint(2, 5))

        # 8. Check KO
        if self.player.state == "ko" and self.state == self.STATE_FIGHT:
            self.state = self.STATE_KO
            self.state_timer = KO_DURATION
            self.sound.play_sound("ko_sound")
            self.sound.stop_music()
            self.screen_shake = 15
        elif self.enemy.state == "ko" and self.state == self.STATE_FIGHT:
            self.state = self.STATE_KO
            self.state_timer = KO_DURATION
            self.sound.play_sound("ko_sound")
            self.sound.stop_music()
            self.screen_shake = 15

        # 9. Time out
        if self.round_timer <= 0 and self.state == self.STATE_FIGHT:
            player_pct = self.player.hp / max(1, self.player.max_hp)
            enemy_pct = self.enemy.hp / max(1, self.enemy.max_hp)
            if player_pct >= enemy_pct:
                self.enemy.hp = 0
                self.enemy.state = "ko"
            else:
                self.player.hp = 0
                self.player.state = "ko"
            self.state = self.STATE_KO
            self.state_timer = KO_DURATION
            self.sound.play_sound("ko_sound")
            self.sound.stop_music()

        self.particles.update()

    def _push_apart(self, a, b):
        """Prevent fighters from overlapping by pushing them apart."""
        ar = a.get_rect()
        br = b.get_rect()
        if not ar.colliderect(br):
            return
        overlap_x = min(ar.right, br.right) - max(ar.left, br.left)
        if overlap_x <= 0:
            return
        push = overlap_x / 2 + 1
        if a.x < b.x:
            a.x -= push
            b.x += push
        else:
            a.x += push
            b.x -= push

    def update_ko(self):
        self.state_timer -= 1
        self.particles.update()
        if self.state_timer <= 0:
            if self.enemy.state == "ko":
                if self.fight_index >= len(ENEMY_ORDER) - 1:
                    self.state = self.STATE_VICTORY
                    self.sound.play_sound("victory_fanfare")
                else:
                    self.fight_index += 1
                    self.setup_fight()
                    self.state = self.STATE_INTRO
                    self.state_timer = INTRO_DURATION
            else:
                self.state = self.STATE_GAME_OVER
                self.sound.play_sound("defeat_sound")

    def update_pause(self):
        for event in self.key_events:
            if event.key == pygame.K_RETURN:
                self.state = self.STATE_FIGHT
                self.sound.play_sound("menu_select")
            elif event.key == pygame.K_q:
                self.state = self.STATE_TITLE
                self.sound.play_music("menu")

    def _on_hit(self, hit_event):
        """Handle a hit event with particles and sound."""
        defender = hit_event["defender"]
        hit_type = hit_event["type"]

        # Screen shake
        shake_map = {"special": 10, "heavy": 6, "projectile": 4}
        self.screen_shake = shake_map.get(hit_type, 3)

        # Particles at hit location
        hit_x = defender.x + defender.width // 2
        hit_y = defender.y + defender.height // 3
        if hit_type == "special":
            self.particles.add_burst(hit_x, hit_y, YELLOW, 20)
            self.particles.add_burst(hit_x, hit_y, WHITE, 10)
        elif hit_type == "heavy":
            self.particles.add_burst(hit_x, hit_y, ORANGE, 12)
        else:
            self.particles.add_burst(hit_x, hit_y, WHITE, 6)

        # Sound effects
        if defender.is_blocking:
            self.sound.play_sound("block_sound")
        elif hit_type == "special":
            self.sound.play_sound("special_hit")
            enemy_data = ENEMY_ORDER[self.fight_index]
            sn = enemy_data.get("special_name", "").lower()
            if "torch" in sn or "fire" in sn:
                self.sound.play_sound("fire_blast")
            elif "freeze" in sn or "brain" in sn:
                self.sound.play_sound("freeze_sound")
            elif "ground" in sn or "rage" in sn:
                self.sound.play_sound("ground_pound")
        elif hit_type == "heavy":
            self.sound.play_sound("heavy_hit")
        else:
            self.sound.play_sound("light_hit")

        # Combo display
        attacker = hit_event["attacker"]
        if attacker == self.player and self.player.combo_count > 1:
            self.combo_display_count = self.player.combo_count
            self.combo_display_side = "player"
            self.combo_display_timer = 60
        elif attacker == self.enemy and self.enemy.combo_count > 1:
            self.combo_display_count = self.enemy.combo_count
            self.combo_display_side = "enemy"
            self.combo_display_timer = 60

    def _clamp_fighter(self, fighter):
        if fighter.x < 10:
            fighter.x = 10
            fighter.vx = 0
        if fighter.x + fighter.width > SCREEN_WIDTH - 10:
            fighter.x = SCREEN_WIDTH - 10 - fighter.width
            fighter.vx = 0

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def draw(self):
        """Render the current frame."""
        shake_x = 0
        shake_y = 0
        if self.screen_shake > 0:
            shake_x = random.randint(int(-self.screen_shake), int(self.screen_shake))
            shake_y = random.randint(int(-self.screen_shake), int(self.screen_shake))

        frame = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))

        if self.state == self.STATE_TITLE:
            draw_title_screen(frame, self.anim_frame)

        elif self.state == self.STATE_INTRO:
            enemy_data = ENEMY_ORDER[self.fight_index]
            draw_fight_intro(
                frame, PLAYER_NAME, enemy_data,
                self.fight_index + 1, INTRO_DURATION - self.state_timer
            )

        elif self.state in (self.STATE_FIGHT, self.STATE_KO, self.STATE_PAUSE):
            enemy_data = ENEMY_ORDER[self.fight_index]
            stage_theme = STAGE_THEMES[enemy_data["stage"]]

            # Background (draw_stage takes 3 args: surface, theme, anim_frame)
            draw_stage(frame, stage_theme, self.anim_frame)

            # Projectiles
            for proj in self.projectiles:
                _draw_projectile_simple(frame, proj)

            # Draw fighters using graphics.draw_character(surface, name, x, y, w, h, facing, state, anim_frame, special_data)
            draw_character(frame, "Chef Blade",
                           int(self.player.x), int(self.player.y),
                           self.player.width, self.player.height,
                           self.player.facing, self.player.state,
                           self.player.anim_frame)

            enemy_special = None
            if hasattr(self.enemy, '_rage_active') and self.enemy._rage_active:
                enemy_special = {"rage": True}

            draw_character(frame, enemy_data["name"],
                           int(self.enemy.x), int(self.enemy.y),
                           self.enemy.width, self.enemy.height,
                           self.enemy.facing, self.enemy.state,
                           self.enemy.anim_frame, enemy_special)

            # Particles
            draw_particles(frame, self.particles.get_particles())

            # HUD - draw_hud expects dicts with hp/max_hp/name/special_meter/combo_count
            draw_hud(frame,
                     _fighter_to_dict(self.player),
                     _fighter_to_dict(self.enemy),
                     self.round_timer,
                     self.fight_index + 1)

            # Combo display
            if self.combo_display_timer > 0 and self.combo_display_count > 1:
                combo_x = 200 if self.combo_display_side == "player" else 700
                scale = min(2.0, 1.0 + self.combo_display_count * 0.15)
                combo_size = int(28 * scale)
                draw_pixel_text(frame, f"{self.combo_display_count} HIT COMBO!",
                                combo_x, 150, combo_size, YELLOW)

            # KO overlay
            if self.state == self.STATE_KO:
                is_player_win = self.enemy.state == "ko"
                winner = PLAYER_NAME if is_player_win else self.enemy.name
                draw_ko_screen(frame, winner, is_player_win,
                               KO_DURATION - self.state_timer)

            # Pause overlay
            if self.state == self.STATE_PAUSE:
                overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 150))
                frame.blit(overlay, (0, 0))
                draw_pixel_text(frame, "PAUSED", SCREEN_WIDTH // 2 - 60, 200, 48, WHITE)
                draw_pixel_text(frame, "ENTER - Resume", SCREEN_WIDTH // 2 - 80, 280, 24, LIGHT_GRAY)
                draw_pixel_text(frame, "Q - Quit to Title", SCREEN_WIDTH // 2 - 90, 320, 24, LIGHT_GRAY)

        elif self.state == self.STATE_VICTORY:
            draw_game_over(frame, True, self.anim_frame)
            for event in self.key_events:
                if event.key == pygame.K_RETURN:
                    self.state = self.STATE_TITLE
                    self.sound.play_music("menu")

        elif self.state == self.STATE_GAME_OVER:
            draw_game_over(frame, False, self.anim_frame)
            for event in self.key_events:
                if event.key == pygame.K_RETURN:
                    self.state = self.STATE_TITLE
                    self.sound.play_music("menu")

        self.screen.blit(frame, (shake_x, shake_y))

        if self.transitioning:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            overlay.fill(BLACK)
            overlay.set_alpha(self.transition_alpha)
            self.screen.blit(overlay, (0, 0))

        pygame.display.flip()

    def run(self):
        """Main game loop."""
        running = True
        while running:
            running = self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
