"""
engine.py - Cooking Combat: Fighter logic, physics, AI, and combat mechanics.

Rewritten for fluid, responsive combat. Key design changes from v1:
- Instant movement (no friction drift) - walk stops when keys release
- Shorter attack durations with attack lunge for satisfying forward motion
- Single-hit enforcement via per-attack hit tracking (not hitbox nulling)
- Input buffering: attack pressed during recovery queues for next frame
- Proper crouch height restoration on any state exit
- AI uses per-enemy speed, closes distance before attacking
"""

import math
import random
import pygame
from config import *


def _clamp(value, lo, hi):
    return max(lo, min(hi, value))


def _sign(value):
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


# ---------------------------------------------------------------------------
# Fighter base class
# ---------------------------------------------------------------------------

class Fighter:

    def __init__(self, x, y, width, height, hp, speed, name):
        # Position
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0

        # Dimensions
        self.width = width
        self.height = height
        self._base_height = height

        # Stats
        self.hp = hp
        self.max_hp = hp
        self.speed = float(speed)
        self.special_meter = 0.0

        # Orientation
        self.facing = 1

        # State machine
        self.state = "idle"
        self.state_timer = 0
        self._state_elapsed = 0

        # Attack tracking
        self.attack_cooldown = 0
        self.attack_hitbox = None
        self._hit_landed_this_attack = False  # prevents multi-hit per swing

        # Input buffer: stores next action to execute when current state ends
        self._input_buffer = None  # "light", "heavy", "special", or None
        self._buffer_timer = 0

        # Flags
        self.is_blocking = False
        self.on_ground = True
        self._is_crouching = False

        # Identity
        self.name = name

        # Combo
        self.combo_count = 0
        self._combo_decay_timer = 0  # frames since last hit; combo resets after threshold

        # Animation
        self.anim_frame = 0

        # Opponent ref
        self.opponent = None

    def get_rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    # ------------------------------------------------------------------
    # Main update
    # ------------------------------------------------------------------

    def update(self):
        if self.state == "ko":
            self.anim_frame += 1
            # Still apply gravity/velocity so KO body slides
            self.vy += GRAVITY
            self.x += self.vx
            self.y += self.vy
            ground_y = GROUND_Y - self._base_height
            if self.y >= ground_y:
                self.y = float(ground_y)
                self.vy = 0.0
                self.vx *= 0.8
            return

        # Gravity
        if not self.on_ground:
            self.vy += GRAVITY

        # Velocity integration
        self.x += self.vx
        self.y += self.vy

        # Ground collision
        ground_y = GROUND_Y - self.height
        if self.y >= ground_y:
            self.y = float(ground_y)
            self.vy = 0.0
            was_airborne = not self.on_ground
            self.on_ground = True
            if was_airborne and self.state == "jump":
                self._set_state("idle")

        # Knockback decay (only for knockback, not intentional movement)
        if self.state == "hit_stun":
            self.vx *= KNOCKBACK_DECAY
            if abs(self.vx) < 0.3:
                self.vx = 0.0

        # Attack lunge: slight forward motion during active frames
        if self.state in ("light_attack", "heavy_attack", "special_attack"):
            active_start, active_end = self._get_active_window()
            if active_start <= self._state_elapsed < active_end:
                lunge = {"light_attack": LIGHT_LUNGE,
                         "heavy_attack": HEAVY_LUNGE,
                         "special_attack": SPECIAL_LUNGE}.get(self.state, 0)
                self.x += lunge * self.facing

        # Screen clamp
        self.x = _clamp(self.x, 0.0, float(SCREEN_WIDTH - self.width))

        # State timer
        if self.state_timer > 0:
            self.state_timer -= 1
            self._state_elapsed += 1

        self._handle_state_exit()

        # Attack hitbox
        self._update_attack_hitbox()

        # Attack cooldown
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1

        # Input buffer timeout
        if self._buffer_timer > 0:
            self._buffer_timer -= 1
            if self._buffer_timer <= 0:
                self._input_buffer = None

        # Combo decay
        if self.combo_count > 0:
            self._combo_decay_timer += 1
            if self._combo_decay_timer > 45:  # ~0.75 seconds without landing a hit
                self.combo_count = 0

        # Face opponent (only in neutral states)
        if self.opponent and self.state in ("idle", "walk", "crouch"):
            if self.opponent.x + self.opponent.width / 2 > self.x + self.width / 2:
                self.facing = 1
            else:
                self.facing = -1

        self.anim_frame += 1

    def _set_state(self, new_state, timer=0):
        prev = self.state
        self.state = new_state
        self.state_timer = timer
        self._state_elapsed = 0

        # Restore height when leaving crouch
        if prev == "crouch" and new_state != "crouch":
            self._restore_height()

        # Clear hitbox when leaving attack states
        if new_state not in ("light_attack", "heavy_attack", "special_attack"):
            self.attack_hitbox = None
            self._hit_landed_this_attack = False

    def _handle_state_exit(self):
        """Auto-transition when timed states expire."""
        if self.state_timer > 0:
            return

        if self.state in ("light_attack", "heavy_attack", "special_attack"):
            self.attack_hitbox = None
            self._hit_landed_this_attack = False
            # Check input buffer for chained attacks
            if self._input_buffer and self.attack_cooldown <= 0:
                buffered = self._input_buffer
                self._input_buffer = None
                self._buffer_timer = 0
                if buffered == "light":
                    self._do_light_attack()
                elif buffered == "heavy":
                    self._do_heavy_attack()
                elif buffered == "special":
                    self._do_special_attack()
                return
            self._set_state("idle")

        elif self.state == "hit_stun":
            self._set_state("idle")
            self.is_blocking = False
            # Opponent's combo doesn't auto-reset here anymore
            # (combo decays on its own timer)

        elif self.state == "block":
            if not self.is_blocking:
                self._set_state("idle")

    def _get_active_window(self):
        windows = {
            "light_attack": LIGHT_ACTIVE,
            "heavy_attack": HEAVY_ACTIVE,
            "special_attack": SPECIAL_ACTIVE,
        }
        return windows.get(self.state, (999, 999))

    def _update_attack_hitbox(self):
        if self.state not in ("light_attack", "heavy_attack", "special_attack"):
            return
        if self._hit_landed_this_attack:
            self.attack_hitbox = None
            return

        active_start, active_end = self._get_active_window()
        if active_start <= self._state_elapsed < active_end:
            self.attack_hitbox = self._build_attack_hitbox()
        else:
            self.attack_hitbox = None

    def _build_attack_hitbox(self):
        if self.state == "light_attack":
            w, h = LIGHT_REACH, 24
        elif self.state == "heavy_attack":
            w, h = HEAVY_REACH, 32
        elif self.state == "special_attack":
            w, h = SPECIAL_REACH, 44
        else:
            w, h = LIGHT_REACH, 24

        y_offset = self.height // 3

        if self.facing == 1:
            hb_x = int(self.x + self.width - 8)  # overlap slightly with body
        else:
            hb_x = int(self.x + 8 - w)

        hb_y = int(self.y + y_offset)
        return pygame.Rect(hb_x, hb_y, w, h)

    # ------------------------------------------------------------------
    # Height management for crouch
    # ------------------------------------------------------------------

    def _apply_crouch_height(self):
        if not self._is_crouching:
            self._is_crouching = True
            self.height = self._base_height * 2 // 3
            self.y = GROUND_Y - self.height

    def _restore_height(self):
        if self._is_crouching:
            self._is_crouching = False
            self.height = self._base_height
            self.y = GROUND_Y - self.height

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def move(self, direction):
        if direction == 0:
            return
        if self.state in ("hit_stun", "ko"):
            return
        if self.state in ("light_attack", "heavy_attack", "special_attack"):
            return  # can't move during attacks

        self._restore_height()
        self.vx = direction * self.speed
        if self.on_ground and self.state not in ("crouch", "block"):
            self.state = "walk"

    def stop_moving(self):
        """Called when no directional keys are held."""
        if self.state == "walk":
            self.vx = 0.0
            self._set_state("idle")

    def jump(self):
        if not self.on_ground:
            return
        if self.state in ("hit_stun", "ko", "light_attack",
                          "heavy_attack", "special_attack"):
            return
        self._restore_height()
        self.vy = JUMP_FORCE
        self.on_ground = False
        self._set_state("jump")

    def crouch(self):
        if self.state in ("hit_stun", "ko", "jump",
                          "light_attack", "heavy_attack", "special_attack"):
            return
        self._apply_crouch_height()
        self.state = "crouch"
        self.vx = 0.0

    def block(self):
        if self.state in ("ko", "jump", "hit_stun",
                          "light_attack", "heavy_attack", "special_attack"):
            return
        self.is_blocking = True
        self._apply_crouch_height()
        self._set_state("block", timer=3)
        self.vx = 0.0

    def light_attack(self):
        """Request a light attack. Buffers if currently in recovery."""
        if self.state in ("hit_stun", "ko"):
            return
        if self.state in ("light_attack", "heavy_attack", "special_attack"):
            # Buffer the input for chaining
            self._input_buffer = "light"
            self._buffer_timer = 12
            return
        if self.attack_cooldown > 0:
            self._input_buffer = "light"
            self._buffer_timer = 12
            return
        self._do_light_attack()

    def _do_light_attack(self):
        self._restore_height()
        self._hit_landed_this_attack = False
        self._set_state("light_attack", timer=LIGHT_ATTACK_DURATION)
        self.attack_cooldown = ATTACK_COOLDOWN_LIGHT
        # Don't kill momentum entirely - slight decel
        self.vx *= 0.3

    def heavy_attack(self):
        if self.state in ("hit_stun", "ko"):
            return
        if self.state in ("light_attack", "heavy_attack", "special_attack"):
            self._input_buffer = "heavy"
            self._buffer_timer = 12
            return
        if self.attack_cooldown > 0:
            self._input_buffer = "heavy"
            self._buffer_timer = 12
            return
        self._do_heavy_attack()

    def _do_heavy_attack(self):
        self._restore_height()
        self._hit_landed_this_attack = False
        self._set_state("heavy_attack", timer=HEAVY_ATTACK_DURATION)
        self.attack_cooldown = ATTACK_COOLDOWN_HEAVY
        self.vx *= 0.2

    def special_attack(self):
        if self.special_meter < SPECIAL_COST:
            return
        if self.state in ("hit_stun", "ko"):
            return
        if self.state in ("light_attack", "heavy_attack", "special_attack"):
            self._input_buffer = "special"
            self._buffer_timer = 12
            return
        if self.attack_cooldown > 0:
            self._input_buffer = "special"
            self._buffer_timer = 12
            return
        self._do_special_attack()

    def _do_special_attack(self):
        if self.special_meter < SPECIAL_COST:
            return
        self._restore_height()
        self._hit_landed_this_attack = False
        self.special_meter -= SPECIAL_COST
        self._set_state("special_attack", timer=SPECIAL_ATTACK_DURATION)
        self.attack_cooldown = ATTACK_COOLDOWN_SPECIAL
        self.vx *= 0.1

    def take_hit(self, damage, knockback_x, stun_frames):
        if self.state == "ko":
            return

        blocking = self.is_blocking and self.state == "block"

        if blocking:
            actual_damage = max(1, int(damage * BLOCK_REDUCTION))
            knockback_x *= 0.3
            stun_frames = max(3, stun_frames // 3)
        else:
            actual_damage = damage

        self.hp = max(0, self.hp - actual_damage)

        # Meter for being hit
        self.special_meter = _clamp(
            self.special_meter + METER_GAIN_HURT, 0.0, float(SPECIAL_METER_MAX))

        # Knockback
        self.vx = knockback_x
        if not blocking:
            self.vy = -2.5  # slight upward pop

        if self.hp <= 0:
            self._restore_height()
            self._set_state("ko")
            self.attack_hitbox = None
            self.vx = knockback_x * 0.6
            self.vy = -5.0  # dramatic launch
            self.is_blocking = False
            return

        self._restore_height()
        self.is_blocking = False
        self._input_buffer = None
        self._set_state("hit_stun", timer=stun_frames)

    def get_attack_damage(self):
        return {"light_attack": LIGHT_DAMAGE,
                "heavy_attack": HEAVY_DAMAGE,
                "special_attack": SPECIAL_DAMAGE}.get(self.state, 0)

    def get_attack_knockback(self):
        base = {"light_attack": 4.5,
                "heavy_attack": 8.0,
                "special_attack": 12.0}.get(self.state, 0.0)
        return base * self.facing

    def get_attack_stun(self):
        return {"light_attack": HIT_STUN_LIGHT,
                "heavy_attack": HIT_STUN_HEAVY,
                "special_attack": HIT_STUN_SPECIAL}.get(self.state, 0)

    def reset(self, x):
        self.x = float(x)
        self.y = float(GROUND_Y - self._base_height)
        self.height = self._base_height
        self._is_crouching = False
        self.vx = 0.0
        self.vy = 0.0
        self.hp = self.max_hp
        self.special_meter = 0.0
        self.facing = 1
        self._set_state("idle")
        self.attack_cooldown = 0
        self.attack_hitbox = None
        self._hit_landed_this_attack = False
        self._input_buffer = None
        self._buffer_timer = 0
        self.is_blocking = False
        self.on_ground = True
        self.combo_count = 0
        self._combo_decay_timer = 0
        self.anim_frame = 0


# ---------------------------------------------------------------------------
# Player
# ---------------------------------------------------------------------------

class Player(Fighter):

    def __init__(self, x, y, name="Player"):
        super().__init__(
            x=x, y=y,
            width=CHAR_WIDTH, height=CHAR_HEIGHT,
            hp=PLAYER_HP, speed=PLAYER_SPEED, name=name
        )
        self.facing = 1

    def handle_input(self, keys, key_events):
        if self.state == "ko":
            return

        moving_left = keys[pygame.K_a] or keys[pygame.K_LEFT]
        moving_right = keys[pygame.K_d] or keys[pygame.K_RIGHT]
        holding_down = keys[pygame.K_s] or keys[pygame.K_DOWN]

        # --- Attacks from key-down events (discrete presses) ---
        for event in key_events:
            if event.type != pygame.KEYDOWN:
                continue
            if event.key in (pygame.K_w, pygame.K_UP):
                self.jump()
            elif event.key == pygame.K_j:
                self.light_attack()
            elif event.key == pygame.K_k:
                self.heavy_attack()
            elif event.key == pygame.K_l:
                self.special_attack()

        # --- Block / crouch (continuous hold) ---
        if holding_down and self.on_ground:
            if self.state in ("light_attack", "heavy_attack",
                              "special_attack", "hit_stun"):
                pass  # can't block/crouch during these
            elif not moving_left and not moving_right:
                self.block()
                return
            else:
                self.crouch()
                return

        # Release crouch/block when down is released
        if not holding_down:
            if self.state == "crouch":
                self._restore_height()
                self._set_state("idle")
            if self.state == "block":
                self.is_blocking = False
                self._restore_height()
                self._set_state("idle")

        # --- Movement (continuous hold) ---
        if self.state in ("light_attack", "heavy_attack",
                          "special_attack", "hit_stun", "block"):
            return  # locked out of movement

        if moving_left and not moving_right:
            self.move(-1)
        elif moving_right and not moving_left:
            self.move(1)
        else:
            self.stop_moving()


# ---------------------------------------------------------------------------
# Enemy
# ---------------------------------------------------------------------------

class Enemy(Fighter):

    _DIST_CLOSE = 70
    _DIST_MEDIUM = 160
    _DIST_FAR = 280

    def __init__(self, x, y, enemy_data, difficulty=1.0):
        is_boss = enemy_data.get("is_boss", False)
        hp_val = enemy_data.get("hp", 100)
        spd = float(enemy_data.get("speed", PLAYER_SPEED))
        w = BOSS_WIDTH if is_boss else CHAR_WIDTH
        h = BOSS_HEIGHT if is_boss else CHAR_HEIGHT

        super().__init__(
            x=x, y=y, width=w, height=h,
            hp=hp_val, speed=spd,
            name=enemy_data.get("name", "Enemy")
        )

        self.enemy_data = enemy_data
        self.difficulty = _clamp(difficulty, 0.5, 5.0)
        self.aggression = float(enemy_data.get("aggression", 0.5))
        self.is_boss = is_boss

        # AI timing: react faster at higher difficulty
        self._base_ai_timer = max(4, int(18 / self.difficulty))
        self.ai_timer = self._base_ai_timer

        # Rage mode (boss)
        self._rage_active = False
        self._rage_speed_mult = 1.0
        self._rage_aggression = self.aggression

        # Boss charge
        self._charge_timer = 0
        self._charging = False

        self._dodge_cooldown = 0
        self.facing = -1

    def ai_update(self, player):
        if self.state == "ko":
            return

        self._update_rage_mode()

        if self.ai_timer > 0:
            self.ai_timer -= 1
        if self._dodge_cooldown > 0:
            self._dodge_cooldown -= 1
        if self._charge_timer > 0:
            self._charge_timer -= 1

        # Don't override locked states
        if self.state in ("hit_stun", "light_attack", "heavy_attack",
                          "special_attack"):
            return

        # Release block after a short time
        if self.state == "block":
            self.is_blocking = False
            self._restore_height()
            self._set_state("idle")

        dx = player.x - self.x
        dist = abs(dx)
        direction = _sign(dx)

        if self.is_boss:
            self._boss_ai(player, dx, dist, direction)
            return

        if self.ai_timer <= 0:
            self._make_decision(player, dx, dist, direction)
            self.ai_timer = max(3, self._base_ai_timer + random.randint(-3, 3))

    def _update_rage_mode(self):
        if not self.is_boss:
            return
        below = self.hp < int(self.max_hp * 0.30)
        if below and not self._rage_active:
            self._rage_active = True
            self._rage_speed_mult = 1.8
            self._rage_aggression = min(1.0, self.aggression * 1.5)
            self._base_ai_timer = max(2, self._base_ai_timer // 2)
        elif not below:
            self._rage_active = False
            self._rage_speed_mult = 1.0
            self._rage_aggression = self.aggression

    def _eff_aggr(self):
        return self._rage_aggression if self._rage_active else self.aggression

    def _ai_walk(self, direction, speed_mult=1.0):
        if direction == 0:
            return
        if self.state in ("hit_stun", "ko", "light_attack",
                          "heavy_attack", "special_attack"):
            return
        self._restore_height()
        self.vx = direction * self.speed * speed_mult
        if self.on_ground:
            self.state = "walk"

    def _ai_stop(self):
        self.vx = 0.0
        if self.state == "walk":
            self._set_state("idle")

    def _try_attack(self, player, dist):
        """Pick an attack type based on distance and aggression. Return True if attacked."""
        aggr = self._eff_aggr()
        reach = SPECIAL_REACH + self.width  # max possible reach

        # Only attack if close enough to actually hit
        if dist > reach + 10:
            return False

        r = random.random()
        if self.special_meter >= SPECIAL_COST and r < 0.25 * aggr:
            self.special_attack()
            return True
        elif dist < HEAVY_REACH + self.width and r < 0.6:
            if random.random() < 0.5:
                self.heavy_attack()
            else:
                self.light_attack()
            return True
        elif dist < LIGHT_REACH + self.width:
            self.light_attack()
            return True
        return False

    def _make_decision(self, player, dx, dist, direction):
        aggr = self._eff_aggr()
        sm = self._rage_speed_mult

        if dist > self._DIST_FAR:
            # Approach
            if random.random() < 0.9:
                self._ai_walk(direction, sm)
            elif self._dodge_cooldown == 0:
                self.jump()
                self._ai_walk(direction, sm)
                self._dodge_cooldown = 30

        elif dist > self._DIST_MEDIUM:
            r = random.random()
            if r < 0.6:
                # Close distance
                self._ai_walk(direction, sm)
            elif r < 0.6 + aggr * 0.25:
                self._try_attack(player, dist)
            elif r < 0.85 and self._dodge_cooldown == 0:
                self.jump()
                self._ai_walk(direction, sm * 0.8)
                self._dodge_cooldown = 30
            else:
                self._ai_stop()

        elif dist > self._DIST_CLOSE:
            # Good fighting distance
            r = random.random()
            if r < aggr * 0.6:
                if not self._try_attack(player, dist):
                    self._ai_walk(direction, sm * 0.7)
            elif r < aggr * 0.7:
                self._ai_walk(direction, sm * 0.5)
            elif r < 0.82:
                # Block briefly if player is attacking
                if player.state in ("light_attack", "heavy_attack", "special_attack"):
                    self.block()
                else:
                    self._ai_walk(direction, sm * 0.5)
            elif r < 0.92:
                self._ai_walk(-direction, sm * 0.6)  # retreat
            else:
                self._ai_stop()

        else:
            # Very close - prioritize attacking
            r = random.random()
            if r < aggr * 0.7:
                self._try_attack(player, dist)
            elif r < aggr * 0.8:
                self._ai_walk(-direction, sm * 0.8)  # push back
            elif r < 0.88:
                if player.state in ("light_attack", "heavy_attack", "special_attack"):
                    self.block()
                else:
                    self.light_attack()
            else:
                if self._dodge_cooldown == 0:
                    self.jump()
                    self._ai_walk(-direction, sm)
                    self._dodge_cooldown = 35

    # ------------------------------------------------------------------
    # Boss AI
    # ------------------------------------------------------------------

    def _boss_ai(self, player, dx, dist, direction):
        sm = self._rage_speed_mult

        # Charge behavior
        if self._charging and self._charge_timer > 0:
            self._ai_walk(direction, sm * 2.2)
            if dist < self._DIST_CLOSE + 20:
                self.heavy_attack()
                self._charging = False
            return
        else:
            self._charging = False

        if self.ai_timer > 0:
            return

        aggr = self._eff_aggr()
        self.ai_timer = max(3, self._base_ai_timer + random.randint(-2, 2))

        r = random.random()

        if dist > self._DIST_FAR:
            if r < 0.35:
                self._start_charge(direction)
            else:
                self._ai_walk(direction, sm)

        elif dist > self._DIST_MEDIUM:
            if r < 0.25 * aggr and self.on_ground:
                # Ground pound: jump high
                self.jump()
                self.vy = JUMP_FORCE * 1.2
            elif r < 0.50:
                self._start_charge(direction)
            elif r < 0.75:
                if self.special_meter >= SPECIAL_COST and random.random() < 0.5:
                    self.special_attack()
                else:
                    self._ai_walk(direction, sm)
            else:
                self._ai_walk(direction, sm)

        else:
            if self._rage_active:
                if r < 0.55:
                    self.heavy_attack()
                elif r < 0.75 and self.special_meter >= SPECIAL_COST:
                    self.special_attack()
                elif r < 0.90:
                    self.light_attack()
                else:
                    self._ai_walk(-direction, sm)
            else:
                if r < 0.35:
                    self.heavy_attack()
                elif r < 0.50 and self.special_meter >= SPECIAL_COST:
                    self.special_attack()
                elif r < 0.65:
                    self.light_attack()
                elif r < 0.80:
                    self.block()
                else:
                    self._ai_walk(-direction, sm)

    def _start_charge(self, direction):
        self._charging = True
        self._charge_timer = 25

    def update(self):
        super().update()

    def reset(self, x):
        super().reset(x)
        self._rage_active = False
        self._rage_speed_mult = 1.0
        self._rage_aggression = self.aggression
        self._charge_timer = 0
        self._charging = False
        self._dodge_cooldown = 0
        self.ai_timer = self._base_ai_timer
        self.facing = -1


# ---------------------------------------------------------------------------
# Projectile
# ---------------------------------------------------------------------------

class Projectile:

    def __init__(self, x, y, vx, vy, damage, owner,
                 lifetime=90, width=16, height=10):
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.damage = damage
        self.owner = owner
        self.lifetime = lifetime
        self.width = width
        self.height = height
        self.active = True

    def update(self):
        if not self.active:
            return
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.05
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.active = False
        if (self.x < -self.width or self.x > SCREEN_WIDTH + self.width
                or self.y > SCREEN_HEIGHT + self.height):
            self.active = False

    def get_rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    def deactivate(self):
        self.active = False


# ---------------------------------------------------------------------------
# Combat resolution
# ---------------------------------------------------------------------------

def check_combat(fighter_a, fighter_b, projectiles):
    events = []

    for attacker, defender in ((fighter_a, fighter_b), (fighter_b, fighter_a)):
        if attacker.attack_hitbox is None:
            continue
        if attacker.state == "ko" or defender.state == "ko":
            continue
        if attacker._hit_landed_this_attack:
            continue

        defender_rect = defender.get_rect()
        if not attacker.attack_hitbox.colliderect(defender_rect):
            continue

        state_to_type = {
            "light_attack": "light",
            "heavy_attack": "heavy",
            "special_attack": "special",
        }
        hit_type = state_to_type.get(attacker.state)
        if hit_type is None:
            continue

        damage = attacker.get_attack_damage()
        knockback = attacker.get_attack_knockback()
        stun = attacker.get_attack_stun()

        defender.take_hit(damage, knockback, stun)

        attacker.special_meter = _clamp(
            attacker.special_meter + METER_GAIN_HIT, 0.0, float(SPECIAL_METER_MAX))
        attacker.combo_count += 1
        attacker._combo_decay_timer = 0  # reset combo decay on hit

        # Mark this attack as having landed (no double-hit)
        attacker._hit_landed_this_attack = True

        events.append({
            "attacker": attacker,
            "defender": defender,
            "damage": damage,
            "type": hit_type,
        })

    # Projectiles
    for proj in projectiles:
        if not proj.active:
            continue
        proj_rect = proj.get_rect()
        for fighter in (fighter_a, fighter_b):
            if fighter is proj.owner:
                continue
            if fighter.state == "ko":
                continue
            if not proj_rect.colliderect(fighter.get_rect()):
                continue
            proj_kb = 5.0 * proj.owner.facing
            fighter.take_hit(proj.damage, proj_kb, HIT_STUN_LIGHT)
            proj.owner.special_meter = _clamp(
                proj.owner.special_meter + METER_GAIN_HIT, 0.0, float(SPECIAL_METER_MAX))
            proj.owner.combo_count += 1
            proj.owner._combo_decay_timer = 0
            proj.deactivate()
            events.append({
                "attacker": proj.owner,
                "defender": fighter,
                "damage": proj.damage,
                "type": "projectile",
            })
            break

    return events


# ---------------------------------------------------------------------------
# Particle system
# ---------------------------------------------------------------------------

class ParticleEffect:

    def __init__(self):
        self.particles = []

    def add_burst(self, x, y, color, count=12,
                  speed_range=(1.5, 5.0), life_range=(10, 25),
                  size_range=(2, 5)):
        for _ in range(count):
            angle = random.uniform(0, 6.2832)
            speed = random.uniform(*speed_range)
            vx = speed * math.cos(angle)
            vy = speed * math.sin(angle)
            r = _clamp(color[0] + random.randint(-20, 20), 0, 255)
            g = _clamp(color[1] + random.randint(-20, 20), 0, 255)
            b = _clamp(color[2] + random.randint(-20, 20), 0, 255)
            life = random.randint(*life_range)
            self.particles.append({
                "x": float(x), "y": float(y),
                "vx": vx, "vy": vy,
                "color": (r, g, b),
                "life": life, "max_life": life,
                "size": random.randint(*size_range),
            })

    def add_single(self, x, y, vx, vy, color, life=20, size=3):
        self.particles.append({
            "x": float(x), "y": float(y),
            "vx": vx, "vy": vy,
            "color": color,
            "life": life, "max_life": life,
            "size": size,
        })

    def update(self):
        alive = []
        for p in self.particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["vy"] += 0.25
            p["vx"] *= 0.93
            p["life"] -= 1
            if p["life"] > 0:
                alive.append(p)
        self.particles = alive

    def get_particles(self):
        return self.particles

    def clear(self):
        self.particles.clear()
