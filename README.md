# Cooking Combat

You play as Chef Blade -- white hat, blue jacket, spatula in hand -- fighting your way through a gauntlet of food-themed opponents in a Street Fighter-style 2D fighter. Built in Python with Pygame. No sprites. Every character is drawn with `pygame.draw.rect` and `pygame.draw.ellipse`, limb by limb, frame by frame.

The roster starts with Pancake Pete and escalates through Waffle Warrior, Banana Bread Brad, Pudding Paul, Creme Brulee, and Sundae Supreme before you reach the final boss: THE BROWNIE. 200 HP. Dark chocolate color scheme. Special move called CHOCOLATE RAGE.

The fighting engine is more real than it has any right to be. Three attack types: light (8 damage, 10-frame duration), heavy (14 damage, 18 frames), and special (22 damage, costs 35 meter). There's proper hit-stun -- 8 frames on light, 14 on heavy, 20 on special. Knockback decays at 0.88 per frame. Attack lunge pushes you forward during active frames so strikes have weight. An input buffer queues your next attack during recovery so combos feel responsive. The state machine tracks idle, walking, jumping, crouching, attacking, blocking, hit-stun, KO, and transitions between all of them.

Each fight happens on a themed stage. Kitchen, bakery, diner, patisserie, ice parlor, candy shop, and the boss arena each have their own sky, floor, and accent colors.

```bash
pip install -r requirements.txt
python main.py
```
