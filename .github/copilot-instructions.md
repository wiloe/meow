# Meow Codebase - AI Coding Agent Instructions

## Project Overview
A scratchpad repository containing multiple experimental projects:
- **C Projects**: 6502 emulator with GUI debugger using Raylib
- **Python Projects**: IsoRPG engine (PyRay), particle simulator, Mandelbrot visualizer, wave generator, sol runner

## Architecture & Key Components

### C Projects (Raylib-based)
**Build**: CMake with FetchContent for dependencies. Run `cmake -S . -B build && cmake --build build`
- **main.c**: 6502 emulator with console UI, C64-style 16-color palette
- **cpu.c/cpu.h**: CPU emulation core (6502 instruction set, addressing modes)
- **debugger.c/debugger.h**: GUI debugger interface with memory viewer, disassembler
- **meowgui.h**: Custom GUI framework wrapper
- **icon_generator.c**: Utility to generate `.ico` assets

**Key Pattern**: State machine in main.c for UI modes, Raylib for all rendering/input.

### Python Projects (PyRay-based)
**Build**: Direct execution via `python protoiso.py` or other entry points
- **protoiso.py** (IsoRPG Engine - main focus):
  - **IsoGame class**: Single monolithic game class managing world, entities, rendering
  - **World Generation**: Procedural biome chunks (temperate, desert, taiga, swamp) → grid maps
  - **Entity System**: Player, NPCs, objects, items stored as dicts in maps/objects/npcs/items
  - **Coordinate System**: Isometric projection (grid coords ↔ screen coords via `utils.iso_to_screen/screen_to_iso`)
  - **Rendering**: Immediate-mode with `pyray` (rl.draw_*), dynamic texture creation for blocks
  - **Game State**: START_MENU, PAUSED, GAMEPLAY (state machine)

**Critical Patterns in protoiso.py**:
1. **Block Definition System**: 256 block types generated from 8 base materials with color variations & detail
2. **Asset Generation**: Procedurally create block/item textures in `generate_assets()` using `rl.gen_image_color()` and `rl.image_draw_*`
3. **Data Organization**: 
   - `self.maps[map_name]` = numpy array of block IDs
   - `self.objects[map_name]` = list of dicts with type/x/y
   - `self.npcs[map_name]` = list of dicts with name/x/y/hp/max_hp/type
   - `self.player` = dict with x/y/grid_x/grid_y/map/stats/inventory
4. **Drawing Order**: Screen → Iso conversion, then draw sorted by Y (depth)
5. **Input System**: Keys 1-5 for items, F for fishing, Q for spells, WASD/mouse for movement

- **utils.py**: Geometry utilities (iso projection, distance, collision, interpolation)

## Developer Workflows

### Running Python Projects
```bash
# IsoRPG
python protoiso.py

# Other scripts
python sol_runner.py
python mandelbrot.py
python generate_wav.py
```

### Building C Projects
```bash
# First configure
cmake -S . -B build

# Then build
cmake --build build

# Or use existing tasks
# "CMake: Build", "CMake: Configure", "CMake: Clean Rebuild"
```

### Key Tools
- **CMake**: Dependency management (Raylib via FetchContent)
- **vcpkg.json**: Package manager config (Windows)
- **PyRay**: Python bindings for Raylib

## Code Conventions

### Naming & Structure
- **C**: snake_case functions/vars, SCREAMING_CAPS constants, header guards in .h files
- **Python**: snake_case functions/vars, CamelCase classes, type hints minimal (legacy style)
- **Constants**: Defined at module top (both C and Python)

### Python-Specific Patterns
1. **Coordinate types**: Mix of float (world coords) and int (grid coords) - maintain distinction
2. **Dictionary-based entities**: All NPCs/objects are dicts, access via `obj['field']` not attributes
3. **Immediate-mode rendering**: Call Raylib draw functions directly each frame, no retained geometry
4. **Resource loading**: Images → textures via `rl.load_texture_from_image()`, must manage lifecycle

### Testing & Debugging
- **protoiso.py**: Press `B` toggle bounding box overlay (green=safe, red=collision)
- **C debugger**: Built-in GUI shows CPU state, memory, execution trace
- **No automated tests**: Manual testing only

## Common Integration Points

### Data Persistence
- **savegame.json**: Game state snapshots (player/inventory/world)
- **presets.json**: Configuration for simulations (particle system, wave gen)

### External Dependencies
- **Raylib** (C): Graphics, input, audio - extensively wrapped in C and PyRay
- **NumPy** (Python): Used for efficient grid/map operations
- **PyRay**: Python wrapper around Raylib C library

### Inter-Project Communication
- Mostly isolated; some shared patterns:
  - Color definitions (rl.Color tuples)
  - Isometric math (reusable in other projects)
  - State machine pattern for game loops

## Critical Implementation Details

### IsoRPG World Data Flow
1. **Generation**: `init_game_world()` → creates biome chunks → fills numpy maps with block IDs
2. **Entities**: Procedurally spawn objects/NPCs based on block type (trees in grass, rocks in sand)
3. **Rendering**: Each frame iterate entities, convert grid → screen, sort by Y, draw with offsets
4. **Collision**: Check `block_definitions[block_id]['walkable']` before movement

### Common Bugs to Avoid
- **Coordinate mismatch**: Screen vs grid coords - always convert at boundary (input/rendering)
- **Texture leaks**: Unload via `rl.unload_texture()` when replacing, esp. in `_create_block_texture()`
- **Dictionary access**: Entities are dicts - use `obj.get('field', default)` for optional fields
- **Occupied tracking**: World gen tracks occupied cells to prevent object overlap at spawn

## When Adding Features
- **Python (PyRay)**: Add to `IsoGame` class, update `_update_gameplay()` for logic, add draw calls to rendering section
- **C (Raylib)**: Add state handling in main.c, separate complex logic to new functions in cpu.c/debugger.c
- **Assets**: Generate procedurally in `generate_assets()` or load from `Assets/` folder
- **Persistence**: Add fields to savegame.json structure and load/save logic
