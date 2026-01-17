# Project Meow

This repository contains a collection of game prototypes and experiments built with Raylib, utilizing both Python (`pyray`) and C.

## Files Overview

### `sol_runner.py`
A 3D space exploration and combat game.
- **Features**: Space flight, combat, trading, planetary docking, and hyperspace travel.
- **Tech**: Uses Raylib 3D camera, mesh generation, and `google.generativeai` for dynamic text generation.

### `protoiso.py`
An isometric RPG engine prototype.
- **Features**: Tile-based world, inventory system, crafting, day/night cycle, weather, and NPCs.
- **Tech**: Isometric projection math (from `utils.py`), 2D rendering with depth sorting.

### `praticalsys.py`
A complex particle system and visualizer.
- **Features**: Various emitter modes (Fire, Galaxy, Rain, etc.), audio visualization, and shader effects (Bloom, Shockwave).
- **Tech**: Custom shaders, render textures, and audio stream analysis.

### `mandelbrot.py`
A real-time Mandelbrot set renderer.
- **Features**: Zooming, panning, and different color palettes.
- **Tech**: GLSL shaders for GPU-accelerated fractal rendering.

### `utils.py`
Shared utility functions.
- Contains math helpers for isometric projection (`iso_to_screen`, `screen_to_iso`), collision detection, and vector math.

### `generate_wav.py`
A utility script to procedurally generate sound assets.
- Generates WAV files for sound effects (explosions, UI blips) and simple music loops.

### `main.c` (6502 Emulator)
A functional 6502 emulator with a graphical debugger.
- **Features**: Step-through debugging, memory inspection, disassembly, and a simple assembler.
- **Tech**: Written in C using Raylib for the UI.

### `rom_generator.c`
A helper utility to create 6502 ROM binaries.
- **Features**: Generates `rom.bin` containing a visual pattern program to test the emulator.

### `TODO.md`
A list of planned features and ideas for the project, including suggestions for `protoiso.py` and `main.c`.

## Setup
### Python
Ensure you have the required dependencies installed:
```bash
pip install raylib numpy google-generativeai psutil
```