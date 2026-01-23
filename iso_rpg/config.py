import pyray as rl
import ctypes

def _ensure_pascal_case(module):
    mapping = {
        'InitWindow': 'init_window',
        'SetConfigFlags': 'set_config_flags',
        'SetTargetFPS': 'set_target_fps',
        'BeginDrawing': 'begin_drawing',
        'EndDrawing': 'end_drawing',
        'ClearBackground': 'clear_background',
        'DrawText': 'draw_text',
        'DrawTextEx': 'draw_text_ex',
        'MeasureText': 'measure_text',
        'MeasureTextEx': 'measure_text_ex',
        'DrawRectangle': 'draw_rectangle',
        'DrawRectangleRec': 'draw_rectangle_rec',
        'DrawRectangleLines': 'draw_rectangle_lines',
        'DrawRectangleLinesEx': 'draw_rectangle_lines_ex',
        'DrawRectangleGradientV': 'draw_rectangle_gradient_v',
        'DrawTexturePro': 'draw_texture_pro',
        'CheckCollisionPointRec': 'check_collision_point_rec',
        'GetMousePosition': 'get_mouse_position',
        'IsMouseButtonPressed': 'is_mouse_button_pressed',
        'IsMouseButtonReleased': 'is_mouse_button_released',
        'GetCharPressed': 'get_char_pressed',
        'IsKeyPressed': 'is_key_pressed',
        'GetMouseWheelMove': 'get_mouse_wheel_move',
        'BeginScissorMode': 'begin_scissor_mode',
        'EndScissorMode': 'end_scissor_mode',
        'LoadFontEx': 'load_font_ex',
        'SetTextureFilter': 'set_texture_filter',
        'LoadTexture': 'load_texture',
        'LoadTextureFromImage': 'load_texture_from_image',
        'GenImageChecked': 'gen_image_checked',
        'UnloadImage': 'unload_image',
        'WindowShouldClose': 'window_should_close',
        'GetScreenWidth': 'get_screen_width',
        'GetScreenHeight': 'get_screen_height',
        'GetFrameTime': 'get_frame_time',
        'GetFPS': 'get_fps',
        'Fade': 'fade',
        'UnloadTexture': 'unload_texture',
        'UnloadFont': 'unload_font',
        'CloseWindow': 'close_window'
    }

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

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
TILE_WIDTH = 64
TILE_HEIGHT = 32
CHUNK_SIZE = 32
WORLD_CHUNKS = 16
MAP_SIZE = CHUNK_SIZE * WORLD_CHUNKS
CAVE_MAP_SIZE = 12
BLOCK_TYPES = 256

# Colors
COLOR_BG = rl.Color(12, 7, 2, 255)
COLOR_GRASS_TOP = rl.Color(129, 199, 132, 255)
COLOR_GRASS_SIDE = rl.Color(102, 187, 106, 255)
COLOR_DIRT_TOP = rl.Color(141, 110, 99, 255)
COLOR_DIRT_SIDE = rl.Color(121, 85, 72, 255)
COLOR_SAND_TOP = rl.Color(240, 217, 181, 255)
COLOR_SAND_SIDE = rl.Color(218, 195, 153, 255)
COLOR_WATER_TOP = rl.Color(41, 182, 246, 255)
COLOR_WATER_SIDE = rl.Color(3, 169, 244, 255)
COLOR_STONE_FLOOR = rl.Color(117, 117, 117, 255)
COLOR_STONE_SIDE = rl.Color(97, 97, 97, 255)
COLOR_CAVE_WALL = rl.Color(74, 74, 74, 255)
COLOR_DUNGEON_FLOOR_TOP = rl.Color(60, 60, 70, 255)
COLOR_DUNGEON_FLOOR_SIDE = rl.Color(40, 40, 50, 255)
COLOR_TAIGA_GRASS_TOP = rl.Color(85, 139, 47, 255)
COLOR_TAIGA_GRASS_SIDE = rl.Color(68, 112, 38, 255)
COLOR_SWAMP_MUD_TOP = rl.Color(85, 74, 65, 255)
COLOR_SWAMP_MUD_SIDE = rl.Color(65, 56, 50, 255)
COLOR_SWAMP_WATER_TOP = rl.Color(60, 98, 85, 255)
COLOR_PINE_LEAVES = rl.Color(34, 87, 54, 255)
COLOR_TREE_TRUNK = rl.Color(93, 64, 55, 255)
COLOR_TREE_LEAVES = rl.Color(46, 125, 50, 255)
COLOR_ROCK_BASE = rl.Color(120, 144, 156, 255)
COLOR_ROCK_OUTLINE = rl.Color(69, 90, 100, 255)
COLOR_PLAYER_BODY = rl.Color(59, 130, 246, 255)
COLOR_PLAYER_SKIN = rl.Color(255, 204, 188, 255)
COLOR_PLAYER_HAIR = rl.Color(93, 64, 55, 255)
COLOR_PLAYER_PANTS = rl.Color(30, 41, 59, 255)
COLOR_NPC_BODY = rl.Color(211, 47, 47, 255)