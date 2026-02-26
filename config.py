"""Game constants and character definitions for Cooking Combat."""

# --- Display ---
SCREEN_WIDTH = 960
SCREEN_HEIGHT = 540
FPS = 60
TITLE = "COOKING COMBAT"

# --- Physics ---
GRAVITY = 0.8
GROUND_Y = 440
PLAYER_SPEED = 5
JUMP_FORCE = -13
KNOCKBACK_DECAY = 0.88

# --- Combat ---
LIGHT_DAMAGE = 8
HEAVY_DAMAGE = 14
SPECIAL_DAMAGE = 22
BLOCK_REDUCTION = 0.2
SPECIAL_METER_MAX = 100
SPECIAL_COST = 35
METER_GAIN_HIT = 10
METER_GAIN_HURT = 14
HIT_STUN_LIGHT = 8
HIT_STUN_HEAVY = 14
HIT_STUN_SPECIAL = 20
ATTACK_COOLDOWN_LIGHT = 4
ATTACK_COOLDOWN_HEAVY = 10
ATTACK_COOLDOWN_SPECIAL = 14

# Attack durations (total frames from start to recovery end)
LIGHT_ATTACK_DURATION = 10
HEAVY_ATTACK_DURATION = 18
SPECIAL_ATTACK_DURATION = 24

# Attack active windows (start_frame, end_frame) - hitbox is live during these
LIGHT_ACTIVE = (2, 5)
HEAVY_ACTIVE = (4, 10)
SPECIAL_ACTIVE = (3, 14)

# Hitbox reach (extends from fighter's front edge)
LIGHT_REACH = 52
HEAVY_REACH = 64
SPECIAL_REACH = 88

# Attack forward lunge distance (pixels moved forward during active frames)
LIGHT_LUNGE = 2.0
HEAVY_LUNGE = 3.0
SPECIAL_LUNGE = 1.5

# --- Character sizes ---
CHAR_WIDTH = 48
CHAR_HEIGHT = 64
BOSS_WIDTH = 72
BOSS_HEIGHT = 96

# --- Colors ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (220, 40, 40)
GREEN = (40, 200, 40)
BLUE = (40, 80, 220)
YELLOW = (240, 200, 40)
ORANGE = (240, 140, 40)
DARK_BROWN = (80, 50, 30)
BROWN = (140, 90, 50)
LIGHT_BROWN = (200, 160, 100)
CREAM = (255, 240, 210)
PINK = (255, 180, 200)
PURPLE = (160, 60, 200)
DARK_RED = (140, 20, 20)
GOLD = (255, 215, 0)
GRAY = (128, 128, 128)
DARK_GRAY = (64, 64, 64)
LIGHT_GRAY = (192, 192, 192)
SKY_BLUE = (135, 200, 235)
DARK_CHOCOLATE = (55, 30, 15)
CARAMEL = (200, 150, 60)
SYRUP = (180, 120, 40)

# --- UI ---
HEALTH_BAR_WIDTH = 350
HEALTH_BAR_HEIGHT = 24
HEALTH_BAR_Y = 30
SPECIAL_BAR_HEIGHT = 10
SPECIAL_BAR_Y = 60
UI_MARGIN = 40

# --- Game flow ---
ROUND_TIME = 90  # seconds
INTRO_DURATION = 120  # frames
KO_DURATION = 120  # frames
TRANSITION_SPEED = 8

# --- Stages (background color themes) ---
STAGE_THEMES = {
    "kitchen":     {"sky": (60, 60, 80),   "floor": (120, 100, 80),  "accent": ORANGE},
    "bakery":      {"sky": (80, 60, 50),   "floor": (160, 120, 80),  "accent": CREAM},
    "diner":       {"sky": (40, 60, 80),   "floor": (100, 80, 70),   "accent": RED},
    "patisserie":  {"sky": (70, 50, 70),   "floor": (140, 110, 100), "accent": PINK},
    "ice_parlor":  {"sky": (60, 80, 100),  "floor": (130, 140, 150), "accent": SKY_BLUE},
    "candy_shop":  {"sky": (80, 50, 80),   "floor": (120, 90, 120),  "accent": PURPLE},
    "boss_arena":  {"sky": (30, 10, 10),   "floor": (60, 30, 20),    "accent": DARK_RED},
}

# --- Enemy roster ---
ENEMY_ORDER = [
    {
        "name": "Pancake Pete",
        "hp": 80,
        "speed": 3.5,
        "aggression": 0.35,
        "stage": "kitchen",
        "intro": "A flat fighter with a flip trick!",
        "color_primary": SYRUP,
        "color_secondary": CREAM,
        "special_name": "SYRUP SPLASH",
    },
    {
        "name": "Waffle Warrior",
        "hp": 100,
        "speed": 3.0,
        "aggression": 0.42,
        "stage": "diner",
        "intro": "Square, sturdy, and ready to stomp!",
        "color_primary": LIGHT_BROWN,
        "color_secondary": GOLD,
        "special_name": "BUTTER BOMB",
    },
    {
        "name": "Banana Bread Brad",
        "hp": 90,
        "speed": 4.0,
        "aggression": 0.48,
        "stage": "bakery",
        "intro": "Slicing through the competition!",
        "color_primary": BROWN,
        "color_secondary": YELLOW,
        "special_name": "BANANA BARRAGE",
    },
    {
        "name": "Pudding Paul",
        "hp": 85,
        "speed": 3.5,
        "aggression": 0.52,
        "stage": "patisserie",
        "intro": "Wobble wobble... SMACK!",
        "color_primary": CARAMEL,
        "color_secondary": CREAM,
        "special_name": "JIGGLE SLAM",
    },
    {
        "name": "Crème Brûlée",
        "hp": 95,
        "speed": 4.0,
        "aggression": 0.58,
        "stage": "patisserie",
        "intro": "Torched to perfection!",
        "color_primary": CREAM,
        "color_secondary": ORANGE,
        "special_name": "TORCH BLAST",
    },
    {
        "name": "Sundae Supreme",
        "hp": 100,
        "speed": 4.5,
        "aggression": 0.62,
        "stage": "ice_parlor",
        "intro": "Cold and ruthless with a cherry on top!",
        "color_primary": PINK,
        "color_secondary": BROWN,
        "special_name": "BRAIN FREEZE",
    },
    {
        "name": "THE BROWNIE",
        "hp": 200,
        "speed": 2.5,
        "aggression": 0.7,
        "stage": "boss_arena",
        "intro": "DENSE. POWERFUL. UNSTOPPABLE.",
        "color_primary": DARK_CHOCOLATE,
        "color_secondary": DARK_RED,
        "special_name": "CHOCOLATE RAGE",
        "is_boss": True,
    },
]

# --- Player ---
PLAYER_HP = 100
PLAYER_COLOR_PRIMARY = WHITE
PLAYER_COLOR_SECONDARY = (40, 100, 180)
PLAYER_NAME = "Chef Blade"
PLAYER_SPECIAL_NAME = "SPATULA FURY"

# --- Audio ---
SAMPLE_RATE = 22050
AUDIO_CHANNELS = 1

# --- Backwards compat aliases (used by sound.py / graphics.py) ---
HIT_STUN_LIGHT_ALIAS = HIT_STUN_LIGHT
ATTACK_COOLDOWN = ATTACK_COOLDOWN_LIGHT
HEAVY_COOLDOWN = ATTACK_COOLDOWN_HEAVY
