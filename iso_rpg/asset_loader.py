import pyray as rl
import random
import ctypes
from config import *

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

class AssetLoader:
    def __init__(self):
        self.assets = {}
        self.block_definitions = []
        self.character_palettes = {
            'body': [rl.Color(59, 130, 246, 255), rl.Color(180, 90, 45, 255), rl.Color(100, 200, 100, 255), rl.Color(200, 100, 150, 255)],
            'skin': [rl.Color(255, 204, 188, 255), rl.Color(230, 190, 150, 255), rl.Color(210, 160, 110, 255), rl.Color(120, 80, 60, 255)],
            'hair': [rl.Color(93, 64, 55, 255), rl.Color(200, 180, 100, 255), rl.Color(60, 40, 80, 255), rl.Color(180, 100, 50, 255)],
            'pants': [rl.Color(30, 41, 59, 255), rl.Color(100, 80, 50, 255), rl.Color(70, 70, 70, 255), rl.Color(120, 40, 40, 255)]
        }
        self._generate_block_definitions()
        self.generate_assets()

    def _generate_block_definitions(self):
        base_materials = {
            'stone': {'base': COLOR_STONE_FLOOR, 'highlight': rl.Color(180, 180, 180, 255), 'shadow': COLOR_STONE_SIDE, 'height': 5, 'walkable': True},
            'dirt': {'base': COLOR_DIRT_TOP, 'highlight': rl.Color(180, 140, 130, 255), 'shadow': COLOR_DIRT_SIDE, 'height': 5, 'walkable': True},
            'grass': {'base': COLOR_GRASS_TOP, 'highlight': rl.Color(180, 230, 140, 255), 'shadow': COLOR_GRASS_SIDE, 'height': 5, 'walkable': True},
            'sand': {'base': COLOR_SAND_TOP, 'highlight': rl.Color(255, 240, 200, 255), 'shadow': rl.Color(200, 170, 130, 255), 'height': 5, 'walkable': True},
            'water': {'base': COLOR_WATER_TOP, 'highlight': rl.Color(100, 220, 255, 255), 'shadow': COLOR_WATER_SIDE, 'height': 0, 'walkable': False},
            'taiga_grass': {'base': COLOR_TAIGA_GRASS_TOP, 'highlight': rl.Color(120, 180, 70, 255), 'shadow': COLOR_TAIGA_GRASS_SIDE, 'height': 5, 'walkable': True},
            'swamp_mud': {'base': COLOR_SWAMP_MUD_TOP, 'highlight': rl.Color(120, 100, 85, 255), 'shadow': rl.Color(50, 35, 25, 255), 'height': 2, 'walkable': True},
            'swamp_water': {'base': COLOR_SWAMP_WATER_TOP, 'highlight': rl.Color(90, 140, 110, 255), 'shadow': rl.Color(30, 60, 50, 255), 'height': 0, 'walkable': False},
            'dungeon_floor': {'base': COLOR_DUNGEON_FLOOR_TOP, 'highlight': rl.Color(80, 80, 90, 255), 'shadow': COLOR_DUNGEON_FLOOR_SIDE, 'height': 5, 'walkable': True},
        }
        material_keys = list(base_materials.keys())
        for i in range(BLOCK_TYPES):
            mat_name = material_keys[i % len(material_keys)]
            base_def = base_materials[mat_name]
            var = (i * 37) % 40 - 20
            base_color = base_def['base']
            varied_base = rl.Color(max(0, min(255, base_color.r + var)), max(0, min(255, base_color.g + var)), max(0, min(255, base_color.b + var)), 255)
            new_def = {
                'material': mat_name,
                'color_base': varied_base,
                'color_highlight': rl.Color(max(0, min(255, base_def['highlight'].r + var)), max(0, min(255, base_def['highlight'].g + var)), max(0, min(255, base_def['highlight'].b + var)), 255),
                'color_shadow': base_def['shadow'],
                'height': base_def['height'], 
                'walkable': base_def['walkable'],
                'detail_type': 'none', 
                'detail_color': rl.BLANK
            }
            if new_def['walkable'] and (i % 10) < 3:
                new_def['detail_type'] = 'speckles'
                det_var = (i * 19) % 30 - 15
                new_def['detail_color'] = rl.Color(max(0, min(255, new_def['color_base'].r - det_var)), max(0, min(255, new_def['color_base'].g - det_var)), max(0, min(255, new_def['color_base'].b - det_var)), 180)
            self.block_definitions.append(new_def)

    def _create_block_texture(self, color_base, color_highlight, color_shadow, height=0, detail_type='none', detail_color=rl.BLANK, **kwargs):
        width, ch = TILE_WIDTH, TILE_HEIGHT
        img_height = ch + height + 10
        img = rl.gen_image_color(width, img_height, rl.BLANK)
        ox, oy = width // 2, ch // 2 + height
        top_pts = [rl.Vector2(ox, oy - ch // 2 - height), rl.Vector2(width, oy - height), rl.Vector2(ox, oy + ch // 2 - height), rl.Vector2(0, oy - height)]
        if height > 0:
            v = [rl.Vector2(0, oy - height), rl.Vector2(ox, oy + ch // 2 - height), rl.Vector2(ox, oy + ch // 2), rl.Vector2(0, oy)]
            rl.image_draw_triangle(img, v[0], v[1], v[3], color_shadow)
            rl.image_draw_triangle(img, v[1], v[2], v[3], color_shadow)
            right_shadow = rl.Color(max(0, min(255, int(color_shadow.r * 1.2))), max(0, min(255, int(color_shadow.g * 1.2))), max(0, min(255, int(color_shadow.b * 1.2))), 255)
            v = [rl.Vector2(width, oy - height), rl.Vector2(ox, oy + ch // 2 - height), rl.Vector2(ox, oy + ch // 2), rl.Vector2(width, oy)]
            rl.image_draw_triangle(img, v[0], v[1], v[3], right_shadow)
            rl.image_draw_triangle(img, v[1], v[2], v[3], right_shadow)
        rl.image_draw_triangle(img, top_pts[0], top_pts[1], top_pts[2], color_base)
        rl.image_draw_triangle(img, top_pts[0], top_pts[2], top_pts[3], color_highlight)
        if detail_type == 'speckles':
            for _ in range(15):
                dx = random.randint(width // 4, 3 * width // 4)
                dy = random.randint(int(oy - ch / 2.5), int(oy + ch / 2.5 - height))
                rl.image_draw_circle(img, dx, dy, random.choice([1, 1, 2]), detail_color)
        texture = rl.load_texture_from_image(img)
        rl.unload_image(img)
        return texture

    def create_character_sheet(self, body_idx=0, skin_idx=0, hair_idx=0, pants_idx=0):
        body_color = self.character_palettes['body'][body_idx % len(self.character_palettes['body'])]
        skin_color = self.character_palettes['skin'][skin_idx % len(self.character_palettes['skin'])]
        hair_color = self.character_palettes['hair'][hair_idx % len(self.character_palettes['hair'])]
        pants_color = self.character_palettes['pants'][pants_idx % len(self.character_palettes['pants'])]
        s = rl.gen_image_color(64, 64, rl.BLANK)
        # Left character (idle)
        rl.image_draw_circle(s, 13, 58, 8, rl.Color(0, 0, 0, 80))
        rl.image_draw_rectangle(s, 10, 48, 4, 10, rl.Color(0, 0, 0, 60)); rl.image_draw_rectangle(s, 10, 48, 3, 10, pants_color)
        rl.image_draw_rectangle(s, 16, 48, 4, 10, rl.Color(0, 0, 0, 60)); rl.image_draw_rectangle(s, 16, 48, 3, 10, pants_color)
        rl.image_draw_rectangle(s, 9, 35, 8, 13, rl.Color(0, 0, 0, 60)); rl.image_draw_rectangle(s, 9, 35, 8, 13, body_color)
        rl.image_draw_rectangle(s, 5, 37, 3, 10, rl.Color(0, 0, 0, 60)); rl.image_draw_rectangle(s, 5, 37, 3, 10, skin_color)
        rl.image_draw_rectangle(s, 19, 37, 3, 10, rl.Color(0, 0, 0, 60)); rl.image_draw_rectangle(s, 19, 37, 3, 10, skin_color)
        rl.image_draw_rectangle(s, 12, 30, 2, 5, rl.Color(0, 0, 0, 40)); rl.image_draw_rectangle(s, 12, 30, 2, 5, skin_color)
        rl.image_draw_circle(s, 13, 22, 7, rl.Color(0, 0, 0, 80)); rl.image_draw_circle(s, 13, 22, 7, skin_color)
        rl.image_draw_circle(s, 13, 18, 7, rl.Color(0, 0, 0, 60)); rl.image_draw_circle(s, 13, 18, 7, hair_color)
        rl.image_draw_rectangle(s, 7, 18, 12, 3, hair_color)
        rl.image_draw_circle(s, 10, 21, 1, rl.BLACK); rl.image_draw_circle(s, 16, 21, 1, rl.BLACK)
        rl.image_draw_circle(s, 10, 21, 0, rl.WHITE); rl.image_draw_circle(s, 16, 21, 0, rl.WHITE)
        rl.image_draw_line(s, 11, 25, 15, 25, rl.Color(100, 50, 50, 255))
        # Right character (walking)
        rl.image_draw_circle(s, 45, 58, 8, rl.Color(0, 0, 0, 80))
        rl.image_draw_rectangle(s, 42, 46, 4, 12, rl.Color(0, 0, 0, 60)); rl.image_draw_rectangle(s, 42, 46, 3, 12, pants_color)
        rl.image_draw_rectangle(s, 48, 50, 4, 8, rl.Color(0, 0, 0, 60)); rl.image_draw_rectangle(s, 48, 50, 3, 8, pants_color)
        rl.image_draw_rectangle(s, 41, 35, 8, 13, rl.Color(0, 0, 0, 60)); rl.image_draw_rectangle(s, 41, 35, 8, 13, body_color)
        rl.image_draw_rectangle(s, 37, 36, 3, 9, rl.Color(0, 0, 0, 60)); rl.image_draw_rectangle(s, 37, 36, 3, 9, skin_color)
        rl.image_draw_rectangle(s, 51, 38, 3, 11, rl.Color(0, 0, 0, 60)); rl.image_draw_rectangle(s, 51, 38, 3, 11, skin_color)
        rl.image_draw_rectangle(s, 44, 30, 2, 5, rl.Color(0, 0, 0, 40)); rl.image_draw_rectangle(s, 44, 30, 2, 5, skin_color)
        rl.image_draw_circle(s, 45, 22, 7, rl.Color(0, 0, 0, 80)); rl.image_draw_circle(s, 45, 22, 7, skin_color)
        rl.image_draw_circle(s, 45, 18, 7, rl.Color(0, 0, 0, 60)); rl.image_draw_circle(s, 45, 18, 7, hair_color)
        rl.image_draw_rectangle(s, 39, 18, 12, 3, hair_color)
        rl.image_draw_circle(s, 42, 21, 1, rl.BLACK); rl.image_draw_circle(s, 48, 21, 1, rl.BLACK)
        rl.image_draw_circle(s, 42, 21, 0, rl.WHITE); rl.image_draw_circle(s, 48, 21, 0, rl.WHITE)
        rl.image_draw_line(s, 43, 25, 47, 25, rl.Color(100, 50, 50, 255))
        return rl.load_texture_from_image(s)

    def generate_assets(self):
        self.assets['blocks'] = [self._create_block_texture(**d) for d in self.block_definitions]
        wall_base = rl.Color(80, 80, 90, 255); wall_highlight = rl.Color(120, 120, 140, 255); wall_shadow = rl.Color(50, 50, 60, 255)
        self.assets['wall'] = self._create_block_texture(wall_base, wall_highlight, wall_shadow, height=int(TILE_HEIGHT*1.5))
        dungeon_wall_base = rl.Color(50, 50, 65, 255); dungeon_wall_highlight = rl.Color(70, 70, 90, 255); dungeon_wall_shadow = rl.Color(30, 30, 40, 255)
        self.assets['dungeon_wall'] = self._create_block_texture(dungeon_wall_base, dungeon_wall_highlight, dungeon_wall_shadow, height=int(TILE_HEIGHT*1.5))
        
        img_ladder = rl.gen_image_color(64, 64, rl.BLANK)
        rl.image_draw_circle(img_ladder, 32, 48, 16, rl.BLACK); rl.image_draw_circle(img_ladder, 32, 48, 12, rl.Color(20, 10, 10, 255))
        rl.image_draw_rectangle(img_ladder, 20, 25, 4, 45, COLOR_TREE_TRUNK); rl.image_draw_rectangle(img_ladder, 40, 25, 4, 45, COLOR_TREE_TRUNK)
        for i in range(6): rl.image_draw_rectangle(img_ladder, 20, 30 + i * 7, 24, 3, rl.Color(100, 70, 40, 255))
        self.assets['ladder'] = rl.load_texture_from_image(img_ladder); rl.unload_image(img_ladder)

        img_tree = rl.gen_image_color(64, 128, rl.BLANK)
        rl.image_draw_rectangle(img_tree, 28, 65, 8, 45, rl.Color(70, 50, 35, 255)); rl.image_draw_rectangle(img_tree, 29, 65, 6, 45, COLOR_TREE_TRUNK)
        rl.image_draw_circle(img_tree, 32, 50, 22, rl.Color(30, 90, 30, 255)); rl.image_draw_circle(img_tree, 32, 48, 20, rl.Color(46, 125, 50, 255))
        rl.image_draw_circle(img_tree, 20, 55, 16, rl.Color(46, 125, 50, 255)); rl.image_draw_circle(img_tree, 44, 55, 16, rl.Color(46, 125, 50, 255))
        rl.image_draw_circle(img_tree, 32, 35, 18, rl.Color(80, 150, 60, 255)); rl.image_draw_circle(img_tree, 32, 35, 14, rl.Color(120, 180, 80, 255))
        rl.image_draw_circle(img_tree, 26, 28, 8, rl.Color(140, 200, 90, 255)); rl.image_draw_circle(img_tree, 38, 28, 8, rl.Color(140, 200, 90, 255))
        rl.image_draw_circle(img_tree, 32, 20, 6, rl.Color(160, 220, 110, 255))
        self.assets['tree'] = rl.load_texture_from_image(img_tree); rl.unload_image(img_tree)
        
        img_pine = rl.gen_image_color(64, 128, rl.BLANK)
        rl.image_draw_rectangle(img_pine, 28, 90, 8, 20, rl.Color(70, 50, 35, 255)); rl.image_draw_rectangle(img_pine, 29, 90, 6, 20, COLOR_TREE_TRUNK)
        rl.image_draw_triangle(img_pine, rl.Vector2(32, 40), rl.Vector2(12, 88), rl.Vector2(52, 88), COLOR_PINE_LEAVES)
        rl.image_draw_triangle(img_pine, rl.Vector2(32, 30), rl.Vector2(10, 75), rl.Vector2(54, 75), rl.Color(60, 130, 50, 255))
        rl.image_draw_triangle(img_pine, rl.Vector2(32, 20), rl.Vector2(8, 62), rl.Vector2(56, 62), rl.Color(80, 160, 60, 255))
        rl.image_draw_triangle(img_pine, rl.Vector2(32, 20), rl.Vector2(45, 50), rl.Vector2(50, 58), rl.Color(100, 180, 80, 255))
        rl.image_draw_triangle(img_pine, rl.Vector2(32, 20), rl.Vector2(35, 28), rl.Vector2(40, 35), rl.Color(120, 200, 80, 255))
        self.assets['pine_tree'] = rl.load_texture_from_image(img_pine); rl.unload_image(img_pine)
        
        img_rock = rl.gen_image_color(64, 64, rl.BLANK)
        rock_pts = [rl.Vector2(15, 50), rl.Vector2(18, 35), rl.Vector2(25, 25), rl.Vector2(35, 20), rl.Vector2(50, 28), rl.Vector2(58, 45), rl.Vector2(55, 60), rl.Vector2(35, 62), rl.Vector2(20, 58)]
        center_pt = rl.Vector2(32, 42)
        rock_colors = [rl.Color(70, 75, 90, 255), rl.Color(75, 80, 95, 255), rl.Color(80, 85, 100, 255), rl.Color(85, 90, 105, 255), rl.Color(100, 110, 130, 255), rl.Color(95, 105, 125, 255), rl.Color(90, 100, 120, 255), rl.Color(85, 95, 115, 255), rl.Color(80, 90, 110, 255)]
        for i in range(len(rock_pts)): rl.image_draw_triangle(img_rock, center_pt, rock_pts[i], rock_pts[(i + 1) % len(rock_pts)], rock_colors[i])
        rl.image_draw_triangle(img_rock, center_pt, rock_pts[1], rock_pts[2], rl.Color(125, 145, 165, 255))
        rl.image_draw_triangle(img_rock, center_pt, rock_pts[2], rock_pts[3], rl.Color(135, 160, 180, 255))
        rl.image_draw_triangle(img_rock, center_pt, rock_pts[3], rock_pts[4], rl.Color(140, 165, 185, 255))
        self.assets['rock'] = rl.load_texture_from_image(img_rock); rl.unload_image(img_rock)
        
        img_chest = rl.gen_image_color(64, 64, rl.BLANK)
        rl.image_draw_rectangle(img_chest, 17, 33, 30, 22, rl.Color(80, 60, 40, 255)); rl.image_draw_rectangle(img_chest, 16, 32, 32, 24, COLOR_TREE_TRUNK)
        rl.image_draw_rectangle(img_chest, 16, 32, 32, 4, rl.Color(180, 120, 80, 255)); rl.image_draw_rectangle_lines(img_chest, rl.Rectangle(16, 32, 32, 24), 2, rl.fade(rl.BLACK, 0.5))
        rl.image_draw_rectangle(img_chest, 28, 42, 8, 8, rl.GOLD); rl.image_draw_circle(img_chest, 32, 46, 2, rl.ORANGE)
        self.assets['chest'] = rl.load_texture_from_image(img_chest); rl.unload_image(img_chest)
        
        img_bush = rl.gen_image_color(64, 64, rl.BLANK)
        rl.image_draw_circle(img_bush, 32, 52, 16, rl.Color(40, 80, 25, 255)); rl.image_draw_circle(img_bush, 28, 48, 14, rl.Color(60, 120, 40, 255))
        rl.image_draw_circle(img_bush, 36, 48, 14, rl.Color(60, 120, 40, 255)); rl.image_draw_circle(img_bush, 32, 38, 13, rl.Color(80, 140, 50, 255))
        rl.image_draw_circle(img_bush, 24, 42, 10, rl.Color(100, 160, 60, 255)); rl.image_draw_circle(img_bush, 40, 42, 10, rl.Color(100, 160, 60, 255))
        rl.image_draw_circle(img_bush, 32, 32, 9, rl.Color(120, 180, 70, 255))
        self.assets['bush'] = rl.load_texture_from_image(img_bush); rl.unload_image(img_bush)
        
        self.assets['player_sheet'] = self.create_character_sheet()
        self.assets['npc_sheet'] = self.create_character_sheet(1, 1, 2, 2)
        self.assets['player_frames'] = [rl.Rectangle(0, 0, 32, 64), rl.Rectangle(32, 0, 32, 64)]
        
        img_potion = rl.gen_image_color(32, 32, rl.BLANK)
        rl.image_draw_circle(img_potion, 16, 21, 11, rl.Color(120, 0, 0, 255)); rl.image_draw_circle(img_potion, 16, 20, 10, rl.RED)
        rl.image_draw_circle(img_potion, 14, 18, 3, rl.Color(255, 100, 100, 255)); rl.image_draw_rectangle(img_potion, 14, 6, 4, 8, rl.Color(150, 150, 150, 255))
        rl.image_draw_rectangle(img_potion, 14, 6, 3, 7, rl.GRAY)
        self.assets['item_potion'] = rl.load_texture_from_image(img_potion); rl.unload_image(img_potion)
        
        img_bomb = rl.gen_image_color(32, 32, rl.BLANK)
        rl.image_draw_circle(img_bomb, 17, 19, 11, rl.Color(60, 60, 60, 255)); rl.image_draw_circle(img_bomb, 16, 18, 10, rl.BLACK)
        rl.image_draw_circle(img_bomb, 14, 16, 2, rl.WHITE); rl.image_draw_line(img_bomb, 16, 8, 18, 3, rl.BEIGE); rl.image_draw_line(img_bomb, 17, 3, 18, 1, rl.ORANGE)
        self.assets['item_bomb'] = rl.load_texture_from_image(img_bomb); rl.unload_image(img_bomb)
        
        img_wood = rl.gen_image_color(32, 32, rl.BLANK)
        rl.image_draw_rectangle(img_wood, 13, 5, 6, 22, rl.Color(80, 50, 30, 255)); rl.image_draw_rectangle(img_wood, 12, 4, 8, 24, rl.BROWN)
        rl.image_draw_rectangle(img_wood, 12, 4, 8, 3, rl.Color(150, 100, 60, 255)); rl.image_draw_circle(img_wood, 14, 8, 2, rl.DARKBROWN)
        self.assets['item_wood'] = rl.load_texture_from_image(img_wood); rl.unload_image(img_wood)
        
        img_stone = rl.gen_image_color(32, 32, rl.BLANK)
        rl.image_draw_circle(img_stone, 17, 17, 11, rl.Color(100, 100, 110, 255)); rl.image_draw_circle(img_stone, 16, 16, 10, rl.GRAY)
        rl.image_draw_circle(img_stone, 13, 13, 4, rl.LIGHTGRAY); rl.image_draw_circle(img_stone, 20, 18, 2, rl.Color(180, 180, 180, 255))
        self.assets['item_stone'] = rl.load_texture_from_image(img_stone); rl.unload_image(img_stone)
        
        img_fiber = rl.gen_image_color(32, 32, rl.BLANK)
        rl.image_draw_line(img_fiber, 8, 24, 24, 8, rl.Color(80, 150, 40, 255)); rl.image_draw_line(img_fiber, 7, 25, 23, 9, rl.LIME)
        rl.image_draw_line(img_fiber, 12, 24, 28, 8, rl.Color(100, 180, 60, 255)); rl.image_draw_line(img_fiber, 11, 25, 27, 9, rl.GREEN)
        rl.image_draw_line(img_fiber, 16, 24, 32, 8, rl.Color(80, 150, 40, 255))
        self.assets['item_fiber'] = rl.load_texture_from_image(img_fiber); rl.unload_image(img_fiber)
        
        img_axe = rl.gen_image_color(32, 32, rl.BLANK)
        rl.image_draw_line(img_axe, 9, 29, 25, 9, rl.Color(100, 70, 40, 255)); rl.image_draw_line(img_axe, 8, 28, 24, 8, rl.BROWN)
        rl.image_draw_circle(img_axe, 25, 8, 7, rl.Color(100, 100, 110, 255)); rl.image_draw_circle(img_axe, 24, 7, 6, rl.GRAY); rl.image_draw_circle(img_axe, 22, 5, 2, rl.LIGHTGRAY)
        self.assets['item_axe'] = rl.load_texture_from_image(img_axe); rl.unload_image(img_axe)
        
        img_pick = rl.gen_image_color(32, 32, rl.BLANK)
        rl.image_draw_line(img_pick, 9, 29, 25, 9, rl.Color(100, 70, 40, 255)); rl.image_draw_line(img_pick, 8, 28, 24, 8, rl.BROWN)
        rl.image_draw_line(img_pick, 17, 3, 29, 15, rl.Color(100, 100, 110, 255)); rl.image_draw_line(img_pick, 18, 4, 28, 14, rl.GRAY); rl.image_draw_circle(img_pick, 26, 12, 1, rl.LIGHTGRAY)
        self.assets['item_pickaxe'] = rl.load_texture_from_image(img_pick); rl.unload_image(img_pick)
        
        img_scroll = rl.gen_image_color(32, 32, rl.BLANK)
        rl.image_draw_rectangle(img_scroll, 7, 7, 18, 22, rl.Color(200, 180, 140, 255)); rl.image_draw_rectangle(img_scroll, 6, 6, 20, 24, rl.BEIGE)
        rl.image_draw_rectangle(img_scroll, 6, 6, 20, 4, rl.Color(255, 220, 180, 255)); rl.image_draw_rectangle_lines(img_scroll, rl.Rectangle(6, 6, 20, 24), 1, rl.BROWN)
        self.assets['item_scroll'] = rl.load_texture_from_image(img_scroll); rl.unload_image(img_scroll)
        
        img_mega = rl.gen_image_color(32, 32, rl.BLANK)
        rl.image_draw_circle(img_mega, 17, 21, 13, rl.Color(150, 0, 150, 255)); rl.image_draw_circle(img_mega, 16, 20, 12, rl.PURPLE)
        rl.image_draw_circle(img_mega, 14, 18, 5, rl.Color(200, 100, 200, 255)); rl.image_draw_rectangle(img_mega, 14, 4, 4, 10, rl.Color(200, 180, 100, 255))
        rl.image_draw_rectangle(img_mega, 14, 3, 4, 10, rl.GOLD)
        self.assets['item_mega_potion'] = rl.load_texture_from_image(img_mega); rl.unload_image(img_mega)
        
        img_gem = rl.gen_image_color(32, 32, rl.BLANK)
        rl.image_draw_triangle(img_gem, rl.Vector2(16, 5), rl.Vector2(4, 17), rl.Vector2(28, 17), rl.Color(0, 0, 150, 255))
        rl.image_draw_triangle(img_gem, rl.Vector2(16, 4), rl.Vector2(4, 16), rl.Vector2(28, 16), rl.BLUE)
        rl.image_draw_triangle(img_gem, rl.Vector2(4, 16), rl.Vector2(16, 27), rl.Vector2(28, 16), rl.SKYBLUE)
        rl.image_draw_triangle(img_gem, rl.Vector2(16, 12), rl.Vector2(10, 16), rl.Vector2(22, 16), rl.Color(100, 150, 255, 255))
        self.assets['item_gem'] = rl.load_texture_from_image(img_gem); rl.unload_image(img_gem)
        
        img_campfire = rl.gen_image_color(64, 64, rl.BLANK)
        rl.image_draw_circle(img_campfire, 33, 49, 13, rl.Color(60, 40, 20, 255)); rl.image_draw_circle(img_campfire, 32, 48, 12, rl.BROWN)
        rl.image_draw_rectangle(img_campfire, 28, 52, 8, 4, rl.DARKBROWN); rl.image_draw_rectangle(img_campfire, 36, 52, 8, 4, rl.DARKBROWN)
        rl.image_draw_triangle(img_campfire, rl.Vector2(32, 15), rl.Vector2(20, 48), rl.Vector2(44, 48), rl.Color(255, 100, 0, 255))
        rl.image_draw_triangle(img_campfire, rl.Vector2(32, 18), rl.Vector2(22, 45), rl.Vector2(42, 45), rl.ORANGE)
        rl.image_draw_triangle(img_campfire, rl.Vector2(32, 22), rl.Vector2(26, 40), rl.Vector2(38, 40), rl.Color(255, 180, 50, 255))
        rl.image_draw_circle(img_campfire, 32, 28, 5, rl.Color(255, 220, 100, 255))
        self.assets['campfire'] = rl.load_texture_from_image(img_campfire); rl.unload_image(img_campfire)
        
        img_slime = rl.gen_image_color(32, 32, rl.BLANK)
        rl.image_draw_circle(img_slime, 17, 21, 11, rl.Color(100, 180, 0, 255)); rl.image_draw_circle(img_slime, 16, 20, 10, rl.LIME)
        rl.image_draw_circle(img_slime, 12, 18, 2, rl.BLACK); rl.image_draw_circle(img_slime, 20, 18, 2, rl.BLACK)
        rl.image_draw_circle(img_slime, 13, 17, 1, rl.WHITE); rl.image_draw_circle(img_slime, 21, 17, 1, rl.WHITE)
        rl.image_draw_circle(img_slime, 14, 24, 2, rl.Color(180, 255, 100, 255))
        self.assets['slime'] = rl.load_texture_from_image(img_slime); rl.unload_image(img_slime)
        
        img_goblin = rl.gen_image_color(32, 32, rl.BLANK)
        rl.image_draw_circle(img_goblin, 17, 21, 11, rl.Color(100, 140, 80, 255)); rl.image_draw_circle(img_goblin, 16, 20, 10, rl.GREEN)
        rl.image_draw_circle(img_goblin, 12, 18, 2, rl.RED); rl.image_draw_circle(img_goblin, 20, 18, 2, rl.RED)
        rl.image_draw_circle(img_goblin, 12, 18, 1, rl.Color(255, 100, 100, 255)); rl.image_draw_circle(img_goblin, 20, 18, 1, rl.Color(255, 100, 100, 255))
        rl.image_draw_triangle(img_goblin, rl.Vector2(6, 20), rl.Vector2(2, 8), rl.Vector2(10, 14), rl.Color(120, 160, 100, 255))
        rl.image_draw_triangle(img_goblin, rl.Vector2(26, 20), rl.Vector2(22, 14), rl.Vector2(30, 8), rl.Color(120, 160, 100, 255))
        self.assets['goblin'] = rl.load_texture_from_image(img_goblin); rl.unload_image(img_goblin)
        
        img_wolf = rl.gen_image_color(32, 32, rl.BLANK)
        rl.image_draw_circle(img_wolf, 16, 20, 10, rl.GRAY); rl.image_draw_circle(img_wolf, 12, 14, 3, rl.DARKGRAY)
        rl.image_draw_circle(img_wolf, 20, 14, 3, rl.DARKGRAY); rl.image_draw_circle(img_wolf, 14, 18, 2, rl.RED)
        rl.image_draw_circle(img_wolf, 18, 18, 2, rl.RED); rl.image_draw_triangle(img_wolf, rl.Vector2(16, 24), rl.Vector2(12, 20), rl.Vector2(20, 20), rl.DARKGRAY)
        self.assets['wolf'] = rl.load_texture_from_image(img_wolf); rl.unload_image(img_wolf)

        img_fur = rl.gen_image_color(32, 32, rl.BLANK)
        rl.image_draw_circle(img_fur, 16, 16, 10, rl.GRAY); rl.image_draw_circle(img_fur, 14, 14, 6, rl.LIGHTGRAY)
        self.assets['item_wolf_fur'] = rl.load_texture_from_image(img_fur); rl.unload_image(img_fur)
        img_coat = rl.gen_image_color(32, 32, rl.BLANK)
        rl.image_draw_rectangle(img_coat, 6, 6, 20, 20, rl.GRAY); rl.image_draw_rectangle(img_coat, 14, 6, 4, 20, rl.LIGHTGRAY)
        self.assets['item_fur_coat'] = rl.load_texture_from_image(img_coat); rl.unload_image(img_coat)

        img_bed = rl.gen_image_color(64, 64, rl.BLANK)
        rl.image_draw_rectangle(img_bed, 10, 30, 44, 20, rl.BROWN); rl.image_draw_rectangle(img_bed, 12, 32, 40, 16, rl.WHITE)
        rl.image_draw_rectangle(img_bed, 14, 34, 15, 12, rl.LIGHTGRAY)
        self.assets['bed'] = rl.load_texture_from_image(img_bed); rl.unload_image(img_bed)
        self.assets['item_bed'] = self.assets['bed']

        img_sheep = rl.gen_image_color(32, 32, rl.BLANK)
        rl.image_draw_circle(img_sheep, 16, 20, 10, rl.WHITE); rl.image_draw_circle(img_sheep, 16, 12, 5, rl.LIGHTGRAY)
        rl.image_draw_circle(img_sheep, 14, 12, 1, rl.BLACK); rl.image_draw_circle(img_sheep, 18, 12, 1, rl.BLACK)
        self.assets['sheep'] = rl.load_texture_from_image(img_sheep); rl.unload_image(img_sheep)

        img_bow = rl.gen_image_color(32, 32, rl.BLANK); rl.image_draw_line(img_bow, 8, 28, 16, 16, rl.BROWN); rl.image_draw_line(img_bow, 16, 16, 28, 8, rl.BROWN); rl.image_draw_line(img_bow, 8, 28, 28, 8, rl.LIGHTGRAY); self.assets['item_bow'] = rl.load_texture_from_image(img_bow); rl.unload_image(img_bow)
        img_arrow = rl.gen_image_color(32, 32, rl.BLANK); rl.image_draw_line(img_arrow, 8, 24, 24, 8, rl.BROWN); rl.image_draw_triangle(img_arrow, rl.Vector2(24, 8), rl.Vector2(20, 7), rl.Vector2(25, 12), rl.GRAY); self.assets['item_arrow'] = rl.load_texture_from_image(img_arrow); rl.unload_image(img_arrow)
        img_proj_arrow = rl.gen_image_color(32, 32, rl.BLANK)
        rl.image_draw_line(img_proj_arrow, 0, 16, 28, 16, rl.BROWN); rl.image_draw_triangle(img_proj_arrow, rl.Vector2(28, 16), rl.Vector2(22, 14), rl.Vector2(22, 18), rl.GRAY)
        self.assets['projectile_arrow'] = rl.load_texture_from_image(img_proj_arrow); rl.unload_image(img_proj_arrow)
        
        img_food = rl.gen_image_color(32, 32, rl.BLANK)
        rl.image_draw_circle(img_food, 17, 17, 11, rl.Color(200, 120, 0, 255)); rl.image_draw_circle(img_food, 16, 16, 10, rl.ORANGE)
        rl.image_draw_circle(img_food, 13, 13, 4, rl.Color(255, 150, 50, 255)); rl.image_draw_circle(img_food, 12, 12, 2, rl.RED)
        self.assets['item_food'] = rl.load_texture_from_image(img_food); rl.unload_image(img_food)
        
        for stage in range(4):
            img = rl.gen_image_color(32, 32, rl.BLANK)
            rl.image_draw_circle(img, 16, 24, 10, rl.Color(60, 40, 20, 200))
            if stage == 0: rl.image_draw_circle(img, 14, 24, 2, rl.BEIGE); rl.image_draw_circle(img, 18, 24, 2, rl.BEIGE)
            elif stage == 1: rl.image_draw_rectangle(img, 15, 18, 2, 6, rl.LIME); rl.image_draw_circle(img, 16, 18, 3, rl.GREEN)
            elif stage == 2: rl.image_draw_rectangle(img, 15, 12, 2, 12, rl.LIME); rl.image_draw_circle(img, 16, 12, 5, rl.GREEN); rl.image_draw_line(img, 16, 18, 10, 14, rl.LIME); rl.image_draw_line(img, 16, 18, 22, 14, rl.LIME)
            elif stage == 3: rl.image_draw_rectangle(img, 15, 8, 2, 16, rl.GOLD); rl.image_draw_circle(img, 16, 8, 6, rl.YELLOW); rl.image_draw_line(img, 16, 16, 8, 10, rl.GOLD); rl.image_draw_line(img, 16, 16, 24, 10, rl.GOLD)
            self.assets[f'crop_wheat_{stage}'] = rl.load_texture_from_image(img); rl.unload_image(img)
            
        img_seeds = rl.gen_image_color(32, 32, rl.BLANK)
        rl.image_draw_circle(img_seeds, 16, 16, 8, rl.BROWN); rl.image_draw_circle(img_seeds, 16, 12, 3, rl.BEIGE)
        self.assets['item_seeds_wheat'] = rl.load_texture_from_image(img_seeds); rl.unload_image(img_seeds)
        
        img_wheat = rl.gen_image_color(32, 32, rl.BLANK)
        rl.image_draw_line(img_wheat, 16, 28, 16, 4, rl.GOLD); rl.image_draw_circle(img_wheat, 16, 8, 4, rl.YELLOW)
        rl.image_draw_line(img_wheat, 16, 14, 10, 8, rl.GOLD); rl.image_draw_line(img_wheat, 16, 14, 22, 8, rl.GOLD)
        self.assets['item_wheat'] = rl.load_texture_from_image(img_wheat); rl.unload_image(img_wheat)

        img_bread = rl.gen_image_color(32, 32, rl.BLANK)
        rl.image_draw_rectangle(img_bread, 6, 14, 20, 10, rl.ORANGE); rl.image_draw_circle(img_bread, 11, 14, 6, rl.ORANGE)
        rl.image_draw_circle(img_bread, 21, 14, 6, rl.ORANGE); rl.image_draw_circle(img_bread, 16, 14, 6, rl.ORANGE)
        self.assets['item_bread'] = rl.load_texture_from_image(img_bread); rl.unload_image(img_bread)

        img_fish = rl.gen_image_color(32, 32, rl.BLANK)
        rl.image_draw_circle(img_fish, 17, 17, 13, rl.Color(0, 0, 150, 255)); rl.image_draw_circle(img_fish, 16, 16, 12, rl.BLUE)
        rl.image_draw_triangle(img_fish, rl.Vector2(28, 16), rl.Vector2(34, 10), rl.Vector2(34, 22), rl.BLUE)
        rl.image_draw_circle(img_fish, 14, 14, 2, rl.BLACK); rl.image_draw_circle(img_fish, 14, 14, 1, rl.WHITE)
        rl.image_draw_triangle(img_fish, rl.Vector2(12, 14), rl.Vector2(18, 12), rl.Vector2(16, 20), rl.SKYBLUE)
        self.assets['item_fish'] = rl.load_texture_from_image(img_fish); rl.unload_image(img_fish)
        
        img_fireball = rl.gen_image_color(32, 32, rl.BLANK)
        rl.image_draw_circle(img_fireball, 16, 16, 12, rl.Color(200, 100, 0, 255)); rl.image_draw_circle(img_fireball, 16, 16, 10, rl.ORANGE)
        rl.image_draw_circle(img_fireball, 16, 16, 7, rl.RED); rl.image_draw_circle(img_fireball, 14, 14, 3, rl.Color(255, 200, 100, 255))
        self.assets['projectile_fireball'] = rl.load_texture_from_image(img_fireball); rl.unload_image(img_fireball)
        
        img_mm = rl.gen_image_color(32, 32, rl.BLANK)
        rl.image_draw_circle(img_mm, 16, 16, 8, rl.PURPLE); rl.image_draw_circle(img_mm, 16, 16, 5, rl.MAGENTA)
        self.assets['projectile_magic_missile'] = rl.load_texture_from_image(img_mm); rl.unload_image(img_mm)

        img_il = rl.gen_image_color(32, 32, rl.BLANK)
        rl.image_draw_triangle(img_il, rl.Vector2(16, 0), rl.Vector2(8, 32), rl.Vector2(24, 32), rl.SKYBLUE)
        self.assets['projectile_ice_lance'] = rl.load_texture_from_image(img_il); rl.unload_image(img_il)

        img_aa = rl.gen_image_color(32, 32, rl.BLANK)
        rl.image_draw_triangle(img_aa, rl.Vector2(16, 0), rl.Vector2(8, 24), rl.Vector2(24, 24), rl.LIME)
        rl.image_draw_rectangle(img_aa, 14, 24, 4, 8, rl.GREEN)
        self.assets['projectile_acid_arrow'] = rl.load_texture_from_image(img_aa); rl.unload_image(img_aa)

        img_skel = rl.gen_image_color(32, 32, rl.BLANK)
        rl.image_draw_circle(img_skel, 16, 10, 6, rl.LIGHTGRAY); rl.image_draw_rectangle(img_skel, 15, 16, 2, 10, rl.LIGHTGRAY)
        rl.image_draw_line(img_skel, 12, 18, 20, 18, rl.LIGHTGRAY); rl.image_draw_line(img_skel, 12, 22, 20, 22, rl.LIGHTGRAY)
        rl.image_draw_line(img_skel, 14, 18, 10, 24, rl.LIGHTGRAY); rl.image_draw_line(img_skel, 18, 18, 22, 24, rl.LIGHTGRAY)
        rl.image_draw_line(img_skel, 15, 26, 12, 32, rl.LIGHTGRAY); rl.image_draw_line(img_skel, 17, 26, 20, 32, rl.LIGHTGRAY)
        self.assets['skeleton'] = rl.load_texture_from_image(img_skel); rl.unload_image(img_skel)

        img_dagger = rl.gen_image_color(32, 32, rl.BLANK)
        rl.image_draw_line(img_dagger, 10, 28, 22, 16, rl.GRAY); rl.image_draw_line(img_dagger, 8, 30, 12, 26, rl.BROWN)
        self.assets['item_dagger'] = rl.load_texture_from_image(img_dagger); rl.unload_image(img_dagger)
        
        img_sword_item = rl.gen_image_color(32, 32, rl.BLANK)
        rl.image_draw_line(img_sword_item, 8, 28, 24, 12, rl.LIGHTGRAY); rl.image_draw_line(img_sword_item, 6, 30, 10, 26, rl.BROWN)
        rl.image_draw_line(img_sword_item, 9, 27, 13, 23, rl.DARKGRAY)
        self.assets['item_sword'] = rl.load_texture_from_image(img_sword_item); rl.unload_image(img_sword_item)
        
        img_hammer = rl.gen_image_color(32, 32, rl.BLANK)
        rl.image_draw_line(img_hammer, 8, 28, 24, 12, rl.BROWN); rl.image_draw_rectangle(img_hammer, 20, 8, 10, 10, rl.GRAY)
        self.assets['item_warhammer'] = rl.load_texture_from_image(img_hammer); rl.unload_image(img_hammer)

        img_armor = rl.gen_image_color(32, 32, rl.BLANK)
        rl.image_draw_rectangle(img_armor, 8, 8, 16, 16, rl.BROWN)
        self.assets['item_leather_armor'] = rl.load_texture_from_image(img_armor); rl.unload_image(img_armor)
        
        img_plate = rl.gen_image_color(32, 32, rl.BLANK)
        rl.image_draw_rectangle(img_plate, 8, 8, 16, 16, rl.LIGHTGRAY)
        self.assets['item_plate_armor'] = rl.load_texture_from_image(img_plate); rl.unload_image(img_plate)

        img_bat = rl.gen_image_color(64, 64, rl.BLANK)
        rl.image_draw_circle(img_bat, 32, 32, 10, rl.DARKGRAY)
        rl.image_draw_triangle(img_bat, rl.Vector2(32, 32), rl.Vector2(10, 10), rl.Vector2(32, 20), rl.BLACK)
        rl.image_draw_triangle(img_bat, rl.Vector2(32, 32), rl.Vector2(54, 10), rl.Vector2(32, 20), rl.BLACK)
        self.assets['bat'] = rl.load_texture_from_image(img_bat); rl.unload_image(img_bat)

        img_sun = rl.gen_image_color(32, 32, rl.BLANK)
        rl.image_draw_circle(img_sun, 16, 16, 11, rl.Color(200, 160, 0, 255)); rl.image_draw_circle(img_sun, 16, 16, 10, rl.YELLOW)
        rl.image_draw_circle(img_sun, 14, 14, 3, rl.Color(255, 255, 150, 255))
        for i in range(8):
            import math
            angle = (i / 8) * 2 * math.pi
            sx = int(16 + math.cos(angle) * 14); sy = int(16 + math.sin(angle) * 14)
            ex = int(16 + math.cos(angle) * 18); ey = int(16 + math.sin(angle) * 18)
            rl.image_draw_line(img_sun, sx, sy, ex, ey, rl.YELLOW)
        self.assets['icon_sun'] = rl.load_texture_from_image(img_sun); rl.unload_image(img_sun)
        
        img_moon = rl.gen_image_color(32, 32, rl.BLANK)
        rl.image_draw_circle(img_moon, 17, 17, 11, rl.Color(120, 120, 140, 255)); rl.image_draw_circle(img_moon, 16, 16, 10, rl.LIGHTGRAY)
        rl.image_draw_circle(img_moon, 14, 14, 2, rl.WHITE); rl.image_draw_circle(img_moon, 20, 20, 2, rl.WHITE); rl.image_draw_circle(img_moon, 18, 12, 1, rl.WHITE)
        self.assets['icon_moon'] = rl.load_texture_from_image(img_moon); rl.unload_image(img_moon)
        
        img_heart = rl.gen_image_color(32, 32, rl.BLANK)
        rl.image_draw_circle(img_heart, 11, 11, 9, rl.Color(150, 0, 0, 255)); rl.image_draw_circle(img_heart, 21, 11, 9, rl.Color(150, 0, 0, 255))
        rl.image_draw_circle(img_heart, 10, 10, 8, rl.RED); rl.image_draw_circle(img_heart, 22, 10, 8, rl.RED)
        rl.image_draw_triangle(img_heart, rl.Vector2(2, 14), rl.Vector2(30, 14), rl.Vector2(16, 30), rl.Color(150, 0, 0, 255))
        rl.image_draw_triangle(img_heart, rl.Vector2(2, 13), rl.Vector2(30, 13), rl.Vector2(16, 29), rl.RED)
        rl.image_draw_circle(img_heart, 14, 8, 3, rl.Color(255, 100, 100, 255))
        self.assets['icon_heart'] = rl.load_texture_from_image(img_heart); rl.unload_image(img_heart)
        
        img_mana = rl.gen_image_color(32, 32, rl.BLANK)
        rl.image_draw_circle(img_mana, 17, 21, 11, rl.Color(0, 0, 150, 255)); rl.image_draw_circle(img_mana, 16, 20, 10, rl.BLUE)
        rl.image_draw_triangle(img_mana, rl.Vector2(16, 1), rl.Vector2(6, 15), rl.Vector2(26, 15), rl.Color(0, 0, 150, 255))
        rl.image_draw_triangle(img_mana, rl.Vector2(16, 2), rl.Vector2(6, 16), rl.Vector2(26, 16), rl.BLUE)
        rl.image_draw_circle(img_mana, 14, 16, 3, rl.Color(100, 150, 255, 255))
        self.assets['icon_mana'] = rl.load_texture_from_image(img_mana); rl.unload_image(img_mana)
        
        img_hunger = rl.gen_image_color(32, 32, rl.BLANK)
        rl.image_draw_circle(img_hunger, 17, 19, 11, rl.Color(180, 100, 0, 255)); rl.image_draw_circle(img_hunger, 16, 18, 10, rl.ORANGE)
        rl.image_draw_rectangle(img_hunger, 15, 3, 2, 8, rl.Color(120, 70, 30, 255)); rl.image_draw_rectangle(img_hunger, 15, 2, 2, 8, rl.BROWN)
        rl.image_draw_circle(img_hunger, 14, 14, 2, rl.Color(255, 180, 100, 255))
        self.assets['icon_hunger'] = rl.load_texture_from_image(img_hunger); rl.unload_image(img_hunger)
        
        img_gold = rl.gen_image_color(32, 32, rl.BLANK)
        rl.image_draw_circle(img_gold, 17, 17, 11, rl.Color(180, 140, 0, 255)); rl.image_draw_circle(img_gold, 16, 16, 10, rl.GOLD)
        rl.image_draw_circle(img_gold, 14, 14, 4, rl.Color(255, 220, 100, 255)); rl.image_draw_circle(img_gold, 12, 12, 1, rl.WHITE)
        self.assets['icon_gold'] = rl.load_texture_from_image(img_gold); rl.unload_image(img_gold)
        
        img_sword = rl.gen_image_color(32, 32, rl.BLANK)
        rl.image_draw_rectangle(img_sword, 15, 5, 2, 18, rl.Color(100, 100, 120, 255)); rl.image_draw_rectangle(img_sword, 14, 4, 4, 20, rl.LIGHTGRAY)
        rl.image_draw_rectangle(img_sword, 14, 4, 4, 4, rl.Color(220, 220, 240, 255)); rl.image_draw_rectangle(img_sword, 10, 24, 12, 2, rl.Color(80, 50, 30, 255))
        rl.image_draw_rectangle(img_sword, 10, 23, 12, 2, rl.DARKGRAY); rl.image_draw_rectangle(img_sword, 15, 26, 2, 6, rl.Color(100, 70, 40, 255))
        rl.image_draw_rectangle(img_sword, 15, 25, 2, 6, rl.BROWN)
        self.assets['icon_sword'] = rl.load_texture_from_image(img_sword); rl.unload_image(img_sword)

        img_stamina = rl.gen_image_color(32, 32, rl.BLANK)
        rl.image_draw_circle(img_stamina, 16, 16, 12, rl.Color(200, 200, 0, 255)); rl.image_draw_circle(img_stamina, 16, 16, 10, rl.YELLOW)
        rl.image_draw_triangle(img_stamina, rl.Vector2(18, 6), rl.Vector2(10, 18), rl.Vector2(22, 18), rl.ORANGE)
        rl.image_draw_triangle(img_stamina, rl.Vector2(10, 18), rl.Vector2(14, 26), rl.Vector2(22, 18), rl.ORANGE)
        self.assets['icon_stamina'] = rl.load_texture_from_image(img_stamina); rl.unload_image(img_stamina)
        
        img_cloud = rl.gen_image_color(64, 32, rl.BLANK)
        rl.image_draw_circle(img_cloud, 20, 20, 12, rl.WHITE); rl.image_draw_circle(img_cloud, 35, 16, 14, rl.WHITE); rl.image_draw_circle(img_cloud, 50, 20, 10, rl.WHITE)
        self.assets['cloud'] = rl.load_texture_from_image(img_cloud); rl.unload_image(img_cloud)