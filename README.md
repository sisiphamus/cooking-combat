# Cooking Combat

A Street Fighter-style 2D fighting game with a cooking theme, built in Python with Pygame.

You play as Chef Blade, a spatula-wielding culinary warrior fighting through waves of enemies in arcade-style combat. Every character is drawn entirely in code. No sprite sheets, no image assets. Just `pygame.draw.rect` and `pygame.draw.ellipse` calls rendering a chef in a white hat and blue jacket swinging a spatula.

## Gameplay

- **Three attack types**: Light (8 damage, fast), Heavy (14 damage, medium), Special (22 damage, costs meter)
- **Special meter** that builds from dealing and taking damage
- **Blocking and crouching** for defense
- **Combo system** with input buffering for responsive controls
- **Boss fights** with larger, tougher enemies
- **Wave-based progression** through multiple opponents

## Under the Hood

The fighting game engine is more complete than it looks:

- Full physics system with gravity, knockback, and knockback decay
- State machine managing title screen, fight intro, fighting, KO, victory, game over, and pause states
- Hit-stun and single-hit enforcement preventing multi-hit bugs per swing
- Attack lunge giving satisfying forward motion on strikes
- AI enemies with per-enemy speed tuning and distance-closing behavior
- Particle effects and screen shake on impacts
- Projectile system for ranged attacks

## Project Structure

| File | Purpose |
|------|---------|
| `main.py` | Entry point |
| `game.py` | Game loop and state management |
| `engine.py` | Physics, collision, combat mechanics |
| `graphics.py` | All procedural character and effect rendering |
| `config.py` | Game constants and tuning parameters |
| `sound.py` | Sound manager |

## Tech

Python, Pygame

## Run It

```bash
pip install -r requirements.txt
python main.py
```
