import pyray as rl
import numpy
import math
import os
import json
import ctypes
import datetime
try:
    import psutil
except ImportError:
    psutil = None
from enum import Enum
from dataclasses import dataclass
from typing import List, Tuple, Deque
from collections import deque

# --- POLYFILLS ---
if not hasattr(rl, 'Color'):
    class Color(ctypes.Structure):
        _fields_ = [("r", ctypes.c_ubyte), ("g", ctypes.c_ubyte), ("b", ctypes.c_ubyte), ("a", ctypes.c_ubyte)]
    rl.Color = Color

if not hasattr(rl, 'Rectangle'):
    class Rectangle(ctypes.Structure):
        _fields_ = [("x", ctypes.c_float), ("y", ctypes.c_float), ("width", ctypes.c_float), ("height", ctypes.c_float)]
    rl.Rectangle = Rectangle

if not hasattr(rl, 'Vector2'):
    class Vector2(ctypes.Structure):
        _fields_ = [("x", ctypes.c_float), ("y", ctypes.c_float)]
    rl.Vector2 = Vector2

# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
MAX_PARTICLES = 2500
PARTICLE_LIFETIME = 5.0  # seconds
GRAVITY = 9.81  # m/s^2
WIND = (30.0, 0.0)
FRICTION = 0.5
PARTICLE_SIZE = 5.0
TRAIL_LENGTH = 10
EMIT_RATE = 100  # particles per second
EMIT_POSITION = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
# Particle States
class ParticleState(Enum):
    ALIVE = 1
    DEAD = 0    
# Emitter Modes
class EmitterMode(Enum):
    CENTER = 0
    QUANTUM = 1
    PREDATOR = 2
    RAIN = 3
    MOUSE = 4
    GRAVITY_WELL = 5
    BLACK_HOLE = 6
    FIREWORKS = 7
    SNOW = 8
    BUBBLES = 9
    CONFETTI = 10
    GALAXY = 11
    VISUALIZER = 12
    SANDBOX = 13
    PORTAL = 14
    GRAVITY_GUN = 15
    FLUID = 16
    HEAT_MAP = 17
    SHAPE = 18
    FORCE_FIELD = 19
    LIFE = 20
    ORBIT = 21
    SWARM = 22
# Particle Dataclass
@dataclass
class Particle:
    position: Tuple[float, float]
    velocity: Tuple[float, float]
    acceleration: Tuple[float, float]
    trail: List[Tuple[float, float]]
    color: Tuple[int, int, int]
    lifetime: float
    state: ParticleState    
    rotation: float
    angular_velocity: float
    is_rocket: bool
    initial_lifetime: float
@dataclass
class Ripple:
    position: Tuple[float, float]
    radius: float
    speed: float
    lifetime: float
    max_lifetime: float
    color: Tuple[int, int, int]
# Particle System Class
class ParticleSystem:
    def __init__(self):
        self.particles: Deque[Particle] = deque(maxlen=MAX_PARTICLES)
        self.ripples: List[Ripple] = []
        self.emit_timer = 0.0    
        self.wind = WIND
        self.color_mode = 0 # Acts as palette index
        self.palettes = [
            ("Random", []),
            ("Fire", [(255, 50, 0), (255, 100, 0), (255, 200, 0), (200, 50, 0)]),
            ("Ice", [(0, 50, 255), (0, 150, 255), (200, 255, 255), (230, 230, 255)]),
            ("Nature", [(34, 139, 34), (107, 142, 35), (139, 69, 19), (218, 165, 32)]),
            ("Neon", [(255, 0, 255), (0, 255, 255), (255, 255, 0), (57, 255, 20)]),
            ("Pastel", [(255, 179, 186), (255, 223, 186), (255, 255, 186), (186, 255, 201), (186, 225, 255)])
        ]
        self.gravity = GRAVITY
        self.repulsion_enabled = False
        self.emitter_mode = EmitterMode.CENTER
        self.mouse_attractor_enabled = False
        self.blackhole_collision = True
        self.vortex_enabled = False
        self.time_scale = 1.0
        self.slow_motion = False
        self.prev_time_scale = 1.0
        self.trail_length = TRAIL_LENGTH
        self.walls: List[rl.Rectangle] = []
        self.portals = [
            {'rect': rl.Rectangle(100, 150, 20, 300), 'color': rl.ORANGE},
            {'rect': rl.Rectangle(SCREEN_WIDTH - 120, 150, 20, 300), 'color': rl.BLUE}
        ]
        # Generate a glow texture
        img = rl.gen_image_gradient_square(32, 32, 0.0, rl.WHITE, rl.Color(255, 255, 255, 0))
        self.texture = rl.load_texture_from_image(img)
        rl.unload_image(img)
        # Generate background texture
        bg_img = rl.gen_image_checked(SCREEN_WIDTH, SCREEN_HEIGHT, 40, 40, rl.Color(20, 20, 20, 255), rl.Color(10, 10, 10, 255))
        self.bg_texture = rl.load_texture_from_image(bg_img)
        rl.unload_image(bg_img)
        sound_path = os.path.join(os.path.dirname(__file__), "../assets/burst.wav")
        self.burst_sound = rl.load_sound(sound_path.encode('utf-8'))
        fuse_path = os.path.join(os.path.dirname(__file__), "../assets/fuse.wav")
        self.fuse_sound = rl.load_sound(fuse_path.encode('utf-8'))
        pop_path = os.path.join(os.path.dirname(__file__), "../assets/pop.wav")
        self.pop_sound = rl.load_sound(pop_path.encode('utf-8'))
        
        # Music & Analysis
        music_path = os.path.join(os.path.dirname(__file__), "../assets/music.wav")
        self.music = None
        self.wave_data = None
        self.wave_sample_rate = 44100
        if os.path.exists(music_path):
            self.music = rl.load_music_stream(music_path.encode('utf-8'))
            self.music.looping = True
            # Load wave for analysis
            wave = rl.load_wave(music_path.encode('utf-8'))
            self.wave_sample_rate = wave.sampleRate
            if wave.data:
                sample_count = wave.frameCount * wave.channels
                # Cast void* to short* (assuming 16-bit audio from generate_wav.py)
                data_addr = int(rl.ffi.cast("uintptr_t", wave.data))
                data_ptr = ctypes.cast(ctypes.c_void_p(data_addr), ctypes.POINTER(ctypes.c_short))
                # Create numpy array (copy) and normalize
                raw_data = numpy.ctypeslib.as_array(data_ptr, shape=(sample_count,))
                self.wave_data = raw_data.astype(numpy.float32) / 32768.0
            rl.unload_wave(wave)
        
        # Shader & Render Target
        self.render_target = rl.load_render_texture(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.render_target2 = rl.load_render_texture(SCREEN_WIDTH, SCREEN_HEIGHT)
        
        # Create default vertex shader to avoid passing NULL
        vs_path = os.path.join(os.path.dirname(__file__), "default.vs")
        if not os.path.exists(vs_path):
            with open(vs_path, 'w') as f:
                f.write("#version 330\nin vec3 vertexPosition;\nin vec2 vertexTexCoord;\nin vec4 vertexColor;\nout vec2 fragTexCoord;\nout vec4 fragColor;\nuniform mat4 mvp;\nvoid main() {\n    fragTexCoord = vertexTexCoord;\n    fragColor = vertexColor;\n    gl_Position = mvp * vec4(vertexPosition, 1.0);\n}")
        
        self.shader = rl.load_shader(vs_path.encode('utf-8'), os.path.join(os.path.dirname(__file__), "shockwave.fs").encode('utf-8'))
        self.sw_loc_center = rl.get_shader_location(self.shader, "center".encode('utf-8'))
        self.sw_loc_radius = rl.get_shader_location(self.shader, "radius".encode('utf-8'))
        self.sw_loc_force = rl.get_shader_location(self.shader, "force".encode('utf-8'))
        self.sw_loc_aspect = rl.get_shader_location(self.shader, "aspectRatio".encode('utf-8'))
        
        self.bloom_shader = rl.load_shader(vs_path.encode('utf-8'), os.path.join(os.path.dirname(__file__), "bloom.fs").encode('utf-8'))
        self.bloom_loc_size = rl.get_shader_location(self.bloom_shader, "renderSize".encode('utf-8'))
        
        self.sw_active = False
        self.sw_time = 0.0
        self.sw_center = [0.5, 0.5]
        self.background_enabled = True
        self.background_opacity = 1.0
        self.reverse_time = False
        self.life_grid = set()
        self.life_step_timer = 0.0
        self.life_cell_size = 10
    def set_max_count(self, count: int):
        if count != self.particles.maxlen:
            self.particles = deque(self.particles, maxlen=count)
    def emit(self, dt: float):
        self.emit_timer += dt
        num_to_emit = int(self.emit_timer * EMIT_RATE)
        self.emit_timer -= num_to_emit / EMIT_RATE
        for _ in range(num_to_emit):
            self.particles.append(self.create_particle())
    def burst(self, pos: Tuple[float, float], count: int):
        if self.emitter_mode == EmitterMode.FIREWORKS:
            rl.play_sound(self.fuse_sound)
        else:
            pitch = 0.5 + (len(self.particles) / self.particles.maxlen)
            rl.set_sound_pitch(self.burst_sound, pitch)
            rl.play_sound(self.burst_sound)
        
        self.sw_active = True
        self.sw_time = 0.0
        self.sw_center = [pos[0] / rl.get_screen_width(), pos[1] / rl.get_screen_height()]
            
        self.ripples.append(Ripple(
            position=pos,
            radius=10.0,
            speed=600.0,
            lifetime=0.4,
            max_lifetime=0.4,
            color=(150, 255, 255)
        ))
        for _ in range(count):
            self.particles.append(self.create_particle(pos))
    def create_particle(self, pos: Tuple[float, float] = None) -> Particle:
        # Determine properties based on Emitter Mode
        velocity = (0.0, 0.0)
        color = (255, 255, 255)
        lifetime = PARTICLE_LIFETIME
        acceleration = (0, self.gravity)
        is_rocket = False
        ang_vel = numpy.random.uniform(-180, 180)
        
        match self.emitter_mode:
            case EmitterMode.QUANTUM:
                if pos is None:
                    pos = (numpy.random.uniform(0, rl.get_screen_width()), numpy.random.uniform(0, rl.get_screen_height()))
                velocity = (numpy.random.uniform(-20, 20), numpy.random.uniform(-20, 20))
                color = (int(numpy.random.randint(0, 100)), int(numpy.random.randint(200, 256)), int(numpy.random.randint(200, 256)))
                lifetime = numpy.random.uniform(0.5, 1.5)
            case EmitterMode.PREDATOR:
                if pos is None:
                    pos = (numpy.random.uniform(0, rl.get_screen_width()), numpy.random.uniform(0, rl.get_screen_height()))
                angle = numpy.random.uniform(0, 2 * math.pi)
                speed = numpy.random.uniform(20, 50)
                velocity = (math.cos(angle) * speed, math.sin(angle) * speed)
                team = numpy.random.randint(0, 3)
                if team == 0: color = (255, 50, 50)   # Red Team
                elif team == 1: color = (50, 255, 50) # Green Team
                else: color = (50, 50, 255)           # Blue Team
            case EmitterMode.RAIN:
                if pos is None:
                    pos = (numpy.random.uniform(0, rl.get_screen_width()), -10)
                velocity = (0, numpy.random.uniform(100, 300))
                color = (150, 150, 255)
            case EmitterMode.SNOW:
                if pos is None:
                    pos = (numpy.random.uniform(0, rl.get_screen_width()), -10)
                velocity = (numpy.random.uniform(-10, 10), numpy.random.uniform(20, 60))
                color = (240, 240, 255)
                acceleration = (0, 2.0) # Low gravity for snow
                lifetime = numpy.random.uniform(15.0, 25.0)
            case EmitterMode.FIREWORKS:
                is_rocket = True
                if pos is None:
                    pos = (numpy.random.uniform(0, rl.get_screen_width()), rl.get_screen_height())
                velocity = (numpy.random.uniform(-30, 30), numpy.random.uniform(-500, -800))
                color = (int(numpy.random.randint(150, 256)), int(numpy.random.randint(150, 256)), int(numpy.random.randint(150, 256)))
                lifetime = numpy.random.uniform(0.8, 1.2)
            case EmitterMode.BUBBLES:
                if pos is None:
                    pos = (numpy.random.uniform(0, rl.get_screen_width()), rl.get_screen_height() + 10)
                velocity = (numpy.random.uniform(-20, 20), numpy.random.uniform(-100, -200))
                color = (200, 255, 255)
                acceleration = (0, -10.0) # Float up
                lifetime = numpy.random.uniform(2.0, 5.0)
            case EmitterMode.CONFETTI:
                if pos is None:
                    pos = (numpy.random.uniform(0, rl.get_screen_width()), -10)
                velocity = (numpy.random.uniform(-20, 20), numpy.random.uniform(100, 200))
                color = (int(numpy.random.randint(50, 256)), int(numpy.random.randint(50, 256)), int(numpy.random.randint(50, 256)))
                lifetime = numpy.random.uniform(3.0, 5.0)
                ang_vel = numpy.random.uniform(-400, 400)
            case EmitterMode.GALAXY:
                if pos is None:
                    cx, cy = rl.get_screen_width() // 2, rl.get_screen_height() // 2
                    arms = 3
                    arm_offset = (numpy.random.randint(0, arms) / arms) * 2 * math.pi
                    r = numpy.random.uniform(20, 350)
                    twist = r * 0.03
                    angle = arm_offset + twist + numpy.random.normal(0, 0.2)
                    pos = (cx + math.cos(angle) * r, cy + math.sin(angle) * r)
                
                cx, cy = rl.get_screen_width() // 2, rl.get_screen_height() // 2
                dx = pos[0] - cx
                dy = pos[1] - cy
                dist = math.sqrt(dx*dx + dy*dy)
                speed = 80.0
                if dist > 0:
                    velocity = (-dy/dist * speed, dx/dist * speed)
                
                color = (int(numpy.random.randint(100, 180)), int(numpy.random.randint(0, 80)), int(numpy.random.randint(180, 255)))
                acceleration = (0, 0)
                lifetime = numpy.random.uniform(4.0, 8.0)
            case EmitterMode.VISUALIZER:
                if pos is None:
                    pos = (rl.get_screen_width() // 2, rl.get_screen_height() // 2)
                angle = numpy.random.uniform(0, 2 * math.pi)
                speed = numpy.random.uniform(100, 300)
                velocity = (math.cos(angle) * speed, math.sin(angle) * speed)
                color = (int(numpy.random.randint(0, 100)), int(numpy.random.randint(200, 255)), 255)
                lifetime = numpy.random.uniform(0.5, 1.0)
            case EmitterMode.PORTAL:
                if pos is None:
                    pos = (rl.get_screen_width() // 2, rl.get_screen_height() // 2)
                angle = numpy.random.uniform(0, 2 * math.pi)
                speed = numpy.random.uniform(100, 300)
                velocity = (math.cos(angle) * speed, math.sin(angle) * speed)
                color = (int(numpy.random.randint(100, 255)), int(numpy.random.randint(100, 255)), int(numpy.random.randint(100, 255)))
                lifetime = numpy.random.uniform(2.0, 4.0)
            case EmitterMode.GRAVITY_GUN:
                if pos is None:
                    pos = (rl.get_screen_width() // 2, rl.get_screen_height() // 2)
                angle = numpy.random.uniform(0, 2 * math.pi)
                speed = numpy.random.uniform(50, 150)
                velocity = (math.cos(angle) * speed, math.sin(angle) * speed)
                color = (50, 255, 50)
                lifetime = numpy.random.uniform(10.0, 20.0)
            case EmitterMode.FLUID:
                if pos is None:
                    pos = (rl.get_screen_width() // 2, 50)
                velocity = (numpy.random.uniform(-20, 20), numpy.random.uniform(50, 150))
                color = (0, 150, 255)
                lifetime = numpy.random.uniform(15.0, 25.0)
            case EmitterMode.HEAT_MAP:
                if pos is None:
                    pos = (rl.get_screen_width() // 2, rl.get_screen_height() // 2)
                angle = numpy.random.uniform(0, 2 * math.pi)
                speed = numpy.random.uniform(50, 200)
                velocity = (math.cos(angle) * speed, math.sin(angle) * speed)
                color = (0, 0, 255)
                lifetime = numpy.random.uniform(2.0, 4.0)
            case EmitterMode.SHAPE:
                if pos is None:
                    cx, cy = rl.get_screen_width() // 2, rl.get_screen_height() // 2
                else:
                    cx, cy = pos
                
                if numpy.random.random() < 0.5:
                    # Heart Shape
                    t = numpy.random.uniform(0, 2 * math.pi)
                    scale = 10.0
                    x = 16 * math.sin(t)**3
                    y = -(13 * math.cos(t) - 5 * math.cos(2*t) - 2 * math.cos(3*t) - math.cos(4*t))
                    pos = (cx + x * scale, cy + y * scale)
                    color = (255, 105, 180) # Hot Pink
                else:
                    # Star Shape
                    t = numpy.random.uniform(0, 2 * math.pi)
                    r = 100 * (1 + 0.5 * math.cos(5 * t))
                    x = r * math.cos(t - math.pi/2)
                    y = r * math.sin(t - math.pi/2)
                    pos = (cx + x, cy + y)
                    color = (255, 215, 0) # Gold
                
                velocity = (numpy.random.uniform(-10, 10), numpy.random.uniform(-10, 10))
                lifetime = numpy.random.uniform(2.0, 3.0)
            case EmitterMode.FORCE_FIELD:
                if pos is None:
                    if numpy.random.random() < 0.5:
                        pos = (numpy.random.choice([0, rl.get_screen_width()]), numpy.random.uniform(0, rl.get_screen_height()))
                    else:
                        pos = (numpy.random.uniform(0, rl.get_screen_width()), numpy.random.choice([0, rl.get_screen_height()]))
                
                cx, cy = rl.get_screen_width() // 2, rl.get_screen_height() // 2
                dx = cx - pos[0]
                dy = cy - pos[1]
                dist = math.sqrt(dx*dx + dy*dy)
                speed = numpy.random.uniform(100, 200)
                if dist > 0:
                    velocity = (dx/dist * speed, dy/dist * speed)
                else:
                    velocity = (0, 0)
                
                color = (255, 100, 100)
                lifetime = numpy.random.uniform(4.0, 6.0)
            case EmitterMode.ORBIT:
                cx, cy = rl.get_screen_width() // 2, rl.get_screen_height() // 2
                if pos is None:
                    angle = numpy.random.uniform(0, 2 * math.pi)
                    radius = numpy.random.uniform(50, 300)
                    pos = (cx + math.cos(angle) * radius, cy + math.sin(angle) * radius)
                
                dx = pos[0] - cx
                dy = pos[1] - cy
                dist = math.sqrt(dx*dx + dy*dy)
                speed = 200.0
                if dist > 0:
                    velocity = (-dy/dist * speed, dx/dist * speed)
                else:
                    velocity = (0, 0)
                
                color = (0, 190, 255)
                lifetime = numpy.random.uniform(5.0, 10.0)
                acceleration = (0, 0)
            case EmitterMode.SWARM:
                if pos is None:
                    pos = (numpy.random.uniform(0, rl.get_screen_width()), numpy.random.uniform(0, rl.get_screen_height()))
                angle = numpy.random.uniform(0, 2 * math.pi)
                speed = numpy.random.uniform(100, 200)
                velocity = (math.cos(angle) * speed, math.sin(angle) * speed)
                color = (255, 215, 0) # Gold
                lifetime = numpy.random.uniform(5.0, 10.0)
            case _:
                # Default / Center
                if pos is None:
                    if self.emitter_mode == EmitterMode.BLACK_HOLE:
                        pos = (numpy.random.uniform(0, rl.get_screen_width()), numpy.random.uniform(0, rl.get_screen_height()))
                    elif self.emitter_mode == EmitterMode.MOUSE:
                        m = rl.get_mouse_position()
                        pos = (m.x, m.y)
                    else:
                        pos = (rl.get_screen_width() // 2, rl.get_screen_height() // 2)
                angle = numpy.random.uniform(0, 2 * math.pi)
                speed = numpy.random.uniform(50, 150)
                velocity = (math.cos(angle) * speed, math.sin(angle) * speed)
                
                # Apply Color Palette
                p_name, p_colors = self.palettes[self.color_mode]
                if p_name == "Random":
                    color = (int(numpy.random.randint(50, 256)), int(numpy.random.randint(50, 256)), int(numpy.random.randint(50, 256)))
                else:
                    base = p_colors[numpy.random.randint(0, len(p_colors))]
                    color = (
                        max(0, min(255, base[0] + numpy.random.randint(-20, 20))),
                        max(0, min(255, base[1] + numpy.random.randint(-20, 20))),
                        max(0, min(255, base[2] + numpy.random.randint(-20, 20)))
                    )

        return Particle(
            position=pos,
            velocity=velocity,
            acceleration=acceleration,
            trail=[],
            color=color,
            lifetime=lifetime,
            state=ParticleState.ALIVE,
            rotation=numpy.random.uniform(0, 360),
            angular_velocity=ang_vel,
            is_rocket=is_rocket,
            initial_lifetime=lifetime
        )       
    def update(self, dt: float):
        if rl.is_window_resized():
            w = rl.get_screen_width()
            h = rl.get_screen_height()
            old_w = self.render_target.texture.width
            old_h = self.render_target.texture.height
            
            if w > 0 and h > 0:
                # Shift entities to keep them centered relative to the new window size
                dx = (w - old_w) / 2.0
                dy = (h - old_h) / 2.0
                
                for p in self.particles:
                    p.position = (p.position[0] + dx, p.position[1] + dy)
                    p.trail = [(t[0] + dx, t[1] + dy) for t in p.trail]
                
                for r in self.ripples:
                    r.position = (r.position[0] + dx, r.position[1] + dy)
                    
                for wall in self.walls:
                    wall.x += dx
                    wall.y += dy
                
                if self.sw_active:
                    self.sw_center[0] = (self.sw_center[0] * old_w + dx) / w
                    self.sw_center[1] = (self.sw_center[1] * old_h + dy) / h

                rl.unload_render_texture(self.render_target)
                rl.unload_render_texture(self.render_target2)
                self.render_target = rl.load_render_texture(w, h)
                self.render_target2 = rl.load_render_texture(w, h)
                # Keep right portal anchored to right side
                self.portals[1]['rect'].x = w - 120
        
        if self.reverse_time:
            for p in self.particles:
                if p.state == ParticleState.ALIVE and len(p.trail) > 0:
                    p.position = p.trail.pop()
                    p.lifetime = min(p.initial_lifetime, p.lifetime + dt)
            
            for r in list(self.ripples):
                r.radius -= r.speed * dt
                r.lifetime += dt
                if r.radius < 0:
                    self.ripples.remove(r)
            return
        
        # Life Mode Logic
        if self.emitter_mode == EmitterMode.LIFE:
            self.life_step_timer += dt
            
            # Interaction: Draw cells
            if rl.is_mouse_button_down(rl.MOUSE_LEFT_BUTTON):
                mp = rl.get_mouse_position()
                gx = int(mp.x / self.life_cell_size)
                gy = int(mp.y / self.life_cell_size)
                self.life_grid.add((gx, gy))
                self._sync_life_particles()
            
            # Auto-init if empty
            if not self.life_grid and len(self.particles) == 0:
                cols = SCREEN_WIDTH // self.life_cell_size
                rows = SCREEN_HEIGHT // self.life_cell_size
                for _ in range(int(cols * rows * 0.15)):
                    self.life_grid.add((numpy.random.randint(0, cols), numpy.random.randint(0, rows)))
                self._sync_life_particles()

            if self.life_step_timer > 0.1:
                self.life_step_timer = 0.0
                new_grid = set()
                candidates = set()
                for x, y in self.life_grid:
                    for dx in (-1, 0, 1):
                        for dy in (-1, 0, 1):
                            candidates.add((x + dx, y + dy))
                
                for x, y in candidates:
                    neighbors = 0
                    for dx in (-1, 0, 1):
                        for dy in (-1, 0, 1):
                            if dx == 0 and dy == 0: continue
                            if (x + dx, y + dy) in self.life_grid:
                                neighbors += 1
                    
                    if (x, y) in self.life_grid:
                        if neighbors == 2 or neighbors == 3:
                            new_grid.add((x, y))
                    else:
                        if neighbors == 3:
                            new_grid.add((x, y))
                self.life_grid = new_grid
                self._sync_life_particles()
        else:
            self.emit(dt)
            if self.life_grid: self.life_grid.clear()

        mp = rl.get_mouse_position()
        
        for ripple in list(self.ripples):
            ripple.radius += ripple.speed * dt
            ripple.lifetime -= dt
            if ripple.lifetime <= 0:
                self.ripples.remove(ripple)
        
        if self.sw_active:
            self.sw_time += dt
            if self.sw_time > 2.0: self.sw_active = False
        
        # Audio Visualization Logic
        bass_energy = 0.0
        if self.emitter_mode == EmitterMode.VISUALIZER and self.music:
            rl.update_music_stream(self.music)
            if not rl.is_music_stream_playing(self.music):
                rl.play_music_stream(self.music)
            
            if self.wave_data is not None:
                # Get current position in samples
                pos = rl.get_music_time_played(self.music)
                idx = int(pos * self.wave_sample_rate)
                window_size = 1024
                
                if idx + window_size < len(self.wave_data):
                    chunk = self.wave_data[idx:idx+window_size]
                    # FFT Analysis
                    fft_vals = numpy.abs(numpy.fft.rfft(chunk))
                    # Bass (Low Freqs)
                    bass_energy = numpy.mean(fft_vals[:15])
                    # Treble (High Freqs)
                    treble_energy = numpy.mean(fft_vals[50:200])
                    
                    # Beat Detection (Threshold)
                    if bass_energy > 5.0: # Threshold depends on normalization
                        self.burst((rl.get_screen_width()/2, rl.get_screen_height()/2), int(bass_energy * 2))
                        self.sw_active = True
                        self.sw_time = 0.0
                        self.sw_center = [0.5, 0.5]
        elif self.music and rl.is_music_stream_playing(self.music):
            rl.stop_music_stream(self.music)

        # Build spatial grid for repulsion
        grid = {}
        cell_size = 25.0
        grid_stride = 1000
        if self.repulsion_enabled or self.emitter_mode == EmitterMode.PREDATOR or self.emitter_mode == EmitterMode.FLUID or self.emitter_mode == EmitterMode.BLACK_HOLE or self.emitter_mode == EmitterMode.SWARM:
            for p in self.particles:
                if p.state == ParticleState.ALIVE:
                    # Spatial Hash using integer keys (with offset for negative coords) to avoid tuple allocation
                    ix = int((p.position[0] + 5000) / cell_size)
                    iy = int((p.position[1] + 5000) / cell_size)
                    key = ix + iy * grid_stride
                    if key not in grid: grid[key] = []
                    grid[key].append(p)

        # Process particles: update alive ones, remove dead ones
        for _ in range(len(self.particles)):
            particle = self.particles.popleft()
            if particle.state == ParticleState.DEAD:
                continue
            particle.rotation += particle.angular_velocity * dt
            particle.lifetime -= dt
            if particle.lifetime <= 0:
                particle.state = ParticleState.DEAD
                
                if particle.is_rocket:
                    rl.set_sound_pitch(self.pop_sound, 0.8 + numpy.random.uniform(-0.2, 0.2))
                    rl.play_sound(self.pop_sound)
                    for _ in range(30):
                        angle = numpy.random.uniform(0, 2 * math.pi)
                        speed = numpy.random.uniform(50, 250)
                        vel = (math.cos(angle) * speed, math.sin(angle) * speed)
                        sub_color = (int(numpy.random.randint(50, 256)), int(numpy.random.randint(50, 256)), int(numpy.random.randint(50, 256)))
                        sub_lifetime = numpy.random.uniform(0.3, 0.8)
                        p = Particle(
                            position=particle.position,
                            velocity=vel,
                            acceleration=(0, self.gravity),
                            trail=[],
                            color=sub_color,
                            lifetime=sub_lifetime,
                            state=ParticleState.ALIVE,
                            rotation=0,
                            angular_velocity=0,
                            is_rocket=False,
                            initial_lifetime=sub_lifetime
                        )
                        self.particles.append(p)
                elif self.emitter_mode == EmitterMode.BUBBLES:
                    self.ripples.append(Ripple(
                        position=particle.position,
                        radius=5.0,
                        speed=200.0,
                        lifetime=0.2,
                        max_lifetime=0.2,
                        color=(200, 255, 255)
                    ))
                    rl.set_sound_pitch(self.burst_sound, numpy.random.uniform(2.0, 3.0))
                    rl.play_sound(self.burst_sound)
                continue            
            
            particle.trail.append(particle.position)
            while len(particle.trail) > self.trail_length:
                particle.trail.pop(0)

            # Calculate Repulsion
            repel_ax, repel_ay = 0.0, 0.0
            swarm_neighbors = 0
            swarm_avg_pos = [0.0, 0.0]
            swarm_avg_vel = [0.0, 0.0]
            if self.repulsion_enabled or self.emitter_mode == EmitterMode.PREDATOR or self.emitter_mode == EmitterMode.FLUID or self.emitter_mode == EmitterMode.BLACK_HOLE or self.emitter_mode == EmitterMode.SWARM:
                ix = int((particle.position[0] + 5000) / cell_size)
                iy = int((particle.position[1] + 5000) / cell_size)
                
                for dy in (-1, 0, 1):
                    y_offset = (iy + dy) * grid_stride
                    for dx in (-1, 0, 1):
                        neighbor_key = (ix + dx) + y_offset
                        if neighbor_key in grid:
                            for other in grid[neighbor_key]:
                                if other is particle: continue
                                dx_val = particle.position[0] - other.position[0]
                                dy_val = particle.position[1] - other.position[1]
                                dist_sq = dx_val*dx_val + dy_val*dy_val
                                
                                # Predator Logic
                                if self.emitter_mode == EmitterMode.PREDATOR and other.state == ParticleState.ALIVE:
                                    if particle.color != other.color:
                                        # Attract different colors
                                        if dist_sq > 1.0:
                                            repel_ax -= (dx_val/dist_sq) * 5000.0
                                            repel_ay -= (dy_val/dist_sq) * 5000.0
                                        # Consume if touching
                                        if dist_sq < PARTICLE_SIZE * PARTICLE_SIZE * 4:
                                            particle.lifetime += other.lifetime * 0.5
                                            other.state = ParticleState.DEAD
                                            continue
                                
                                # Fluid Logic
                                if self.emitter_mode == EmitterMode.FLUID:
                                    interaction_radius = 25.0
                                    if 0.01 < dist_sq < interaction_radius*interaction_radius:
                                        dist = math.sqrt(dist_sq)
                                        q = 1.0 - (dist / interaction_radius)
                                        
                                        # Pressure (Repulsion)
                                        pressure = 1500.0 * q * q
                                        repel_ax += (dx_val/dist) * pressure
                                        repel_ay += (dy_val/dist) * pressure
                                        
                                        # Viscosity (Damping relative motion)
                                        rel_vx = other.velocity[0] - particle.velocity[0]
                                        rel_vy = other.velocity[1] - particle.velocity[1]
                                        visc_strength = 15.0 * q
                                        repel_ax += rel_vx * visc_strength
                                        repel_ay += rel_vy * visc_strength
                                    continue
                                
                                # Black Hole Collision Logic
                                if self.emitter_mode == EmitterMode.BLACK_HOLE and self.blackhole_collision and other.state == ParticleState.ALIVE:
                                    if dist_sq < 100.0: # Collision radius approx 10
                                        particle.state = ParticleState.DEAD
                                        other.state = ParticleState.DEAD
                                        
                                        # Spawn debris
                                        for _ in range(4):
                                            angle = numpy.random.uniform(0, 2 * math.pi)
                                            speed = numpy.random.uniform(50, 150)
                                            vel = (math.cos(angle) * speed, math.sin(angle) * speed)
                                            p = Particle(
                                                position=particle.position,
                                                velocity=vel,
                                                acceleration=(0, 0),
                                                trail=[],
                                                color=(255, 100, 255),
                                                lifetime=numpy.random.uniform(0.2, 0.5),
                                                state=ParticleState.ALIVE,
                                                rotation=0,
                                                angular_velocity=0,
                                                is_rocket=False,
                                                initial_lifetime=0.5
                                            )
                                            self.particles.append(p)
                                        continue
                                
                                # Swarm Logic
                                if self.emitter_mode == EmitterMode.SWARM:
                                    if dist_sq < 1600.0: # View radius 40
                                        swarm_neighbors += 1
                                        swarm_avg_pos[0] += other.position[0]
                                        swarm_avg_pos[1] += other.position[1]
                                        swarm_avg_vel[0] += other.velocity[0]
                                        swarm_avg_vel[1] += other.velocity[1]
                                        
                                        if dist_sq < 400.0: # Separation radius 20
                                            dist = math.sqrt(dist_sq)
                                            force = (20.0 - dist) * 15.0
                                            repel_ax += (dx_val/dist) * force
                                            repel_ay += (dy_val/dist) * force

                                if 0.1 < dist_sq < cell_size*cell_size:
                                    dist = math.sqrt(dist_sq)
                                    force = (1.0 - dist/cell_size) * 1000.0
                                    repel_ax += (dx_val/dist) * force
                                    repel_ay += (dy_val/dist) * force
            
            if self.emitter_mode == EmitterMode.SWARM and swarm_neighbors > 0:
                swarm_avg_pos[0] /= swarm_neighbors
                swarm_avg_pos[1] /= swarm_neighbors
                swarm_avg_vel[0] /= swarm_neighbors
                swarm_avg_vel[1] /= swarm_neighbors
                
                # Cohesion
                repel_ax += (swarm_avg_pos[0] - particle.position[0]) * 2.0
                repel_ay += (swarm_avg_pos[1] - particle.position[1]) * 2.0
                
                # Alignment
                repel_ax += (swarm_avg_vel[0] - particle.velocity[0]) * 0.5
                repel_ay += (swarm_avg_vel[1] - particle.velocity[1]) * 0.5
                
                # Center pull
                cx, cy = rl.get_screen_width() / 2, rl.get_screen_height() / 2
                repel_ax += (cx - particle.position[0]) * 0.5
                repel_ay += (cy - particle.position[1]) * 0.5

            # Calculate Vortex
            vortex_ax, vortex_ay = 0.0, 0.0
            if self.vortex_enabled:
                cx, cy = rl.get_screen_width() / 2, rl.get_screen_height() / 2
                dx = particle.position[0] - cx
                dy = particle.position[1] - cy
                dist_sq = dx*dx + dy*dy
                if dist_sq > 1.0:
                    dist = math.sqrt(dist_sq)
                    vortex_ax += (-dy / dist) * 1000.0 # Spin force
                    vortex_ay += (dx / dist) * 1000.0
                    vortex_ax -= (dx / dist) * 500.0   # Pull inward

            # Gravity Well Logic
            well_ax, well_ay = 0.0, 0.0
            if self.emitter_mode == EmitterMode.GRAVITY_WELL:
                dx = mp.x - particle.position[0]
                dy = mp.y - particle.position[1]
                dist_sq = dx*dx + dy*dy
                if dist_sq > 10.0:
                    dist = math.sqrt(dist_sq)
                    well_ax = (dx / dist) * 2000.0
                    well_ay = (dy / dist) * 2000.0
            elif self.emitter_mode == EmitterMode.BLACK_HOLE:
                cx, cy = rl.get_screen_width() / 2, rl.get_screen_height() / 2
                dx = cx - particle.position[0]
                dy = cy - particle.position[1]
                dist_sq = dx*dx + dy*dy
                
                if dist_sq < 900.0: # Destroy if within radius 30
                    particle.state = ParticleState.DEAD
                    continue
                    
                dist = math.sqrt(dist_sq)
                
                # Red Shift near Event Horizon
                if dist < 250.0:
                    c = particle.color
                    r = min(255, c[0] + 5)
                    g = max(0, c[1] - 5)
                    b = max(0, c[2] - 5)
                    particle.color = (r, g, b)

                well_ax = (dx / dist) * 5000.0
                well_ay = (dy / dist) * 5000.0
            elif self.emitter_mode == EmitterMode.VISUALIZER:
                # Particles dance to the music
                if bass_energy > 0:
                    # Push out on beat
                    well_ax = particle.velocity[0] * bass_energy * 0.05
                    well_ay = particle.velocity[1] * bass_energy * 0.05
            elif self.emitter_mode == EmitterMode.GALAXY:
                cx, cy = rl.get_screen_width() / 2, rl.get_screen_height() / 2
                dx = cx - particle.position[0]
                dy = cy - particle.position[1]
                dist_sq = dx*dx + dy*dy
                if dist_sq > 1.0:
                    dist = math.sqrt(dist_sq)
                    force = 6400.0 / dist
                    well_ax = (dx / dist) * force
                    well_ay = (dy / dist) * force
            elif self.emitter_mode == EmitterMode.ORBIT:
                cx, cy = rl.get_screen_width() / 2, rl.get_screen_height() / 2
                dx = cx - particle.position[0]
                dy = cy - particle.position[1]
                dist_sq = dx*dx + dy*dy
                if dist_sq > 1.0:
                    dist = math.sqrt(dist_sq)
                    force = 40000.0 / dist
                    well_ax = (dx / dist) * force
                    well_ay = (dy / dist) * force
            
            # Gravity Gun Logic
            is_held = False
            if self.emitter_mode == EmitterMode.GRAVITY_GUN:
                if rl.is_mouse_button_down(rl.MOUSE_LEFT_BUTTON):
                    dx = mp.x - particle.position[0]
                    dy = mp.y - particle.position[1]
                    dist_sq = dx*dx + dy*dy
                    
                    if dist_sq < 2500: # Hold (radius 50)
                        is_held = True
                        particle.position = (mp.x + numpy.random.uniform(-2, 2), mp.y + numpy.random.uniform(-2, 2))
                        delta = rl.get_mouse_delta()
                        particle.velocity = (delta.x / dt * 1.5, delta.y / dt * 1.5) if dt > 0 else (0,0)
                    elif dist_sq < 250000: # Pull (radius 500)
                        dist = math.sqrt(dist_sq)
                        force = 15000.0
                        well_ax += (dx / dist) * force
                        well_ay += (dy / dist) * force
                        particle.velocity = (particle.velocity[0] * 0.9, particle.velocity[1] * 0.9)

            # Quantum Jitter
            if self.emitter_mode == EmitterMode.QUANTUM:
                particle.velocity = (particle.velocity[0] + numpy.random.uniform(-50, 50), particle.velocity[1] + numpy.random.uniform(-50, 50))

            wobble_ax = 0.0
            if self.emitter_mode == EmitterMode.BUBBLES:
                wobble_ax = math.sin(particle.lifetime * 10.0) * 200.0
            elif self.emitter_mode == EmitterMode.CONFETTI:
                wobble_ax = math.sin(particle.lifetime * 5.0) * 100.0

            # Magnet Repulsion (Right Mouse Button)
            magnet_ax, magnet_ay = 0.0, 0.0
            if rl.is_mouse_button_down(rl.MOUSE_RIGHT_BUTTON):
                dx = particle.position[0] - mp.x
                dy = particle.position[1] - mp.y
                dist_sq = dx*dx + dy*dy
                if dist_sq > 10.0:
                    dist = math.sqrt(dist_sq)
                    magnet_ax = (dx / dist) * 5000.0
                    magnet_ay = (dy / dist) * 5000.0
            
            # Force Field Logic
            force_field_ax, force_field_ay = 0.0, 0.0
            if self.emitter_mode == EmitterMode.FORCE_FIELD:
                cx, cy = rl.get_screen_width() / 2, rl.get_screen_height() / 2
                dx = particle.position[0] - cx
                dy = particle.position[1] - cy
                dist_sq = dx*dx + dy*dy
                radius = 150.0
                if dist_sq < radius*radius:
                    dist = math.sqrt(dist_sq)
                    if dist > 0.1:
                        force = 8000.0 * (1.0 - dist/radius)
                        force_field_ax = (dx / dist) * force
                        force_field_ay = (dy / dist) * force
            
            # Mouse Attractor Logic
            attractor_ax, attractor_ay = 0.0, 0.0
            if self.mouse_attractor_enabled:
                dx = mp.x - particle.position[0]
                dy = mp.y - particle.position[1]
                dist_sq = dx*dx + dy*dy
                if dist_sq > 100.0:
                    dist = math.sqrt(dist_sq)
                    attractor_ax = (dx / dist) * 1500.0
                    attractor_ay = (dy / dist) * 1500.0

            wind_x, wind_y = self.wind
            if self.emitter_mode == EmitterMode.GALAXY or self.emitter_mode == EmitterMode.ORBIT:
                wind_x, wind_y = 0.0, 0.0

            if is_held:
                vx, vy = particle.velocity
            else:
                vx = particle.velocity[0] + (particle.acceleration[0] + wind_x + repel_ax + vortex_ax + well_ax + wobble_ax + magnet_ax + force_field_ax + attractor_ax) * dt
                vy = particle.velocity[1] + (particle.acceleration[1] + wind_y + repel_ay + vortex_ay + well_ay + magnet_ay + force_field_ay + attractor_ay) * dt
            
            # Apply Friction
            if self.emitter_mode != EmitterMode.GALAXY and self.emitter_mode != EmitterMode.ORBIT:
                vx *= max(0.0, 1.0 - FRICTION * dt)
                vy *= max(0.0, 1.0 - FRICTION * dt)
            
            # Wall Collision
            if self.walls:
                next_x = particle.position[0] + vx * dt
                next_y = particle.position[1] + vy * dt
                for wall in self.walls:
                    if rl.check_collision_point_rec(rl.Vector2(next_x, next_y), wall):
                        if rl.check_collision_point_rec(rl.Vector2(next_x, particle.position[1]), wall):
                            vx = -vx * 0.8
                        else:
                            vy = -vy * 0.8
                        break
            
            # Portal Logic
            if self.emitter_mode == EmitterMode.PORTAL:
                p_vec = rl.Vector2(particle.position[0], particle.position[1])
                for i, portal in enumerate(self.portals):
                    if rl.check_collision_point_rec(p_vec, portal['rect']):
                        target_idx = (i + 1) % len(self.portals)
                        target = self.portals[target_idx]
                        if i == 0: px_new = target['rect'].x - 5
                        else: px_new = target['rect'].x + target['rect'].width + 5
                        rel_y = (particle.position[1] - portal['rect'].y) / portal['rect'].height
                        py_new = target['rect'].y + rel_y * target['rect'].height
                        particle.position = (px_new, py_new)
                        particle.trail.clear()
                        c = target['color']
                        if isinstance(c, tuple):
                            particle.color = (c[0], c[1], c[2])
                        else:
                            particle.color = (c.r, c.g, c.b)
                        break

            px = particle.position[0] + vx * dt
            py = particle.position[1] + vy * dt

            # Screen Bounce Logic
            sw, sh = rl.get_screen_width(), rl.get_screen_height()
            bounced = False
            
            if self.emitter_mode == EmitterMode.SNOW:
                # Wrap X for snow
                if px < 0: px = sw
                elif px > sw: px = 0
                
                # Accumulate at bottom
                if py > sh:
                    py = sh
                    vx, vy = 0, 0
                    particle.acceleration = (0, 0) # Stop falling
            elif self.emitter_mode == EmitterMode.CONFETTI:
                if px < 0: px = sw
                elif px > sw: px = 0
            else:
                if px < 0: px, vx = 0, -vx * 0.8; bounced = True
                elif px > sw: px, vx = sw, -vx * 0.8; bounced = True
                if py < 0: py, vy = 0, -vy * 0.8; bounced = True
                elif py > sh: py, vy = sh, -vy * 0.8; bounced = True

            if bounced:
                particle.color = (int(numpy.random.randint(50, 256)), int(numpy.random.randint(50, 256)), int(numpy.random.randint(50, 256)))

            particle.velocity = (vx, vy)
            particle.position = (px, py)
            
            if self.emitter_mode == EmitterMode.HEAT_MAP:
                speed = math.sqrt(vx*vx + vy*vy)
                hue = max(0.0, 240.0 - (speed / 600.0) * 240.0)
                c = rl.color_from_hsv(hue, 1.0, 1.0)
                particle.color = (c.r, c.g, c.b)

            self.particles.append(particle)
    def draw(self):
        rl.begin_texture_mode(self.render_target)
        rl.clear_background(rl.BLACK)
        
        if self.background_enabled:
            # Draw background texture scaled to screen size
            source = rl.Rectangle(0, 0, float(self.bg_texture.width), float(self.bg_texture.height))
            dest = rl.Rectangle(0, 0, float(rl.get_screen_width()), float(rl.get_screen_height()))
            tint = rl.fade(rl.WHITE, self.background_opacity)
            rl.draw_texture_pro(self.bg_texture, source, dest, rl.Vector2(0, 0), 0.0, tint)

        if self.emitter_mode == EmitterMode.BLACK_HOLE:
            cx, cy = rl.get_screen_width() // 2, rl.get_screen_height() // 2
            rl.draw_circle(cx, cy, 45, rl.Color(50, 0, 50, 255))
            rl.draw_circle(cx, cy, 30, rl.BLACK)
            rl.draw_circle_lines(cx, cy, 30, rl.PURPLE)
        
        # Draw Walls
        for wall in self.walls:
            rl.draw_rectangle_rec(wall, rl.GRAY)
            rl.draw_rectangle_lines(int(wall.x), int(wall.y), int(wall.width), int(wall.height), rl.WHITE)
        
        if self.emitter_mode == EmitterMode.PORTAL:
            for portal in self.portals:
                rl.draw_rectangle_rec(portal['rect'], rl.fade(portal['color'], 0.3))
                rl.draw_rectangle_lines(int(portal['rect'].x), int(portal['rect'].y), int(portal['rect'].width), int(portal['rect'].height), portal['color'])
        
        if self.emitter_mode == EmitterMode.FORCE_FIELD:
            cx, cy = rl.get_screen_width() // 2, rl.get_screen_height() // 2
            rl.draw_circle_gradient(cx, cy, 150, rl.fade(rl.RED, 0.4), rl.fade(rl.RED, 0.0))
            rl.draw_circle_lines(cx, cy, 150, rl.RED)

        rl.begin_blend_mode(rl.BLEND_ADDITIVE)
        for ripple in self.ripples:
            alpha = int(255 * (ripple.lifetime / ripple.max_lifetime))
            color = rl.Color(ripple.color[0], ripple.color[1], ripple.color[2], alpha)
            rl.draw_circle_lines(int(ripple.position[0]), int(ripple.position[1]), ripple.radius, color)
            rl.draw_circle_lines(int(ripple.position[0]), int(ripple.position[1]), ripple.radius - 5, color)

        for particle in self.particles:
            if particle.state == ParticleState.ALIVE:
                life_ratio = particle.lifetime / particle.initial_lifetime
                alpha = int(255 * life_ratio)
                alpha = max(0, min(alpha, 255))
                
                if len(particle.trail) > 0:
                    for i in range(len(particle.trail) - 1):
                        start_pos = particle.trail[i]
                        end_pos = particle.trail[i+1]
                        trail_alpha = int(alpha * (i / len(particle.trail)))
                        rl.draw_line(int(start_pos[0]), int(start_pos[1]), int(end_pos[0]), int(end_pos[1]), rl.Color(particle.color[0], particle.color[1], particle.color[2], trail_alpha))
                    
                    rl.draw_line(int(particle.trail[-1][0]), int(particle.trail[-1][1]), int(particle.position[0]), int(particle.position[1]), rl.Color(particle.color[0], particle.color[1], particle.color[2], alpha))

                # Draw glow texture centered
                color = rl.Color(particle.color[0], particle.color[1], particle.color[2], alpha)
                scale = max(0.0, life_ratio)

                if self.emitter_mode == EmitterMode.CONFETTI:
                    rect = rl.Rectangle(particle.position[0], particle.position[1], 12 * scale, 6 * scale)
                    origin = rl.Vector2(6 * scale, 3 * scale)
                    rl.draw_rectangle_pro(rect, origin, particle.rotation, color)
                else:
                    source = rl.Rectangle(0, 0, float(self.texture.width), float(self.texture.height))
                    dest_w, dest_h = float(self.texture.width) * scale, float(self.texture.height) * scale
                    dest = rl.Rectangle(particle.position[0], particle.position[1], dest_w, dest_h)
                    origin = rl.Vector2(dest_w/2, dest_h/2)
                    rl.draw_texture_pro(self.texture, source, dest, origin, particle.rotation, color)
                    if self.emitter_mode == EmitterMode.BUBBLES:
                        rl.draw_circle_lines(int(particle.position[0]), int(particle.position[1]), 8 * scale, color)
        rl.end_blend_mode()
        rl.end_texture_mode()
        
        # --- PASS 2: Apply Shockwave (RT1 -> RT2) ---
        rl.begin_texture_mode(self.render_target2)
        rl.clear_background(rl.BLACK)
        rl.begin_shader_mode(self.shader)
        radius = self.sw_time * 1.0
        force = 0.1 * (1.0 - (self.sw_time / 2.0))
        if not self.sw_active: force = 0.0
        
        rl.set_shader_value(self.shader, self.sw_loc_center, rl.ffi.new("float[]", self.sw_center), rl.SHADER_UNIFORM_VEC2)
        rl.set_shader_value(self.shader, self.sw_loc_radius, rl.ffi.new("float *", radius), rl.SHADER_UNIFORM_FLOAT)
        rl.set_shader_value(self.shader, self.sw_loc_force, rl.ffi.new("float *", force), rl.SHADER_UNIFORM_FLOAT)
        rl.set_shader_value(self.shader, self.sw_loc_aspect, rl.ffi.new("float *", float(rl.get_screen_width())/float(rl.get_screen_height())), rl.SHADER_UNIFORM_FLOAT)
        
        # Draw RT1 to RT2
        source_rect = rl.Rectangle(0, 0, float(self.render_target.texture.width), float(-self.render_target.texture.height))
        dest_rect = rl.Rectangle(0, 0, float(self.render_target2.texture.width), float(self.render_target2.texture.height))
        rl.draw_texture_pro(self.render_target.texture, source_rect, dest_rect, rl.Vector2(0, 0), 0.0, rl.WHITE)
        rl.end_shader_mode()
        rl.end_texture_mode()

        # --- PASS 3: Apply Bloom (RT2 -> Screen) ---
        rl.begin_shader_mode(self.bloom_shader)
        render_size = [float(self.render_target2.texture.width), float(self.render_target2.texture.height)]
        rl.set_shader_value(self.bloom_shader, self.bloom_loc_size, rl.ffi.new("float[]", render_size), rl.SHADER_UNIFORM_VEC2)
        
        screen_dest = rl.Rectangle(0, 0, float(rl.get_screen_width()), float(rl.get_screen_height()))
        rl.draw_texture_pro(self.render_target2.texture, source_rect, screen_dest, rl.Vector2(0, 0), 0.0, rl.WHITE)
        rl.end_shader_mode()

    def cleanup(self):
        rl.unload_texture(self.texture)
        rl.unload_texture(self.bg_texture)
        rl.unload_sound(self.burst_sound)
        rl.unload_sound(self.fuse_sound)
        rl.unload_sound(self.pop_sound)
        if self.music:
            rl.unload_music_stream(self.music)
        rl.unload_render_texture(self.render_target)
        rl.unload_render_texture(self.render_target2)
        rl.unload_shader(self.shader)
        rl.unload_shader(self.bloom_shader)

    def get_state(self):
        return {
            "max_particles": self.particles.maxlen,
            "emitter_mode": self.emitter_mode.value,
            "color_mode": self.color_mode,
            "wind": self.wind,
            "gravity": self.gravity,
            "repulsion_enabled": self.repulsion_enabled,
            "vortex_enabled": self.vortex_enabled,
            "mouse_attractor_enabled": self.mouse_attractor_enabled,
            "blackhole_collision": self.blackhole_collision,
            "time_scale": self.time_scale,
            "slow_motion": self.slow_motion,
            "trail_length": self.trail_length,
            "background_enabled": self.background_enabled,
            "background_opacity": self.background_opacity
        }

    def set_state(self, state):
        match state:
            case dict():
                self.set_max_count(state.get("max_particles", 1000))
                
                match state.get("emitter_mode"):
                    case int() as val:
                        try: self.emitter_mode = EmitterMode(val)
                        except ValueError: self.emitter_mode = EmitterMode.CENTER
                    case _: self.emitter_mode = EmitterMode.CENTER

                self.color_mode = state.get("color_mode", 0)
                
                match state.get("wind"):
                    case [float() as x, float() as y] | (float() as x, float() as y):
                        self.wind = (x, y)
                    case _:
                        self.wind = (30.0, 0.0)

                self.gravity = state.get("gravity", 9.81)
                self.repulsion_enabled = state.get("repulsion_enabled", False)
                self.vortex_enabled = state.get("vortex_enabled", False)
                self.mouse_attractor_enabled = state.get("mouse_attractor_enabled", False)
                self.blackhole_collision = state.get("blackhole_collision", True)
                self.time_scale = state.get("time_scale", 1.0)
                self.slow_motion = state.get("slow_motion", False)
                self.trail_length = state.get("trail_length", TRAIL_LENGTH)
                self.background_enabled = state.get("background_enabled", True)
                self.background_opacity = state.get("background_opacity", 1.0)
            case _:
                print("Invalid state: Expected dictionary")

    def _sync_life_particles(self):
        self.particles.clear()
        for x, y in self.life_grid:
            px = x * self.life_cell_size + self.life_cell_size / 2
            py = y * self.life_cell_size + self.life_cell_size / 2
            p = Particle(
                position=(px, py),
                velocity=(0, 0),
                acceleration=(0, 0),
                trail=[],
                color=(0, 255, 0),
                lifetime=1.0,
                state=ParticleState.ALIVE,
                rotation=0,
                angular_velocity=0,
                is_rocket=False,
                initial_lifetime=1.0
            )
            self.particles.append(p)

    def randomize(self):
        self.set_max_count(int(numpy.random.randint(100, 5001)))
        self.emitter_mode = EmitterMode(int(numpy.random.randint(0, 23)))
        self.color_mode = int(numpy.random.randint(0, len(self.palettes)))
        self.wind = (float(numpy.random.choice([0, 30, 100, -50])), 0.0)
        self.gravity = float(numpy.random.choice([9.81, -9.81]))
        for p in self.particles:
            p.acceleration = (0, self.gravity)
        self.repulsion_enabled = bool(numpy.random.choice([True, False]))
        self.vortex_enabled = bool(numpy.random.choice([True, False]))
        self.mouse_attractor_enabled = bool(numpy.random.choice([True, False]))
        self.blackhole_collision = bool(numpy.random.choice([True, False]))
        self.time_scale = float(numpy.random.uniform(0.1, 3.0))
        self.slow_motion = False
        self.trail_length = int(numpy.random.randint(0, 50))
        self.walls = []
        self.background_enabled = bool(numpy.random.choice([True, False]))
        self.background_opacity = float(numpy.random.uniform(0.1, 1.0))
        self.life_grid = set()

    def reset_defaults(self):
        self.set_max_count(MAX_PARTICLES)
        self.emitter_mode = EmitterMode.CENTER
        self.color_mode = 0
        self.wind = WIND
        self.gravity = GRAVITY
        for p in self.particles:
            p.acceleration = (0, self.gravity)
        self.repulsion_enabled = False
        self.vortex_enabled = False
        self.mouse_attractor_enabled = False
        self.blackhole_collision = True
        self.time_scale = 1.0
        self.slow_motion = False
        self.trail_length = TRAIL_LENGTH
        self.walls = []
        self.background_enabled = True
        self.background_opacity = 1.0
        self.life_grid = set()

# Main Function
def main():
    rl.set_config_flags(rl.FLAG_WINDOW_RESIZABLE)
    rl.init_window(SCREEN_WIDTH, SCREEN_HEIGHT, "Particle System Example".encode('utf-8'))
    rl.set_exit_key(0)
    rl.init_audio_device()
    rl.set_target_fps(60)
    particle_system = ParticleSystem()    
    game_state = 0 # 0: Menu, 1: Simulation
    paused = False
    show_ui = True
    show_debug = False

    # Load Presets
    presets_file = os.path.join(os.path.dirname(__file__), "presets.json")
    presets = [None] * 3
    if os.path.exists(presets_file):
        try:
            with open(presets_file, 'r') as f:
                loaded = json.load(f)
                for i in range(min(len(loaded), 3)):
                    presets[i] = loaded[i]
        except Exception as e:
            print(f"Error loading presets: {e}")

    while not rl.window_should_close():
        if rl.is_key_pressed(rl.KEY_F1):
            show_ui = not show_ui
        
        if rl.is_key_pressed(rl.KEY_F3):
            show_debug = not show_debug

        if rl.is_key_pressed(rl.KEY_F12):
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            rl.take_screenshot(filename.encode('utf-8'))

        if game_state == 1: # Simulation
            if rl.is_key_pressed(rl.KEY_ESCAPE):
                game_state = 0
            
            if rl.is_key_pressed(rl.KEY_SPACE):
                paused = not paused
            
            if rl.is_key_pressed(rl.KEY_C):
                particle_system.walls = []
            
            # Time Warp
            if rl.is_key_down(rl.KEY_RIGHT):
                particle_system.time_scale = min(5.0, particle_system.time_scale + rl.get_frame_time())
            if rl.is_key_down(rl.KEY_LEFT):
                particle_system.time_scale = max(0.05, particle_system.time_scale - rl.get_frame_time())
            
            # Reverse Time
            particle_system.reverse_time = rl.is_key_down(rl.KEY_R)

            if not paused:
                if particle_system.emitter_mode == EmitterMode.SANDBOX:
                    if rl.is_mouse_button_down(rl.MOUSE_LEFT_BUTTON):
                        mp = rl.get_mouse_position()
                        particle_system.walls.append(rl.Rectangle(mp.x - 10, mp.y - 10, 20, 20))
                elif rl.is_mouse_button_pressed(rl.MOUSE_LEFT_BUTTON):
                    mp = rl.get_mouse_position()
                    particle_system.burst((mp.x, mp.y), 100)

            dt = rl.get_frame_time()
            if not paused:
                particle_system.update(dt * particle_system.time_scale)        
            rl.begin_drawing()
            rl.clear_background(rl.BLACK)
            particle_system.draw()
            
            if show_ui:
                if paused:
                    rl.draw_text("PAUSED".encode('utf-8'), rl.get_screen_width() // 2 - 70, 80, 40, rl.YELLOW)
                elif particle_system.emitter_mode == EmitterMode.SANDBOX:
                    rl.draw_text("Hold Left Click to Draw Walls | Press C to Clear".encode('utf-8'), 10, 40, 20, rl.GRAY)

                rl.draw_fps(10, 70)
                rl.draw_text(f"Time Scale: {particle_system.time_scale:.2f}x".encode('utf-8'), 10, 95, 20, rl.GREEN)
                if particle_system.reverse_time:
                    rl.draw_text("REVERSING TIME".encode('utf-8'), 10, 120, 20, rl.RED)
                else:
                    rl.draw_text("Hold R to Reverse".encode('utf-8'), 10, 120, 20, rl.GRAY)
                rl.draw_text("Press ESC for Menu".encode('utf-8'), 10, 10, 20, rl.GRAY)
                
                # Draw Load Bar
                bar_w = 200
                bar_h = 20
                bar_x = rl.get_screen_width() - bar_w - 10
                bar_y = 10
                ratio = len(particle_system.particles) / particle_system.particles.maxlen
                rl.draw_rectangle(bar_x, bar_y, bar_w, bar_h, rl.DARKGRAY)
                rl.draw_rectangle(bar_x, bar_y, int(bar_w * ratio), bar_h, rl.RED if ratio > 0.9 else rl.GREEN)
                rl.draw_rectangle_lines(bar_x, bar_y, bar_w, bar_h, rl.WHITE)
                rl.draw_text(f"{len(particle_system.particles)} / {particle_system.particles.maxlen}".encode('utf-8'), bar_x + 5, bar_y + 2, 20, rl.WHITE)

            if show_debug:
                # Debug Panel
                panel_x, panel_y = 10, 100
                rl.draw_rectangle(panel_x, panel_y, 220, 110, rl.fade(rl.BLACK, 0.7))
                rl.draw_rectangle_lines(panel_x, panel_y, 220, 110, rl.GREEN)
                
                y_off = panel_y + 10
                rl.draw_text(f"Particles: {len(particle_system.particles)}".encode('utf-8'), panel_x + 10, y_off, 20, rl.GREEN); y_off += 25
                rl.draw_text(f"Ripples: {len(particle_system.ripples)}".encode('utf-8'), panel_x + 10, y_off, 20, rl.GREEN); y_off += 25
                
                mem_str = "N/A"
                if psutil:
                    mem = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
                    mem_str = f"{mem:.2f} MB"
                rl.draw_text(f"Memory: {mem_str}".encode('utf-8'), panel_x + 10, y_off, 20, rl.GREEN); y_off += 25
                rl.draw_text(f"Mode: {particle_system.emitter_mode.name}".encode('utf-8'), panel_x + 10, y_off, 20, rl.GREEN)

            rl.end_drawing()
        else: # Menu
            sw = rl.get_screen_width()
            sh = rl.get_screen_height()
            mouse_pos = rl.get_mouse_position()
            
            btn_mode = rl.Rectangle(sw//2 - 100, sh//2 - 180, 200, 40)
            btn_color = rl.Rectangle(sw//2 - 100, sh//2 - 120, 200, 40)
            btn_wind = rl.Rectangle(sw//2 - 100, sh//2 - 60, 200, 40)
            btn_gravity = rl.Rectangle(sw//2 - 100, sh//2, 200, 40)
            btn_repulsion = rl.Rectangle(sw//2 - 100, sh//2 + 60, 200, 40)
            btn_vortex = rl.Rectangle(sw//2 - 100, sh//2 + 120, 200, 40)
            btn_start = rl.Rectangle(sw//2 - 100, sh//2 + 180, 200, 40)
            btn_random = rl.Rectangle(sw//2 + 130, sh//2, 130, 40)
            btn_reset = rl.Rectangle(sw//2 + 130, sh//2 + 60, 130, 40)
            btn_bg = rl.Rectangle(sw//2 + 130, sh//2 + 120, 130, 40)
            slider_opacity = rl.Rectangle(sw//2 + 130, sh//2 + 180, 130, 20)
            
            # Slider logic
            slider_bar = rl.Rectangle(sw//2 - 100, sh//2 + 250, 200, 20)
            slider_speed = rl.Rectangle(sw//2 - 100, sh//2 + 310, 200, 20)
            slider_trail = rl.Rectangle(sw//2 - 100, sh//2 + 370, 200, 20)

            # Layout Configuration
            col_w = 220
            btn_h = 40
            spacing = 10
            center_x = sw // 2
            start_y = sh // 2 - 220

            # Left Column (Simulation Settings)
            left_x = center_x - col_w - 10
            btn_mode = rl.Rectangle(left_x, start_y, col_w, btn_h)
            btn_color = rl.Rectangle(left_x, start_y + (btn_h + spacing), col_w, btn_h)
            btn_wind = rl.Rectangle(left_x, start_y + (btn_h + spacing)*2, col_w, btn_h)
            btn_gravity = rl.Rectangle(left_x, start_y + (btn_h + spacing)*3, col_w, btn_h)
            btn_repulsion = rl.Rectangle(left_x, start_y + (btn_h + spacing)*4, col_w, btn_h)
            btn_vortex = rl.Rectangle(left_x, start_y + (btn_h + spacing)*5, col_w, btn_h)
            btn_bh_col = rl.Rectangle(left_x, start_y + (btn_h + spacing)*6, col_w, btn_h)
            btn_attractor = rl.Rectangle(left_x, start_y + (btn_h + spacing)*7, col_w, btn_h)

            # Right Column (System & Visuals)
            right_x = center_x + 10
            btn_pulse = rl.Rectangle(right_x + 115, start_y, 105, btn_h)
            slider_opacity = rl.Rectangle(right_x, start_y + (btn_h + spacing) + 15, col_w, 20)
            btn_random = rl.Rectangle(right_x, start_y + (btn_h + spacing)*2, col_w, btn_h)
            btn_reset = rl.Rectangle(right_x, start_y + (btn_h + spacing)*3, 105, btn_h)
            btn_slow_mo = rl.Rectangle(right_x + 115, start_y + (btn_h + spacing)*3, 105, btn_h)

            # Presets Area (Right Column, below Reset)
            preset_y = start_y + (btn_h + spacing)*4

            # Bottom Section (Sliders & Start)
            bottom_y = start_y + (btn_h + spacing)*8 + 20
            slider_width = 450
            slider_x = center_x - slider_width // 2

            slider_bar = rl.Rectangle(slider_x, bottom_y, slider_width, 20)
            slider_speed = rl.Rectangle(slider_x, bottom_y + 40, slider_width, 20)
            slider_trail = rl.Rectangle(slider_x, bottom_y + 80, slider_width, 20)

            btn_start = rl.Rectangle(center_x - 100, bottom_y + 130, 200, 50)

            min_p, max_p = 100, 5000

            if rl.is_mouse_button_pressed(rl.MOUSE_LEFT_BUTTON):
                if rl.check_collision_point_rec(mouse_pos, btn_mode):
                    # Cycle through modes
                    new_val = (particle_system.emitter_mode.value + 1) % 23
                    particle_system.emitter_mode = EmitterMode(new_val)
                elif rl.check_collision_point_rec(mouse_pos, btn_color):
                    particle_system.color_mode = (particle_system.color_mode + 1) % len(particle_system.palettes)
                elif rl.check_collision_point_rec(mouse_pos, btn_wind):
                    if particle_system.wind[0] == 0.0: particle_system.wind = (30.0, 0.0)
                    elif particle_system.wind[0] == 30.0: particle_system.wind = (100.0, 0.0)
                    elif particle_system.wind[0] == 100.0: particle_system.wind = (-50.0, 0.0)
                    else: particle_system.wind = (0.0, 0.0)
                elif rl.check_collision_point_rec(mouse_pos, btn_gravity):
                    particle_system.gravity = -particle_system.gravity
                    for p in particle_system.particles:
                        p.acceleration = (0, particle_system.gravity)
                elif rl.check_collision_point_rec(mouse_pos, btn_repulsion):
                    particle_system.repulsion_enabled = not particle_system.repulsion_enabled
                elif rl.check_collision_point_rec(mouse_pos, btn_vortex):
                    particle_system.vortex_enabled = not particle_system.vortex_enabled
                elif rl.check_collision_point_rec(mouse_pos, btn_bh_col):
                    particle_system.blackhole_collision = not particle_system.blackhole_collision
                elif rl.check_collision_point_rec(mouse_pos, btn_attractor):
                    particle_system.mouse_attractor_enabled = not particle_system.mouse_attractor_enabled
                elif rl.check_collision_point_rec(mouse_pos, btn_slow_mo):
                    particle_system.slow_motion = not particle_system.slow_motion
                    if particle_system.slow_motion:
                        particle_system.prev_time_scale = particle_system.time_scale
                        particle_system.time_scale = 0.2
                    else:
                        particle_system.time_scale = particle_system.prev_time_scale
                elif rl.check_collision_point_rec(mouse_pos, btn_pulse):
                    particle_system.burst((sw//2, sh//2), 300)
                elif rl.check_collision_point_rec(mouse_pos, btn_start):
                    game_state = 1
                elif rl.check_collision_point_rec(mouse_pos, btn_random):
                    particle_system.randomize()
                elif rl.check_collision_point_rec(mouse_pos, btn_reset):
                    particle_system.reset_defaults()
                elif rl.check_collision_point_rec(mouse_pos, btn_bg):
                    particle_system.background_enabled = not particle_system.background_enabled
            
            # Preset Buttons Logic
            for i in range(3):
                p_y = preset_y + i * 50
                btn_load = rl.Rectangle(right_x, p_y, 95, 40)
                btn_save = rl.Rectangle(right_x + 105, p_y, 95, 40)
                if rl.is_mouse_button_pressed(rl.MOUSE_LEFT_BUTTON):
                    if rl.check_collision_point_rec(mouse_pos, btn_load):
                        if presets[i]: particle_system.set_state(presets[i])
                    elif rl.check_collision_point_rec(mouse_pos, btn_save):
                        presets[i] = particle_system.get_state()
                        try:
                            with open(presets_file, 'w') as f: json.dump(presets, f)
                        except Exception as e: print(f"Error saving presets: {e}")

            if rl.is_mouse_button_down(rl.MOUSE_LEFT_BUTTON):
                slider_hitbox = rl.Rectangle(slider_bar.x, slider_bar.y - 10, slider_bar.width, slider_bar.height + 20)
                if rl.check_collision_point_rec(mouse_pos, slider_hitbox):
                    val = (mouse_pos.x - slider_bar.x) / slider_bar.width
                    val = max(0.0, min(1.0, val))
                    new_count = int(min_p + val * (max_p - min_p))
                    particle_system.set_max_count(new_count)
                
                slider_speed_hitbox = rl.Rectangle(slider_speed.x, slider_speed.y - 10, slider_speed.width, slider_speed.height + 20)
                if rl.check_collision_point_rec(mouse_pos, slider_speed_hitbox):
                    val = (mouse_pos.x - slider_speed.x) / slider_speed.width
                    val = max(0.0, min(1.0, val))
                    particle_system.time_scale = 0.1 + val * 2.9
                    particle_system.slow_motion = False
                
                slider_trail_hitbox = rl.Rectangle(slider_trail.x, slider_trail.y - 10, slider_trail.width, slider_trail.height + 20)
                if rl.check_collision_point_rec(mouse_pos, slider_trail_hitbox):
                    val = (mouse_pos.x - slider_trail.x) / slider_trail.width
                    val = max(0.0, min(1.0, val))
                    particle_system.trail_length = int(val * 50)
                
                slider_opacity_hitbox = rl.Rectangle(slider_opacity.x, slider_opacity.y - 10, slider_opacity.width, slider_opacity.height + 20)
                if rl.check_collision_point_rec(mouse_pos, slider_opacity_hitbox):
                    val = (mouse_pos.x - slider_opacity.x) / slider_opacity.width
                    val = max(0.0, min(1.0, val))
                    particle_system.background_opacity = val

            rl.begin_drawing()
            rl.clear_background(rl.RAYWHITE)
            rl.draw_text("Particle System".encode('utf-8'), sw//2 - rl.measure_text("Particle System".encode('utf-8'), 40)//2, 40, 40, rl.DARKGRAY)
            
            # Column Headers
            rl.draw_text("Parameters".encode('utf-8'), int(left_x), start_y - 30, 20, rl.GRAY)
            rl.draw_text("Controls".encode('utf-8'), int(center_x), start_y - 30, 20, rl.GRAY)
            rl.draw_text("Visuals & Presets".encode('utf-8'), int(right_x), start_y - 30, 20, rl.GRAY)
            
            rl.draw_rectangle_rec(btn_mode, rl.LIGHTGRAY); rl.draw_text(f"Mode: {particle_system.emitter_mode.name}".encode('utf-8'), int(btn_mode.x + 10), int(btn_mode.y + 10), 20, rl.BLACK)
            rl.draw_rectangle_rec(btn_color, rl.LIGHTGRAY); rl.draw_text(f"Palette: {particle_system.palettes[particle_system.color_mode][0]}".encode('utf-8'), int(btn_color.x + 10), int(btn_color.y + 10), 20, rl.BLACK)
            rl.draw_rectangle_rec(btn_wind, rl.LIGHTGRAY); rl.draw_text(f"Wind X: {particle_system.wind[0]}".encode('utf-8'), int(btn_wind.x + 10), int(btn_wind.y + 10), 20, rl.BLACK)
            rl.draw_rectangle_rec(btn_gravity, rl.LIGHTGRAY); rl.draw_text(f"Gravity: {'Down' if particle_system.gravity > 0 else 'Up'}".encode('utf-8'), int(btn_gravity.x + 10), int(btn_gravity.y + 10), 20, rl.BLACK)
            rl.draw_rectangle_rec(btn_repulsion, rl.LIGHTGRAY); rl.draw_text(f"Repulsion: {'On' if particle_system.repulsion_enabled else 'Off'}".encode('utf-8'), int(btn_repulsion.x + 10), int(btn_repulsion.y + 10), 20, rl.BLACK)
            rl.draw_rectangle_rec(btn_vortex, rl.LIGHTGRAY); rl.draw_text(f"Vortex: {'On' if particle_system.vortex_enabled else 'Off'}".encode('utf-8'), int(btn_vortex.x + 10), int(btn_vortex.y + 10), 20, rl.BLACK)
            rl.draw_rectangle_rec(btn_bh_col, rl.LIGHTGRAY); rl.draw_text(f"BH Collision: {'On' if particle_system.blackhole_collision else 'Off'}".encode('utf-8'), int(btn_bh_col.x + 10), int(btn_bh_col.y + 10), 20, rl.BLACK)
            rl.draw_rectangle_rec(btn_attractor, rl.LIGHTGRAY); rl.draw_text(f"Mouse Attractor: {'On' if particle_system.mouse_attractor_enabled else 'Off'}".encode('utf-8'), int(btn_attractor.x + 10), int(btn_attractor.y + 10), 20, rl.BLACK)
            rl.draw_rectangle_rec(btn_start, rl.GREEN); rl.draw_text("START".encode('utf-8'), int(btn_start.x + 70), int(btn_start.y + 15), 20, rl.WHITE)
            
            # Draw Randomize
            rl.draw_rectangle_rec(btn_random, rl.ORANGE)
            rl.draw_text("Randomize".encode('utf-8'), int(btn_random.x + 10), int(btn_random.y + 10), 20, rl.WHITE)

            # Draw Reset
            rl.draw_rectangle_rec(btn_reset, rl.RED)
            rl.draw_text("Reset".encode('utf-8'), int(btn_reset.x + 10), int(btn_reset.y + 10), 20, rl.WHITE)
            rl.draw_rectangle_rec(btn_slow_mo, rl.BLUE if particle_system.slow_motion else rl.LIGHTGRAY)
            rl.draw_text("Slow Mo".encode('utf-8'), int(btn_slow_mo.x + 10), int(btn_slow_mo.y + 10), 20, rl.WHITE if particle_system.slow_motion else rl.BLACK)

            # Draw BG Toggle
            rl.draw_rectangle_rec(btn_bg, rl.LIGHTGRAY)
            rl.draw_text(f"BG: {'On' if particle_system.background_enabled else 'Off'}".encode('utf-8'), int(btn_bg.x + 10), int(btn_bg.y + 10), 20, rl.BLACK)
            rl.draw_rectangle_rec(btn_pulse, rl.PURPLE)
            rl.draw_text("Pulse".encode('utf-8'), int(btn_pulse.x + 10), int(btn_pulse.y + 10), 20, rl.WHITE)

            # Draw Opacity Slider
            curr_o = particle_system.background_opacity
            rl.draw_text(f"Opacity: {curr_o:.2f}".encode('utf-8'), int(slider_opacity.x), int(slider_opacity.y - 20), 20, rl.DARKGRAY)
            rl.draw_rectangle_rec(slider_opacity, rl.LIGHTGRAY)
            rl.draw_rectangle(int(slider_opacity.x + curr_o * slider_opacity.width - 5), int(slider_opacity.y - 5), 10, 30, rl.DARKGRAY)

            # Draw Slider
            curr_p = particle_system.particles.maxlen
            norm_val = (curr_p - min_p) / (max_p - min_p)
            rl.draw_text(f"Max Particles: {curr_p}".encode('utf-8'), int(slider_bar.x), int(slider_bar.y - 20), 20, rl.DARKGRAY)
            rl.draw_rectangle_rec(slider_bar, rl.LIGHTGRAY)
            rl.draw_rectangle(int(slider_bar.x + norm_val * slider_bar.width - 5), int(slider_bar.y - 5), 10, 30, rl.DARKGRAY)
            
            # Draw Speed Slider
            curr_s = particle_system.time_scale
            norm_s = (curr_s - 0.1) / 2.9
            rl.draw_text(f"Speed: {curr_s:.2f}x".encode('utf-8'), int(slider_speed.x), int(slider_speed.y - 20), 20, rl.DARKGRAY)
            rl.draw_rectangle_rec(slider_speed, rl.LIGHTGRAY)
            rl.draw_rectangle(int(slider_speed.x + norm_s * slider_speed.width - 5), int(slider_speed.y - 5), 10, 30, rl.DARKGRAY)
            
            # Draw Trail Slider
            curr_t = particle_system.trail_length
            norm_t = curr_t / 50.0
            rl.draw_text(f"Trail Length: {curr_t}".encode('utf-8'), int(slider_trail.x), int(slider_trail.y - 20), 20, rl.DARKGRAY)
            rl.draw_rectangle_rec(slider_trail, rl.LIGHTGRAY)
            rl.draw_rectangle(int(slider_trail.x + norm_t * slider_trail.width - 5), int(slider_trail.y - 5), 10, 30, rl.DARKGRAY)
            
            # Draw Presets
            for i in range(3):
                p_y = preset_y + i * 50
                btn_load = rl.Rectangle(right_x, p_y, 95, 40)
                btn_save = rl.Rectangle(right_x + 105, p_y, 95, 40)
                rl.draw_rectangle_rec(btn_load, rl.LIGHTGRAY if presets[i] else rl.fade(rl.LIGHTGRAY, 0.3))
                rl.draw_text(f"Load {i+1}".encode('utf-8'), int(btn_load.x + 15), int(btn_load.y + 10), 20, rl.BLACK if presets[i] else rl.GRAY)
                rl.draw_rectangle_rec(btn_save, rl.LIGHTGRAY)
                rl.draw_text(f"Save {i+1}".encode('utf-8'), int(btn_save.x + 15), int(btn_save.y + 10), 20, rl.BLACK)

            rl.end_drawing()

    particle_system.cleanup()
    rl.close_audio_device()
    rl.close_window()
if __name__ == "__main__":
    main()  
# Particle System Example   using Raylib and Python
