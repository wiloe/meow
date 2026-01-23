# Project Meow

This repository contains a collection of game prototypes and experiments built with Raylib, utilizing both Python (`pyray`) and C.

## Directory Structure

### `emulator_6502/`
A functional 6502 emulator with a graphical debugger.
- **Languages**: C
- **Key Files**: `main.c`, `cpu.c`, `debugger.c`, `rom_generator.c`
- **Features**: Step-through debugging, memory inspection, disassembly, and a simple assembler.
- **Build**: Contains `CMakeLists.txt` and `Makefile`.

### `iso_rpg/`
An isometric RPG engine prototype.
- **Languages**: Python
- **Key Files**: `protoiso.py`, `utils.py`, `quest_system.py`, `ecs.py`
- **Features**: Tile-based world, inventory system, crafting, day/night cycle, weather, and NPCs.

### `space_sim/`
A 3D space exploration and combat game.
- **Languages**: Python
- **Key Files**: `sol_runner.py`
- **Features**: Space flight, combat, trading, planetary docking, and hyperspace travel.

### `particles/`
A complex particle system and visualizer.
- **Languages**: Python, GLSL
- **Key Files**: `particle_sys.py`, `bloom.fs`, `shockwave.fs`
- **Features**: Various emitter modes (Fire, Galaxy, Rain, etc.), audio visualization, and shader effects.

### `fractals/`
A real-time Mandelbrot set renderer.
- **Languages**: Python
- **Key Files**: `mandelbrot.py`
- **Features**: Zooming, panning, and different color palettes using GLSL shaders.

### `tools/`
Utility scripts and tools.
- **`generate_wav.py`**: Procedurally generate WAV files for sound effects.
- **`icon_generator.c`**: Utility to generate icon data.

### `assets/`
Shared assets for the projects.
- Contains `.wav` files, images, and binary ROMs.

## Setup

### Python Projects
Ensure you have the required dependencies installed:
```bash
pip install raylib numpy google-generativeai psutil
```
To run a project, navigate to its directory and run the main script (e.g., `python protoiso.py`).

### C Projects
Navigate to `emulator_6502` and use CMake or Make to build:
```bash
cd emulator_6502
cmake -S . -B build
cmake --build build
```
