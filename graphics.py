"""graphics.py - All rendering logic for Cooking Combat."""

import math
import pygame
from config import *

# ---------------------------------------------------------------------------
# HELPER UTILITIES
# ---------------------------------------------------------------------------

def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _lerp_color(c1, c2, t):
    t = _clamp(t, 0.0, 1.0)
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def draw_pixel_text(surface, text, x, y, size, color):
    """Render text using a pixel-art-friendly monospace font."""
    font = pygame.font.Font(None, max(8, size))
    rendered = font.render(str(text), False, color)
    surface.blit(rendered, (x, y))


def draw_health_bar(surface, x, y, width, height, current, maximum, color, bg_color):
    """Outlined health bar, fill proportional to current/maximum."""
    # Background
    pygame.draw.rect(surface, bg_color, (x, y, width, height))
    # Fill
    if maximum > 0:
        fill_w = int(width * _clamp(current / maximum, 0.0, 1.0))
        if fill_w > 0:
            pygame.draw.rect(surface, color, (x, y, fill_w, height))
    # Outline
    pygame.draw.rect(surface, WHITE, (x, y, width, height), 2)


def _draw_limb(surface, color, cx, cy, w, h):
    """Draw a simple rounded limb rectangle centred at (cx, cy)."""
    pygame.draw.rect(surface, color, (int(cx - w // 2), int(cy - h // 2), w, h))


# ---------------------------------------------------------------------------
# CHEF BLADE (Player)
# White chef hat, blue jacket, black pants, spatula
# ---------------------------------------------------------------------------

def draw_chef_blade(surface, x, y, width, height, facing, state, anim_frame, special_data=None):
    cx = x + width // 2

    # -- colours --
    HAT_COL    = (240, 240, 240)
    JACKET_COL = (50, 100, 190)
    SKIN_COL   = (220, 180, 140)
    PANTS_COL  = (30, 30, 30)
    SPATULA_COL= (180, 180, 180)
    HANDLE_COL = (100, 60, 30)

    # -- proportions (relative to height=64) --
    sc = height / 64.0
    hat_h  = int(14 * sc)
    head_h = int(12 * sc)
    body_h = int(18 * sc)
    leg_h  = int(16 * sc)
    head_w = int(16 * sc)
    body_w = int(20 * sc)

    # -- vertical offsets --
    bob = int(math.sin(anim_frame * 0.15) * 1.5 * sc) if state == "idle" else 0

    if state == "crouch":
        body_base = y + hat_h + head_h + int(body_h * 0.6)
        leg_draw_h = int(leg_h * 0.5)
        vert_shift = int(body_h * 0.4)
    elif state == "jump":
        body_base = y + hat_h + head_h + body_h
        leg_draw_h = int(leg_h * 0.8)
        vert_shift = -int(4 * sc)
    elif state == "ko":
        # Draw collapsed
        pygame.draw.rect(surface, JACKET_COL, (x + 4, y + height - int(14*sc), width - 8, int(12*sc)))
        pygame.draw.ellipse(surface, SKIN_COL, (cx - int(10*sc), y + height - int(20*sc), int(20*sc), int(14*sc)))
        pygame.draw.rect(surface, HAT_COL, (cx - int(8*sc), y + height - int(28*sc), int(16*sc), int(10*sc)))
        return
    else:
        body_base = y + hat_h + head_h + body_h
        leg_draw_h = leg_h
        vert_shift = 0

    top = y + bob + vert_shift

    # -- hat --
    hat_brim_y = top + int(2 * sc)
    pygame.draw.rect(surface, HAT_COL, (cx - int(10*sc), hat_brim_y, int(20*sc), int(4*sc)))
    pygame.draw.rect(surface, HAT_COL, (cx - int(7*sc), top, int(14*sc), hat_h))

    # -- head --
    head_y = hat_brim_y + int(3*sc)
    pygame.draw.rect(surface, SKIN_COL, (cx - head_w//2, head_y, head_w, head_h))
    # eyes
    eye_y = head_y + int(4*sc)
    if state == "hit_stun":
        # X eyes
        for ex in [cx - int(4*sc)*facing, cx + int(2*sc)*facing]:
            pygame.draw.line(surface, BLACK, (int(ex-2*sc), int(eye_y-2*sc)), (int(ex+2*sc), int(eye_y+2*sc)), 2)
            pygame.draw.line(surface, BLACK, (int(ex+2*sc), int(eye_y-2*sc)), (int(ex-2*sc), int(eye_y+2*sc)), 2)
    else:
        pygame.draw.rect(surface, BLACK, (int(cx + facing*int(2*sc) - int(2*sc)), eye_y, int(3*sc), int(3*sc)))

    # -- body / jacket --
    body_y = head_y + head_h
    pygame.draw.rect(surface, JACKET_COL, (cx - body_w//2, body_y, body_w, body_h))
    # collar
    pygame.draw.line(surface, WHITE, (cx, body_y), (cx, body_y + int(6*sc)), 2)

    # -- legs --
    leg_w = int(7 * sc)
    lleg_x = cx - leg_w - int(1*sc)
    rleg_x = cx + int(1*sc)
    leg_y  = body_y + body_h

    if state == "walk":
        swing = int(math.sin(anim_frame * 0.3) * 5 * sc)
        l_off, r_off = swing, -swing
    else:
        l_off = r_off = 0

    pygame.draw.rect(surface, PANTS_COL, (lleg_x, leg_y + l_off, leg_w, leg_draw_h))
    pygame.draw.rect(surface, PANTS_COL, (rleg_x, leg_y + r_off, leg_w, leg_draw_h))

    # -- spatula weapon --
    spat_base_x = cx + facing * int(10*sc)
    spat_base_y = body_y + int(6*sc)

    if state == "light_attack":
        angle_off = int(math.sin(anim_frame * 0.8) * 8 * sc)
        spat_tip_x = cx + facing * int(26*sc)
        spat_tip_y = spat_base_y - angle_off
    elif state == "heavy_attack":
        # overhead swing
        spat_tip_x = cx + facing * int(10*sc)
        spat_tip_y = spat_base_y - int(24*sc)
    elif state == "special_attack":
        # rapid slash - draw blur trails
        for trail in range(3):
            tx = cx + facing * (int(14*sc) + trail * int(5*sc))
            ty = spat_base_y - trail * int(6*sc)
            alpha_col = (180 - trail*50, 180 - trail*50, 200 - trail*50)
            pygame.draw.line(surface, alpha_col,
                             (cx + facing*int(8*sc), spat_base_y),
                             (tx, ty), max(1, int(3*sc) - trail))
        spat_tip_x = cx + facing * int(28*sc)
        spat_tip_y = spat_base_y - int(10*sc)
    elif state == "block":
        spat_tip_x = cx + facing * int(14*sc)
        spat_tip_y = body_y + int(2*sc)
        # crossed arms
        pygame.draw.line(surface, JACKET_COL,
                         (cx - int(8*sc), body_y + int(8*sc)),
                         (cx + int(8*sc), body_y + int(16*sc)), int(4*sc))
        pygame.draw.line(surface, JACKET_COL,
                         (cx + int(8*sc), body_y + int(8*sc)),
                         (cx - int(8*sc), body_y + int(16*sc)), int(4*sc))
    else:
        spat_tip_x = cx + facing * int(22*sc)
        spat_tip_y = spat_base_y + int(4*sc)

    # handle
    pygame.draw.line(surface, HANDLE_COL,
                     (int(spat_base_x), int(spat_base_y)),
                     (int(spat_tip_x - facing*int(6*sc)), int(spat_tip_y + int(3*sc))),
                     max(1, int(3*sc)))
    # blade
    pygame.draw.rect(surface, SPATULA_COL,
                     (int(spat_tip_x - int(3*sc)), int(spat_tip_y - int(2*sc)),
                      int(8*sc), int(5*sc)))


# ---------------------------------------------------------------------------
# PANCAKE PETE
# Flat golden-brown disc, tiny eyes, syrup dripping
# ---------------------------------------------------------------------------

def draw_pancake_pete(surface, x, y, width, height, facing, state, anim_frame, special_data=None):
    cx = x + width // 2
    sc = height / 64.0

    PANCAKE_COL = (200, 155, 60)
    PANCAKE_DARK= (170, 120, 40)
    SYRUP_COL   = (140, 80, 20)
    EYE_COL     = (40, 20, 10)

    # Disc dimensions change with state
    if state == "crouch":
        disc_rx = int(width * 0.52)
        disc_ry = int(6 * sc)
        disc_cy = y + height - int(10*sc)
    elif state == "jump":
        disc_rx = int(width * 0.36)
        disc_ry = int(14 * sc)
        disc_cy = y + height // 2 - int(8*sc)
    elif state == "ko":
        disc_rx = int(width * 0.55)
        disc_ry = int(5 * sc)
        disc_cy = y + height - int(8*sc)
        pygame.draw.ellipse(surface, PANCAKE_COL,
                            (cx - disc_rx, disc_cy - disc_ry, disc_rx*2, disc_ry*2))
        return
    else:
        wobble = int(math.sin(anim_frame * 0.18) * 2 * sc)
        disc_rx = int(width * 0.44)
        disc_ry = int(10 * sc) + wobble
        disc_cy = y + height // 2 + int(8*sc) - wobble

    # Shadow
    pygame.draw.ellipse(surface, PANCAKE_DARK,
                        (cx - disc_rx - 2, disc_cy - disc_ry + 4, (disc_rx+2)*2, disc_ry*2))
    # Main disc
    pygame.draw.ellipse(surface, PANCAKE_COL,
                        (cx - disc_rx, disc_cy - disc_ry, disc_rx*2, disc_ry*2))
    # Darker ring (edge browning)
    pygame.draw.ellipse(surface, PANCAKE_DARK,
                        (cx - disc_rx, disc_cy - disc_ry, disc_rx*2, disc_ry*2), 3)

    # Syrup drips (static + animated)
    drip_xs = [cx - int(6*sc), cx + int(4*sc), cx - int(14*sc)]
    for di, drip_x in enumerate(drip_xs):
        drip_len = int((6 + (anim_frame * 2 + di * 7) % 8) * sc)
        drip_y   = disc_cy + disc_ry - 3
        pygame.draw.line(surface, SYRUP_COL,
                         (drip_x, drip_y), (drip_x - di, drip_y + drip_len), max(1, int(2*sc)))
        pygame.draw.circle(surface, SYRUP_COL,
                           (drip_x - di, drip_y + drip_len), max(1, int(2*sc)))

    # Eyes
    eye_y = disc_cy - int(2*sc)
    pygame.draw.circle(surface, EYE_COL, (int(cx - int(5*sc)*facing), eye_y), max(1, int(2*sc)))
    pygame.draw.circle(surface, EYE_COL, (int(cx + int(3*sc)*facing), eye_y), max(1, int(2*sc)))

    # Tiny arms
    arm_y = disc_cy
    arm_len = int(10*sc)
    pygame.draw.line(surface, PANCAKE_DARK,
                     (cx - disc_rx + 4, arm_y),
                     (cx - disc_rx - arm_len, arm_y + int(4*sc)), max(1, int(2*sc)))
    pygame.draw.line(surface, PANCAKE_DARK,
                     (cx + disc_rx - 4, arm_y),
                     (cx + disc_rx + arm_len, arm_y + int(4*sc)), max(1, int(2*sc)))

    # Tiny legs
    leg_y = disc_cy + disc_ry - 2
    for lx in [cx - int(7*sc), cx + int(3*sc)]:
        swing = int(math.sin(anim_frame * 0.3 + (0 if lx < cx else math.pi)) * 4*sc) if state == "walk" else 0
        pygame.draw.line(surface, PANCAKE_DARK,
                         (int(lx), leg_y),
                         (int(lx + swing), int(leg_y + 10*sc)), max(1, int(3*sc)))

    # Attack – spatula-like swing
    if state in ("light_attack", "heavy_attack"):
        sw = int(math.sin(anim_frame * 0.6) * 12*sc)
        pygame.draw.line(surface, (200, 200, 200),
                         (cx + facing*disc_rx, arm_y),
                         (int(cx + facing*(disc_rx + 16*sc)), int(arm_y - sw)), 3)

    # Special – syrup splash droplets
    if state == "special_attack":
        for i in range(6):
            angle = (anim_frame * 12 + i * 60) % 360
            rad   = math.radians(angle)
            sx    = cx + int(math.cos(rad) * (disc_rx + 10*sc + (anim_frame % 8)*2))
            sy    = disc_cy + int(math.sin(rad) * (disc_ry + 6*sc + (anim_frame % 8)*2))
            pygame.draw.circle(surface, SYRUP_COL, (int(sx), int(sy)), max(1, int(3*sc)))


# ---------------------------------------------------------------------------
# WAFFLE WARRIOR
# Square body with grid pattern, golden brown
# ---------------------------------------------------------------------------

def draw_waffle_warrior(surface, x, y, width, height, facing, state, anim_frame, special_data=None):
    cx = x + width // 2
    sc = height / 64.0

    WAFFLE_COL  = (200, 160, 80)
    WAFFLE_DARK = (160, 120, 50)
    GRID_COL    = (140, 100, 40)
    BUTTER_COL  = (255, 230, 80)
    EYE_COL     = (40, 25, 10)

    sway = int(math.sin(anim_frame * 0.1) * 2*sc) if state == "idle" else 0

    # Body dimensions
    if state == "crouch":
        bw = int(28*sc); bh = int(18*sc)
        by = y + height - bh - int(8*sc)
    elif state == "ko":
        pygame.draw.rect(surface, WAFFLE_COL,
                         (x + 4, y + height - int(18*sc), width - 8, int(16*sc)))
        # grid on KO
        for gx in range(x+6, x+width-6, int(5*sc)):
            pygame.draw.line(surface, GRID_COL, (gx, y+height-int(18*sc)), (gx, y+height-int(4*sc)), 1)
        return
    else:
        bw = int(24*sc); bh = int(28*sc)
        by = y + int(12*sc) + sway

    bx = cx - bw // 2

    # Main body block
    pygame.draw.rect(surface, WAFFLE_COL, (bx, by, bw, bh))
    # Darker border
    pygame.draw.rect(surface, WAFFLE_DARK, (bx, by, bw, bh), 2)

    # Waffle grid pattern
    grid_spacing = max(4, int(5*sc))
    for gx in range(bx + grid_spacing, bx + bw, grid_spacing):
        pygame.draw.line(surface, GRID_COL, (gx, by+2), (gx, by+bh-2), 1)
    for gy in range(by + grid_spacing, by + bh, grid_spacing):
        pygame.draw.line(surface, GRID_COL, (bx+2, gy), (bx+bw-2, gy), 1)

    # Eyes
    eye_y = by + int(8*sc)
    pygame.draw.rect(surface, EYE_COL,
                     (int(cx + facing*int(4*sc) - int(2*sc)), eye_y, int(4*sc), int(4*sc)))
    pygame.draw.rect(surface, EYE_COL,
                     (int(cx - facing*int(4*sc) - int(2*sc)), eye_y, int(4*sc), int(4*sc)))

    # Thick arms
    arm_y = by + int(10*sc)
    arm_h = int(8*sc)
    if state == "heavy_attack":
        # arm raised
        pygame.draw.rect(surface, WAFFLE_COL,
                         (int(cx + facing*bw//2), by - int(6*sc), int(10*sc), arm_h))
    elif state == "special_attack":
        # butter pats orbit
        for i in range(4):
            angle = math.radians((anim_frame * 6 + i * 90) % 360)
            ox = cx + int(math.cos(angle) * (bw//2 + int(10*sc)))
            oy = by + bh//2 + int(math.sin(angle) * int(10*sc))
            pygame.draw.ellipse(surface, BUTTER_COL, (int(ox-4), int(oy-3), 8, 6))
        # golden glow outline
        for d in range(1, 4):
            pygame.draw.rect(surface, (min(255,WAFFLE_COL[0]+30), min(255,WAFFLE_COL[1]+30), 0),
                             (bx-d, by-d, bw+d*2, bh+d*2), 1)
    else:
        pygame.draw.rect(surface, WAFFLE_COL,
                         (bx - int(10*sc), arm_y, int(10*sc), arm_h))
        pygame.draw.rect(surface, WAFFLE_COL,
                         (bx + bw, arm_y, int(10*sc), arm_h))

    # Legs
    leg_w = int(8*sc); leg_h = int(12*sc)
    leg_y = by + bh
    if state == "walk":
        l_off = int(math.sin(anim_frame * 0.25) * 3*sc)
        r_off = -l_off
    elif state == "crouch":
        l_off = r_off = 0; leg_h = int(6*sc)
    else:
        l_off = r_off = 0

    pygame.draw.rect(surface, WAFFLE_DARK,
                     (cx - leg_w - int(1*sc), leg_y + l_off, leg_w, leg_h))
    pygame.draw.rect(surface, WAFFLE_DARK,
                     (cx + int(1*sc), leg_y + r_off, leg_w, leg_h))


# ---------------------------------------------------------------------------
# BANANA BREAD BRAD
# Loaf-shaped body, golden brown, banana slice decorations
# ---------------------------------------------------------------------------

def draw_banana_bread_brad(surface, x, y, width, height, facing, state, anim_frame, special_data=None):
    cx = x + width // 2
    sc = height / 64.0

    LOAF_COL   = (190, 140, 70)
    LOAF_DARK  = (150, 100, 40)
    BANANA_COL = (230, 210, 60)
    BANANA_OUT = (180, 160, 30)
    EYE_COL    = (40, 25, 10)

    # Bread-rise idle animation
    rise = int(math.sin(anim_frame * 0.12) * 2*sc) if state == "idle" else 0

    if state == "crouch":
        bw = int(28*sc); bh = int(16*sc)
        by = y + height - bh - int(6*sc)
        rounded_top = False
    elif state == "ko":
        pygame.draw.rect(surface, LOAF_COL,
                         (x+2, y+height-int(14*sc), width-4, int(12*sc)))
        pygame.draw.ellipse(surface, LOAF_COL,
                            (x+2, y+height-int(20*sc), width-4, int(10*sc)))
        return
    else:
        bw = int(22*sc); bh = int(30*sc)
        by = y + int(10*sc) - rise
        rounded_top = True

    bx = cx - bw // 2

    # Main loaf rectangle
    pygame.draw.rect(surface, LOAF_COL, (bx, by + int(6*sc) if rounded_top else by, bw, bh))
    # Rounded top dome
    if rounded_top:
        pygame.draw.ellipse(surface, LOAF_COL,
                            (bx, by, bw, int(12*sc)))
    pygame.draw.rect(surface, LOAF_DARK,
                     (bx, by + (int(6*sc) if rounded_top else 0), bw, bh), 2)

    # Banana chunk decorations (oval slices)
    slice_positions = [
        (cx - int(5*sc), by + int(10*sc)),
        (cx + int(4*sc), by + int(18*sc)),
        (cx - int(3*sc), by + int(24*sc)),
    ]
    for sx, sy in slice_positions:
        pygame.draw.ellipse(surface, BANANA_COL,
                            (int(sx - int(5*sc)), int(sy - int(3*sc)), int(10*sc), int(6*sc)))
        pygame.draw.ellipse(surface, BANANA_OUT,
                            (int(sx - int(5*sc)), int(sy - int(3*sc)), int(10*sc), int(6*sc)), 1)

    # Eyes
    eye_y = by + int(5*sc)
    pygame.draw.circle(surface, EYE_COL,
                       (int(cx + facing*int(4*sc)), eye_y), max(1, int(2*sc)))
    pygame.draw.circle(surface, EYE_COL,
                       (int(cx - facing*int(4*sc)), eye_y), max(1, int(2*sc)))

    # Arms
    arm_y = by + int(12*sc) + int(6*sc)
    if state == "heavy_attack":
        pygame.draw.rect(surface, LOAF_COL,
                         (int(cx + facing*bw//2), int(by + int(8*sc)), int(12*sc), int(6*sc)))
    elif state == "special_attack":
        # Throw animation – arm extended
        pygame.draw.rect(surface, LOAF_COL,
                         (int(cx + facing*bw//2), arm_y - int(2*sc), int(16*sc), int(6*sc)))
        # Flying banana slice
        bsx = int(cx + facing*(bw//2 + int(20*sc) + (anim_frame % 12)*facing*2))
        bsy = arm_y
        pygame.draw.ellipse(surface, BANANA_COL,
                            (bsx - int(5*sc), bsy - int(3*sc), int(10*sc), int(6*sc)))
        pygame.draw.ellipse(surface, BANANA_OUT,
                            (bsx - int(5*sc), bsy - int(3*sc), int(10*sc), int(6*sc)), 1)
    else:
        pygame.draw.rect(surface, LOAF_DARK,
                         (bx - int(10*sc), arm_y, int(10*sc), int(6*sc)))
        pygame.draw.rect(surface, LOAF_DARK,
                         (bx + bw, arm_y, int(10*sc), int(6*sc)))

    # Legs
    leg_y = by + (int(6*sc) if rounded_top else 0) + bh
    leg_w = int(7*sc); leg_h = int(12*sc)
    if state == "walk":
        sw = int(math.sin(anim_frame * 0.3) * 5*sc)
    else:
        sw = 0
    pygame.draw.rect(surface, LOAF_DARK,
                     (cx - leg_w - int(1*sc), leg_y + sw, leg_w, leg_h))
    pygame.draw.rect(surface, LOAF_DARK,
                     (cx + int(1*sc), leg_y - sw, leg_w, leg_h))


# ---------------------------------------------------------------------------
# PUDDING PAUL
# Dome/cup shape, caramel coloured, constant jiggle
# ---------------------------------------------------------------------------

def draw_pudding_paul(surface, x, y, width, height, facing, state, anim_frame, special_data=None):
    cx = x + width // 2
    sc = height / 64.0

    PUDDING_COL = (200, 150, 60)
    RAMEKIN_COL = (220, 200, 170)
    CREAM_COL   = (255, 245, 230)
    EYE_COL     = (60, 35, 10)

    jiggle = int(math.sin(anim_frame * 0.22) * 3 * sc)

    if state == "ko":
        pygame.draw.ellipse(surface, PUDDING_COL,
                            (x + 2, y + height - int(16*sc), width - 4, int(14*sc)))
        pygame.draw.ellipse(surface, CREAM_COL,
                            (cx - int(8*sc), y + height - int(18*sc), int(16*sc), int(8*sc)))
        return

    if state == "crouch":
        dome_rx = int(14*sc) + jiggle
        dome_ry = int(8*sc)
        ramekin_h = int(10*sc)
        ramekin_w = int(26*sc)
        dome_cy = y + height - ramekin_h - dome_ry
    elif state == "jump":
        dome_rx = int(12*sc) - jiggle
        dome_ry = int(18*sc)
        ramekin_h = int(8*sc)
        ramekin_w = int(22*sc)
        dome_cy = y + int(14*sc)
    elif state == "special_attack":
        pulse = int((anim_frame % 20) * sc)
        dome_rx = int(14*sc) + pulse
        dome_ry = int(12*sc) + pulse // 2
        ramekin_h = int(12*sc)
        ramekin_w = int(26*sc)
        dome_cy = y + height - ramekin_h - dome_ry + int(4*sc)
        for ring in range(1, 4):
            r_rad = dome_rx + ring * int(8*sc)
            ring_alpha = max(0, 180 - ring * 50)
            ring_col = (
                int(PUDDING_COL[0] * ring_alpha / 180),
                int(PUDDING_COL[1] * ring_alpha / 180),
                int(PUDDING_COL[2] * ring_alpha / 180),
            )
            if r_rad > 0:
                pygame.draw.ellipse(surface, ring_col,
                                    (cx - r_rad, dome_cy - dome_ry // 2, r_rad * 2, dome_ry), 2)
    else:
        dome_rx = int(14*sc) + jiggle
        dome_ry = int(14*sc) - abs(jiggle) // 2
        ramekin_h = int(12*sc)
        ramekin_w = int(26*sc)
        dome_cy = y + height - ramekin_h - dome_ry + int(4*sc)

    ramekin_y = dome_cy + dome_ry - int(4*sc)

    pygame.draw.rect(surface, RAMEKIN_COL,
                     (cx - ramekin_w//2, ramekin_y, ramekin_w, ramekin_h))
    pygame.draw.rect(surface, (180, 160, 130),
                     (cx - ramekin_w//2, ramekin_y, ramekin_w, ramekin_h), 2)

    pygame.draw.ellipse(surface, PUDDING_COL,
                        (cx - dome_rx, dome_cy - dome_ry, dome_rx*2, dome_ry*2))
    cream_ry = max(2, dome_ry // 3)
    pygame.draw.ellipse(surface, CREAM_COL,
                        (cx - dome_rx//2, dome_cy - dome_ry, dome_rx, cream_ry*2))
    pygame.draw.ellipse(surface, (160, 110, 30),
                        (cx - dome_rx, dome_cy - dome_ry, dome_rx*2, dome_ry*2), 2)

    eye_y = dome_cy - dome_ry // 3
    pygame.draw.circle(surface, EYE_COL, (int(cx - int(4*sc)*facing), eye_y), max(1, int(2*sc)))
    pygame.draw.circle(surface, EYE_COL, (int(cx + int(3*sc)*facing), eye_y), max(1, int(2*sc)))

    arm_y = dome_cy
    if state in ("light_attack", "heavy_attack"):
        pygame.draw.ellipse(surface, PUDDING_COL,
                            (int(cx + facing*dome_rx - int(2*sc)), arm_y - int(4*sc),
                             int(14*sc), int(8*sc)))
    else:
        pygame.draw.ellipse(surface, PUDDING_COL,
                            (cx - dome_rx - int(8*sc), arm_y - int(3*sc), int(10*sc), int(7*sc)))
        pygame.draw.ellipse(surface, PUDDING_COL,
                            (cx + dome_rx - int(2*sc), arm_y - int(3*sc), int(10*sc), int(7*sc)))

    leg_h = int(8*sc)
    for lx in [cx - int(5*sc), cx + int(1*sc)]:
        sw = int(math.sin(anim_frame * 0.3) * 4*sc) if state == "walk" else 0
        pygame.draw.rect(surface, RAMEKIN_COL,
                         (int(lx), ramekin_y + ramekin_h, int(5*sc), leg_h + sw))


# ---------------------------------------------------------------------------
# CREME BRULEE
# Elegant ramekin (trapezoid), caramelized shimmer top, torch weapon
# ---------------------------------------------------------------------------

def draw_creme_brulee(surface, x, y, width, height, facing, state, anim_frame, special_data=None):
    cx = x + width // 2
    sc = height / 64.0

    PORCELAIN    = (240, 235, 220)
    CARAMEL_TOP  = (200, 150, 40)
    GOLD_SHIMMER = (255, 220, 60)
    TORCH_BODY   = (150, 120, 80)
    FLAME_COLS   = [(255, 60, 0), (255, 140, 0), (255, 220, 60)]
    EYE_COL      = (50, 30, 10)

    if state == "ko":
        pygame.draw.polygon(surface, PORCELAIN, [
            (x + 4, y + height - int(10*sc)),
            (x + width - 4, y + height - int(10*sc)),
            (x + width, y + height - int(4*sc)),
            (x, y + height - int(4*sc)),
        ])
        return

    if state == "crouch":
        body_top_y  = y + height - int(20*sc)
        body_bot_y  = y + height - int(6*sc)
        top_half_w  = int(20*sc)
        bot_half_w  = int(24*sc)
    else:
        body_top_y  = y + int(20*sc)
        body_bot_y  = y + height - int(10*sc)
        top_half_w  = int(18*sc)
        bot_half_w  = int(22*sc)

    trap = [
        (cx - top_half_w, body_top_y),
        (cx + top_half_w, body_top_y),
        (cx + bot_half_w, body_bot_y),
        (cx - bot_half_w, body_bot_y),
    ]
    pygame.draw.polygon(surface, PORCELAIN, trap)
    pygame.draw.polygon(surface, (200, 190, 170), trap, 2)

    caramel_h = int(6*sc)
    pygame.draw.rect(surface, CARAMEL_TOP,
                     (cx - top_half_w, body_top_y - caramel_h, top_half_w*2, caramel_h))
    shimmer_on  = (anim_frame // 4) % 2 == 0
    shimmer_col = GOLD_SHIMMER if shimmer_on else CARAMEL_TOP
    for px in range(cx - top_half_w + 2, cx + top_half_w - 2, int(4*sc)):
        pygame.draw.rect(surface, shimmer_col,
                         (int(px), body_top_y - caramel_h + 1, max(2, int(3*sc)), int(3*sc)))

    eye_y = body_top_y + int(8*sc)
    pygame.draw.circle(surface, EYE_COL, (int(cx + facing*int(5*sc)), eye_y), max(1, int(2*sc)))
    pygame.draw.circle(surface, EYE_COL, (int(cx - facing*int(3*sc)), eye_y), max(1, int(2*sc)))

    torch_base_x = cx + facing * int(12*sc)
    torch_base_y = body_top_y + int(4*sc)
    torch_tip_x  = torch_base_x + facing * int(10*sc)
    torch_tip_y  = torch_base_y - int(12*sc)

    if state == "special_attack":
        blast_len = int(30*sc + (anim_frame % 12) * sc)
        for i, fc in enumerate(FLAME_COLS):
            spread = (2 - i) * int(6*sc)
            tip_x  = torch_tip_x + facing * blast_len
            pygame.draw.polygon(surface, fc, [
                (int(torch_tip_x), int(torch_tip_y - spread)),
                (int(torch_tip_x), int(torch_tip_y + spread)),
                (int(tip_x),       int(torch_tip_y)),
            ])
    else:
        pygame.draw.line(surface, TORCH_BODY,
                         (int(torch_base_x), int(torch_base_y)),
                         (int(torch_tip_x),  int(torch_tip_y)), max(2, int(3*sc)))
        flicker = int(math.sin(anim_frame * 0.5) * 3*sc)
        for i, fc in enumerate(FLAME_COLS):
            pygame.draw.circle(surface, fc,
                               (int(torch_tip_x), int(torch_tip_y - i*int(2*sc) - flicker)),
                               max(2, int((4 - i) * sc)))

    pygame.draw.line(surface, PORCELAIN,
                     (cx - top_half_w + 2, arm_y := body_top_y + int(12*sc)),
                     (int(torch_base_x), int(torch_base_y)), max(1, int(3*sc)))


# ---------------------------------------------------------------------------
# SUNDAE SUPREME
# Stacked ice cream scoops in a bowl, cherry on top, wafer stick
# ---------------------------------------------------------------------------

def draw_sundae_supreme(surface, x, y, width, height, facing, state, anim_frame, special_data=None):
    cx = x + width // 2
    sc = height / 64.0

    BOWL_COL   = (230, 220, 200)
    SCOOP1_COL = (240, 160, 180)
    SCOOP2_COL = (140, 90, 50)
    SCOOP3_COL = (245, 240, 230)
    CHERRY_COL = (200, 30, 50)
    STEM_COL   = (60, 120, 40)
    WAFER_COL  = (230, 185, 100)
    ICE_COL    = (140, 200, 240)
    EYE_COL    = (30, 20, 10)

    if state == "ko":
        pygame.draw.ellipse(surface, SCOOP1_COL,
                            (x + 2, y + height - int(18*sc), width - 4, int(16*sc)))
        pygame.draw.ellipse(surface, SCOOP2_COL,
                            (x + 8, y + height - int(14*sc), width - 16, int(10*sc)))
        return

    bob = int(math.sin(anim_frame * 0.14) * 2*sc) if state == "idle" else 0

    bowl_w = int(28*sc)
    bowl_h = int(14*sc)
    bowl_y = y + height - bowl_h - int(2*sc)
    pygame.draw.ellipse(surface, BOWL_COL,
                        (cx - bowl_w//2, bowl_y, bowl_w, bowl_h))
    pygame.draw.ellipse(surface, (200, 190, 170),
                        (cx - bowl_w//2, bowl_y, bowl_w, bowl_h), 2)

    scoop_data = [
        (SCOOP1_COL, int(12*sc), bowl_y - int(10*sc) + bob),
        (SCOOP2_COL, int(11*sc), bowl_y - int(22*sc) + bob),
        (SCOOP3_COL, int(9*sc),  bowl_y - int(32*sc) + bob),
    ]
    for s_col, s_r, s_cy in scoop_data:
        pygame.draw.circle(surface, s_col, (cx, int(s_cy)), s_r)
        darker = tuple(_clamp(c - 20, 0, 255) for c in s_col)
        pygame.draw.circle(surface, darker, (cx, int(s_cy)), s_r, 2)

    cherry_y = scoop_data[-1][2] - scoop_data[-1][1] - int(4*sc)
    pygame.draw.circle(surface, CHERRY_COL, (cx, int(cherry_y)), max(2, int(4*sc)))
    pygame.draw.line(surface, STEM_COL,
                     (cx, int(cherry_y - int(4*sc))),
                     (cx + int(4*sc)*facing, int(cherry_y - int(10*sc))), 2)

    eye_y = int(scoop_data[1][2])
    pygame.draw.circle(surface, EYE_COL, (int(cx + facing*int(4*sc)), eye_y), max(1, int(2*sc)))
    pygame.draw.circle(surface, EYE_COL, (int(cx - facing*int(2*sc)), eye_y), max(1, int(2*sc)))

    wafer_x = cx + facing * int(12*sc)
    wafer_y = int(scoop_data[1][2])
    if state in ("light_attack", "heavy_attack"):
        swing = int(math.sin(anim_frame * 0.6) * 10*sc)
        pygame.draw.rect(surface, WAFER_COL,
                         (int(wafer_x), int(wafer_y - int(3*sc) - swing), int(18*sc), int(5*sc)))
    else:
        pygame.draw.rect(surface, WAFER_COL,
                         (int(wafer_x), int(wafer_y - int(3*sc)), int(18*sc), int(5*sc)))
    for wi in range(1, 3):
        lx = int(wafer_x + wi * int(6*sc))
        pygame.draw.line(surface, (200, 155, 70),
                         (lx, int(wafer_y - int(3*sc))),
                         (lx, int(wafer_y + int(2*sc))), 1)

    if state == "special_attack":
        for i in range(8):
            angle = math.radians((anim_frame * 8 + i * 45) % 360)
            dist  = int(10*sc + (anim_frame % 15) * sc * 2)
            ix = cx + int(math.cos(angle) * dist)
            iy = int(scoop_data[1][2]) + int(math.sin(angle) * dist)
            hs = max(2, int(4*sc))
            pygame.draw.polygon(surface, ICE_COL, [
                (int(ix),      int(iy - hs)),
                (int(ix + hs), int(iy)),
                (int(ix),      int(iy + hs)),
                (int(ix - hs), int(iy)),
            ])
            pygame.draw.polygon(surface, WHITE, [
                (int(ix),      int(iy - hs)),
                (int(ix + hs), int(iy)),
                (int(ix),      int(iy + hs)),
                (int(ix - hs), int(iy)),
            ], 1)


# ---------------------------------------------------------------------------
# THE BROWNIE (Boss)
# Massive dark brown square, hulk proportions, crack lines, red eyes
# ---------------------------------------------------------------------------

def draw_the_brownie(surface, x, y, width, height, facing, state, anim_frame, special_data=None):
    cx = x + width // 2
    sc = height / 96.0

    BROWNIE_COL   = (60, 35, 15)
    BROWNIE_DARK  = (45, 25, 10)
    BROWNIE_LIGHT = (80, 50, 25)
    CRACK_COL     = (25, 12, 5)
    EYE_COL       = (220, 30, 10)
    EYE_GLOW      = (255, 80, 0)
    FIST_COL      = (50, 28, 12)
    RAGE_AURA     = (180, 20, 20)
    STEAM_COL     = (80, 60, 50)

    rage = special_data.get("rage", False) if isinstance(special_data, dict) else False

    if state == "ko":
        pieces = [
            (x + 4,           y + height - int(20*sc), int(16*sc), int(18*sc)),
            (x + int(22*sc),  y + height - int(14*sc), int(18*sc), int(12*sc)),
            (x + int(42*sc),  y + height - int(22*sc), int(12*sc), int(20*sc)),
            (x + int(6*sc),   y + height - int(36*sc), int(10*sc), int(14*sc)),
        ]
        for px, py, pw, ph in pieces:
            rot = int(math.sin(anim_frame * 0.05 + px) * 5)
            pygame.draw.rect(surface, BROWNIE_DARK, (int(px) + rot, int(py), int(pw), int(ph)))
        return

    vert_off = 0
    if state == "special_attack":
        phase = anim_frame % 40
        if phase < 20:
            vert_off = -int(phase * 2 * sc)
        else:
            vert_off = 0
            shock_dist = (phase - 20) * int(5*sc)
            ground_y   = y + height
            for d in range(1, 4):
                lx1 = cx - shock_dist - d * int(4*sc)
                lx2 = cx + shock_dist + d * int(4*sc)
                pygame.draw.line(surface, CRACK_COL,
                                 (int(lx1), int(ground_y)),
                                 (int(lx1 + int(8*sc)), int(ground_y - int(8*sc))), 2)
                pygame.draw.line(surface, CRACK_COL,
                                 (int(lx2), int(ground_y)),
                                 (int(lx2 - int(8*sc)), int(ground_y - int(8*sc))), 2)

    if rage:
        for d in range(1, 6):
            aura_alpha = max(0, 100 - d * 18)
            pygame.draw.rect(surface, (min(255, RAGE_AURA[0]), aura_alpha, 0),
                             (x - d*2 + int(4*sc), y - d*2 + vert_off, width + d*4, height + d*4), 2)

    body_col = (40, 20, 8) if rage else BROWNIE_COL
    pygame.draw.rect(surface, body_col,
                     (x + int(4*sc), y + vert_off, width - int(8*sc), height - int(8*sc)))
    pygame.draw.rect(surface, BROWNIE_DARK,
                     (x + int(4*sc), y + vert_off, width - int(8*sc), height - int(8*sc)), 3)
    pygame.draw.rect(surface, BROWNIE_LIGHT,
                     (x + int(6*sc), y + vert_off + int(4*sc), width - int(12*sc), int(8*sc)))

    crack_lines = [
        [(x + int(10*sc), y + int(12*sc) + vert_off),
         (x + int(18*sc), y + int(22*sc) + vert_off),
         (x + int(14*sc), y + int(35*sc) + vert_off)],
        [(cx + int(2*sc), y + int(8*sc) + vert_off),
         (cx + int(8*sc), y + int(20*sc) + vert_off)],
        [(x + width - int(12*sc), y + int(18*sc) + vert_off),
         (x + width - int(20*sc), y + int(30*sc) + vert_off),
         (x + width - int(16*sc), y + int(45*sc) + vert_off)],
    ]
    for crack in crack_lines:
        if len(crack) >= 2:
            pygame.draw.lines(surface, CRACK_COL, False,
                              [(int(p[0]), int(p[1])) for p in crack], 2)

    eye_y = y + int(18*sc) + vert_off
    eye_glow_r = int(4*sc + math.sin(anim_frame * 0.2) * sc)
    for ex in [cx - int(8*sc), cx + int(4*sc)]:
        pygame.draw.circle(surface, EYE_GLOW, (int(ex), int(eye_y)), int(eye_glow_r + 2))
        pygame.draw.circle(surface, EYE_COL,  (int(ex), int(eye_y)), int(eye_glow_r))

    fist_w = int(16*sc)
    fist_h = int(14*sc)
    fist_y = y + int(35*sc) + vert_off
    if state == "heavy_attack":
        fist_extend = int(10*sc)
    elif state == "light_attack":
        fist_extend = int(6*sc)
    else:
        fist_extend = 0

    lfist_x = x - fist_w // 2 - int(2*sc)
    pygame.draw.rect(surface, FIST_COL,
                     (int(lfist_x - fist_extend * facing), int(fist_y), fist_w, fist_h))
    pygame.draw.rect(surface, BROWNIE_DARK,
                     (int(lfist_x - fist_extend * facing), int(fist_y), fist_w, fist_h), 2)
    rfist_x = x + width - fist_w // 2 + int(2*sc)
    pygame.draw.rect(surface, FIST_COL,
                     (int(rfist_x + fist_extend * facing), int(fist_y), fist_w, fist_h))
    pygame.draw.rect(surface, BROWNIE_DARK,
                     (int(rfist_x + fist_extend * facing), int(fist_y), fist_w, fist_h), 2)

    if rage:
        for i in range(5):
            sx = x + int(8*sc) + i * int(10*sc) + int(math.sin(anim_frame * 0.15 + i) * 4*sc)
            sy = y + vert_off - int((anim_frame * 1.5 + i * 12) % int(30*sc))
            r  = max(1, int(3*sc) - i // 2)
            pygame.draw.circle(surface, STEAM_COL, (int(sx), int(sy)), r)

    if state == "block":
        pygame.draw.line(surface, FIST_COL,
                         (cx - int(12*sc), y + int(30*sc) + vert_off),
                         (cx + int(12*sc), y + int(45*sc) + vert_off), int(6*sc))
        pygame.draw.line(surface, FIST_COL,
                         (cx + int(12*sc), y + int(30*sc) + vert_off),
                         (cx - int(12*sc), y + int(45*sc) + vert_off), int(6*sc))


# ---------------------------------------------------------------------------
# CHARACTER DISPATCH
# Maps character name -> draw function for use by main game loop
# ---------------------------------------------------------------------------

CHARACTER_DRAW_FUNCS = {
    "Chef Blade":       draw_chef_blade,
    "Pancake Pete":     draw_pancake_pete,
    "Waffle Warrior":   draw_waffle_warrior,
    "Banana Bread Brad":draw_banana_bread_brad,
    "Pudding Paul":     draw_pudding_paul,
    "Crème Brûlée":     draw_creme_brulee,
    "Sundae Supreme":   draw_sundae_supreme,
    "THE BROWNIE":      draw_the_brownie,
}


def draw_character(surface, name, x, y, width, height, facing, state, anim_frame, special_data=None):
    """Dispatch to the correct character draw function by name."""
    fn = CHARACTER_DRAW_FUNCS.get(name)
    if fn:
        fn(surface, x, y, width, height, facing, state, anim_frame, special_data)


# ---------------------------------------------------------------------------
# STAGE / BACKGROUND RENDERING
# ---------------------------------------------------------------------------

def _draw_sky_gradient(surface, sky_color):
    """Draw a top-to-bottom gradient from a darkened sky_color to the colour itself."""
    dark = tuple(max(0, c - 40) for c in sky_color)
    floor_top = GROUND_Y
    for row in range(floor_top):
        t = row / floor_top
        r = int(dark[0] + (sky_color[0] - dark[0]) * t)
        g = int(dark[1] + (sky_color[1] - dark[1]) * t)
        b = int(dark[2] + (sky_color[2] - dark[2]) * t)
        pygame.draw.line(surface, (r, g, b), (0, row), (SCREEN_WIDTH, row))


def draw_stage(surface, stage_theme, anim_frame):
    """Draw the full background for the given stage theme dict."""
    sky_col    = stage_theme["sky"]
    floor_col  = stage_theme["floor"]
    accent_col = stage_theme["accent"]

    # Sky gradient
    _draw_sky_gradient(surface, sky_col)

    # Floor
    pygame.draw.rect(surface, floor_col,
                     (0, GROUND_Y, SCREEN_WIDTH, SCREEN_HEIGHT - GROUND_Y))
    # Floor highlight strip
    lighter_floor = tuple(min(255, c + 20) for c in floor_col)
    pygame.draw.rect(surface, lighter_floor,
                     (0, GROUND_Y, SCREEN_WIDTH, 4))

    # Parallax offset from anim_frame (subtle drift)
    px_off = int(math.sin(anim_frame * 0.01) * 6)

    # Determine stage key by matching sky/floor/accent to STAGE_THEMES entries
    stage_key = None
    for key, theme in STAGE_THEMES.items():
        if theme["sky"] == sky_col and theme["floor"] == floor_col:
            stage_key = key
            break

    if stage_key == "kitchen":
        _draw_kitchen(surface, accent_col, px_off, anim_frame)
    elif stage_key == "bakery":
        _draw_bakery(surface, accent_col, px_off, anim_frame)
    elif stage_key == "diner":
        _draw_diner(surface, accent_col, px_off, anim_frame)
    elif stage_key == "patisserie":
        _draw_patisserie(surface, accent_col, px_off, anim_frame)
    elif stage_key == "ice_parlor":
        _draw_ice_parlor(surface, accent_col, px_off, anim_frame)
    elif stage_key == "candy_shop":
        _draw_candy_shop(surface, accent_col, px_off, anim_frame)
    elif stage_key == "boss_arena":
        _draw_boss_arena(surface, accent_col, px_off, anim_frame)
    else:
        # Fallback generic background
        _draw_generic_bg(surface, accent_col, px_off)


def _draw_kitchen(surface, accent, px_off, anim_frame):
    """Kitchen stage: counter, hanging utensils, tiled floor."""
    # Tiled floor
    tile_col1 = (130, 110, 90)
    tile_col2 = (100, 80, 65)
    tile_size = 48
    for tx in range(0, SCREEN_WIDTH + tile_size, tile_size):
        for ty in range(GROUND_Y, SCREEN_HEIGHT, tile_size // 2):
            col = tile_col1 if ((tx // tile_size + ty // (tile_size // 2)) % 2 == 0) else tile_col2
            pygame.draw.rect(surface, col, (tx, ty, tile_size, tile_size // 2))
            pygame.draw.rect(surface, (80, 60, 45), (tx, ty, tile_size, tile_size // 2), 1)

    # Counter / worktop at back
    pygame.draw.rect(surface, (100, 80, 60),
                     (0, GROUND_Y - 80, SCREEN_WIDTH, 80))
    pygame.draw.rect(surface, (140, 110, 80),
                     (0, GROUND_Y - 80, SCREEN_WIDTH, 12))
    pygame.draw.rect(surface, (70, 50, 35),
                     (0, GROUND_Y - 80, SCREEN_WIDTH, 80), 2)

    # Cabinet doors on counter
    for cx in range(40, SCREEN_WIDTH - 40, 160):
        pygame.draw.rect(surface, (90, 70, 50),
                         (cx + px_off, GROUND_Y - 78, 140, 70))
        pygame.draw.rect(surface, (60, 42, 28),
                         (cx + px_off, GROUND_Y - 78, 140, 70), 2)
        # Knob
        pygame.draw.circle(surface, accent, (cx + px_off + 130, GROUND_Y - 43), 4)

    # Hanging utensils from top
    utensil_x_positions = [120, 280, 480, 680, 840]
    for ux in utensil_x_positions:
        hook_x = ux + px_off
        pygame.draw.line(surface, (80, 80, 80), (hook_x, 0), (hook_x, 80), 2)
        # Ladle shape
        pygame.draw.line(surface, accent, (hook_x, 80), (hook_x, 160), 3)
        pygame.draw.circle(surface, accent, (hook_x, 168), 10)


def _draw_bakery(surface, accent, px_off, anim_frame):
    """Bakery: brick oven, flour bags, warm tones."""
    # Brick oven – left side background element
    oven_x = 60 + px_off
    oven_y = GROUND_Y - 200
    # Oven body
    pygame.draw.rect(surface, (100, 60, 40), (oven_x, oven_y, 160, 200))
    pygame.draw.rect(surface, (70, 40, 20), (oven_x, oven_y, 160, 200), 3)
    # Oven door
    pygame.draw.rect(surface, (40, 25, 15), (oven_x + 20, oven_y + 60, 120, 100))
    pygame.draw.rect(surface, (80, 50, 30), (oven_x + 20, oven_y + 60, 120, 100), 3)
    # Glow inside oven
    glow_bright = 150 + int(math.sin(anim_frame * 0.1) * 40)
    pygame.draw.rect(surface, (glow_bright, 80, 20),
                     (oven_x + 22, oven_y + 62, 116, 96))
    # Bricks pattern on oven
    for brow in range(oven_y, oven_y + 200, 16):
        for bcol in range(oven_x, oven_x + 160, 32):
            pygame.draw.rect(surface, (80, 45, 25),
                             (bcol, brow, 30, 14), 1)

    # Flour bags – right side
    bag_x = SCREEN_WIDTH - 160 + px_off // 2
    bag_y = GROUND_Y - 100
    for i in range(2):
        bx = bag_x + i * 10
        by = bag_y + i * (-55)
        pygame.draw.rect(surface, accent, (bx, by, 80, 55))
        pygame.draw.rect(surface, (200, 190, 170), (bx, by, 80, 55), 2)
        # Tie at top
        pygame.draw.ellipse(surface, (220, 210, 190), (bx + 20, by - 10, 40, 20))
        draw_pixel_text(surface, "FLOUR", bx + 8, by + 18, 16, (160, 140, 110))

    # Decorative bread loaves on counter shelf
    shelf_y = GROUND_Y - 90
    pygame.draw.rect(surface, (130, 100, 70), (0, shelf_y, SCREEN_WIDTH, 8))
    for lx in range(200, SCREEN_WIDTH - 100, 120):
        pygame.draw.ellipse(surface, BROWN, (lx + px_off // 2, shelf_y - 30, 70, 34))
        pygame.draw.ellipse(surface, (160, 110, 50), (lx + px_off // 2, shelf_y - 30, 70, 34), 2)


def _draw_diner(surface, accent, px_off, anim_frame):
    """Diner: checkered floor, booth seats in background."""
    # Checkered floor
    tile = 40
    for tx in range(0, SCREEN_WIDTH + tile, tile):
        for ty in range(GROUND_Y, SCREEN_HEIGHT + tile, tile):
            col = WHITE if ((tx // tile + ty // tile) % 2 == 0) else (50, 50, 60)
            pygame.draw.rect(surface, col, (tx, ty, tile, tile))

    # Booth seats background
    for bx in [80, 420, 760]:
        booth_x = bx + px_off
        # Back cushion
        pygame.draw.rect(surface, accent, (booth_x, GROUND_Y - 110, 160, 80))
        pygame.draw.rect(surface, (180, 30, 30), (booth_x, GROUND_Y - 110, 160, 80), 3)
        # Seat
        pygame.draw.rect(surface, accent, (booth_x, GROUND_Y - 32, 160, 32))
        pygame.draw.rect(surface, (180, 30, 30), (booth_x, GROUND_Y - 32, 160, 32), 2)
        # Table in front
        pygame.draw.rect(surface, (140, 110, 80),
                         (booth_x - 10, GROUND_Y - 50, 180, 8))
        pygame.draw.line(surface, (100, 80, 60),
                         (booth_x + 80, GROUND_Y - 50),
                         (booth_x + 80, GROUND_Y), 4)

    # Neon sign glow at top
    sign_bright = 200 + int(math.sin(anim_frame * 0.08) * 55)
    sign_col = (sign_bright, 30, 30)
    pygame.draw.rect(surface, sign_col, (SCREEN_WIDTH // 2 - 100, 20, 200, 40))
    pygame.draw.rect(surface, WHITE, (SCREEN_WIDTH // 2 - 100, 20, 200, 40), 2)
    draw_pixel_text(surface, "DINER", SCREEN_WIDTH // 2 - 38, 28, 24, WHITE)


def _draw_patisserie(surface, accent, px_off, anim_frame):
    """Patisserie: arched windows, pink curtains."""
    # Arched windows
    for wx in [80, 400, 720]:
        wndx = wx + px_off
        # Frame
        pygame.draw.rect(surface, (180, 160, 190), (wndx, GROUND_Y - 220, 120, 200))
        pygame.draw.rect(surface, (140, 110, 140), (wndx, GROUND_Y - 220, 120, 200), 4)
        # Arch top
        pygame.draw.ellipse(surface, (180, 160, 190), (wndx, GROUND_Y - 260, 120, 80))
        pygame.draw.ellipse(surface, (140, 110, 140), (wndx, GROUND_Y - 260, 120, 80), 4)
        # Glass (lighter sky tone)
        pygame.draw.rect(surface, (90, 70, 100), (wndx + 6, GROUND_Y - 214, 108, 188))
        # Cross bar
        pygame.draw.line(surface, (140, 110, 140),
                         (wndx + 60, GROUND_Y - 220),
                         (wndx + 60, GROUND_Y - 20), 3)
        pygame.draw.line(surface, (140, 110, 140),
                         (wndx + 6, GROUND_Y - 120),
                         (wndx + 114, GROUND_Y - 120), 3)

        # Pink curtains (triangles draping from top corners)
        curtain_bob = int(math.sin(anim_frame * 0.05 + wx) * 3)
        pygame.draw.polygon(surface, accent, [
            (wndx + 6, GROUND_Y - 214),
            (wndx + 40, GROUND_Y - 214),
            (wndx + 6, GROUND_Y - 160 + curtain_bob),
        ])
        pygame.draw.polygon(surface, accent, [
            (wndx + 80, GROUND_Y - 214),
            (wndx + 114, GROUND_Y - 214),
            (wndx + 114, GROUND_Y - 160 + curtain_bob),
        ])

    # Decorative floor border
    pygame.draw.rect(surface, (160, 130, 150), (0, GROUND_Y - 8, SCREEN_WIDTH, 8))


def _draw_ice_parlor(surface, accent, px_off, anim_frame):
    """Ice cream parlor: freezer cases, neon sign glow."""
    # Freezer cases along back wall
    for fx in [40, 260, 500, 720]:
        fcase_x = fx + px_off
        pygame.draw.rect(surface, (160, 175, 185), (fcase_x, GROUND_Y - 170, 180, 170))
        pygame.draw.rect(surface, (120, 140, 155), (fcase_x, GROUND_Y - 170, 180, 170), 3)
        # Glass top panel
        pygame.draw.rect(surface, (180, 215, 235), (fcase_x + 4, GROUND_Y - 168, 172, 60))
        # Ice cream blobs inside
        blob_cols = [(240, 160, 180), (140, 90, 50), (245, 240, 230)]
        for bi, bc in enumerate(blob_cols):
            pygame.draw.circle(surface, bc,
                               (fcase_x + 30 + bi * 50, GROUND_Y - 130), 18)
        # Freezer control panel
        pygame.draw.rect(surface, (100, 120, 130),
                         (fcase_x + 4, GROUND_Y - 50, 172, 50))
        pygame.draw.circle(surface, accent, (fcase_x + 30, GROUND_Y - 25), 6)
        pygame.draw.circle(surface, RED, (fcase_x + 50, GROUND_Y - 25), 6)

    # Neon sign
    neon_flicker = (anim_frame // 8) % 3 != 0
    neon_col = accent if neon_flicker else (80, 120, 140)
    for d in range(3):
        pygame.draw.rect(surface, neon_col,
                         (SCREEN_WIDTH // 2 - 120 - d, 15 - d, 240 + d*2, 50 + d*2), 2)
    draw_pixel_text(surface, "ICE PARLOR", SCREEN_WIDTH // 2 - 72, 24, 22, WHITE)

    # Icicles hanging from ceiling
    for ix in range(30, SCREEN_WIDTH, 60):
        ici_len = 20 + int(math.sin(ix) * 12)
        pygame.draw.polygon(surface, (200, 230, 250), [
            (ix - 6, 0), (ix + 6, 0), (ix, ici_len)
        ])


def _draw_candy_shop(surface, accent, px_off, anim_frame):
    """Candy shop: jars on shelves, colorful striped walls."""
    # Striped wall
    stripe_w = 40
    stripe_cols = [(200, 120, 200), (240, 80, 160), (255, 160, 220), (220, 80, 200)]
    for sx in range(0, SCREEN_WIDTH + stripe_w, stripe_w):
        col = stripe_cols[(sx // stripe_w) % len(stripe_cols)]
        pygame.draw.rect(surface, col, (sx, 0, stripe_w, GROUND_Y))

    # Overlay darker tint for depth
    overlay = pygame.Surface((SCREEN_WIDTH, GROUND_Y), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 60))
    surface.blit(overlay, (0, 0))

    # Shelves
    for shelf_y in [GROUND_Y - 60, GROUND_Y - 130, GROUND_Y - 200]:
        pygame.draw.rect(surface, (140, 80, 60),
                         (0, shelf_y, SCREEN_WIDTH, 10))
        # Jars on shelf
        jar_cols = [(255, 80, 80), (80, 200, 80), (80, 80, 255),
                    (255, 200, 0), (200, 80, 255), (255, 140, 0)]
        for ji, jx in enumerate(range(30, SCREEN_WIDTH - 30, 70)):
            jcol = jar_cols[ji % len(jar_cols)]
            joffset = px_off // 2
            # Jar body
            pygame.draw.rect(surface, jcol,
                             (jx + joffset, shelf_y - 42, 40, 40))
            pygame.draw.rect(surface, WHITE, (jx + joffset, shelf_y - 42, 40, 40), 2)
            # Lid
            pygame.draw.rect(surface, (100, 70, 50),
                             (jx + 4 + joffset, shelf_y - 48, 32, 8))
        pygame.draw.rect(surface, (100, 60, 40), (0, shelf_y, SCREEN_WIDTH, 10), 1)


def _draw_boss_arena(surface, accent, px_off, anim_frame):
    """Boss arena: dark, fire pits, chains, cracked floor."""
    # Cracked floor
    crack_col = (35, 15, 8)
    for cx2 in range(80, SCREEN_WIDTH, 120):
        cx2 += px_off // 3
        fy = GROUND_Y
        pygame.draw.line(surface, crack_col,
                         (cx2, fy), (cx2 - 20, fy + 30), 2)
        pygame.draw.line(surface, crack_col,
                         (cx2, fy), (cx2 + 15, fy + 50), 2)
        pygame.draw.line(surface, crack_col,
                         (cx2 + 15, fy + 50), (cx2 + 35, fy + 35), 2)

    # Fire pits on sides
    for fp_x, flipped in [(40, False), (SCREEN_WIDTH - 120, True)]:
        # Stone pit bowl
        pygame.draw.ellipse(surface, (60, 40, 30),
                            (fp_x, GROUND_Y - 30, 80, 30))
        pygame.draw.ellipse(surface, (40, 25, 15),
                            (fp_x, GROUND_Y - 30, 80, 30), 3)
        # Flames
        flicker = int(math.sin(anim_frame * 0.18 + fp_x) * 8)
        for fi in range(4):
            flame_phase = (anim_frame * 0.2 + fi * 0.8) % (2 * math.pi)
            fh = 30 + int(math.sin(flame_phase) * 15) + flicker
            fxoff = fi * 14 - 6
            flame_col = [(255, 60, 0), (255, 140, 0), (255, 200, 0), (255, 80, 0)][fi]
            pygame.draw.polygon(surface, flame_col, [
                (fp_x + 10 + fxoff, GROUND_Y - 30),
                (fp_x + 18 + fxoff, GROUND_Y - 30),
                (fp_x + 14 + fxoff, GROUND_Y - 30 - fh),
            ])

    # Chains hanging from ceiling
    for chain_x in [200, 480, 760]:
        cx3 = chain_x + px_off // 4
        sway = int(math.sin(anim_frame * 0.04 + chain_x) * 5)
        for link_y in range(0, 200, 14):
            lx = cx3 + sway
            pygame.draw.ellipse(surface, (80, 70, 65),
                                (lx - 6, link_y, 12, 8))
            pygame.draw.ellipse(surface, (50, 45, 40),
                                (lx - 6, link_y, 12, 8), 2)

    # Dark red vignette on floor near edges
    pygame.draw.rect(surface, accent, (0, GROUND_Y, 60, SCREEN_HEIGHT - GROUND_Y))
    pygame.draw.rect(surface, accent, (SCREEN_WIDTH - 60, GROUND_Y, 60, SCREEN_HEIGHT - GROUND_Y))


def _draw_generic_bg(surface, accent, px_off):
    """Fallback simple background."""
    pygame.draw.rect(surface, accent,
                     (20 + px_off, 40, 80, 60))
    pygame.draw.rect(surface, WHITE,
                     (20 + px_off, 40, 80, 60), 2)


# ---------------------------------------------------------------------------
# HUD / UI RENDERING
# ---------------------------------------------------------------------------

def draw_hud(surface, player, enemy, timer, fight_number):
    """Draw health bars, special meters, names, timer, combo counter."""

    # -- Player health bar (left side, fills left-to-right) --
    px = UI_MARGIN
    py = HEALTH_BAR_Y
    draw_health_bar(surface, px, py, HEALTH_BAR_WIDTH, HEALTH_BAR_HEIGHT,
                    player["hp"], player["max_hp"], RED, DARK_GRAY)
    # Thin yellow section showing damage taken since last hit (gusto effect)
    draw_pixel_text(surface, player["name"], px, py + HEALTH_BAR_HEIGHT + 4, 20, WHITE)

    # -- Enemy health bar (right side, fills right-to-left) --
    ex = SCREEN_WIDTH - UI_MARGIN - HEALTH_BAR_WIDTH
    ey = HEALTH_BAR_Y
    # Draw background then fill from right
    pygame.draw.rect(surface, DARK_GRAY, (ex, ey, HEALTH_BAR_WIDTH, HEALTH_BAR_HEIGHT))
    if enemy["max_hp"] > 0:
        fill_w = int(HEALTH_BAR_WIDTH * _clamp(enemy["hp"] / enemy["max_hp"], 0, 1))
        if fill_w > 0:
            pygame.draw.rect(surface, RED,
                             (ex + HEALTH_BAR_WIDTH - fill_w, ey, fill_w, HEALTH_BAR_HEIGHT))
    pygame.draw.rect(surface, WHITE, (ex, ey, HEALTH_BAR_WIDTH, HEALTH_BAR_HEIGHT), 2)
    draw_pixel_text(surface, enemy["name"],
                    SCREEN_WIDTH - UI_MARGIN - HEALTH_BAR_WIDTH,
                    ey + HEALTH_BAR_HEIGHT + 4, 20, WHITE)

    # -- Special meters --
    sp_y = SPECIAL_BAR_Y
    # Player special (yellow, left)
    p_meter = player.get("special_meter", 0)
    draw_health_bar(surface, px, sp_y, HEALTH_BAR_WIDTH, SPECIAL_BAR_HEIGHT,
                    p_meter, SPECIAL_METER_MAX, YELLOW, (50, 50, 20))
    # Enemy special (yellow, right, fills from right)
    e_meter = enemy.get("special_meter", 0)
    pygame.draw.rect(surface, (50, 50, 20), (ex, sp_y, HEALTH_BAR_WIDTH, SPECIAL_BAR_HEIGHT))
    if SPECIAL_METER_MAX > 0:
        e_fill_w = int(HEALTH_BAR_WIDTH * _clamp(e_meter / SPECIAL_METER_MAX, 0, 1))
        if e_fill_w > 0:
            pygame.draw.rect(surface, YELLOW,
                             (ex + HEALTH_BAR_WIDTH - e_fill_w, sp_y, e_fill_w, SPECIAL_BAR_HEIGHT))
    pygame.draw.rect(surface, WHITE, (ex, sp_y, HEALTH_BAR_WIDTH, SPECIAL_BAR_HEIGHT), 1)

    # -- Timer (centre top) --
    timer_display = max(0, int(timer))
    timer_font_size = 40
    timer_col = RED if timer_display <= 10 else WHITE
    t_str = str(timer_display)
    t_surf = pygame.font.Font(None, timer_font_size).render(t_str, False, timer_col)
    t_x = SCREEN_WIDTH // 2 - t_surf.get_width() // 2
    # Background pill
    pygame.draw.rect(surface, DARK_GRAY, (t_x - 14, 18, t_surf.get_width() + 28, 36))
    pygame.draw.rect(surface, WHITE,     (t_x - 14, 18, t_surf.get_width() + 28, 36), 2)
    surface.blit(t_surf, (t_x, 22))

    # -- Fight number --
    total_fights = len(ENEMY_ORDER)
    fight_str = f"FIGHT {fight_number}/{total_fights}"
    draw_pixel_text(surface, fight_str, SCREEN_WIDTH // 2 - 42, 58, 18, LIGHT_GRAY)

    # -- Combo counter --
    p_combo = player.get("combo_count", 0)
    e_combo = enemy.get("combo_count", 0)
    if p_combo > 1:
        scale = 1.0 + (p_combo * 0.06)
        combo_size = int(28 * scale)
        combo_text = f"{p_combo} HIT COMBO!"
        cx_pos = UI_MARGIN + HEALTH_BAR_WIDTH // 2
        draw_pixel_text(surface, combo_text,
                        cx_pos - len(combo_text) * combo_size // 5,
                        HEALTH_BAR_Y + HEALTH_BAR_HEIGHT + 30, combo_size, YELLOW)
    if e_combo > 1:
        scale = 1.0 + (e_combo * 0.06)
        combo_size = int(28 * scale)
        combo_text = f"{e_combo} HIT COMBO!"
        ex_pos = SCREEN_WIDTH - UI_MARGIN - HEALTH_BAR_WIDTH // 2
        draw_pixel_text(surface, combo_text,
                        ex_pos - len(combo_text) * combo_size // 5,
                        HEALTH_BAR_Y + HEALTH_BAR_HEIGHT + 30, combo_size, YELLOW)


# ---------------------------------------------------------------------------
# TITLE SCREEN
# ---------------------------------------------------------------------------

def draw_title_screen(surface, anim_frame):
    """Animated title screen."""
    # Dark kitchen background
    surface.fill((30, 30, 45))
    # Floor
    pygame.draw.rect(surface, (80, 65, 50),
                     (0, GROUND_Y, SCREEN_WIDTH, SCREEN_HEIGHT - GROUND_Y))
    pygame.draw.rect(surface, (100, 80, 60), (0, GROUND_Y, SCREEN_WIDTH, 6))

    # Decorative kitchen steam rising from background
    for i in range(6):
        sx = 80 + i * 140 + int(math.sin(anim_frame * 0.05 + i) * 10)
        sy = GROUND_Y - int((anim_frame * 0.8 + i * 30) % 120)
        r  = 8 + i % 3 * 4
        alpha = max(0, 120 - abs(sy - GROUND_Y))
        steam_s = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
        pygame.draw.circle(steam_s, (180, 180, 180, alpha), (r, r), r)
        surface.blit(steam_s, (sx - r, sy - r))

    # ---- Title text: draw each letter as thick pixel blocks ----
    title_chars = "COOKING COMBAT"
    char_w, char_h = 32, 48
    gap = 4
    total_w = len(title_chars) * (char_w + gap) - gap
    start_x = SCREEN_WIDTH // 2 - total_w // 2
    title_y  = 80 + int(math.sin(anim_frame * 0.07) * 5)

    font_big = pygame.font.Font(None, 72)
    title_surf = font_big.render("COOKING COMBAT", False, ORANGE)
    # Shadow
    shadow_surf = font_big.render("COOKING COMBAT", False, (80, 40, 0))
    surface.blit(shadow_surf, (SCREEN_WIDTH // 2 - title_surf.get_width() // 2 + 4, title_y + 4))
    surface.blit(title_surf,  (SCREEN_WIDTH // 2 - title_surf.get_width() // 2, title_y))

    # Subtitle
    subtitle_surf = pygame.font.Font(None, 28).render("KITCHEN BRAWL EDITION", False, CREAM)
    surface.blit(subtitle_surf,
                 (SCREEN_WIDTH // 2 - subtitle_surf.get_width() // 2, title_y + 68))

    # Decorative line under title
    pygame.draw.rect(surface, ORANGE,
                     (SCREEN_WIDTH // 2 - 200, title_y + 98, 400, 4))

    # Animated preview: Chef vs Brownie facing off
    chef_x  = SCREEN_WIDTH // 2 - 160
    brownie_x = SCREEN_WIDTH // 2 + 60
    preview_y = GROUND_Y - CHAR_HEIGHT - 20
    draw_chef_blade(surface, chef_x, preview_y, CHAR_WIDTH, CHAR_HEIGHT,
                    1, "idle", anim_frame)
    draw_the_brownie(surface, brownie_x, GROUND_Y - BOSS_HEIGHT - 20,
                     BOSS_WIDTH, BOSS_HEIGHT, -1, "idle", anim_frame)

    # VS text between them
    vs_font = pygame.font.Font(None, 56)
    vs_surf = vs_font.render("VS", False, RED)
    vs_bob  = int(math.sin(anim_frame * 0.12) * 4)
    surface.blit(vs_surf, (SCREEN_WIDTH // 2 - vs_surf.get_width() // 2, preview_y + 20 + vs_bob))

    # Blinking "PRESS ENTER" text
    if (anim_frame // 30) % 2 == 0:
        enter_surf = pygame.font.Font(None, 32).render("PRESS ENTER TO START", False, WHITE)
        surface.blit(enter_surf,
                     (SCREEN_WIDTH // 2 - enter_surf.get_width() // 2, SCREEN_HEIGHT - 60))

    # Decorative utensil silhouettes
    for i, ux in enumerate([40, SCREEN_WIDTH - 60]):
        pygame.draw.line(surface, DARK_GRAY, (ux, 40), (ux, 140), 4)
        pygame.draw.circle(surface, DARK_GRAY, (ux, 148), 12)


# ---------------------------------------------------------------------------
# FIGHT INTRO SCREEN
# ---------------------------------------------------------------------------

def draw_fight_intro(surface, player_name, enemy_data, fight_number, anim_frame):
    """Split-screen intro with character slide-in, VS, names."""
    # Background halves
    pygame.draw.rect(surface, (20, 20, 50), (0, 0, SCREEN_WIDTH // 2, SCREEN_HEIGHT))
    pygame.draw.rect(surface, (50, 10, 10), (SCREEN_WIDTH // 2, 0, SCREEN_WIDTH // 2, SCREEN_HEIGHT))

    # Slide in: frames 0-40 = slide, 40+ = held
    slide_progress = _clamp(anim_frame / 40.0, 0.0, 1.0)

    # Player slides in from left
    p_target_x = SCREEN_WIDTH // 4 - CHAR_WIDTH // 2
    p_start_x  = -CHAR_WIDTH - 20
    p_x = int(p_start_x + (p_target_x - p_start_x) * slide_progress)
    draw_chef_blade(surface, p_x, GROUND_Y - CHAR_HEIGHT - 30,
                    CHAR_WIDTH, CHAR_HEIGHT, 1, "idle", anim_frame)

    # Enemy slides in from right
    is_boss    = enemy_data.get("is_boss", False)
    e_w = BOSS_WIDTH if is_boss else CHAR_WIDTH
    e_h = BOSS_HEIGHT if is_boss else CHAR_HEIGHT
    e_target_x = SCREEN_WIDTH * 3 // 4 - e_w // 2
    e_start_x  = SCREEN_WIDTH + e_w + 20
    e_x = int(e_start_x + (e_target_x - e_start_x) * slide_progress)
    draw_character(surface, enemy_data["name"], e_x, GROUND_Y - e_h - 30,
                   e_w, e_h, -1, "idle", anim_frame)

    # Floor line
    pygame.draw.rect(surface, GRAY,
                     (0, GROUND_Y - 30, SCREEN_WIDTH, 4))

    # VS text (appears after slide completes)
    if slide_progress >= 1.0:
        vs_shake = int(math.sin(anim_frame * 0.5) * 3)
        vs_font  = pygame.font.Font(None, 96)
        vs_surf  = vs_font.render("VS", False, YELLOW)
        surface.blit(vs_surf, (SCREEN_WIDTH // 2 - vs_surf.get_width() // 2 + vs_shake,
                                SCREEN_HEIGHT // 2 - vs_surf.get_height() // 2))
        pygame.draw.rect(surface, WHITE,
                         (SCREEN_WIDTH // 2 - 80, SCREEN_HEIGHT // 2 - 6, 160, 6))

    # Player name
    pname_surf = pygame.font.Font(None, 36).render(player_name, False, WHITE)
    surface.blit(pname_surf, (p_target_x - pname_surf.get_width() // 2 + CHAR_WIDTH // 2,
                               SCREEN_HEIGHT - 140))

    # Enemy name
    ename_surf = pygame.font.Font(None, 36).render(enemy_data["name"], False, WHITE)
    surface.blit(ename_surf, (e_target_x - ename_surf.get_width() // 2 + e_w // 2,
                               SCREEN_HEIGHT - 140))

    # Enemy intro quote
    if slide_progress >= 1.0:
        quote = enemy_data.get("intro", "")
        quote_surf = pygame.font.Font(None, 24).render(f'"{quote}"', False, LIGHT_GRAY)
        surface.blit(quote_surf,
                     (SCREEN_WIDTH // 2 - quote_surf.get_width() // 2,
                      SCREEN_HEIGHT - 100))

    # Fight number + stage
    stage = enemy_data.get("stage", "")
    stage_label = f"FIGHT {fight_number}/{len(ENEMY_ORDER)} - {stage.replace('_', ' ').upper()}"
    stage_surf = pygame.font.Font(None, 22).render(stage_label, False, LIGHT_GRAY)
    surface.blit(stage_surf, (SCREEN_WIDTH // 2 - stage_surf.get_width() // 2, 18))


# ---------------------------------------------------------------------------
# KO SCREEN
# ---------------------------------------------------------------------------

def draw_ko_screen(surface, winner_name, is_player_win, anim_frame):
    """K.O.! screen with winner declaration."""
    # Semi-transparent dark overlay
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    surface.blit(overlay, (0, 0))

    # K.O.! text – shakes
    ko_font  = pygame.font.Font(None, 120)
    shake_x  = int(math.sin(anim_frame * 1.2) * 6)
    shake_y  = int(math.cos(anim_frame * 0.9) * 4)
    ko_surf  = ko_font.render("K.O.!", False, RED)
    ko_x     = SCREEN_WIDTH // 2 - ko_surf.get_width() // 2 + shake_x
    ko_y     = SCREEN_HEIGHT // 2 - 100 + shake_y
    # Shadow
    ko_shadow = ko_font.render("K.O.!", False, DARK_RED)
    surface.blit(ko_shadow, (ko_x + 5, ko_y + 5))
    surface.blit(ko_surf,   (ko_x,     ko_y))

    # Winner / result
    if is_player_win:
        result_text = "YOU WIN!"
        result_col  = YELLOW
        # Celebration sparkles
        for i in range(8):
            angle  = math.radians((anim_frame * 5 + i * 45) % 360)
            radius = 80 + int(math.sin(anim_frame * 0.15 + i) * 20)
            sx = SCREEN_WIDTH // 2 + int(math.cos(angle) * radius)
            sy = SCREEN_HEIGHT // 2 + int(math.sin(angle) * radius)
            pygame.draw.circle(surface, YELLOW, (int(sx), int(sy)), 5)
            pygame.draw.circle(surface, ORANGE,  (int(sx), int(sy)), 3)
    else:
        result_text = "YOU LOSE..."
        result_col  = GRAY

    result_font = pygame.font.Font(None, 52)
    result_surf = result_font.render(result_text, False, result_col)
    surface.blit(result_surf,
                 (SCREEN_WIDTH // 2 - result_surf.get_width() // 2,
                  SCREEN_HEIGHT // 2 + 20))

    # Winner name
    wname_font = pygame.font.Font(None, 34)
    wname_surf = wname_font.render(winner_name + " WINS!", False, WHITE)
    surface.blit(wname_surf,
                 (SCREEN_WIDTH // 2 - wname_surf.get_width() // 2,
                  SCREEN_HEIGHT // 2 + 80))


# ---------------------------------------------------------------------------
# GAME OVER / VICTORY SCREEN
# ---------------------------------------------------------------------------

def draw_game_over(surface, is_victory, anim_frame):
    """Final game-over or victory screen."""
    if is_victory:
        bg_col = (20, 40, 20)
    else:
        bg_col = (30, 10, 10)
    surface.fill(bg_col)

    if is_victory:
        # Confetti particles
        for i in range(40):
            cx2 = (i * 67 + anim_frame * 3) % SCREEN_WIDTH
            cy2 = (i * 43 + anim_frame * 2) % SCREEN_HEIGHT
            ccol = [(255, 200, 0), (255, 80, 80), (80, 200, 255),
                    (80, 255, 80), (255, 160, 0)][i % 5]
            pygame.draw.rect(surface, ccol, (int(cx2), int(cy2), 8, 8))

        # Title text
        font_big = pygame.font.Font(None, 48)
        line1 = font_big.render("CONGRATULATIONS!", False, YELLOW)
        line2 = font_big.render("THE KITCHEN IS SAVED!", False, GREEN)
        surface.blit(line1, (SCREEN_WIDTH // 2 - line1.get_width() // 2, 180))
        surface.blit(line2, (SCREEN_WIDTH // 2 - line2.get_width() // 2, 240))

        # Animated chef celebrating
        draw_chef_blade(surface,
                        SCREEN_WIDTH // 2 - CHAR_WIDTH // 2,
                        GROUND_Y - CHAR_HEIGHT - 20,
                        CHAR_WIDTH, CHAR_HEIGHT,
                        1, "idle", anim_frame)

    else:
        # GAME OVER
        shake = int(math.sin(anim_frame * 0.4) * 4)
        font_big  = pygame.font.Font(None, 100)
        go_surf   = font_big.render("GAME OVER", False, RED)
        go_shadow = font_big.render("GAME OVER", False, DARK_RED)
        gx = SCREEN_WIDTH // 2 - go_surf.get_width() // 2 + shake
        gy = SCREEN_HEIGHT // 2 - go_surf.get_height() // 2
        surface.blit(go_shadow, (gx + 5, gy + 5))
        surface.blit(go_surf,   (gx, gy))

        # Retry prompt
        retry_surf = pygame.font.Font(None, 30).render("PRESS ENTER TO RETRY", False, LIGHT_GRAY)
        surface.blit(retry_surf,
                     (SCREEN_WIDTH // 2 - retry_surf.get_width() // 2,
                      SCREEN_HEIGHT // 2 + 80))


# ---------------------------------------------------------------------------
# PARTICLE RENDERING
# ---------------------------------------------------------------------------

def draw_particles(surface, particles):
    """Draw pixel-art style particles, fading based on remaining life."""
    for p in particles:
        life     = p.get("life", 1)
        max_life = p.get("max_life", life)
        size     = max(1, int(p.get("size", 4)))
        color    = p.get("color", WHITE)
        px2      = int(p["x"])
        py2      = int(p["y"])

        if max_life > 0:
            alpha_ratio = _clamp(life / max_life, 0.0, 1.0)
        else:
            alpha_ratio = 1.0

        # Fade colour toward black
        faded = tuple(int(c * alpha_ratio) for c in color)

        # Draw as square for pixel-art aesthetic
        pygame.draw.rect(surface, faded, (px2 - size // 2, py2 - size // 2, size, size))
