import pyray as rl
import ctypes
import math
import random
import threading
import os
import google.generativeai as genai
import json

# --- CONFIGURATION ---
API_KEY = os.getenv("GEMINI_API_KEY", "")  # Uses env var or empty string fallback
if API_KEY:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-pro')

# --- POLYFILLS FOR MISSING RAYLIB STRUCTS/FUNCTIONS ---
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

if not hasattr(rl, 'Vector3'):
    class Vector3(ctypes.Structure):
        _fields_ = [("x", ctypes.c_float), ("y", ctypes.c_float), ("z", ctypes.c_float)]
        def __repr__(self): return f"Vector3({self.x}, {self.y}, {self.z})"
    rl.Vector3 = Vector3

if not hasattr(rl, 'Camera3D'):
    class Camera3D(ctypes.Structure):
        _fields_ = [
            ("position", rl.Vector3),
            ("target", rl.Vector3),
            ("up", rl.Vector3),
            ("fovy", ctypes.c_float),
            ("projection", ctypes.c_int)
        ]
    rl.Camera3D = Camera3D

if not hasattr(rl, 'Matrix'):
    class Matrix(ctypes.Structure):
        _fields_ = [
            ("m0", ctypes.c_float), ("m4", ctypes.c_float), ("m8", ctypes.c_float), ("m12", ctypes.c_float),
            ("m1", ctypes.c_float), ("m5", ctypes.c_float), ("m9", ctypes.c_float), ("m13", ctypes.c_float),
            ("m2", ctypes.c_float), ("m6", ctypes.c_float), ("m10", ctypes.c_float), ("m14", ctypes.c_float),
            ("m3", ctypes.c_float), ("m7", ctypes.c_float), ("m11", ctypes.c_float), ("m15", ctypes.c_float)
        ]
    rl.Matrix = Matrix

if not hasattr(rl, 'Vector3Add'):
    def Vector3Add(v1, v2): return rl.Vector3(v1.x + v2.x, v1.y + v2.y, v1.z + v2.z)
    rl.Vector3Add = Vector3Add

if not hasattr(rl, 'Vector3Subtract'):
    def Vector3Subtract(v1, v2): return rl.Vector3(v1.x - v2.x, v1.y - v2.y, v1.z - v2.z)
    rl.Vector3Subtract = Vector3Subtract

if not hasattr(rl, 'Vector3Scale'):
    def Vector3Scale(v, scale): return rl.Vector3(v.x * scale, v.y * scale, v.z * scale)
    rl.Vector3Scale = Vector3Scale

if not hasattr(rl, 'Vector3Distance'):
    def Vector3Distance(v1, v2): 
        dx = v1.x - v2.x; dy = v1.y - v2.y; dz = v1.z - v2.z
        return math.sqrt(dx*dx + dy*dy + dz*dz)
    rl.Vector3Distance = Vector3Distance

if not hasattr(rl, 'Vector3Normalize'):
    def Vector3Normalize(v):
        length = math.sqrt(v.x*v.x + v.y*v.y + v.z*v.z)
        if length == 0: return rl.Vector3(0,0,0)
        return rl.Vector3(v.x/length, v.y/length, v.z/length)
    rl.Vector3Normalize = Vector3Normalize

if not hasattr(rl, 'Vector3Transform'):
    def Vector3Transform(v, mat):
        x = v.x; y = v.y; z = v.z
        return rl.Vector3(
            mat.m0*x + mat.m4*y + mat.m8*z + mat.m12,
            mat.m1*x + mat.m5*y + mat.m9*z + mat.m13,
            mat.m2*x + mat.m6*y + mat.m10*z + mat.m14
        )
    rl.Vector3Transform = Vector3Transform

if not hasattr(rl, 'MatrixIdentity'):
    def MatrixIdentity():
        m = rl.Matrix()
        m.m0 = m.m5 = m.m10 = m.m15 = 1.0
        return m
    rl.MatrixIdentity = MatrixIdentity

if not hasattr(rl, 'MatrixMultiply'):
    def MatrixMultiply(left, right):
        result = rl.Matrix()
        result.m0 = left.m0*right.m0 + left.m4*right.m1 + left.m8*right.m2 + left.m12*right.m3
        result.m4 = left.m0*right.m4 + left.m4*right.m5 + left.m8*right.m6 + left.m12*right.m7
        result.m8 = left.m0*right.m8 + left.m4*right.m9 + left.m8*right.m10 + left.m12*right.m11
        result.m12 = left.m0*right.m12 + left.m4*right.m13 + left.m8*right.m14 + left.m12*right.m15
        result.m1 = left.m1*right.m0 + left.m5*right.m1 + left.m9*right.m2 + left.m13*right.m3
        result.m5 = left.m1*right.m4 + left.m5*right.m5 + left.m9*right.m6 + left.m13*right.m7
        result.m9 = left.m1*right.m8 + left.m5*right.m9 + left.m9*right.m10 + left.m13*right.m11
        result.m13 = left.m1*right.m12 + left.m5*right.m13 + left.m9*right.m14 + left.m13*right.m15
        result.m2 = left.m2*right.m0 + left.m6*right.m1 + left.m10*right.m2 + left.m14*right.m3
        result.m6 = left.m2*right.m4 + left.m6*right.m5 + left.m10*right.m6 + left.m14*right.m7
        result.m10 = left.m2*right.m8 + left.m6*right.m9 + left.m10*right.m10 + left.m14*right.m11
        result.m14 = left.m2*right.m12 + left.m6*right.m13 + left.m10*right.m14 + left.m14*right.m15
        result.m3 = left.m3*right.m0 + left.m7*right.m1 + left.m11*right.m2 + left.m15*right.m3
        result.m7 = left.m3*right.m4 + left.m7*right.m5 + left.m11*right.m6 + left.m15*right.m7
        result.m11 = left.m3*right.m8 + left.m7*right.m9 + left.m11*right.m10 + left.m15*right.m11
        result.m15 = left.m3*right.m12 + left.m7*right.m13 + left.m11*right.m14 + left.m15*right.m15
        return result
    rl.MatrixMultiply = MatrixMultiply

if not hasattr(rl, 'MatrixTranslate'):
    def MatrixTranslate(x, y, z):
        m = rl.MatrixIdentity(); m.m12 = x; m.m13 = y; m.m14 = z
        return m
    rl.MatrixTranslate = MatrixTranslate

if not hasattr(rl, 'MatrixScale'):
    def MatrixScale(x, y, z):
        m = rl.MatrixIdentity(); m.m0 = x; m.m5 = y; m.m10 = z
        return m
    rl.MatrixScale = MatrixScale

if not hasattr(rl, 'MatrixRotateXYZ'):
    def MatrixRotateXYZ(ang):
        cx, sx = math.cos(ang.x), math.sin(ang.x)
        cy, sy = math.cos(ang.y), math.sin(ang.y)
        cz, sz = math.cos(ang.z), math.sin(ang.z)
        m = rl.MatrixIdentity()
        m.m0 = cz*cy; m.m4 = cz*sy*sx - sz*cx; m.m8 = cz*sy*cx + sz*sx
        m.m1 = sz*cy; m.m5 = sz*sy*sx + cz*cx; m.m9 = sz*sy*cx - cz*sx
        m.m2 = -sy;   m.m6 = cy*sx;            m.m10 = cy*cx
        return m
    rl.MatrixRotateXYZ = MatrixRotateXYZ

def MatrixRotateX(angle):
    m = rl.MatrixIdentity()
    c = math.cos(angle)
    s = math.sin(angle)
    m.m5 = c; m.m6 = s
    m.m9 = -s; m.m10 = c
    return m
rl.MatrixRotateX = MatrixRotateX

def MatrixRotateY(angle):
    m = rl.MatrixIdentity()
    c = math.cos(angle)
    s = math.sin(angle)
    m.m0 = c; m.m2 = -s
    m.m8 = s; m.m10 = c
    return m
rl.MatrixRotateY = MatrixRotateY

def MatrixRotateZ(angle):
    m = rl.MatrixIdentity()
    c = math.cos(angle)
    s = math.sin(angle)
    m.m0 = c; m.m1 = s
    m.m4 = -s; m.m5 = c
    return m
rl.MatrixRotateZ = MatrixRotateZ

def CheckCollisionSpheres(c1, r1, c2, r2):
    return rl.Vector3Distance(c1, c2) < (r1 + r2)
rl.CheckCollisionSpheres = CheckCollisionSpheres

if not hasattr(rl, 'RAD2DEG'):
    rl.RAD2DEG = 57.295779513

if not hasattr(rl, 'CAMERA_PERSPECTIVE'):
    rl.CAMERA_PERSPECTIVE = 0
if not hasattr(rl, 'CAMERA_ORTHOGRAPHIC'):
    rl.CAMERA_ORTHOGRAPHIC = 1

# --- FIX FOR RAYLIB STRING ENCODING ---
# The raylib ctypes binding requires bytes for char*, but the code uses strings.
# We monkey-patch the functions to automatically encode strings to UTF-8.

# Compatibility: Map snake_case to PascalCase if missing
_compat_map = {
    'InitWindow': 'init_window', 'DrawText': 'draw_text', 'SetTargetFPS': 'set_target_fps',
    'SetExitKey': 'set_exit_key', 'CloseWindow': 'close_window', 'WindowShouldClose': 'window_should_close',
    'BeginDrawing': 'begin_drawing', 'EndDrawing': 'end_drawing', 'ClearBackground': 'clear_background',
    'BeginMode3D': 'begin_mode_3d', 'EndMode3D': 'end_mode_3d', 'DrawGrid': 'draw_grid',
    'DrawCube': 'draw_cube', 'DrawSphere': 'draw_sphere', 'DrawLine': 'draw_line',
    'DrawCircle': 'draw_circle', 'DrawCircleLines': 'draw_circle_lines', 'DrawRectangle': 'draw_rectangle',
    'DrawRectangleRec': 'draw_rectangle_rec', 'DrawRectangleLines': 'draw_rectangle_lines',
    'GetFrameTime': 'get_frame_time', 'GetTime': 'get_time', 'IsKeyDown': 'is_key_down',
    'IsKeyPressed': 'is_key_pressed', 'IsMouseButtonPressed': 'is_mouse_button_pressed',
    'GetMousePosition': 'get_mouse_position', 'CheckCollisionPointRec': 'check_collision_point_rec',
    'GenImagePerlinNoise': 'gen_image_perlin_noise', 'LoadTextureFromImage': 'load_texture_from_image',
    'UnloadImage': 'unload_image', 'GenMeshSphere': 'gen_mesh_sphere', 'GenMeshCone': 'gen_mesh_cone',
    'LoadMaterialDefault': 'load_material_default', 'GetColor': 'get_color', 'ColorAlpha': 'color_alpha',
    'Fade': 'fade', 'SetTraceLogLevel': 'set_trace_log_level', 'GetScreenToWorldRay': 'get_screen_to_world_ray',
    'GetRayCollisionSphere': 'get_ray_collision_sphere', 'DrawMesh': 'draw_mesh', 'DrawCircle3D': 'draw_circle_3d',
    'rlPushMatrix': 'rl_push_matrix', 'rlPopMatrix': 'rl_pop_matrix', 'rlTranslatef': 'rl_translatef',
    'rlRotatef': 'rl_rotatef', 'rlBegin': 'rl_begin', 'rlEnd': 'rl_end', 'rlVertex3f': 'rl_vertex3f',
    'rlColor4ub': 'rl_color4ub', 'rlSetClipPlanes': 'rl_set_clip_planes'
}
for pascal, snake in _compat_map.items():
    if not hasattr(rl, pascal) and hasattr(rl, snake): setattr(rl, pascal, getattr(rl, snake))

# --- SAFETY MOCKS FOR RLGL FUNCTIONS ---
# If these are missing, the game would crash during drawing.
_rlgl_mocks = ['rlPushMatrix', 'rlPopMatrix', 'rlTranslatef', 'rlRotatef', 'rlBegin', 'rlEnd', 'rlVertex3f', 'rlColor4ub', 'rlSetClipPlanes']
for func in _rlgl_mocks:
    if not hasattr(rl, func):
        print(f"WARNING: {func} missing. Mocking to prevent crash.")
        setattr(rl, func, lambda *args: None)

_orig_init_window = getattr(rl, 'InitWindow', getattr(rl, 'init_window', None))
_orig_draw_text = getattr(rl, 'DrawText', getattr(rl, 'draw_text', None))

def _init_window_wrapper(width, height, title):
    if isinstance(title, str):
        title = title.encode('utf-8')
    return _orig_init_window(width, height, title)

def _draw_text_wrapper(text, x, y, font_size, color):
    if isinstance(text, str):
        text = text.encode('utf-8')
    return _orig_draw_text(text, x, y, font_size, color)

rl.InitWindow = _init_window_wrapper
rl.DrawText = _draw_text_wrapper
# --------------------------------------

def c(r, g, b, a):
    return rl.GetColor((r << 24) | (g << 16) | (b << 8) | a)

# --- GAME CONSTANTS ---
PLANET_DATA = [
    {"name": "SUN", "color": rl.ORANGE, "scale": 100, "dist": 0, "speed": 0},
    {"name": "MERCURY", "color": rl.GRAY, "scale": 4, "dist": 160, "speed": 0.5},
    {"name": "VENUS", "color": c(255, 200, 100, 255), "scale": 8, "dist": 240, "speed": 0.35},
    {"name": "EARTH", "color": rl.BLUE, "scale": 8.5, "dist": 340, "speed": 0.3},
    {"name": "MARS", "color": rl.RED, "scale": 5, "dist": 440, "speed": 0.24},
    {"name": "JUPITER", "color": c(255, 150, 100, 255), "scale": 24, "dist": 700, "speed": 0.13},
    {"name": "SATURN", "color": c(200, 170, 120, 255), "scale": 20, "dist": 1000, "speed": 0.1, "ring": True},
    {"name": "URANUS", "color": rl.SKYBLUE, "scale": 12, "dist": 1400, "speed": 0.07},
    {"name": "NEPTUNE", "color": rl.SKYBLUE, "scale": 12, "dist": 1800, "speed": 0.05},
]

SYSTEMS = {
    "SOL": PLANET_DATA,
    "ALPHA CENTAURI": [
        {"name": "ALPHA CEN A", "color": rl.YELLOW, "scale": 110, "dist": 0, "speed": 0},
        {"name": "ALPHA CEN B", "color": rl.ORANGE, "scale": 90, "dist": 600, "speed": 0.05},
        # Alpha Centauri planets are largely unconfirmed/debated, adding a generic rocky world
        {"name": "AC-1 (Hypothetical)", "color": rl.BROWN, "scale": 10, "dist": 300, "speed": 0.2},
    ],
    "PROXIMA CENTAURI": [
        {"name": "PROXIMA CEN", "color": rl.RED, "scale": 40, "dist": 0, "speed": 0},
        {"name": "PROXIMA B", "color": c(150, 100, 50, 255), "scale": 9, "dist": 120, "speed": 0.4}, # Rocky, habitable zone
        {"name": "PROXIMA C", "color": rl.BLUE, "scale": 14, "dist": 300, "speed": 0.15}, # Super-Earth/Mini-Neptune
        {"name": "PROXIMA D", "color": rl.GRAY, "scale": 3, "dist": 60, "speed": 1.2}, # Sub-Earth
    ]
}

FALLBACK_BRIEFINGS = [
    "Sector 7G is hot. Swarms detected. Survive at all costs.",
    "Warning: Anomaly detected. Hostiles inbound.",
    "Intelligence reports heavy pirate activity. Clear the lane.",
]
FALLBACK_DEATHS = [
    "Hull integrity critical. Life support failed.",
    "Pilot error detected. Simulation terminated.",
    "Shields overwhelmed by kinetic impact.",
]

# --- CLASSES ---
class Ship:
    def __init__(self):
        self.position = rl.Vector3(0, 0, 0)
        self.rotation = rl.Vector3(0, 0, 0) # pitch, yaw, roll in degrees
        self.radius = 1.0

class Planet:
    def __init__(self, data, mesh, material, texture):
        self.data = data
        self.position = rl.Vector3(data['dist'], 0, 0)
        self.angle = random.uniform(0, 6.28)
        self.rotation_y = 0
        self.mesh = mesh
        self.material = material
        
        # Texture assignment disabled due to stability issues
        # try:
        #     # Try API call first
        #     rl.set_material_texture(self.material, rl.MATERIAL_MAP_DIFFUSE, texture)
        # except Exception:
        #     try:
        #         # Fallback: Copy texture fields manually
        #         self.material.maps[rl.MATERIAL_MAP_DIFFUSE].texture.id = texture.id
        #         self.material.maps[rl.MATERIAL_MAP_DIFFUSE].texture.width = texture.width
        #         self.material.maps[rl.MATERIAL_MAP_DIFFUSE].texture.height = texture.height
        #         self.material.maps[rl.MATERIAL_MAP_DIFFUSE].texture.mipmaps = texture.mipmaps
        #         self.material.maps[rl.MATERIAL_MAP_DIFFUSE].texture.format = texture.format
        #     except Exception as e:
        #         print(f"Texture assignment failed for {data['name']}: {e}")

        self.market = {
            "Fuel": int(random.uniform(5, 20)),
            "Minerals": int(random.uniform(20, 100)),
            "Food": int(random.uniform(5, 50)),
            "Tech": int(random.uniform(100, 500))
        }
        self.available_quests = []


    def update(self, dt):
        if self.data['dist'] > 0:
            self.angle += self.data['speed'] * dt * 0.1
            self.position.x = math.cos(self.angle) * self.data['dist']
            self.position.z = math.sin(self.angle) * self.data['dist']
            self.rotation_y += 10 * dt

class Enemy:
    def __init__(self, pos, mesh, material):
        self.position = pos
        self.hp = 2
        self.shoot_timer = random.uniform(0, 2)
        self.mesh = mesh
        self.material = material
        self.radius = 1.0
    
    def update(self, dt, player, game_state):
        if rl.Vector3Distance(self.position, player.position) > 300:
            if self in game_state["enemies"]: game_state["enemies"].remove(self)
            return

        # Move towards player
        direction = rl.Vector3Normalize(rl.Vector3Subtract(player.position, self.position))
        self.position = rl.Vector3Add(self.position, rl.Vector3Scale(direction, 20 * dt))

        # Shoot
        self.shoot_timer -= dt
        if self.shoot_timer <= 0:
            forward = rl.Vector3Normalize(rl.Vector3Subtract(player.position, self.position))
            game_state["projectiles"].append(Projectile(self.position, forward, speed=100, is_enemy=True))
            self.shoot_timer = 2.0
        
class Asteroid:
    def __init__(self, pos, mesh, material):
        self.position = pos
        self.hp = 3
        self.rot_vel = rl.Vector3Scale(rl.Vector3(random.uniform(-1,1), random.uniform(-1,1), random.uniform(-1,1)), 50)
        self.rotation = rl.Vector3(0,0,0)
        self.mesh = mesh
        self.material = material
        self.radius = 2.0

    def update(self, dt, player, game_state):
        self.rotation.x += self.rot_vel.x * dt
        self.rotation.y += self.rot_vel.y * dt
        self.rotation.z += self.rot_vel.z * dt
        if rl.Vector3Distance(self.position, player.position) > 300:
            if self in game_state["asteroids"]: game_state["asteroids"].remove(self)
            return

class Projectile:
    def __init__(self, pos, forward, speed=300, lifetime=2, is_enemy=False):
        self.position = pos
        self.forward = forward
        self.speed = speed
        self.lifetime = lifetime
        self.is_enemy = is_enemy
        self.color = rl.RED if is_enemy else rl.GREEN
        self.radius = 0.5

    def update(self, dt, game_state):
        self.position = rl.Vector3Add(self.position, rl.Vector3Scale(self.forward, self.speed * dt))
        self.lifetime -= dt
        if self.lifetime <= 0:
            if self in game_state["projectiles"]:
                game_state["projectiles"].remove(self)
            return

class Missile:
    def __init__(self, pos, forward, target):
        self.position = pos
        self.forward = forward
        self.target = target
        self.speed = 50
        self.life = 5
        self.color = rl.YELLOW
        self.radius = 0.5

    def update(self, dt, game_state):
        self.life -= dt
        self.speed += 50 * dt
        if self.life <= 0: 
            if self in game_state["missiles"]:
                game_state["missiles"].remove(self)
            return
        
        if self.target:
            if self.target.hp > 0:
                direction = rl.Vector3Normalize(rl.Vector3Subtract(self.target.position, self.position))
                self.position = rl.Vector3Add(self.position, rl.Vector3Scale(direction, self.speed * dt))
            else:
                # Target is destroyed, missile continues straight
                self.position = rl.Vector3Add(self.position, rl.Vector3Scale(self.forward, self.speed * dt))

class Explosion:
    def __init__(self, pos, scale=1.0, duration=0.2):
        self.position = pos
        self.scale = scale
        self.duration = duration
        self.life = 0

    def update(self, dt, game_state):
        self.life += dt
        if self.life >= self.duration:
            if self in game_state["explosions"]:
                game_state["explosions"].remove(self)

class Particle:
    def __init__(self, pos, vel, color, size, lifetime):
        self.position = pos
        self.velocity = vel
        self.color = color
        self.size = size
        self.lifetime = lifetime
        self.max_lifetime = lifetime

    def update(self, dt):
        self.position = rl.Vector3Add(self.position, rl.Vector3Scale(self.velocity, dt))
        self.lifetime -= dt

class Game:
    def __init__(self):
        self.screen_width = 1280
        self.screen_height = 720
        rl.SetExitKey(0)
        rl.SetTargetFPS(60)

        self.state = {
            "score": 0,
            "kills": 0,
            "hull": 100,
            "shields": 100,
            "throttle": 0,
            "playing": True,
            "orbiting": False,
            "orbit_target": None,
            "orbit_angle": 0,
            "missile_cd": 0,
            "enemies": [],
            "asteroids": [],
            "projectiles": [],
            "missiles": [],
            "explosions": [],
            "particles": [],
            "active_quests": [],
            "credits": 500,
            "inventory": {"Fuel": 10, "Minerals": 0, "Food": 0, "Tech": 0},
            "docked": False,
            "target_planet": None,
            "last_damage_time": 0,
            "location": "DEEP SPACE",
            "comms_text": "Initializing systems...",
            "death_text": ""
        }
        
        self.hyperspace_timer = 0.0
        self.system_names = list(SYSTEMS.keys())
        self.current_system_idx = 0
        self.in_menu = True
        self.should_quit = False
        self.warp_menu_active = False
        self.pending_warp_destination = None

        self.init_assets()
        self.init_scene()
        self.generate_ai_text("Generate a short start-up sequence message for a sci-fi fighter HUD.", "comms_text")

    def init_assets(self):
        print("Loading assets...")
        noise_image = rl.GenImagePerlinNoise(256, 256, 0, 0, 4.0)
        self.noise_texture = rl.LoadTextureFromImage(noise_image)
        rl.UnloadImage(noise_image)
        
        self.sphere_mesh = rl.GenMeshSphere(1, 32, 32)
        
        self.enemy_mesh = rl.GenMeshCone(0.5, 1, 16)
        self.enemy_material = rl.LoadMaterialDefault()
        self.enemy_material.maps[rl.MATERIAL_MAP_DIFFUSE].color = rl.RED
        
        self.asteroid_mesh = rl.GenMeshSphere(1, 16, 16)
        self.asteroid_material = rl.LoadMaterialDefault()
        self.asteroid_material.maps[rl.MATERIAL_MAP_DIFFUSE].color = rl.BROWN
        print("Assets loaded.")

    def init_scene(self):
        print("Initializing scene...")
        self.player = Ship()
        self.load_system(self.system_names[0])
            
        # Generate Starfield
        self.stars = []
        for _ in range(2000):
            u = random.random()
            v = random.random()
            theta = 2 * math.pi * u
            phi = math.acos(2 * v - 1)
            r = random.uniform(3000, 4500)
            x = r * math.sin(phi) * math.cos(theta)
            y = r * math.sin(phi) * math.sin(theta)
            z = r * math.cos(phi)
            self.stars.append(rl.Vector3(x, y, z))

        self.camera = rl.Camera3D(
            rl.Vector3(0.0, 5.0, -15.0),
            rl.Vector3(0.0, 0.0, 0.0),
            rl.Vector3(0.0, 1.0, 0.0),
            45.0,
            rl.CAMERA_PERSPECTIVE
        )
        print("Scene initialized.")

    def load_system(self, system_name):
        self.planets = []
        self.state["target_planet"] = None
        self.state["active_quests"] = []
        data = SYSTEMS[system_name]
        for p_data in data:
            material = rl.LoadMaterialDefault()
            material.maps[rl.MATERIAL_MAP_DIFFUSE].color = p_data['color']
            p = Planet(p_data, self.sphere_mesh, material, self.noise_texture)
            self.planets.append(p)
        self.state["location"] = f"{system_name} SYSTEM"
        self.generate_ai_text(f"Welcome to the {system_name} system. Scan for hostiles.", "comms_text")

    def generate_ai_text(self, prompt, target_key):
        if not API_KEY:
            fallback = FALLBACK_BRIEFINGS if "mission" in prompt else FALLBACK_DEATHS
            self.state[target_key] = random.choice(fallback)
            return

        def run_ai():
            try:
                response = model.generate_content(prompt)
                self.state[target_key] = response.text
            except:
                fallback = FALLBACK_BRIEFINGS if "mission" in prompt else FALLBACK_DEATHS
                self.state[target_key] = random.choice(fallback)
        
        threading.Thread(target=run_ai, daemon=True).start()

    def draw_ship(self, ship):
        rl.rlPushMatrix()
        rl.rlTranslatef(ship.position.x, ship.position.y, ship.position.z)
        rl.rlRotatef(ship.rotation.y, 0, 1, 0)
        rl.rlRotatef(ship.rotation.x, 1, 0, 0)
        rl.rlRotatef(ship.rotation.z, 0, 0, 1)

        # Body
        rl.DrawCube(rl.Vector3(0,0,0), 1, 0.5, 2, rl.SKYBLUE)
        
        # Wings
        rl.DrawCube(rl.Vector3(0,0,0), 3, 0.1, 0.5, rl.DARKGRAY)

        # Engine Glow
        glow_color = rl.ColorAlpha(rl.SKYBLUE, self.state['throttle'])
        rl.DrawCube(rl.Vector3(0,0, -1.1), 0.8, 0.4, 0.1, glow_color)

        rl.rlPopMatrix()

    def spawn_manager(self):
        if not self.state['playing']: return
        if random.random() < 0.02:
            pos = rl.Vector3Add(self.player.position, rl.Vector3Scale(rl.Vector3(random.uniform(-1,1), random.uniform(-1,1), 1), 200))
            if random.random() > 0.7: 
                enemy = Enemy(pos, self.enemy_mesh, self.enemy_material)
                self.state["enemies"].append(enemy)
            else: 
                asteroid = Asteroid(pos, self.asteroid_mesh, self.asteroid_material)
                self.state["asteroids"].append(asteroid)

    def take_damage(self, amount):
        self.state['last_damage_time'] = rl.GetTime()
        if self.state['shields'] > 0:
            self.state['shields'] = max(0, self.state['shields'] - amount)
        else:
            self.state['hull'] = max(0, self.state['hull'] - amount)
        
        if self.state['hull'] <= 0:
            self.game_over()

    def game_over(self):
        self.state['playing'] = False
        self.generate_ai_text(f"Generate a sarcastic sci-fi death log for a pilot who died with Score: {self.state['score']}. Max 15 words.", "death_text")

    def check_collisions(self):
        # Projectile collisions
        for p in self.state["projectiles"][:]:
            if not p.is_enemy:
                for e in self.state["enemies"][:]:
                    if rl.CheckCollisionSpheres(p.position, p.radius, e.position, e.radius):
                        e.hp -= 1
                        self.state["explosions"].append(Explosion(p.position))
                        if p in self.state["projectiles"]: self.state["projectiles"].remove(p)
                        if e.hp <= 0:
                            self.state["explosions"].append(Explosion(e.position, scale=3))
                            if e in self.state["enemies"]: self.state["enemies"].remove(e)
                            self.state["score"] += 100
                            self.state["kills"] += 1
                for a in self.state["asteroids"][:]:
                    if rl.CheckCollisionSpheres(p.position, p.radius, a.position, a.radius):
                        a.hp -= 1
                        self.state["explosions"].append(Explosion(p.position))
                        if p in self.state["projectiles"]: self.state["projectiles"].remove(p)
                        if a.hp <= 0:
                            self.state["explosions"].append(Explosion(a.position, scale=3))
                            if a in self.state["asteroids"]: self.state["asteroids"].remove(a)
                            self.state["score"] += 50
            else:
                if rl.CheckCollisionSpheres(p.position, p.radius, self.player.position, self.player.radius):
                    self.take_damage(10)
                    self.state["explosions"].append(Explosion(p.position))
                    if p in self.state["projectiles"]: self.state["projectiles"].remove(p)
                    
        # Asteroid-player collision
        for a in self.state["asteroids"][:]:
            if rl.CheckCollisionSpheres(a.position, a.radius, self.player.position, self.player.radius):
                self.take_damage(20)
                self.state["explosions"].append(Explosion(a.position, scale=3))
                if a in self.state["asteroids"]: self.state["asteroids"].remove(a)

        # Missile collisions
        for m in self.state["missiles"][:]:
            if m.target and m.target.hp > 0:
                if rl.CheckCollisionSpheres(m.position, m.radius, m.target.position, m.target.radius):
                    m.target.hp -= 5
                    self.state["explosions"].append(Explosion(m.position, scale=3))
                    if m in self.state["missiles"]: self.state["missiles"].remove(m)
                    if m.target.hp <= 0:
                        self.state["explosions"].append(Explosion(m.target.position, scale=5))
                        if m.target in self.state["enemies"]: self.state["enemies"].remove(m.target)
                        if m.target in self.state["asteroids"]: self.state["asteroids"].remove(m.target)
                        self.state["score"] += 300
                        self.state["kills"] += 1

    def draw_radar(self):
        radar_radius = 80
        cx = self.screen_width - 100
        cy = self.screen_height - 100
        radar_range = 500.0

        rl.DrawCircle(cx, cy, radar_radius, rl.Fade(rl.BLACK, 0.5))
        rl.DrawCircleLines(cx, cy, radar_radius, rl.SKYBLUE)
        rl.DrawCircle(cx, cy, 2, rl.WHITE)

        player_yaw_rad = math.radians(self.player.rotation.y)

        def draw_blips(entities, color):
            for e in entities:
                dx = e.position.x - self.player.position.x
                dz = e.position.z - self.player.position.z
                dist = math.sqrt(dx*dx + dz*dz)
                
                if dist > radar_range: continue

                angle = math.atan2(dx, dz)
                rel_angle = angle - player_yaw_rad
                
                rx = math.sin(rel_angle) * dist
                ry = math.cos(rel_angle) * dist
                
                screen_x = cx + (rx / radar_range) * radar_radius
                screen_y = cy - (ry / radar_range) * radar_radius
                
                rl.DrawCircle(int(screen_x), int(screen_y), 3, color)

        draw_blips(self.state["enemies"], rl.RED)
        draw_blips(self.state["asteroids"], rl.GRAY)
        draw_blips(self.state["missiles"], rl.YELLOW)

    def draw_minimap(self):
        map_size = 150
        cx = self.screen_width - map_size - 20
        cy = map_size + 20
        
        rl.DrawRectangle(cx - map_size//2, cy - map_size//2, map_size, map_size, rl.Fade(rl.BLACK, 0.5))
        rl.DrawRectangleLines(cx - map_size//2, cy - map_size//2, map_size, map_size, rl.SKYBLUE)
        rl.DrawText("SYSTEM MAP", cx - 40, cy - map_size//2 - 15, 10, rl.SKYBLUE)
        
        max_dist = 2000
        if self.planets:
            max_dist = max(p.data['dist'] for p in self.planets) + 200
            
        scale = (map_size / 2) / max_dist
        
        # Draw Sun
        rl.DrawCircle(cx, cy, 4, rl.YELLOW)
        
        for p in self.planets:
            if p.data['dist'] == 0: continue
            mx = cx + int(p.position.x * scale)
            my = cy + int(p.position.z * scale)
            rl.DrawCircle(int(mx), int(my), 2, p.data['color'])
            
        px = cx + int(self.player.position.x * scale)
        py = cy + int(self.player.position.z * scale)
        rl.DrawCircle(int(px), int(py), 3, rl.GREEN)

    def generate_planet_quests(self, planet):
        if planet.available_quests: return
        
        targets = [p for p in self.planets if p != planet and p.data['dist'] > 0]
        if not targets: return
        
        num_quests = random.randint(1, 3)
        for _ in range(num_quests):
            target = random.choice(targets)
            item = random.choice(["Fuel", "Minerals", "Food", "Tech"])
            amount = random.randint(2, 10)
            reward = amount * planet.market.get(item, 10) * 2 + 100
            planet.available_quests.append({
                "target": target.data['name'],
                "item": item,
                "amount": amount,
                "reward": reward,
                "desc": f"Deliver {amount} {item} to {target.data['name']}"
            })

    def draw_trading_ui(self):
        cx, cy = self.screen_width // 2, self.screen_height // 2
        rl.DrawRectangle(cx - 300, cy - 200, 600, 400, rl.Fade(rl.BLACK, 0.9))
        rl.DrawRectangleLines(cx - 300, cy - 200, 600, 400, rl.SKYBLUE)
        
        planet = self.state['target_planet']
        rl.DrawText(f"MARKET: {planet.data['name']}", cx - 280, cy - 180, 20, rl.WHITE)
        rl.DrawText(f"CREDITS: {self.state['credits']}", cx + 100, cy - 180, 20, rl.GREEN)
        
        y = cy - 130
        rl.DrawText("ITEM", cx - 280, y, 20, rl.GRAY)
        rl.DrawText("PRICE", cx - 100, y, 20, rl.GRAY)
        rl.DrawText("OWNED", cx, y, 20, rl.GRAY)
        
        y += 30
        for item, price in planet.market.items():
            rl.DrawText(item, cx - 280, y, 20, rl.WHITE)
            rl.DrawText(str(price), cx - 100, y, 20, rl.YELLOW)
            owned = self.state['inventory'].get(item, 0)
            rl.DrawText(str(owned), cx, y, 20, rl.WHITE)
            
            # Buy Button
            buy_rect = rl.Rectangle(cx + 80, y, 60, 20)
            rl.DrawRectangleRec(buy_rect, rl.GREEN)
            rl.DrawText("BUY", int(buy_rect.x + 10), int(buy_rect.y + 2), 10, rl.BLACK)
            
            # Sell Button
            sell_rect = rl.Rectangle(cx + 150, y, 60, 20)
            rl.DrawRectangleRec(sell_rect, rl.RED)
            rl.DrawText("SELL", int(sell_rect.x + 10), int(sell_rect.y + 2), 10, rl.BLACK)
            
            if rl.IsMouseButtonPressed(rl.MOUSE_LEFT_BUTTON):
                mp = rl.GetMousePosition()
                if rl.CheckCollisionPointRec(mp, buy_rect):
                    if self.state['credits'] >= price:
                        self.state['credits'] -= price
                        self.state['inventory'][item] = owned + 1
                elif rl.CheckCollisionPointRec(mp, sell_rect):
                    if owned > 0:
                        self.state['credits'] += price
                        self.state['inventory'][item] = owned - 1
            
            y += 40
            
        # --- QUEST SECTION ---
        self.generate_planet_quests(planet)
        qy = cy + 40
        rl.DrawLine(cx - 280, qy, cx + 280, qy, rl.GRAY)
        qy += 10
        rl.DrawText("MISSIONS", cx - 280, qy, 20, rl.GRAY)
        qy += 30
        
        # Available Quests
        for q in planet.available_quests[:]:
            rl.DrawText(q['desc'], cx - 280, qy, 10, rl.WHITE)
            rl.DrawText(f"${q['reward']}", cx - 50, qy, 10, rl.GREEN)
            
            accept_rect = rl.Rectangle(cx + 20, qy, 50, 15)
            rl.DrawRectangleRec(accept_rect, rl.BLUE)
            rl.DrawText("ACCEPT", int(accept_rect.x + 5), int(accept_rect.y + 2), 10, rl.WHITE)
            
            if rl.IsMouseButtonPressed(rl.MOUSE_LEFT_BUTTON):
                if rl.CheckCollisionPointRec(rl.GetMousePosition(), accept_rect):
                    self.state['active_quests'].append(q)
                    planet.available_quests.remove(q)
            qy += 20
            
        # Active Quests Completion
        qy += 10
        rl.DrawText("ACTIVE QUESTS", cx - 280, qy, 20, rl.GRAY)
        qy += 30
        for q in self.state['active_quests'][:]:
            color = rl.WHITE
            status = "IN PROGRESS"
            
            if q['target'] == planet.data['name']:
                if self.state['inventory'].get(q['item'], 0) >= q['amount']:
                    status = "COMPLETE"
                    color = rl.GREEN
                    
                    comp_rect = rl.Rectangle(cx + 20, qy, 60, 15)
                    rl.DrawRectangleRec(comp_rect, rl.GREEN)
                    rl.DrawText("FINISH", int(comp_rect.x + 5), int(comp_rect.y + 2), 10, rl.BLACK)
                    
                    if rl.IsMouseButtonPressed(rl.MOUSE_LEFT_BUTTON):
                        if rl.CheckCollisionPointRec(rl.GetMousePosition(), comp_rect):
                            self.state['inventory'][q['item']] -= q['amount']
                            self.state['credits'] += q['reward']
                            self.state['active_quests'].remove(q)
                else:
                    status = "MISSING ITEMS"
                    color = rl.RED
            
            rl.DrawText(f"{q['desc']} ({status})", cx - 280, qy, 10, color)
            qy += 20

        rl.DrawText("Press ESC to Undock", cx - 280, cy + 170, 20, rl.GRAY)

    def draw_warp_menu(self):
        cx, cy = self.screen_width // 2, self.screen_height // 2
        w, h = 600, 400
        rl.DrawRectangle(cx - w//2, cy - h//2, w, h, rl.Fade(rl.BLACK, 0.9))
        rl.DrawRectangleLines(cx - w//2, cy - h//2, w, h, rl.SKYBLUE)
        rl.DrawText("WARP NAVIGATION", cx - 100, cy - h//2 + 20, 20, rl.SKYBLUE)
        
        # Systems
        rl.DrawText("SYSTEMS", cx - 200, cy - h//2 + 60, 20, rl.GRAY)
        for i, sys_name in enumerate(self.system_names):
            color = rl.GREEN if sys_name in self.state['location'] else rl.WHITE
            rl.DrawText(sys_name, cx - 250, cy - h//2 + 90 + i * 30, 20, color)
            
        # Planets
        rl.DrawText("PLANETS", cx + 50, cy - h//2 + 60, 20, rl.GRAY)
        for i, p in enumerate(self.planets):
            rl.DrawText(p.data['name'], cx + 20, cy - h//2 + 90 + i * 30, 20, rl.WHITE)

    def update_warp_menu(self):
        cx, cy = self.screen_width // 2, self.screen_height // 2
        h = 400
        
        if rl.IsMouseButtonPressed(rl.MOUSE_LEFT_BUTTON):
            mp = rl.GetMousePosition()
            
            # Check Systems
            for i, sys_name in enumerate(self.system_names):
                rect = rl.Rectangle(cx - 250, cy - h//2 + 90 + i * 30, 200, 25)
                if rl.CheckCollisionPointRec(mp, rect):
                    if sys_name not in self.state['location']:
                        self.initiate_warp(sys_name)
                        return

            # Check Planets
            for i, p in enumerate(self.planets):
                rect = rl.Rectangle(cx + 20, cy - h//2 + 90 + i * 30, 200, 25)
                if rl.CheckCollisionPointRec(mp, rect):
                    self.initiate_warp(p)
                    return

    def initiate_warp(self, destination):
        self.warp_menu_active = False
        self.hyperspace_timer = 3.0
        self.pending_warp_destination = destination
        self.state["comms_text"] = "WARP DRIVE ENGAGED"

    def draw_menu(self):
        cx = self.screen_width // 2
        cy = self.screen_height // 2
        
        rl.DrawText("COSMIC DODGER", cx - 150, cy - 150, 40, rl.SKYBLUE)
        
        # Start Button
        start_rect = rl.Rectangle(cx - 100, cy - 80, 200, 40)
        mouse_pos = rl.GetMousePosition()
        start_hover = rl.CheckCollisionPointRec(mouse_pos, start_rect)
        rl.DrawRectangleRec(start_rect, rl.LIGHTGRAY if start_hover else rl.GRAY)
        btn_text = "RESUME" if self.state['playing'] and self.state['hull'] > 0 else "START"
        rl.DrawText(btn_text, int(start_rect.x + 60), int(start_rect.y + 10), 20, rl.WHITE)
        
        # Save Button (Only if playing)
        if self.state['playing'] and self.state['hull'] > 0:
            save_rect = rl.Rectangle(cx - 100, cy - 30, 200, 40)
            save_hover = rl.CheckCollisionPointRec(mouse_pos, save_rect)
            rl.DrawRectangleRec(save_rect, rl.LIGHTGRAY if save_hover else rl.GRAY)
            rl.DrawText("SAVE", int(save_rect.x + 75), int(save_rect.y + 10), 20, rl.WHITE)

        # Load Button
        load_rect = rl.Rectangle(cx - 100, cy + 20, 200, 40)
        load_hover = rl.CheckCollisionPointRec(mouse_pos, load_rect)
        rl.DrawRectangleRec(load_rect, rl.LIGHTGRAY if load_hover else rl.GRAY)
        rl.DrawText("LOAD", int(load_rect.x + 75), int(load_rect.y + 10), 20, rl.WHITE)
        
        # Quit Button
        quit_rect = rl.Rectangle(cx - 100, cy + 70, 200, 40)
        quit_hover = rl.CheckCollisionPointRec(mouse_pos, quit_rect)
        rl.DrawRectangleRec(quit_rect, rl.LIGHTGRAY if quit_hover else rl.GRAY)
        rl.DrawText("QUIT", int(quit_rect.x + 75), int(quit_rect.y + 10), 20, rl.WHITE)

    def update_menu(self):
        cx = self.screen_width // 2
        cy = self.screen_height // 2
        if rl.IsMouseButtonPressed(rl.MOUSE_LEFT_BUTTON):
            mp = rl.GetMousePosition()
            
            # Start/Resume
            if rl.CheckCollisionPointRec(mp, rl.Rectangle(cx - 100, cy - 80, 200, 40)):
                self.in_menu = False
                if not self.state['playing']:
                    # Reset game state
                    self.state['playing'] = True
                    self.state['hull'] = 100
                    self.state['shields'] = 100
                    self.state['score'] = 0
                    self.state['enemies'] = []
                    self.state['asteroids'] = []
                    self.state['projectiles'] = []
                    self.state['missiles'] = []
                    self.state['explosions'] = []
                    self.player.position = rl.Vector3(0, 0, 0)
                    self.load_system(self.system_names[0])
            
            # Save
            elif self.state['playing'] and self.state['hull'] > 0 and rl.CheckCollisionPointRec(mp, rl.Rectangle(cx - 100, cy - 30, 200, 40)):
                self.save_game()
                
            # Load
            elif rl.CheckCollisionPointRec(mp, rl.Rectangle(cx - 100, cy + 20, 200, 40)):
                self.load_game()
                
            # Quit
            elif rl.CheckCollisionPointRec(mp, rl.Rectangle(cx - 100, cy + 70, 200, 40)):
                self.should_quit = True

    def save_game(self):
        data = {
            "player": {
                "position": [self.player.position.x, self.player.position.y, self.player.position.z],
                "rotation": [self.player.rotation.x, self.player.rotation.y, self.player.rotation.z]
            },
            "system_idx": self.current_system_idx,
            "target_planet_name": self.state['target_planet'].data['name'] if self.state['target_planet'] else None,
            "state": {k: v for k, v in self.state.items() if k not in [
                "enemies", "asteroids", "projectiles", "missiles", "explosions", "particles", "target_planet", "orbit_target"
            ]}
        }
        try:
            with open("savegame.json", "w") as f:
                json.dump(data, f)
            self.state["comms_text"] = "Game Saved."
        except Exception as e:
            print(f"Save failed: {e}")
            self.state["comms_text"] = "Save failed."

    def load_game(self):
        if not os.path.exists("savegame.json"):
            self.state["comms_text"] = "No save file found."
            return
        
        try:
            with open("savegame.json", "r") as f:
                data = json.load(f)
            
            self.current_system_idx = data["system_idx"]
            self.load_system(self.system_names[self.current_system_idx])
            
            p_pos = data["player"]["position"]
            self.player.position = rl.Vector3(p_pos[0], p_pos[1], p_pos[2])
            p_rot = data["player"]["rotation"]
            self.player.rotation = rl.Vector3(p_rot[0], p_rot[1], p_rot[2])
            
            saved_state = data["state"]
            for k, v in saved_state.items():
                self.state[k] = v
            
            # Restore target planet reference
            target_name = data.get("target_planet_name")
            if target_name:
                self.state['target_planet'] = next((p for p in self.planets if p.data['name'] == target_name), None)
            
            # Reset non-serialized lists
            self.state["enemies"] = []
            self.state["asteroids"] = []
            self.state["projectiles"] = []
            self.state["missiles"] = []
            self.state["explosions"] = []
            self.state["particles"] = []
            
            self.in_menu = False
            self.state["playing"] = True
            self.state["comms_text"] = "Game Loaded."
            
        except Exception as e:
            print(f"Load failed: {e}")
            self.state["comms_text"] = "Load failed."

    def draw_ui(self):
        if self.state['docked']:
            self.draw_trading_ui()
            return

        rl.DrawLine(self.screen_width // 2, self.screen_height // 2 - 10, self.screen_width // 2, self.screen_height // 2 + 10, rl.SKYBLUE)
        rl.DrawLine(self.screen_width // 2 - 10, self.screen_height // 2, self.screen_width // 2 + 10, self.screen_height // 2, rl.SKYBLUE)

        rl.DrawText(f"SCORE: {self.state['score']} | KILLS: {self.state['kills']}", 20, 20, 20, rl.LIGHTGRAY)
        rl.DrawText(f"LOC: {self.state['location']}", 20, 50, 20, rl.SKYBLUE)
        rl.DrawText(f"CR: {self.state['credits']}", 20, 80, 20, rl.GREEN)
        
        # Comms text
        rl.DrawRectangle(self.screen_width // 2 - 200, 20, 400, 40, rl.Fade(rl.BLACK, 0.5))
        rl.DrawText(self.state["comms_text"], self.screen_width // 2 - 190, 30, 20, rl.WHITE)

        # Health and shield bars
        rl.DrawRectangle(self.screen_width // 2 - 100, self.screen_height - 40, 200, 10, rl.DARKGRAY)
        rl.DrawRectangle(self.screen_width // 2 - 100, self.screen_height - 40, int(200 * self.state['hull'] / 100), 10, rl.GREEN)
        rl.DrawRectangle(self.screen_width // 2 - 100, self.screen_height - 60, 200, 10, rl.DARKGRAY)
        rl.DrawRectangle(self.screen_width // 2 - 100, self.screen_height - 60, int(200 * self.state['shields'] / 100), 10, rl.SKYBLUE)
        
        rl.DrawText(f"SPD: {int(self.state['throttle'] * 1000)} m/s", self.screen_width // 2 - 50, self.screen_height - 90, 20, rl.LIGHTGRAY)
        
        if not self.state['playing']:
            rl.DrawRectangle(0, 0, self.screen_width, self.screen_height, rl.Fade(rl.BLACK, 0.8))
            rl.DrawText("MISSION FAILED", self.screen_width // 2 - 150, self.screen_height // 2 - 40, 40, rl.RED)
            rl.DrawText(self.state["death_text"], self.screen_width // 2 - 200, self.screen_height // 2 + 20, 20, rl.WHITE)

        if self.state['target_planet']:
            dist = rl.Vector3Distance(self.player.position, self.state['target_planet'].position)
            rl.DrawText(f"TARGET: {self.state['target_planet'].data['name']} ({int(dist)}m)", self.screen_width // 2 - 100, self.screen_height // 2 + 100, 20, rl.YELLOW)
            if self.state['target_planet'].data['dist'] > 0 and dist < self.state['target_planet'].data['scale'] * 3 + 20:
                rl.DrawText("PRESS F TO DOCK", self.screen_width // 2 - 80, self.screen_height // 2 + 130, 20, rl.GREEN)

        self.draw_radar()
        self.draw_minimap()

    def update(self):
        if self.in_menu:
            self.update_menu()
            return

        if self.state['docked']:
            if rl.is_key_pressed(rl.KEY_ESCAPE):
                self.state['docked'] = False
            return

        if rl.is_key_pressed(rl.KEY_ESCAPE):
            self.in_menu = True
            return

        if rl.IsKeyPressed(rl.KEY_TAB):
            self.warp_menu_active = not self.warp_menu_active
        
        if self.warp_menu_active:
            self.update_warp_menu()
            return

        dt = rl.GetFrameTime()

        if self.state['playing']:
            # Planet Selection
            if rl.IsMouseButtonPressed(rl.MOUSE_LEFT_BUTTON):
                ray = rl.GetScreenToWorldRay(rl.GetMousePosition(), self.camera)
                best_hit = None
                min_dist = float('inf')
                for p in self.planets:
                    coll = rl.GetRayCollisionSphere(ray, p.position, p.data['scale'])
                    if coll.hit and coll.distance < min_dist:
                        min_dist = coll.distance
                        best_hit = p
                if best_hit:
                    self.state['target_planet'] = best_hit
                    self.state['comms_text'] = f"Target locked: {best_hit.data['name']}"

            # Docking Logic
            if self.state['target_planet']:
                dist = rl.Vector3Distance(self.player.position, self.state['target_planet'].position)
                if self.state['target_planet'].data['dist'] > 0 and dist < self.state['target_planet'].data['scale'] * 3 + 20:
                    if rl.IsKeyPressed(rl.KEY_F):
                        self.state['docked'] = True
                        self.state['throttle'] = 0
                        self.state['comms_text'] = f"Docked at {self.state['target_planet'].data['name']}"

            self.spawn_manager()
            self.check_collisions()
            
            if self.hyperspace_timer <= 0:
                for p in self.planets:
                    if rl.Vector3Distance(self.player.position, p.position) < p.data['scale'] * 4:
                        self.state["location"] = f"{p.data['name']} ORBIT"
            
            # Throttle Logic
            if rl.IsKeyDown(rl.KEY_LEFT_SHIFT): self.state['throttle'] = min(1.0, self.state['throttle'] + dt * 0.5)
            if rl.IsKeyDown(rl.KEY_LEFT_CONTROL): self.state['throttle'] = max(0.0, self.state['throttle'] - dt * 0.5)

            # Shield Recharge
            if rl.GetTime() - self.state['last_damage_time'] > 5.0:
                if self.state['shields'] < 100:
                    self.state['shields'] = min(100, self.state['shields'] + 15 * dt)

            # Calculate forward vector from rotation
            pitch = math.radians(self.player.rotation.x)
            yaw = math.radians(self.player.rotation.y)
            
            forward = rl.Vector3(
                math.sin(yaw) * math.cos(pitch),
                -math.sin(pitch),
                math.cos(yaw) * math.cos(pitch)
            )

            # Hyperspace Logic
            if rl.IsKeyPressed(rl.KEY_J) and self.state['throttle'] > 0.5 and self.hyperspace_timer <= 0:
                self.hyperspace_timer = 3.0
                self.state["comms_text"] = "HYPERSPACE DRIVE ENGAGED"
            
            if self.hyperspace_timer > 0:
                self.hyperspace_timer -= dt
                self.state['throttle'] = 1.0 # Force max throttle
                if self.hyperspace_timer <= 0:
                    if self.pending_warp_destination:
                        if isinstance(self.pending_warp_destination, str):
                            # Warp to System
                            self.current_system_idx = self.system_names.index(self.pending_warp_destination)
                            self.load_system(self.pending_warp_destination)
                            self.player.position = rl.Vector3(0, 0, 1000)
                        elif isinstance(self.pending_warp_destination, Planet):
                            # Warp to Planet
                            offset = rl.Vector3(self.pending_warp_destination.data['scale']*4 + 50, 0, 0)
                            self.player.position = rl.Vector3Add(self.pending_warp_destination.position, offset)
                        self.pending_warp_destination = None
                    else:
                        self.current_system_idx = (self.current_system_idx + 1) % len(self.system_names)
                        self.load_system(self.system_names[self.current_system_idx])
                        self.player.position = rl.Vector3(0, 0, 1000) # Reset position slightly away from sun

            # Input
            if rl.IsKeyPressed(rl.KEY_SPACE):
                # Fire Lasers
                self.state["projectiles"].append(Projectile(rl.Vector3Add(self.player.position, rl.Vector3Scale(forward, 2)), forward))
            
            if rl.IsKeyPressed(rl.KEY_M):
                # Fire Missile
                targets = self.state["enemies"] + self.state["asteroids"]
                if targets:
                    closest = min(targets, key=lambda t: rl.Vector3Distance(self.player.position, t.position))
                    self.state["missiles"].append(Missile(self.player.position, forward, closest))

            # Rotation
            pitch_speed = (rl.IsKeyDown(rl.KEY_S) - rl.IsKeyDown(rl.KEY_W)) * 100
            yaw_speed = (rl.IsKeyDown(rl.KEY_D) - rl.IsKeyDown(rl.KEY_A)) * 100
            roll_speed = (rl.IsKeyDown(rl.KEY_E) - rl.IsKeyDown(rl.KEY_Q)) * 100

            if roll_speed == 0:
                roll_speed = -yaw_speed * 1.5

            self.player.rotation.x += pitch_speed * dt * 0.5
            self.player.rotation.y += yaw_speed * dt * 0.5
            self.player.rotation.z += roll_speed * dt * 0.5

            # Forward Motion
            speed = self.state['throttle'] * 100
            self.player.position = rl.Vector3Add(self.player.position, rl.Vector3Scale(forward, speed * dt))
            
            # Engine Particles
            if self.state['throttle'] > 0:
                offset = rl.Vector3Scale(forward, -1.2)
                spawn_pos = rl.Vector3Add(self.player.position, offset)
                for _ in range(int(self.state['throttle'] * 3) + 1):
                    p_vel = rl.Vector3Add(rl.Vector3Scale(forward, -20 * self.state['throttle']), 
                                         rl.Vector3(random.uniform(-2,2), random.uniform(-2,2), random.uniform(-2,2)))
                    self.state["particles"].append(Particle(spawn_pos, p_vel, rl.SKYBLUE, random.uniform(0.1, 0.3), random.uniform(0.3, 0.6)))

        for p in self.planets:
            p.update(dt)
            
        for e in self.state["enemies"][:]:
            e.update(dt, self.player, self.state)
        
        for a in self.state["asteroids"][:]:
            a.update(dt, self.player, self.state)
            
        for p in self.state["projectiles"][:]:
            p.update(dt, self.state)
            
        for m in self.state["missiles"][:]:
            m.update(dt, self.state)
            
        for ex in self.state["explosions"][:]:
            ex.update(dt, self.state)
            
        for p in self.state["particles"][:]:
            p.update(dt)
            if p.lifetime <= 0:
                self.state["particles"].remove(p)

    def draw(self):
        # Update camera
        cam_pos_offset = rl.Vector3(0, 5, -15)
        
        # Camera rotation matrix
        cam_rot_mat = rl.MatrixMultiply(
            rl.MatrixRotateZ(math.radians(self.player.rotation.z)),
            rl.MatrixMultiply(
                rl.MatrixRotateX(math.radians(self.player.rotation.x)),
                rl.MatrixRotateY(math.radians(self.player.rotation.y))
            )
        )
        
        transformed_offset = rl.Vector3Transform(cam_pos_offset, cam_rot_mat)
        self.camera.position = rl.Vector3Add(self.player.position, transformed_offset)
        self.camera.target = self.player.position

        # Draw
        rl.BeginDrawing()
        rl.ClearBackground(rl.BLACK)

        if self.in_menu:
            self.draw_menu()
            rl.EndDrawing()
            return

        rl.BeginMode3D(self.camera)
        rl.rlSetClipPlanes(0.1, 10000.0)

        # Calculate forward vector for warp effect
        pitch = math.radians(self.player.rotation.x)
        yaw = math.radians(self.player.rotation.y)
        forward = rl.Vector3(
            math.sin(yaw) * math.cos(pitch),
            -math.sin(pitch),
            math.cos(yaw) * math.cos(pitch)
        )

        # Draw Starfield (Skybox)
        rl.rlPushMatrix()
        rl.rlTranslatef(self.player.position.x, self.player.position.y, self.player.position.z)
        rl.rlBegin(1) # RL_LINES
        rl.rlColor4ub(255, 255, 255, 255)
        
        warp_stretch = 2.0 + (self.state['throttle'] * 100.0) if self.state['throttle'] > 0.1 else 0.0
        if self.hyperspace_timer > 0: warp_stretch = 500.0 + (3.0 - self.hyperspace_timer) * 500.0

        for s in self.stars:
            rl.rlVertex3f(s.x, s.y, s.z)
            end_pos = rl.Vector3Subtract(s, rl.Vector3Scale(forward, warp_stretch))
            rl.rlVertex3f(end_pos.x, end_pos.y, end_pos.z)
        rl.rlEnd()
        rl.rlPopMatrix()

        self.draw_ship(self.player)
        
        for p in self.planets:
            transform = rl.MatrixMultiply(rl.MatrixScale(p.data['scale'], p.data['scale'], p.data['scale']), rl.MatrixTranslate(p.position.x, p.position.y, p.position.z))
            rl.DrawMesh(p.mesh, p.material, transform)
            if p.data.get('ring'):
                rl.DrawCircle3D(p.position, p.data['scale'] * 1.5, rl.Vector3(1,0,0), 90, rl.Color(200,200,200,150))
        
        for e in self.state["enemies"]:
            direction = rl.Vector3Subtract(self.player.position, e.position)
            angle = math.atan2(direction.x, direction.z) * rl.RAD2DEG
            
            rl.rlPushMatrix()
            rl.rlTranslatef(e.position.x, e.position.y, e.position.z)
            rl.rlRotatef(angle, 0, 1, 0)
            rl.rlRotatef(90, 1, 0, 0)
            rl.DrawMesh(e.mesh, e.material, rl.MatrixIdentity())
            rl.rlPopMatrix()

            
        for a in self.state["asteroids"]:
            transform = rl.MatrixMultiply(rl.MatrixRotateXYZ(a.rotation), rl.MatrixTranslate(a.position.x, a.position.y, a.position.z))
            rl.DrawMesh(a.mesh, a.material, transform)

        for p in self.state["projectiles"]:
            rl.DrawSphere(p.position, p.radius, p.color)
            
        for m in self.state["missiles"]:
            rl.DrawCube(m.position, 0.3, 0.3, 1, m.color)
            
        for ex in self.state["explosions"]:
            rl.DrawSphere(ex.position, ex.scale * (ex.life / ex.duration), rl.ColorAlpha(rl.ORANGE, 1 - (ex.life / ex.duration)))
            
        for p in self.state["particles"]:
            alpha = p.lifetime / p.max_lifetime
            col = rl.ColorAlpha(p.color, alpha)
            rl.DrawCube(p.position, p.size, p.size, p.size, col)

        rl.DrawGrid(100, 10.0)
        rl.EndMode3D()
        
        self.draw_ui()
        if self.warp_menu_active:
            self.draw_warp_menu()
            
        rl.EndDrawing()

    def run(self):
        while not rl.WindowShouldClose() and not self.should_quit:
            self.update()
            self.draw()

def main():
    print("Starting game...")
    try:
        rl.InitWindow(1280, 720, "Solar Runner ")
        rl.SetTraceLogLevel(rl.LOG_INFO) # Enable info logs for debugging
        print("Window initialized.")
        game = Game()
        print("Game object created. Running...")
        game.run()
    except Exception as e:
        print(f"Game Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        rl.CloseWindow()

if __name__ == '__main__':
    main()