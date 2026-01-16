import pyray as rl
import random
import numpy as np
import json
import os
from utils import iso_to_screen

# --- CONSTANTS ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
TILE_WIDTH = 64
TILE_HEIGHT = 32
CHUNK_SIZE = 32
WORLD_CHUNKS = 4
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

class IsoGame:
    def __init__(self):
        rl.set_config_flags(rl.FLAG_WINDOW_RESIZABLE)
        rl.init_window(SCREEN_WIDTH, SCREEN_HEIGHT, "IsoRPG Engine (pyray)")
        rl.init_audio_device()
        rl.set_target_fps(60)

        # Game State and UI
        self.game_state = 'START_MENU'
        self.pause_menu_active_tab = 0
        self.day_time = 0.5
        self.day_duration = 60.0
        self.selected_item_index = -1
        self.world_map_texture = None
        self.should_close = False
        self.active_dialogue = None
        self.projectiles = []
        self.fishing = {'active': False, 'state': 'idle', 'timer': 0}
        self.spells = {'fireball': {'cost': 5, 'damage': 10, 'speed': 400}}
        
        self.weather = 'sunny'
        self.weather_timer = 0
        self.weather_duration = 60.0
        self.lightning_timer = 0
        self.lightning_active = False

        self.recipes = [
            {'name': 'Mega Potion', 'result': 'item_mega_potion', 'ingredients': {'item_potion': 2}},
            {'name': 'Ancient Scroll', 'result': 'item_scroll', 'ingredients': {'item_potion': 1, 'item_gem': 1}}
        ]
        self.assets = {}
        self.block_definitions = []
        self._generate_block_definitions()
        self.generate_assets()

        # Game World Data
        self.maps = {}
        self.chunk_grid = []
        self.objects = {}
        self.npcs = {}
        self.player = {}
        self.active_dialogue = None
        self.particles = []
        self.fx_use = rl.load_sound("pop.wav")
        self.camera = rl.Camera2D(rl.Vector2(SCREEN_WIDTH//2, SCREEN_HEIGHT//2), rl.Vector2(0,0), 0.0, 1.0)
        
        self.object_draw_offsets = {'tree':-110, 'pine_tree':-110, 'rock':-45, 'ladder':-32, 'chest':-32, 'wall':-80, 'campfire':-32}
        self.draw_dispatch = {'player':self._draw_player, 'npc':self._draw_npc, 'obj':self._draw_obj, 'item':self._draw_item}

    def _generate_block_definitions(self):
        base_materials = {
            'stone': {'color': COLOR_STONE_FLOOR, 'side_color': COLOR_STONE_SIDE, 'height': 5, 'walkable': True},
            'dirt': {'color': COLOR_DIRT_TOP, 'side_color': COLOR_DIRT_SIDE, 'height': 5, 'walkable': True},
            'grass': {'color': COLOR_GRASS_TOP, 'side_color': COLOR_GRASS_SIDE, 'height': 5, 'walkable': True},
            'sand': {'color': COLOR_SAND_TOP, 'side_color': COLOR_SAND_SIDE, 'height': 5, 'walkable': True},
            'water': {'color': COLOR_WATER_TOP, 'side_color': COLOR_WATER_SIDE, 'height': 0, 'walkable': False},
            'taiga_grass': {'color': COLOR_TAIGA_GRASS_TOP, 'side_color': COLOR_TAIGA_GRASS_SIDE, 'height': 5, 'walkable': True},
            'swamp_mud': {'color': COLOR_SWAMP_MUD_TOP, 'side_color': COLOR_SWAMP_MUD_SIDE, 'height': 2, 'walkable': True},
            'swamp_water': {'color': COLOR_SWAMP_WATER_TOP, 'side_color': COLOR_WATER_SIDE, 'height': 0, 'walkable': False},
        }
        material_keys = list(base_materials.keys())
        for i in range(BLOCK_TYPES):
            mat_name = material_keys[i % len(material_keys)]
            base_def = base_materials[mat_name]
            var = (i * 37) % 40 - 20
            new_def = {
                'material': mat_name,
                'color_top': rl.Color(max(0,min(255,base_def['color'].r+var)), max(0,min(255,base_def['color'].g+var)), max(0,min(255,base_def['color'].b+var)), 255),
                'side_color': base_def['side_color'], 'height': base_def['height'], 'walkable': base_def['walkable'],
                'detail_type': 'none', 'detail_color': rl.BLANK
            }
            if new_def['walkable'] and (i % 10) < 3:
                new_def['detail_type'] = 'speckles'; det_var = (i * 19) % 30 - 15
                new_def['detail_color'] = rl.Color(max(0,min(255,new_def['color_top'].r-det_var)), max(0,min(255,new_def['color_top'].g-det_var)), max(0,min(255,new_def['color_top'].b-det_var)), 180)
            self.block_definitions.append(new_def)

    def _create_block_texture(self, color_top, side_color, height=0, detail_type='none', detail_color=rl.BLANK, **kwargs):
        width, ch = TILE_WIDTH, TILE_HEIGHT; img_height = ch + height + 10; img = rl.gen_image_color(width, img_height, rl.BLANK); ox, oy = width // 2, ch // 2 + height; top_pts = [rl.Vector2(ox,oy-ch//2-height), rl.Vector2(width,oy-height), rl.Vector2(ox,oy+ch//2-height), rl.Vector2(0,oy-height)]
        if height > 0:
            left_c = rl.Color(max(0,side_color.r-40),max(0,side_color.g-40),max(0,side_color.b-40),255); v=[rl.Vector2(0,oy-height),rl.Vector2(ox,oy+ch//2-height),rl.Vector2(ox,oy+ch//2),rl.Vector2(0,oy)]; rl.image_draw_triangle(img,v[0],v[1],v[3],left_c); rl.image_draw_triangle(img,v[1],v[2],v[3],left_c)
            right_c=rl.Color(max(0,side_color.r-60),max(0,side_color.g-60),max(0,side_color.b-60),255); v=[rl.Vector2(width,oy-height),rl.Vector2(ox,oy+ch//2-height),rl.Vector2(ox,oy+ch//2),rl.Vector2(width,oy)]; rl.image_draw_triangle(img,v[0],v[1],v[3],right_c); rl.image_draw_triangle(img,v[1],v[2],v[3],right_c)
        rl.image_draw_triangle(img,top_pts[0],top_pts[1],top_pts[2],color_top); rl.image_draw_triangle(img,top_pts[0],top_pts[2],top_pts[3],color_top)
        if detail_type == 'speckles':
            for _ in range(15): dx,dy=random.randint(width//4,3*width//4),random.randint(int(oy-ch/2.5),int(oy+ch/2.5-height)); rl.image_draw_circle(img,dx,dy,random.choice([1,1,2]),detail_color)
        texture = rl.load_texture_from_image(img); rl.unload_image(img); return texture

    def generate_assets(self):
        self.assets['blocks'] = [self._create_block_texture(**d) for d in self.block_definitions]
        img_wall=rl.gen_image_color(TILE_WIDTH,TILE_HEIGHT*2+10,rl.BLANK); self.assets['wall']=self._create_block_texture(rl.BLANK,COLOR_CAVE_WALL,height=int(TILE_HEIGHT*1.5))
        img_ladder=rl.gen_image_color(64,64,rl.BLANK); rl.image_draw_rectangle(img_ladder,18,8,28,48,rl.BLACK); [rl.image_draw_rectangle(img_ladder,20,12+i*8,24,4,COLOR_TREE_TRUNK) for i in range(6)]; self.assets['ladder']=rl.load_texture_from_image(img_ladder); rl.unload_image(img_ladder)
        img_tree=rl.gen_image_color(64,128,rl.BLANK); rl.image_draw_rectangle(img_tree,28,80,8,30,COLOR_TREE_TRUNK); rl.image_draw_circle(img_tree,32,70,20,COLOR_TREE_LEAVES); rl.image_draw_circle(img_tree,20,60,15,COLOR_TREE_LEAVES); rl.image_draw_circle(img_tree,44,60,15,COLOR_TREE_LEAVES); rl.image_draw_circle(img_tree,32,45,18,COLOR_TREE_LEAVES); rl.image_draw_circle(img_tree,32,45,12,rl.Color(76,175,80,255)); self.assets['tree']=rl.load_texture_from_image(img_tree); rl.unload_image(img_tree)
        img_pine=rl.gen_image_color(64,128,rl.BLANK); rl.image_draw_rectangle(img_pine,28,90,8,20,COLOR_TREE_TRUNK); rl.image_draw_triangle(img_pine,rl.Vector2(32,20),rl.Vector2(8,70),rl.Vector2(56,70),COLOR_PINE_LEAVES); rl.image_draw_triangle(img_pine,rl.Vector2(32,40),rl.Vector2(12,90),rl.Vector2(52,90),COLOR_PINE_LEAVES); self.assets['pine_tree']=rl.load_texture_from_image(img_pine); rl.unload_image(img_pine)
        img_rock=rl.gen_image_color(64,64,rl.BLANK); rock_pts=[rl.Vector2(10,50),rl.Vector2(20,30),rl.Vector2(40,20),rl.Vector2(55,45),rl.Vector2(50,60),rl.Vector2(20,60)]; rl.image_draw_triangle(img_rock,rock_pts[0],rock_pts[1],rock_pts[5],COLOR_ROCK_BASE); rl.image_draw_triangle(img_rock,rock_pts[1],rock_pts[2],rock_pts[3],COLOR_ROCK_BASE); rl.image_draw_triangle(img_rock,rock_pts[1],rock_pts[3],rock_pts[5],COLOR_ROCK_BASE); self.assets['rock']=rl.load_texture_from_image(img_rock); rl.unload_image(img_rock)
        img_chest=rl.gen_image_color(64,64,rl.BLANK); rl.image_draw_rectangle(img_chest,16,32,32,24,COLOR_TREE_TRUNK); rl.image_draw_rectangle_lines(img_chest,rl.Rectangle(16,32,32,24),2,rl.fade(rl.BLACK,0.5)); rl.image_draw_rectangle(img_chest,28,42,8,8,rl.GOLD); self.assets['chest']=rl.load_texture_from_image(img_chest); rl.unload_image(img_chest)
        def create_character_sheet(body_color):
            s=rl.gen_image_color(64,64,rl.BLANK); rl.image_draw_rectangle(s,6,54,20,8,rl.Color(0,0,0,80)); rl.image_draw_rectangle(s,11,50,4,10,COLOR_PLAYER_PANTS); rl.image_draw_rectangle(s,17,50,4,10,COLOR_PLAYER_PANTS); rl.image_draw_rectangle(s,10,25,12,25,body_color); rl.image_draw_rectangle(s,10,13,12,12,COLOR_PLAYER_SKIN); rl.image_draw_rectangle(s,9,10,14,6,COLOR_PLAYER_HAIR); rl.image_draw_rectangle(s,32+6,54,20,8,rl.Color(0,0,0,80)); rl.image_draw_rectangle(s,32+9,50,4,10,COLOR_PLAYER_PANTS); rl.image_draw_rectangle(s,32+19,50,4,10,COLOR_PLAYER_PANTS); rl.image_draw_rectangle(s,32+10,25,12,25,body_color); rl.image_draw_rectangle(s,32+10,13,12,12,COLOR_PLAYER_SKIN); rl.image_draw_rectangle(s,32+9,10,14,6,COLOR_PLAYER_HAIR); return rl.load_texture_from_image(s)
        self.assets['player_sheet']=create_character_sheet(COLOR_PLAYER_BODY); self.assets['npc_sheet']=create_character_sheet(COLOR_NPC_BODY); self.assets['player_frames']=[rl.Rectangle(0,0,32,64),rl.Rectangle(32,0,32,64)]
        
        img_potion = rl.gen_image_color(32, 32, rl.BLANK); rl.image_draw_circle(img_potion, 16, 20, 10, rl.RED); rl.image_draw_rectangle(img_potion, 14, 6, 4, 8, rl.GRAY); self.assets['item_potion'] = rl.load_texture_from_image(img_potion); rl.unload_image(img_potion)
        img_scroll = rl.gen_image_color(32, 32, rl.BLANK); rl.image_draw_rectangle(img_scroll, 6, 6, 20, 24, rl.BEIGE); rl.image_draw_rectangle_lines(img_scroll, rl.Rectangle(6, 6, 20, 24), 1, rl.BROWN); self.assets['item_scroll'] = rl.load_texture_from_image(img_scroll); rl.unload_image(img_scroll)
        img_mega = rl.gen_image_color(32, 32, rl.BLANK); rl.image_draw_circle(img_mega, 16, 20, 12, rl.PURPLE); rl.image_draw_rectangle(img_mega, 14, 4, 4, 10, rl.GOLD); self.assets['item_mega_potion'] = rl.load_texture_from_image(img_mega); rl.unload_image(img_mega)
        img_gem = rl.gen_image_color(32, 32, rl.BLANK); rl.image_draw_triangle(img_gem, rl.Vector2(16, 4), rl.Vector2(4, 16), rl.Vector2(28, 16), rl.BLUE); rl.image_draw_triangle(img_gem, rl.Vector2(4, 16), rl.Vector2(16, 28), rl.Vector2(28, 16), rl.SKYBLUE); self.assets['item_gem'] = rl.load_texture_from_image(img_gem); rl.unload_image(img_gem)
        img_campfire = rl.gen_image_color(64, 64, rl.BLANK); rl.image_draw_circle(img_campfire, 32, 48, 12, rl.BROWN); rl.image_draw_triangle(img_campfire, rl.Vector2(32, 20), rl.Vector2(20, 48), rl.Vector2(44, 48), rl.ORANGE); self.assets['campfire'] = rl.load_texture_from_image(img_campfire); rl.unload_image(img_campfire)
        img_slime = rl.gen_image_color(32, 32, rl.BLANK); rl.image_draw_circle(img_slime, 16, 20, 10, rl.LIME); rl.image_draw_circle(img_slime, 12, 18, 2, rl.BLACK); rl.image_draw_circle(img_slime, 20, 18, 2, rl.BLACK); self.assets['slime'] = rl.load_texture_from_image(img_slime); rl.unload_image(img_slime)
        img_goblin = rl.gen_image_color(32, 32, rl.BLANK); rl.image_draw_circle(img_goblin, 16, 20, 10, rl.GREEN); rl.image_draw_circle(img_goblin, 12, 18, 2, rl.RED); rl.image_draw_circle(img_goblin, 20, 18, 2, rl.RED); rl.image_draw_triangle(img_goblin, rl.Vector2(6, 20), rl.Vector2(2, 10), rl.Vector2(10, 16), rl.GREEN); rl.image_draw_triangle(img_goblin, rl.Vector2(26, 20), rl.Vector2(22, 16), rl.Vector2(30, 10), rl.GREEN); self.assets['goblin'] = rl.load_texture_from_image(img_goblin); rl.unload_image(img_goblin)
        img_food = rl.gen_image_color(32, 32, rl.BLANK); rl.image_draw_circle(img_food, 16, 16, 10, rl.ORANGE); rl.image_draw_circle(img_food, 12, 12, 3, rl.RED); self.assets['item_food'] = rl.load_texture_from_image(img_food); rl.unload_image(img_food)
        img_fish = rl.gen_image_color(32, 32, rl.BLANK); rl.image_draw_circle(img_fish, 16, 16, 12, rl.BLUE); rl.image_draw_triangle(img_fish, rl.Vector2(26, 16), rl.Vector2(32, 10), rl.Vector2(32, 22), rl.BLUE); self.assets['item_fish'] = rl.load_texture_from_image(img_fish); rl.unload_image(img_fish)
        img_fireball = rl.gen_image_color(32, 32, rl.BLANK); rl.image_draw_circle(img_fireball, 16, 16, 10, rl.ORANGE); rl.image_draw_circle(img_fireball, 16, 16, 7, rl.RED); self.assets['projectile_fireball'] = rl.load_texture_from_image(img_fireball); rl.unload_image(img_fireball)
        img_sun = rl.gen_image_color(32, 32, rl.BLANK); rl.image_draw_circle(img_sun, 16, 16, 10, rl.YELLOW); self.assets['icon_sun'] = rl.load_texture_from_image(img_sun); rl.unload_image(img_sun)
        img_moon = rl.gen_image_color(32, 32, rl.BLANK); rl.image_draw_circle(img_moon, 16, 16, 10, rl.LIGHTGRAY); self.assets['icon_moon'] = rl.load_texture_from_image(img_moon); rl.unload_image(img_moon)
        img_heart = rl.gen_image_color(32, 32, rl.BLANK); rl.image_draw_circle(img_heart, 10, 10, 8, rl.RED); rl.image_draw_circle(img_heart, 22, 10, 8, rl.RED); rl.image_draw_triangle(img_heart, rl.Vector2(2, 14), rl.Vector2(30, 14), rl.Vector2(16, 30), rl.RED); self.assets['icon_heart'] = rl.load_texture_from_image(img_heart); rl.unload_image(img_heart)
        img_mana = rl.gen_image_color(32, 32, rl.BLANK); rl.image_draw_circle(img_mana, 16, 20, 10, rl.BLUE); rl.image_draw_triangle(img_mana, rl.Vector2(16, 2), rl.Vector2(6, 16), rl.Vector2(26, 16), rl.BLUE); self.assets['icon_mana'] = rl.load_texture_from_image(img_mana); rl.unload_image(img_mana)
        img_hunger = rl.gen_image_color(32, 32, rl.BLANK); rl.image_draw_circle(img_hunger, 16, 18, 10, rl.ORANGE); rl.image_draw_rectangle(img_hunger, 15, 4, 2, 6, rl.BROWN); self.assets['icon_hunger'] = rl.load_texture_from_image(img_hunger); rl.unload_image(img_hunger)
        img_gold = rl.gen_image_color(32, 32, rl.BLANK); rl.image_draw_circle(img_gold, 16, 16, 10, rl.GOLD); self.assets['icon_gold'] = rl.load_texture_from_image(img_gold); rl.unload_image(img_gold)
        img_sword = rl.gen_image_color(32, 32, rl.BLANK); rl.image_draw_rectangle(img_sword, 14, 4, 4, 20, rl.LIGHTGRAY); rl.image_draw_rectangle(img_sword, 10, 24, 12, 2, rl.DARKGRAY); rl.image_draw_rectangle(img_sword, 15, 26, 2, 6, rl.BROWN); self.assets['icon_sword'] = rl.load_texture_from_image(img_sword); rl.unload_image(img_sword)

    def _generate_world_map_texture(self):
        if self.world_map_texture: rl.unload_render_texture(self.world_map_texture)
        map_image_size=256; self.world_map_texture=rl.load_render_texture(map_image_size,map_image_size); biome_colors={'temperate':COLOR_GRASS_TOP,'desert':COLOR_SAND_TOP,'taiga':COLOR_TAIGA_GRASS_TOP,'swamp':COLOR_SWAMP_MUD_TOP}; chunk_pixel_size=map_image_size//WORLD_CHUNKS
        rl.begin_texture_mode(self.world_map_texture); rl.clear_background(rl.BLACK)
        for cy in range(WORLD_CHUNKS):
            for cx in range(WORLD_CHUNKS): rl.draw_rectangle(cx*chunk_pixel_size,cy*chunk_pixel_size,chunk_pixel_size,chunk_pixel_size,biome_colors.get(self.chunk_grid[cy][cx],rl.MAGENTA))
        rl.end_texture_mode()

    def add_inventory_item(self, item_type, count=1):
        for slot in self.player['inventory']:
            if slot['type'] == item_type: slot['count'] += count; return
        self.player['inventory'].append({'type': item_type, 'count': count})

    def init_game_world(self):
        self.maps,self.objects,self.npcs,self.items,occupied={}, {'world':[],'cave':[]},{'world':[],'cave':[]},{'world':[],'cave':[]},{'world':set(),'cave':set()}
        self.player={'x':4.0,'y':4.0,'grid_x':4,'grid_y':4,'map':'world','moving':False,'move_start_time':0,'start_pos':(4,4),'target_pos':(4,4),'stats':{'str':5,'dex':5,'int':5,'hp':20,'max_hp':20,'mana':20,'max_mana':20,'level':1,'xp':0,'next_level_xp':100,'weapon_durability':50,'max_weapon_durability':50,'gold':0,'hunger':100,'max_hunger':100},'inventory':[],'quests':[],'last_attack':0}
        biomes={'temperate':{'base':16,'range':8},'desert':{'base':32,'range':8},'taiga':{'base':48,'range':8},'swamp':{'base':64,'range':16}}; self.chunk_grid=[[random.choice(list(biomes.keys()))for _ in range(WORLD_CHUNKS)]for _ in range(WORLD_CHUNKS)]; world_map=np.zeros((MAP_SIZE, MAP_SIZE), dtype=int)
        for cy in range(WORLD_CHUNKS):
            for cx in range(WORLD_CHUNKS):
                b_info=biomes[self.chunk_grid[cy][cx]]
                for yo in range(CHUNK_SIZE):
                    for xo in range(CHUNK_SIZE):
                        x,y=cx*CHUNK_SIZE+xo,cy*CHUNK_SIZE+yo; b_id=b_info['base']+random.randint(0,b_info['range']-1); world_map[y, x]=b_id
                        if self.block_definitions[b_id]['walkable']:
                            mat=self.block_definitions[b_id]['material']
                            if mat in['grass','dirt']and random.random()<0.1: self.objects['world'].append({'type':'tree','x':x,'y':y}); occupied['world'].add((x,y))
                            elif mat=='sand'and random.random()<0.05: self.objects['world'].append({'type':'rock','x':x,'y':y}); occupied['world'].add((x,y))
                            elif mat=='taiga_grass'and random.random()<0.15: self.objects['world'].append({'type':'pine_tree','x':x,'y':y}); occupied['world'].add((x,y))
                            elif self.chunk_grid[cy][cx] == 'swamp' and random.random() < 0.05: self.npcs['world'].append({'name': 'Slime', 'x': x, 'y': y, 'hp': 10, 'max_hp': 10, 'type': 'slime'})
                            elif self.chunk_grid[cy][cx] == 'taiga' and random.random() < 0.04: self.npcs['world'].append({'name': 'Goblin', 'x': x, 'y': y, 'hp': 15, 'max_hp': 15, 'type': 'goblin'})
                            elif random.random() < 0.02: self.items['world'].append({'type': random.choice(['item_potion', 'item_scroll', 'item_food']), 'x': x, 'y': y})
        self.maps['world']=world_map; lx,ly=5,5
        while not self.block_definitions[self.maps['world'][ly, lx]]['walkable']: lx,ly=random.randint(3,MAP_SIZE-4),random.randint(3,MAP_SIZE-4)
        self.player['x'],self.player['y'],self.player['grid_x'],self.player['grid_y']=float(lx+1),float(ly),lx+1,ly
        self.npcs['world'].append({'name':'Guide','x':lx+2,'y':ly+2,'hp':20,'max_hp':20,'quest':{'req':'item_potion','desc':'Fetch Potion','completed':False}})
        self.npcs['world'].append({'name':'Merchant','x':lx+3,'y':ly,'hp':20,'max_hp':20})
        self.objects['world'].append({'type':'campfire','x':lx+1,'y':ly+1}); occupied['world'].add((lx+1,ly+1))
        self.objects['world'].append({'type':'ladder','x':lx,'y':ly,'target_map':'cave','target_pos':(2,2)}); occupied['world'].add((lx,ly))
        cave_map,conceptual_cave_map=np.zeros((CAVE_MAP_SIZE, CAVE_MAP_SIZE), dtype=int),[['cave_wall'for _ in range(CAVE_MAP_SIZE)]for _ in range(CAVE_MAP_SIZE)]; px,py=CAVE_MAP_SIZE//2,CAVE_MAP_SIZE//2
        for _ in range(150): conceptual_cave_map[py][px]='stone_floor'; dx,dy=random.choice([(0,1),(0,-1),(1,0),(-1,0)]); px,py=max(1,min(CAVE_MAP_SIZE-2,px+dx)),max(1,min(CAVE_MAP_SIZE-2,py+dy))
        for y in range(CAVE_MAP_SIZE):
            for x in range(CAVE_MAP_SIZE):
                if conceptual_cave_map[y][x]=='cave_wall': self.objects['cave'].append({'type':'wall','x':x,'y':y}); occupied['cave'].add((x,y))
        self.maps['cave']=cave_map
        self.objects['cave'].append({'type':'ladder','x':2,'y':2,'target_map':'world','target_pos':(lx,ly)}); occupied['cave'].add((2,2))
        self.objects['cave']=[o for o in self.objects['cave']if o.get('type')!='wall'or o['x']!=2 or o['y']!=2]
        self._generate_world_map_texture()

    def to_screen(self, gx, gy): return iso_to_screen(gx, gy, TILE_WIDTH, TILE_HEIGHT)
    def change_map(self, t_map, t_pos): self.player['map']=t_map; self.player['x'],self.player['y']=float(t_pos[0]),float(t_pos[1]); self.player['grid_x'],self.player['grid_y']=t_pos[0],t_pos[1]; self.player['moving']=False

    def gain_xp(self, amount):
        s=self.player['stats']; s['xp']=s.get('xp',0)+amount; nxt=s.get('next_level_xp',100)
        if s['xp']>=nxt:
            s['xp']-=nxt; s['level']=s.get('level',1)+1; s['next_level_xp']=int(nxt*1.5)
            s['str']+=1; s['dex']+=1; s['int']+=1; s['max_hp']+=5; s['hp']=s['max_hp']
            self.active_dialogue={'text':f"LEVEL UP! You are now level {s['level']}!",'time':rl.get_time()+4.0}

    def _spawn_particles(self, gx, gy, count, color):
        sx, sy = self.to_screen(gx, gy)
        for _ in range(count):
            self.particles.append({
                'x': sx, 'y': sy - 30,
                'vx': random.uniform(-60, 60), 'vy': random.uniform(-60, 60),
                'life': random.uniform(0.5, 1.0),
                'color': color
            })

    def use_item(self, index):
        inv = self.player.get('inventory', [])
        if 0 <= index < len(inv):
            item = inv[index]; used = False
            match item['type']:
                case 'item_potion':
                    if self.player['stats']['hp'] < self.player['stats']['max_hp']:
                        self.player['stats']['hp'] = min(self.player['stats']['max_hp'], self.player['stats']['hp'] + 10)
                        self._spawn_particles(self.player['x'], self.player['y'], 20, rl.RED)
                        self.active_dialogue = {'text': "Used Potion (+10 HP)", 'time': rl.get_time() + 2.0}; used = True
                    else: self.active_dialogue = {'text': "HP full!", 'time': rl.get_time() + 1.0}
                case 'item_mega_potion':
                    if self.player['stats']['hp'] < self.player['stats']['max_hp']:
                        self.player['stats']['hp'] = min(self.player['stats']['max_hp'], self.player['stats']['hp'] + 50)
                        self._spawn_particles(self.player['x'], self.player['y'], 30, rl.PURPLE)
                        self.active_dialogue = {'text': "Used Mega Potion (+50 HP)", 'time': rl.get_time() + 2.0}; used = True
                    else: self.active_dialogue = {'text': "HP full!", 'time': rl.get_time() + 1.0}
                case 'item_scroll': self.active_dialogue = {'text': "You read the scroll... It's blank.", 'time': rl.get_time() + 2.0}
                case 'item_gem':
                    if self.player['stats']['weapon_durability'] < self.player['stats']['max_weapon_durability']:
                        self.player['stats']['weapon_durability'] = min(self.player['stats']['max_weapon_durability'], self.player['stats']['weapon_durability'] + 20)
                        self.active_dialogue = {'text': "Repaired Weapon (+20)", 'time': rl.get_time() + 2.0}; used = True
                    else: self.active_dialogue = {'text': "Weapon Durability full!", 'time': rl.get_time() + 1.0}
                case 'item_food':
                    if self.player['stats'].get('hunger', 0) < self.player['stats'].get('max_hunger', 100):
                        self.player['stats']['hunger'] = min(self.player['stats'].get('max_hunger', 100), self.player['stats'].get('hunger', 0) + 20)
                        self.active_dialogue = {'text': "Ate Food (+20 Hunger)", 'time': rl.get_time() + 2.0}; used = True
                case 'item_fish':
                    if self.player['stats'].get('hunger', 0) < self.player['stats'].get('max_hunger', 100):
                        self.player['stats']['hunger'] = min(self.player['stats'].get('max_hunger', 100), self.player['stats'].get('hunger', 0) + 15)
                        self.active_dialogue = {'text': "Ate Fish (+15 Hunger)", 'time': rl.get_time() + 2.0}; used = True
                    else: self.active_dialogue = {'text': "Not hungry!", 'time': rl.get_time() + 1.0}
            if used:
                rl.play_sound(self.fx_use)
                item['count'] -= 1; 
                if item['count'] <= 0: inv.pop(index)

    def _update_gameplay(self):
        if rl.is_key_pressed(rl.KEY_TAB): self.game_state='PAUSED'; return
        for i, key in enumerate([rl.KEY_ONE, rl.KEY_TWO, rl.KEY_THREE, rl.KEY_FOUR, rl.KEY_FIVE]):
            if rl.is_key_pressed(key): self.use_item(i)
        
        dt = rl.get_frame_time()
        for p in self.particles:
            p['x'] += p['vx'] * dt; p['y'] += p['vy'] * dt; p['life'] -= dt
        self.particles = [p for p in self.particles if p['life'] > 0]
        
        self.weather_timer += dt
        if self.weather_timer > self.weather_duration:
            self.weather_timer = 0; self.weather_duration = random.uniform(60, 120)
            self.weather = random.choice(['sunny', 'sunny', 'rainy', 'stormy'])
            self.active_dialogue = {'text': f"Weather: {self.weather.title()}", 'time': rl.get_time() + 3.0}
        
        if self.weather in ['rainy', 'stormy']:
            psx, psy = self.to_screen(self.player['x'], self.player['y'])
            for _ in range(4):
                self.particles.append({'x': psx + random.uniform(-500, 500), 'y': psy + random.uniform(-400, 400) - 300, 'vx': -20, 'vy': 500, 'life': 1.0, 'color': rl.BLUE, 'type': 'rain'})
        
        if self.weather == 'stormy':
            self.lightning_timer -= dt
            if self.lightning_timer <= 0: self.lightning_timer = random.uniform(5, 15); self.lightning_active = True; rl.play_sound(self.fx_use)
            if self.lightning_active and random.random() < 0.1: self.lightning_active = False

        if random.random() < 0.05:
            for obj in self.objects.get(self.player['map'], []):
                if obj['type'] == 'campfire': self._spawn_particles(obj['x'], obj['y'], 1, rl.ORANGE)

        if 'hunger' in self.player['stats']:
            self.player['stats']['hunger'] = max(0, self.player['stats']['hunger'] - dt * 0.5)
            if self.player['stats']['hunger'] <= 0 and rl.get_time() % 3.0 < dt:
                self.player['stats']['hp'] = max(0, self.player['stats']['hp'] - 1)
                self.active_dialogue = {'text': "Starving! (-1 HP)", 'time': rl.get_time() + 1.0}
        
        if 'mana' in self.player['stats']:
            self.player['stats']['mana'] = min(self.player['stats']['max_mana'], self.player['stats']['mana'] + dt * 0.5)

        # Fishing Logic
        if self.fishing['active']:
            if rl.is_key_pressed(rl.KEY_SPACE):
                if self.fishing['state'] == 'bite':
                    self.fishing['active'] = False
                    self.add_inventory_item('item_fish')
                    self.active_dialogue = {'text': "Caught a Fish!", 'time': rl.get_time() + 2.0}
                    self.gain_xp(10)
                else:
                    self.fishing['active'] = False
                    self.active_dialogue = {'text': "Pulled too early!", 'time': rl.get_time() + 1.0}
            elif self.fishing['state'] == 'waiting' and rl.get_time() > self.fishing['timer']:
                self.fishing['state'] = 'bite'
                self.fishing['timer'] = rl.get_time() + 0.7
                self.active_dialogue = {'text': "BITE! Press SPACE!", 'time': rl.get_time() + 0.7}
                rl.play_sound(self.fx_use)
            elif self.fishing['state'] == 'bite' and rl.get_time() > self.fishing['timer']:
                self.fishing['active'] = False
                self.active_dialogue = {'text': "It got away...", 'time': rl.get_time() + 1.0}
            return

        if rl.is_key_pressed(rl.KEY_F):
            px, py = int(self.player['x']), int(self.player['y'])
            near_water = False
            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    if dx == 0 and dy == 0: continue
                    tx, ty = px + dx, py + dy
                    if 0 <= tx < len(self.maps[self.player['map']]) and 0 <= ty < len(self.maps[self.player['map']]):
                        mat = self.block_definitions[self.maps[self.player['map']][ty, tx]]['material']
                        if 'water' in mat: near_water = True
            if near_water:
                if self.weather in ['rainy', 'stormy']: wait *= 0.5
                self.fishing = {'active': True, 'state': 'waiting', 'timer': rl.get_time() + wait}
                self.active_dialogue = {'text': "Fishing... (Wait for BITE)", 'time': rl.get_time() + 10.0}
            else: self.active_dialogue = {'text': "No water nearby.", 'time': rl.get_time() + 1.0}

        # Spell Casting
        if rl.is_key_pressed(rl.KEY_Q):
            spell = self.spells['fireball']
            if self.player['stats']['mana'] >= spell['cost']:
                self.player['stats']['mana'] -= spell['cost']
                sp = self.to_screen(self.player['x'], self.player['y'])
                mp = rl.get_screen_to_world_2d(rl.get_mouse_position(), self.camera)
                dx, dy = mp.x - sp[0], mp.y - (sp[1] - 30)
                dist = np.hypot(dx, dy)
                if dist > 0:
                    self.projectiles.append({'x': sp[0], 'y': sp[1]-30, 'vx': (dx/dist)*spell['speed'], 'vy': (dy/dist)*spell['speed'], 'life': 2.0, 'damage': spell['damage']})
            else: self.active_dialogue = {'text': "Not enough Mana!", 'time': rl.get_time() + 1.0}

        # Update Projectiles
        for p in self.projectiles:
            p['x'] += p['vx'] * dt; p['y'] += p['vy'] * dt; p['life'] -= dt
            for npc in self.npcs[self.player['map']]:
                nsx, nsy = self.to_screen(npc['x'], npc['y'])
                if np.hypot(p['x'] - nsx, p['y'] - (nsy - 30)) < 30:
                    npc['hp'] -= p['damage']; p['life'] = 0
                    self._spawn_particles(npc['x'], npc['y'], 10, rl.ORANGE)
                    if npc['hp'] <= 0: self.npcs[self.player['map']].remove(npc); self.gain_xp(50)
                    break
        self.projectiles = [p for p in self.projectiles if p['life'] > 0]

        # NPC Logic (Goblin AI)
        if self.player['map'] in self.npcs:
            for npc in self.npcs[self.player['map']]:
                if npc.get('type') == 'goblin':
                    dist = np.hypot(self.player['x'] - npc['x'], self.player['y'] - npc['y'])
                    if 0.8 < dist < 8.0:
                        speed = 2.0 * dt
                        dx = (self.player['x'] - npc['x']) / dist * speed
                        dy = (self.player['y'] - npc['y']) / dist * speed
                        nx, ny = npc['x'] + dx, npc['y'] + dy
                        if 0 <= int(nx) < len(self.maps[self.player['map']]) and 0 <= int(ny) < len(self.maps[self.player['map']]):
                            b_id = self.maps[self.player['map']][int(ny), int(nx)]
                            if self.block_definitions[b_id]['walkable']:
                                npc['x'], npc['y'] = nx, ny

        self.day_time = (self.day_time + dt / self.day_duration) % 1.0
        if self.active_dialogue and rl.get_time() > self.active_dialogue['time']: self.active_dialogue = None
        if self.player.get('moving'): self._update_player_movement(); return
        
        # Combat & Interaction
        if rl.is_key_pressed(rl.KEY_SPACE):
            if rl.get_time() - self.player.get('last_attack',0) > 0.5:
                if self.player['stats'].get('weapon_durability', 0) <= 0:
                    self.active_dialogue = {'text': "Weapon broken!", 'time': rl.get_time() + 1.0}
                else:
                    self.player['last_attack'] = rl.get_time()
                    self.player['stats']['weapon_durability'] -= 1
                    px, py = self.player['grid_x'], self.player['grid_y']
                    hit_npc = False
                    for npc in self.npcs[self.player['map']]:
                        if abs(int(npc['x'])-px) <= 1 and abs(int(npc['y'])-py) <= 1:
                            npc['hp'] -= self.player['stats']['str']
                            self.active_dialogue = {'text': f"Hit {npc['name']} for {self.player['stats']['str']} dmg!", 'time': rl.get_time() + 1.0}
                            if npc['hp'] <= 0:
                                self.npcs[self.player['map']].remove(npc); self.gain_xp(50)
                                if "LEVEL UP" not in self.active_dialogue.get('text',''): self.active_dialogue = {'text': f"Defeated {npc['name']}! (+50 XP)", 'time': rl.get_time() + 2.0}
                            hit_npc = True
                            break
                    
                    if not hit_npc:
                        for obj in self.objects[self.player['map']]:
                            if obj['type'] == 'rock' and abs(obj['x']-px) <= 1 and abs(obj['y']-py) <= 1:
                                self.objects[self.player['map']].remove(obj)
                                self.items[self.player['map']].append({'type': 'item_gem', 'x': obj['x'], 'y': obj['y']})
                                self.active_dialogue = {'text': "Smashed rock! Found a Gem!", 'time': rl.get_time() + 2.0}
                                self._spawn_particles(obj['x'], obj['y'], 10, rl.GRAY)
                                break

        if rl.is_key_pressed(rl.KEY_E):
            px,py,cmap=self.player['grid_x'],self.player['grid_y'],self.player['map']
            for npc in self.npcs[cmap]:
                if abs(int(npc['x'])-px) <= 1 and abs(int(npc['y'])-py) <= 1:
                    if npc.get('name') == 'Merchant':
                        self.game_state = 'SHOP'
                        return
                    if 'quest' in npc and not npc['quest']['completed']:
                        req = npc['quest']['req']
                        slot = next((s for s in self.player['inventory'] if s['type'] == req), None)
                        if slot:
                            slot['count'] -= 1
                            if slot['count'] <= 0: self.player['inventory'].remove(slot)
                            npc['quest']['completed'] = True
                            self.player['quests'].append(npc['quest'])
                            self.gain_xp(100)
                            if "LEVEL UP" not in self.active_dialogue.get('text',''): self.active_dialogue = {'text': "Quest Completed! (+100 XP)", 'time': rl.get_time() + 3.0}
                        else:
                            self.active_dialogue = {'text': f"Quest: {npc['quest']['desc']}", 'time': rl.get_time() + 3.0}
                    else:
                        self.active_dialogue = {'text': f"Hello, traveler.", 'time': rl.get_time() + 2.0}
                    return
            for obj in self.objects[cmap]:
                if obj['type']=='ladder' and obj['x']==px and obj['y']==py: self.change_map(obj['target_map'],obj['target_pos']); return
                if obj['type']=='campfire' and abs(obj['x']-px)<=1 and abs(obj['y']-py)<=1:
                    self.day_time = 0.25
                    self.player['stats']['hp'] = self.player['stats']['max_hp']
                    self.player['stats']['mana'] = self.player['stats']['max_mana']
                    self.active_dialogue = {'text': "Slept by the fire. Morning comes.", 'time': rl.get_time() + 3.0}
                    return
        if rl.is_key_pressed(rl.KEY_G):
            px,py,cmap=self.player['grid_x'],self.player['grid_y'],self.player['map']
            found = [i for i in self.items[cmap] if i['x']==px and i['y']==py]
            for item in found:
                self.add_inventory_item(item['type'])
                self.items[cmap].remove(item)
        if rl.is_mouse_button_pressed(rl.MOUSE_LEFT_BUTTON):
            w_pos=rl.get_screen_to_world_2d(rl.get_mouse_position(),self.camera); gx,gy=round(w_pos.x/TILE_WIDTH+w_pos.y/TILE_HEIGHT),round(w_pos.y/TILE_HEIGHT-w_pos.x/TILE_WIDTH); self.attempt_move(gx,gy)
        dx,dy=0,0
        if rl.is_key_down(rl.KEY_W) or rl.is_key_down(rl.KEY_UP): dy=-1
        elif rl.is_key_down(rl.KEY_S) or rl.is_key_down(rl.KEY_DOWN): dy=1
        elif rl.is_key_down(rl.KEY_A) or rl.is_key_down(rl.KEY_LEFT): dx=-1
        elif rl.is_key_down(rl.KEY_D) or rl.is_key_down(rl.KEY_RIGHT): dx=1
        if dx!=0 or dy!=0: self.attempt_move(self.player['grid_x']+dx,self.player['grid_y']+dy)

    def _update_player_movement(self):
        now=rl.get_time(); dur=0.2; el=now-self.player['move_start_time']; t=min(1.0,el/dur)
        if now-self.player.get('anim_time',0)>0.1: self.player['anim_frame']=(self.player.get('anim_frame',0)+1)%2; self.player['anim_time']=now
        sx,sy=self.player['start_pos']; tx,ty=self.player['target_pos']
        self.player['x'],self.player['y']=sx+(tx-sx)*t,sy+(ty-sy)*t
        if t>=1.0: self.player.update({'moving':False,'x':float(tx),'y':float(ty),'grid_x':tx,'grid_y':ty,'anim_frame':0})
        px_scr,py_scr=self.to_screen(self.player['x'],self.player['y']); self.camera.target=rl.Vector2(px_scr,py_scr)

    def attempt_move(self, tx, ty):
        if self.player['map'] not in self.maps: return
        current_map=self.maps[self.player['map']]; map_size=len(current_map)
        if not (0<=tx<map_size and 0<=ty<map_size) or (tx==self.player['grid_x'] and ty==self.player['grid_y']): return
        b_id=current_map[ty, tx]
        if not self.block_definitions[b_id]['walkable']: return
        for e_list in[self.objects[self.player['map']],self.npcs[self.player['map']]]:
            for e in e_list:
                if e.get('type') not in['ladder','chest']and int(e['x'])==tx and int(e['y'])==ty: return
        self.player.update({'moving':True,'start_pos':(self.player['x'],self.player['y']),'target_pos':(tx,ty),'move_start_time':rl.get_time()})

    def _draw_gameplay(self):
        sw, sh = rl.get_screen_width(), rl.get_screen_height()
        self.camera.offset = rl.Vector2(sw // 2, sh // 2)
        
        brightness = 1.0
        if self.player.get('map') == 'cave':
            brightness = 0.2
            bg_color = COLOR_BG
        else:
            brightness = (np.sin((self.day_time - 0.25) * np.pi * 2) + 1) / 2
            bg_color = rl.Color(int(20 + 80 * brightness), int(20 + 160 * brightness), int(40 + 215 * brightness), 255)
        tint = rl.Color(int(255*brightness), int(255*brightness), int(255*brightness), 255)
            
        rl.begin_drawing(); rl.clear_background(bg_color); rl.begin_mode_2d(self.camera)
        if self.player.get('map')in self.maps:
            current_map=self.maps[self.player['map']]; map_size=len(current_map)
            for y in range(map_size):
                for x in range(map_size):
                    sx,sy=self.to_screen(x,y); b_id=current_map[y, x]
                    if b_id<len(self.assets['blocks']): rl.draw_texture(self.assets['blocks'][b_id],int(sx-TILE_WIDTH//2),int(sy-TILE_HEIGHT//2),tint)
        render_list=[{'entity_type':'player',**self.player,'depth':self.player.get('x',0)+self.player.get('y',0)+0.6}]
        if self.player.get('map')in self.npcs: render_list.extend([{'entity_type':'npc',**n,'depth':n['x']+n['y']+0.5}for n in self.npcs[self.player['map']]])
        if self.player.get('map')in self.objects: render_list.extend([{'entity_type':'obj',**o,'depth':o['x']+o['y']-(0.5 if o['type']in['ladder','chest']else -0.5)}for o in self.objects[self.player['map']]])
        if self.player.get('map')in self.items: render_list.extend([{'entity_type':'item',**i,'depth':i['x']+i['y']+0.1}for i in self.items[self.player['map']]])
        render_list.sort(key=lambda item:item['depth'])
        for item in render_list:
            sx,sy=self.to_screen(item.get('x',0),item.get('y',0)); draw_func=self.draw_dispatch.get(item['entity_type'])
            if draw_func: draw_func(item,sx,sy,tint)
        
        for p in self.particles:
            rl.draw_rectangle(int(p['x']), int(p['y']), 4, 4, rl.fade(p['color'], p['life']))
        for p in self.projectiles:
            rl.draw_texture(self.assets['projectile_fireball'], int(p['x']-16), int(p['y']-16), rl.WHITE)
        rl.end_mode_2d()
        
        # Lighting System
        if brightness < 1.0:
            rl.begin_blend_mode(rl.BLEND_ADDITIVE)
            torch_radius = 200 + np.sin(rl.get_time() * 10) * 5
            rl.draw_circle_gradient(sw // 2, sh // 2 - 25, torch_radius, rl.Color(255, 170, 80, int(200 * (1.0 - brightness))), rl.Color(0, 0, 0, 0))
            rl.end_blend_mode()
            
        if self.lightning_active: rl.draw_rectangle(0, 0, sw, sh, rl.fade(rl.WHITE, 0.3))
        elif self.weather == 'stormy': rl.draw_rectangle(0, 0, sw, sh, rl.fade(rl.BLACK, 0.3))
        elif self.weather == 'rainy': rl.draw_rectangle(0, 0, sw, sh, rl.fade(rl.BLUE, 0.1))
            
        stats=self.player.get('stats',{}); rl.draw_rectangle(5,5,200,130,rl.fade(rl.BLACK,0.5)); rl.draw_text("Player",10,10,20,rl.WHITE)
        rl.draw_texture_ex(self.assets['icon_heart'], rl.Vector2(10, 30), 0, 0.8, rl.WHITE); rl.draw_text(f"{stats.get('hp',0)}/{stats.get('max_hp',0)}", 40, 35, 20, rl.LIME)
        rl.draw_texture_ex(self.assets['icon_mana'], rl.Vector2(110, 30), 0, 0.8, rl.WHITE); rl.draw_text(f"{int(stats.get('mana',0))}/{stats.get('max_mana',20)}", 140, 35, 20, rl.BLUE)
        rl.draw_text(f"STR:{stats.get('str',0)} DEX:{stats.get('dex',0)} INT:{stats.get('int',0)}",10,60,10,rl.LIGHTGRAY)
        rl.draw_texture_ex(self.assets['icon_sword'], rl.Vector2(10, 75), 0, 0.6, rl.WHITE); rl.draw_text(f"{stats.get('weapon_durability',0)}/{stats.get('max_weapon_durability',0)}", 35, 78, 10, rl.ORANGE)
        rl.draw_texture_ex(self.assets['icon_gold'], rl.Vector2(110, 75), 0, 0.6, rl.WHITE); rl.draw_text(f"{stats.get('gold',0)}", 135, 78, 10, rl.GOLD)
        rl.draw_texture_ex(self.assets['icon_hunger'], rl.Vector2(10, 95), 0, 0.6, rl.WHITE); rl.draw_text(f"{int(stats.get('hunger',0))}/{stats.get('max_hunger',100)}", 35, 98, 10, rl.ORANGE)
        is_day = 0.25 < self.day_time < 0.75; time_icon = self.assets['icon_sun'] if is_day else self.assets['icon_moon']
        rl.draw_texture_ex(time_icon, rl.Vector2(110, 95), 0, 0.6, rl.WHITE); rl.draw_text(f"{int(self.day_time*24):02d}:00", 135, 98, 10, rl.YELLOW)
        
        # Hotbar
        hotbar_x = sw // 2 - 125; hotbar_y = sh - 60
        for i in range(5):
            rect = rl.Rectangle(hotbar_x + i * 50, hotbar_y, 45, 45)
            rl.draw_rectangle_rec(rect, rl.fade(rl.BLACK, 0.5)); rl.draw_rectangle_lines(int(rect.x), int(rect.y), int(rect.width), int(rect.height), rl.GRAY)
            rl.draw_text(str(i+1), int(rect.x + 2), int(rect.y + 2), 10, rl.WHITE)
            inv = self.player.get('inventory', [])
            if i < len(inv) and inv[i]['type'] in self.assets:
                tex = self.assets[inv[i]['type']]; rl.draw_texture_pro(tex, rl.Rectangle(0,0,tex.width,tex.height), rl.Rectangle(rect.x+5, rect.y+5, 35, 35), rl.Vector2(0,0), 0.0, rl.WHITE)
                if inv[i]['count'] > 1: rl.draw_text(str(inv[i]['count']), int(rect.x + 28), int(rect.y + 32), 10, rl.WHITE)

        if self.active_dialogue:
            txt = self.active_dialogue['text']; tw = rl.measure_text(txt, 20)
            rl.draw_rectangle(sw//2 - tw//2 - 10, sh - 100, tw + 20, 40, rl.fade(rl.BLACK, 0.7))
            rl.draw_text(txt, sw//2 - tw//2, sh - 90, 20, rl.WHITE)
        rl.end_drawing()

    def save_game(self):
        serializable_maps = {k: v.tolist() for k, v in self.maps.items()}
        data = {'player':self.player,'maps':serializable_maps,'objects':self.objects,'npcs':self.npcs,'items':self.items,'day_time':self.day_time,'chunk_grid':self.chunk_grid,'weather':self.weather}
        try:
            with open('savegame.json','w')as f: json.dump(data,f)
        except Exception as e: print(f"Error saving: {e}")

    def load_game(self):
        if not os.path.exists('savegame.json'): return
        try:
            with open('savegame.json','r')as f:
                data=json.load(f); self.player=data['player']; self.maps={k: np.array(v, dtype=int) for k, v in data['maps'].items()}; self.objects=data['objects']; self.npcs=data['npcs']; self.items=data['items']; self.day_time=data['day_time']; self.weather=data.get('weather','sunny')
                if 'weapon_durability' not in self.player['stats']: self.player['stats'].update({'weapon_durability':50,'max_weapon_durability':50})
                if 'gold' not in self.player['stats']: self.player['stats']['gold'] = 0
                if 'hunger' not in self.player['stats']: self.player['stats'].update({'hunger': 100, 'max_hunger': 100})
                if 'mana' not in self.player['stats']: self.player['stats'].update({'mana': 20, 'max_mana': 20})
                # Migrate inventory to stacked format
                new_inv = []
                for i in self.player.get('inventory', []):
                    if isinstance(i, str):
                        found = next((s for s in new_inv if s['type'] == i), None)
                        if found: found['count'] += 1
                        else: new_inv.append({'type': i, 'count': 1})
                    else: new_inv.append(i)
                self.player['inventory'] = new_inv
                self.chunk_grid=data.get('chunk_grid',[])
                if not self.chunk_grid: biomes=['temperate','desert','taiga','swamp']; self.chunk_grid=[[random.choice(biomes)for _ in range(WORLD_CHUNKS)]for _ in range(WORLD_CHUNKS)]
                self._generate_world_map_texture(); self.game_state='GAMEPLAY'
        except Exception as e: print(f"Error loading: {e}")

    def _draw_start_menu(self):
        sw, sh = rl.get_screen_width(), rl.get_screen_height()
        rl.begin_drawing(); rl.clear_background(rl.BLACK); title,font_size="Isometric RPG",40; rl.draw_text(title,(sw-rl.measure_text(title,font_size))//2,sh//4,font_size,rl.WHITE); btn_w,btn_h=200,40; btn_x=(sw-btn_w)//2
        
        has_save = os.path.exists('savegame.json')
        start_y = sh/2 - (50 if has_save else 30)
        
        if rl.gui_button(rl.Rectangle(btn_x,start_y,btn_w,btn_h),"New Game"): self.init_game_world(); self.game_state='GAMEPLAY'
        next_y = start_y + 50
        if has_save:
            if rl.gui_button(rl.Rectangle(btn_x,next_y,btn_w,btn_h),"Load Game"): self.load_game()
            next_y += 50
        if rl.gui_button(rl.Rectangle(btn_x,next_y,btn_w,btn_h),"Quit"): self.should_close=True
        rl.end_drawing()

    def _draw_shop_menu(self):
        sw, sh = rl.get_screen_width(), rl.get_screen_height()
        self._draw_gameplay()
        rl.begin_drawing()
        rl.draw_rectangle(0,0,sw,sh,rl.Color(0,0,0,150))
        win_w,win_h=400,300; win_x,win_y=(sw-win_w)//2,(sh-win_h)//2
        rl.gui_window_box(rl.Rectangle(win_x,win_y,win_w,win_h),"Merchant Shop")
        rl.draw_text(f"Gold: {self.player['stats'].get('gold', 0)}", int(win_x+20), int(win_y+40), 20, rl.GOLD)
        inv = self.player.get('inventory', [])
        gems = [slot for slot in inv if slot['type'] == 'item_gem']
        y = win_y + 80
        if not gems: rl.draw_text("No gems to sell.", int(win_x+20), int(y), 20, rl.GRAY)
        else:
            for slot in gems:
                rl.draw_text(f"Gem (x{slot['count']})", int(win_x+20), int(y), 20, rl.WHITE)
                if rl.gui_button(rl.Rectangle(win_x+250, y, 100, 25), "Sell (50G)"):
                    slot['count'] -= 1; self.player['stats']['gold'] = self.player['stats'].get('gold', 0) + 50
                    self.active_dialogue = {'text': "Sold Gem for 50 Gold", 'time': rl.get_time() + 2.0}
                    if slot['count'] <= 0: self.player['inventory'].remove(slot)
                y += 35
        if rl.gui_button(rl.Rectangle(win_x+win_w//2-50, win_y+win_h-40, 100, 30), "Close"): self.game_state = 'GAMEPLAY'
        rl.end_drawing()

    def _draw_pause_menu(self):
        sw, sh = rl.get_screen_width(), rl.get_screen_height()
        self._draw_gameplay(); rl.begin_drawing(); rl.draw_rectangle(0,0,sw,sh,rl.Color(0,0,0,150)); win_w,win_h=700,450; win_x,win_y=(sw-win_w)//2,(sh-win_h)//2; rl.gui_window_box(rl.Rectangle(win_x,win_y,win_w,win_h),"Menu"); tabs=["Character","Inventory","Crafting","Map","Options"]
        active_tab = rl.ffi.new("int *", self.pause_menu_active_tab)
        rl.gui_tab_bar(rl.Rectangle(win_x+10,win_y+24,win_w-20,20),tabs,len(tabs),active_tab)
        self.pause_menu_active_tab = int(active_tab[0])
        content_rect=rl.Rectangle(win_x+10,win_y+54,win_w-20,win_h-64)
        match self.pause_menu_active_tab:
            case 0: self._draw_character_sheet_tab(content_rect)
            case 1: self._draw_inventory_tab(content_rect)
            case 2: self._draw_crafting_tab(content_rect)
            case 3: self._draw_map_tab(content_rect)
            case 4: self._draw_options_tab(content_rect)
        rl.end_drawing()

    def _draw_character_sheet_tab(self, rect):
        stats=self.player.get('stats',{}); y_pos=int(rect.y); rl.draw_text("Character Stats",int(rect.x),y_pos,20,rl.BLACK); y_pos+=30
        rl.draw_text(f"Level: {stats.get('level',1)}",int(rect.x+20),y_pos,20,rl.DARKGRAY); y_pos+=25
        xp,nxp=stats.get('xp',0),stats.get('next_level_xp',100); rl.draw_text(f"XP: {xp}/{nxp}",int(rect.x+20),y_pos,20,rl.DARKGRAY); y_pos+=25
        rl.draw_rectangle_lines(int(rect.x+20),y_pos,200,10,rl.GRAY); rl.draw_rectangle(int(rect.x+20),y_pos,int((xp/nxp)*200) if nxp else 0,10,rl.BLUE); y_pos+=25
        for key in ['str','dex','int','hp','max_hp']:
            if key in stats: rl.draw_text(f"{key.upper()}: {stats[key]}",int(rect.x+20),y_pos,20,rl.DARKGRAY); y_pos+=25
        y_pos += 20; rl.draw_text("Completed Quests", int(rect.x), y_pos, 20, rl.BLACK); y_pos += 30
        for q in self.player.get('quests', []):
            rl.draw_text(f"- {q['desc']}", int(rect.x+20), y_pos, 10, rl.DARKGRAY); y_pos += 15

    def _draw_inventory_tab(self, rect):
        rl.draw_text("Inventory (G to pickup)",int(rect.x),int(rect.y),20,rl.BLACK)
        inv = self.player.get('inventory', [])
        cols, rows, size, pad = 5, 4, 50, 10
        tooltip = None
        for i in range(cols * rows):
            c, r = i % cols, i // cols
            x, y = rect.x + c * (size + pad), rect.y + 30 + r * (size + pad)
            slot_rect = rl.Rectangle(x, y, size, size)
            if rl.gui_button(slot_rect, ""): self.selected_item_index = i if i < len(inv) else -1
            if i == self.selected_item_index: rl.draw_rectangle_lines(int(x), int(y), int(size), int(size), rl.YELLOW)
            if i < len(inv):
                item_data = inv[i]
                if item_data['type'] in self.assets:
                    tex = self.assets[item_data['type']]
                    rl.draw_texture_pro(tex, rl.Rectangle(0,0,tex.width,tex.height), rl.Rectangle(x+5,y+5,size-10,size-10), rl.Vector2(0,0), 0.0, rl.WHITE)
                    if item_data['count'] > 1: rl.draw_text(str(item_data['count']), int(x+2), int(y+size-12), 10, rl.WHITE)
                    if rl.check_collision_point_rec(rl.get_mouse_position(), slot_rect):
                        tooltip = item_data['type'].replace('item_', '').replace('_', ' ').title()
        if self.selected_item_index != -1 and self.selected_item_index < len(inv):
            if rl.gui_button(rl.Rectangle(rect.x, rect.y + 30 + rows * (size + pad) + 10, 100, 30), "Drop"):
                slot = inv[self.selected_item_index]; slot['count'] -= 1
                if slot['count'] <= 0: inv.pop(self.selected_item_index); self.selected_item_index = -1
                self.items[self.player['map']].append({'type':slot['type'], 'x':self.player['grid_x'], 'y':self.player['grid_y']})
            if self.selected_item_index != -1 and self.selected_item_index < len(inv) and inv[self.selected_item_index]['type'] == 'item_gem':
                if rl.gui_button(rl.Rectangle(rect.x + 110, rect.y + 30 + rows * (size + pad) + 10, 100, 30), "Repair"):
                    self.use_item(self.selected_item_index)
        if tooltip:
            mp = rl.get_mouse_position()
            tw = rl.measure_text(tooltip, 10)
            rl.draw_rectangle(int(mp.x + 10), int(mp.y + 10), tw + 10, 20, rl.fade(rl.BLACK, 0.8))
            rl.draw_text(tooltip, int(mp.x + 15), int(mp.y + 15), 10, rl.WHITE)

    def _draw_crafting_tab(self, rect):
        rl.draw_text("Crafting Station", int(rect.x), int(rect.y), 20, rl.BLACK)
        y_pos = rect.y + 35
        inv_counts = {}
        for slot in self.player.get('inventory', []): inv_counts[slot['type']] = inv_counts.get(slot['type'], 0) + slot['count']
        
        for recipe in self.recipes:
            can_craft = True; ing_text_parts = []
            for ing, count in recipe['ingredients'].items():
                has = inv_counts.get(ing, 0); 
                if has < count: can_craft = False
                ing_text_parts.append(f"{ing.replace('item_', '').title()}: {has}/{count}")
            
            rl.draw_text(recipe['name'], int(rect.x), int(y_pos), 20, rl.DARKGRAY)
            rl.draw_text(", ".join(ing_text_parts), int(rect.x + 150), int(y_pos + 5), 10, rl.GRAY)
            btn_rect = rl.Rectangle(rect.x + 400, y_pos, 100, 25)
            if can_craft:
                if rl.gui_button(btn_rect, "Craft"):
                    for ing, count in recipe['ingredients'].items():
                        slot = next((s for s in self.player['inventory'] if s['type'] == ing), None)
                        if slot:
                            slot['count'] -= count
                            if slot['count'] <= 0: self.player['inventory'].remove(slot)
                    self.add_inventory_item(recipe['result'])
            else: rl.gui_lock(); rl.gui_button(btn_rect, "Need Items"); rl.gui_unlock()
            y_pos += 35

    def _draw_map_tab(self, rect):
        rl.draw_text("World Map",int(rect.x),int(rect.y),20,rl.BLACK)
        if self.world_map_texture:
            brightness = (np.sin((self.day_time - 0.25) * np.pi * 2) + 1) / 2
            map_tint = rl.Color(int(255*max(0.4, brightness)), int(255*max(0.4, brightness)), int(255*max(0.4, brightness)), 255)
            map_tex=self.world_map_texture.texture; dest_w,dest_h=rect.width,rect.height-30; scale=min(dest_w/map_tex.width,dest_h/map_tex.height); draw_w,draw_h=map_tex.width*scale,map_tex.height*scale; draw_x,draw_y=rect.x+(dest_w-draw_w)/2,rect.y+30+(dest_h-draw_h)/2
            rl.draw_texture_pro(map_tex,rl.Rectangle(0,0,map_tex.width,-map_tex.height),rl.Rectangle(draw_x,draw_y,draw_w,draw_h),rl.Vector2(0,0),0.0,map_tint)
            player_chunk_x,player_chunk_y=self.player['grid_x']//CHUNK_SIZE,self.player['grid_y']//CHUNK_SIZE; chunk_pixel_size=(map_tex.width/WORLD_CHUNKS)*scale; marker_x,marker_y=draw_x+(player_chunk_x*chunk_pixel_size)+chunk_pixel_size/2,draw_y+(player_chunk_y*chunk_pixel_size)+chunk_pixel_size/2
            rl.draw_circle(int(marker_x),int(marker_y),5,rl.YELLOW); rl.draw_text("You are here",int(marker_x)-30,int(marker_y)-20,10,rl.RED)

    def _draw_options_tab(self, rect):
        rl.draw_text("Options",int(rect.x),int(rect.y),20,rl.BLACK)
        if rl.gui_button(rl.Rectangle(rect.x,rect.y+40,180,30),"Save Game"): self.save_game()
        if rl.gui_button(rl.Rectangle(rect.x,rect.y+80,180,30),"Return to Main Menu"): self.game_state='START_MENU'

    def run(self):
        while not self.should_close and not rl.window_should_close():
            if self.game_state=='GAMEPLAY': self._update_gameplay()
            elif self.game_state=='PAUSED' and (rl.is_key_pressed(rl.KEY_TAB) or rl.is_key_pressed(rl.KEY_ESCAPE)): self.game_state='GAMEPLAY'
            match self.game_state:
                case 'START_MENU': self._draw_start_menu()
                case 'GAMEPLAY': self._draw_gameplay()
                case 'PAUSED': self._draw_pause_menu()
                case 'SHOP': self._draw_shop_menu()
        if self.world_map_texture: rl.unload_render_texture(self.world_map_texture)
        rl.unload_sound(self.fx_use)
        rl.close_audio_device()
        rl.close_window()

    def _draw_player(self, item, sx, sy, color): rl.draw_texture_rec(self.assets['player_sheet'],self.assets['player_frames'][item.get('anim_frame',0)],rl.Vector2(int(sx-16),int(sy-55)),color)
    def _draw_npc(self, item, sx, sy, color):
        if item.get('type') == 'slime': rl.draw_texture(self.assets['slime'], int(sx-16), int(sy-24), color)
        elif item.get('type') == 'goblin': rl.draw_texture(self.assets['goblin'], int(sx-16), int(sy-24), color)
        else: rl.draw_texture_rec(self.assets['npc_sheet'],self.assets['player_frames'][0],rl.Vector2(int(sx-16),int(sy-55)),color)
        rl.draw_text(item['name'],int(sx-rl.measure_text(item['name'],10)/2),int(sy-65),10,color)
        if item.get('hp') < item.get('max_hp'):
            ratio = item['hp'] / item['max_hp']
            rl.draw_rectangle(int(sx-16), int(sy-70), 32, 4, rl.RED)
            rl.draw_rectangle(int(sx-16), int(sy-70), int(32*ratio), 4, rl.GREEN)
    def _draw_obj(self, item, sx, sy, color):
        if item['type']in self.assets: rl.draw_texture(self.assets[item['type']],int(sx-32),int(sy+self.object_draw_offsets.get(item['type'],0)),color)
    def _draw_item(self, item, sx, sy, color):
        if item['type']in self.assets: rl.draw_texture(self.assets[item['type']],int(sx-16),int(sy-16),color)

if __name__ == "__main__":
    IsoGame().run()
