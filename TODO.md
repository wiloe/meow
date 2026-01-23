# Project Ideas

## protoiso.py (Isometric RPG)
- [ ] **Magic Missile Spell**: Add a fast-moving projectile spell.
- [ ] **Bat Enemy**: Create a flying enemy that can cross water and walls.
- [ ] **Ice Blast**: A spell that applies a slow effect to enemies.
- [ ] **Skeleton Enemy**: A melee-focused undead enemy.

## main.c (6502 Emulator)
- [ ] **Assembler Instructions**: Add more opcodes to the internal assembler.
- [ ] **Step-Back**: Implement reverse debugging (state history).

## Technical Debt & Architecture (iso_rpg)
- [ ] **Data Externalization**: Move `self.recipes` and `self.spells` from `protoiso.py` to `data/recipes.json` and `data/spells.json`.
- [ ] **Audio Manager**: Replace ad-hoc `rl.load_sound` calls with a centralized `AudioManager` class in `iso_rpg/audio.py` that handles resource management and volume control.
- [ ] **ECS Rendering**: Move the main isometric world rendering loop from `protoiso.py` into a new `RenderSystem` in `iso_rpg/systems.py` to fully utilize the ECS architecture.
- [ ] **Refactor IsoGame**: Extract `IsoGame` logic into specialized managers (e.g., `InputManager`, `StateManager`) to reduce the "God Object" anti-pattern.
- [ ] **Quest System**: Decouple `QuestSystem` from `IsoGame.player` dictionary by introducing a proper `Player` class or component.
