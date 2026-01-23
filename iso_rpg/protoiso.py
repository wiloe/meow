import pyray as rl
import random
import numpy as np
import json
import os
import psutil
import math
import ctypes
from config import *
from ecs import ECSRegistry, Transform, Velocity, Lifetime, Health, ProjectileComp, ParticleComp, ParticleEmitter, Sprite, ScreenSpace, AIComponent, Animation
from systems import PhysicsSystem, ParticleUpdateSystem, ParticleEmitterSystem, LifetimeSystem, MobSystem, AnimationSystem, RenderSystem, ProjectileSystem
from asset_loader import AssetLoader
from utils import iso_to_screen, normalize, clamp, get_angle, check_circle_collision, screen_to_iso, a_star_search
from ui import ChatSystem
from quest_system import QuestSystem, Quest

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

class IsoGame:
    def __init__(self):
        rl.set_config_flags(rl.FLAG_WINDOW_RESIZABLE)
        rl.init_window(SCREEN_WIDTH, SCREEN_HEIGHT, "IsoRPG Engine (pyray)")
        rl.init_audio_device()
        rl.set_target_fps(60)

        # Game State and UI
        self.game_state = 'SPLASH'
        self.splash_timer = 3.0  # Show splash for 3 seconds
        self.pause_menu_active_tab = 0
        self.day_time = 0.5
        self.day_duration = 1440.0 # 24 minutes
        self.calendar = {'day': 1, 'week': 1, 'month': 1, 'year': 1, 'season': 'Spring'}
        self.selected_item_index = -1
        self.drag_data = None
        self.world_map_texture = None
        self.should_close = False
        self.gameplay_cache_texture = None
        self.gameplay_cache_valid = False
        self.fishing = {'active': False, 'state': 'idle', 'timer': 0}
        self.spells = { # TODO: Convert to data file
            'fireball': {'cost': 5, 'damage': 10, 'speed': 400, 'tex': 'projectile_fireball'},
            'magic_missile': {'cost': 2, 'damage': 4, 'speed': 600, 'tex': 'projectile_magic_missile'},
            'ice_lance': {'cost': 8, 'damage': 8, 'speed': 500, 'tex': 'projectile_ice_lance'},
            'acid_arrow': {'cost': 6, 'damage': 5, 'speed': 450, 'tex': 'projectile_acid_arrow'}
        }
        self.current_spell = 'fireball'
        
        self.weather = 'sunny'
        self.weather_timer = 0
        self.weather_duration = 60.0
        self.lightning_timer = 0
        self.lightning_active = False
        self.clouds = [{'x': random.randint(0, SCREEN_WIDTH), 'y': random.randint(0, SCREEN_HEIGHT//2), 'speed': random.uniform(5, 15)} for _ in range(10)]
        self.lightning_bolts = []

        self.recipes = [ # TODO: Convert to data file
            {'name': 'Mega Potion', 'result': 'item_mega_potion', 'ingredients': {'item_potion': 2}},
            {'name': 'Ancient Scroll', 'result': 'item_scroll', 'ingredients': {'item_potion': 1, 'item_gem': 1}},
            {'name': 'Bomb', 'result': 'item_bomb', 'ingredients': {'item_fiber': 2, 'item_stone': 1}},
            {'name': 'Stone Axe', 'result': 'item_axe', 'ingredients': {'item_wood': 2, 'item_stone': 2}},
            {'name': 'Stone Pick', 'result': 'item_pickaxe', 'ingredients': {'item_wood': 2, 'item_stone': 2}},
            {'name': 'Iron Sword', 'result': 'item_sword', 'ingredients': {'item_wood': 1, 'item_stone': 3}},
            {'name': 'Bread', 'result': 'item_bread', 'ingredients': {'item_wheat': 3}},
            {'name': 'Fur Coat', 'result': 'item_fur_coat', 'ingredients': {'item_wolf_fur': 3}},
            {'name': 'Bow', 'result': 'item_bow', 'ingredients': {'item_wood': 3, 'item_fiber': 2}},
            {'name': 'Arrows (x4)', 'result': 'item_arrow', 'count': 4, 'ingredients': {'item_wood': 1, 'item_stone': 1}}
        ]
        self.asset_loader = AssetLoader()
        self.assets = self.asset_loader.assets
        self.block_definitions = self.asset_loader.block_definitions
        self.character_palettes = self.asset_loader.character_palettes
        self.character_sheet_constructor = self.asset_loader.create_character_sheet
        self.player_appearance = {'body_idx': 0, 'skin_idx': 0, 'hair_idx': 0, 'pants_idx': 0}

        # Game World Data
        self.maps = {}
        self.chunk_grid = []
        self.objects = {}
        self.collision_cache = {} # New spatial cache
        self.npcs = {}
        self.player = {}
        self.fx_use = rl.load_sound(os.path.join(os.path.dirname(__file__), "../assets/pop.wav"))
        self.fx_step = rl.load_sound(os.path.join(os.path.dirname(__file__), "../assets/pop.wav")); rl.set_sound_pitch(self.fx_step, 0.6); rl.set_sound_volume(self.fx_step, 0.3) # TODO: Use a better sound
        self.camera = rl.Camera2D(rl.Vector2(SCREEN_WIDTH//2, SCREEN_HEIGHT//2), rl.Vector2(0,0), 0.0, 1.5)
        
        self.object_draw_offsets = {'tree':-110, 'pine_tree':-110, 'rock':-45, 'ladder':-32, 'chest':-32, 'wall':-80, 'dungeon_wall':-80, 'campfire':-32, 'bush':-32}
        self.draw_dispatch = {'player':self._draw_player, 'npc':self._draw_npc, 'obj':self._draw_obj, 'item':self._draw_item, 'ecs_sprite':self._draw_ecs_sprite}
        self.process = psutil.Process(os.getpid())
        self.debug_stats = {'ram': 0, 'cpu': 0, 'timer': 0}
        self.vignette = self._create_vignette()
        
        # Item Statistics Database
        self.item_stats = {
            # Tools
            'item_axe': {'type': 'tool', 'subtype': 'axe', 'damage': 4, 'weight': 'medium', 'durability': 50},
            'item_pickaxe': {'type': 'tool', 'subtype': 'pickaxe', 'damage': 3, 'weight': 'medium', 'durability': 50},
            # Weapons
            'item_dagger': {'type': 'weapon', 'subtype': 'dagger', 'damage': 5, 'weight': 'light', 'durability': 40},
            'item_sword': {'type': 'weapon', 'subtype': 'sword', 'damage': 8, 'weight': 'medium', 'durability': 80},
            'item_warhammer': {'type': 'weapon', 'subtype': 'hammer', 'damage': 15, 'weight': 'heavy', 'durability': 120},
            'item_bow': {'type': 'weapon', 'subtype': 'bow', 'damage': 2, 'weight': 'light', 'durability': 60},
            # Armor
            'item_leather_armor': {'type': 'armor', 'slot': 'chest', 'defense': 2, 'weight': 'light', 'durability': 80},
            'item_chainmail': {'type': 'armor', 'slot': 'chest', 'defense': 5, 'weight': 'medium', 'durability': 120},
            'item_plate_armor': {'type': 'armor', 'slot': 'chest', 'defense': 8, 'weight': 'heavy', 'durability': 200},
            'item_iron_helm': {'type': 'armor', 'slot': 'head', 'defense': 3, 'weight': 'medium', 'durability': 100},
            'item_fur_coat': {'type': 'armor', 'slot': 'chest', 'defense': 4, 'weight': 'light', 'durability': 100},
        }
        
        # Initialize ECS
        self.ecs = ECSRegistry()
        self.systems = [ParticleEmitterSystem(), ParticleUpdateSystem(), PhysicsSystem(), ProjectileSystem(), LifetimeSystem(), MobSystem(), AnimationSystem()]
        self.render_systems = [RenderSystem()]
        self.chat = ChatSystem(self)
        self.quest_system = QuestSystem(self)

    def _create_vignette(self):
        img = rl.gen_image_gradient_radial(800, 800, 0.0, rl.Color(0, 0, 0, 0), rl.Color(0, 0, 0, 255))
        texture = rl.load_texture_from_image(img)
        rl.unload_image(img)
        return texture

    def _generate_world_map_texture(self):
        if self.world_map_texture: rl.unload_render_texture(self.world_map_texture)
        map_image_size=256; self.world_map_texture=rl.load_render_texture(map_image_size,map_image_size); biome_colors={'temperate':COLOR_GRASS_TOP,'desert':COLOR_SAND_TOP,'taiga':COLOR_TAIGA_GRASS_TOP,'swamp':COLOR_SWAMP_MUD_TOP}; chunk_pixel_size=map_image_size//WORLD_CHUNKS
        rl.begin_texture_mode(self.world_map_texture); rl.clear_background(rl.BLACK)
        for cy in range(WORLD_CHUNKS):
            for cx in range(WORLD_CHUNKS): rl.draw_rectangle(cx*chunk_pixel_size,cy*chunk_pixel_size,chunk_pixel_size,chunk_pixel_size,biome_colors.get(self.chunk_grid[cy][cx],rl.MAGENTA))
        rl.end_texture_mode()

    def add_inventory_item(self, item_type, count=1):
        # Try to stack
        for slot in self.player['inventory']:
            if slot and slot['type'] == item_type: slot['count'] += count; return True
        # Find empty slot
        for i, slot in enumerate(self.player['inventory']):
            if slot is None:
                self.player['inventory'][i] = {'type': item_type, 'count': count}; return True
        return False # Inventory full

    def init_game_world(self):
        self.maps,self.objects,self.npcs,self.items,occupied={}, {'world':[],'cave':[],'dungeon':[]},{'world':[],'cave':[],'dungeon':[]},{'world':[],'cave':[],'dungeon':[]},{'world':set(),'cave':set(),'dungeon':set()}
        self.player={'x':4.0,'y':4.0,'grid_x':4,'grid_y':4,'map':'world','moving':False,'move_start_time':0,'start_pos':(4,4),'target_pos':(4,4),'stats':{'str':5,'dex':5,'int':5,'hp':20,'max_hp':20,'mana':20,'max_mana':20,'stamina':100,'max_stamina':100,'level':1,'xp':0,'next_level_xp':100,'weapon_durability':50,'max_weapon_durability':50,'gold':0,'hunger':100,'max_hunger':100,'farming_level':1,'farming_xp':0,'farming_next_xp':100},'inventory':[None]*20,'equipment':{'head':None,'chest':None,'hands':None,'legs':None,'feet':None,'weapon':None},'quests':[],'last_attack':0}
        self.player['inventory'][0] = {'type': 'item_food', 'count': 3}
        self.player['inventory'][1] = {'type': 'item_seeds_wheat', 'count': 5}
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
                            elif mat == 'grass' and random.random() < 0.02: self.npcs['world'].append({'name': 'Sheep', 'x': x, 'y': y, 'hp': 5, 'max_hp': 5, 'type': 'sheep', 'behavior': 'flee'})
                            elif mat=='sand'and random.random()<0.05: self.objects['world'].append({'type':'rock','x':x,'y':y}); occupied['world'].add((x,y))
                            elif mat=='taiga_grass'and random.random()<0.15: self.objects['world'].append({'type':'pine_tree','x':x,'y':y}); occupied['world'].add((x,y))
                            elif mat in ['grass', 'taiga_grass', 'swamp_mud'] and random.random() < 0.08: self.objects['world'].append({'type':'bush','x':x,'y':y}); occupied['world'].add((x,y))
                            elif self.chunk_grid[cy][cx] == 'swamp' and random.random() < 0.05: self.npcs['world'].append({'name': 'Slime', 'x': x, 'y': y, 'hp': 10, 'max_hp': 10, 'type': 'slime'})
                            elif self.chunk_grid[cy][cx] == 'taiga' and random.random() < 0.04: self.npcs['world'].append({'name': 'Goblin', 'x': x, 'y': y, 'hp': 15, 'max_hp': 15, 'type': 'goblin'})
                            elif self.chunk_grid[cy][cx] == 'taiga' and random.random() < 0.03: self.npcs['world'].append({'name': 'Wolf', 'x': x, 'y': y, 'hp': 25, 'max_hp': 25, 'type': 'wolf'})
                            elif random.random() < 0.03: self.npcs['world'].append({'name': 'Bat', 'x': x, 'y': y, 'hp': 8, 'max_hp': 8, 'type': 'bat', 'nocturnal': True})
                            elif random.random() < 0.03: self.items['world'].append({'type': random.choice(['item_potion', 'item_scroll', 'item_food', 'item_wood', 'item_stone', 'item_fiber', 'item_dagger', 'item_leather_armor']), 'x': x, 'y': y})
        self.maps['world']=world_map; lx,ly=5,5
        while not self.block_definitions[self.maps['world'][ly, lx]]['walkable']: lx,ly=random.randint(3,MAP_SIZE-4),random.randint(3,MAP_SIZE-4)
        self.player['x'],self.player['y'],self.player['grid_x'],self.player['grid_y']=float(lx+1),float(ly),lx+1,ly
        
        # Find unoccupied positions for spawn area entities
        def find_unoccupied(center_x, center_y, radius=5):
            for attempt in range(50):
                dx, dy = random.randint(-radius, radius), random.randint(-radius, radius)
                nx, ny = center_x + dx, center_y + dy
                if 0 <= nx < MAP_SIZE and 0 <= ny < MAP_SIZE and (nx, ny) not in occupied['world']:
                    if self.block_definitions[self.maps['world'][ny, nx]]['walkable']:
                        return nx, ny
            return center_x, center_y
        
        guide_x, guide_y = find_unoccupied(lx+2, ly+2)
        self.npcs['world'].append({'name':'Guide','x':guide_x,'y':guide_y,'hp':20,'max_hp':20,'quest':{'req':'item_potion','count': 1, 'desc':'Bring me a Potion for a reward.','completed':False, 'reward': {'xp': 100, 'gold': 20}}})
        occupied['world'].add((guide_x, guide_y))
        
        farmer_x, farmer_y = find_unoccupied(lx-2, ly+2)
        self.npcs['world'].append({'name':'Farmer','x':farmer_x,'y':farmer_y,'hp':20,'max_hp':20,'quest':{'req':'item_wheat','count': 5, 'desc':'I could use 5 wheat for some bread.','completed':False, 'reward': {'item': 'item_bread', 'count': 2}}})
        occupied['world'].add((farmer_x, farmer_y))
        
        merchant_x, merchant_y = find_unoccupied(lx+3, ly)
        self.npcs['world'].append({'name':'Merchant','x':merchant_x,'y':merchant_y,'hp':20,'max_hp':20})
        occupied['world'].add((merchant_x, merchant_y))
        
        campfire_x, campfire_y = find_unoccupied(lx+1, ly+1)
        self.objects['world'].append({'type':'campfire','x':campfire_x,'y':campfire_y}); occupied['world'].add((campfire_x,campfire_y))        
        bed_x, bed_y = find_unoccupied(lx-1, ly-1)
        self.objects['world'].append({'type':'bed','x':bed_x,'y':bed_y}); occupied['world'].add((bed_x,bed_y))
        
        ladder_x, ladder_y = find_unoccupied(lx, ly)
        # Clear obstacles around ladder
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                nx, ny = ladder_x + dx, ladder_y + dy
                to_remove = [o for o in self.objects['world'] if o['x'] == nx and o['y'] == ny and o['type'] in ['tree', 'pine_tree', 'rock', 'bush', 'wall']]
                for obj in to_remove:
                    self.objects['world'].remove(obj)
                    if (nx, ny) in occupied['world']: occupied['world'].remove((nx, ny))

        self.objects['world'].append({'type':'ladder','x':ladder_x,'y':ladder_y,'target_map':'cave','target_pos':(2,2)}); occupied['world'].add((ladder_x,ladder_y))
        cave_map,conceptual_cave_map=np.zeros((CAVE_MAP_SIZE, CAVE_MAP_SIZE), dtype=int),[['cave_wall'for _ in range(CAVE_MAP_SIZE)]for _ in range(CAVE_MAP_SIZE)]; px,py=CAVE_MAP_SIZE//2,CAVE_MAP_SIZE//2
        for _ in range(150): conceptual_cave_map[py][px]='stone_floor'; dx,dy=random.choice([(0,1),(0,-1),(1,0),(-1,0)]); px,py=max(1,min(CAVE_MAP_SIZE-2,px+dx)),max(1,min(CAVE_MAP_SIZE-2,py+dy))
        for y in range(CAVE_MAP_SIZE):
            for x in range(CAVE_MAP_SIZE):
                if conceptual_cave_map[y][x]=='cave_wall': self.objects['cave'].append({'type':'wall','x':x,'y':y}); occupied['cave'].add((x,y))
                elif random.random() < 0.08 and (x!=2 or y!=2): self.npcs['cave'].append({'name': 'Skeleton', 'x': x, 'y': y, 'hp': 12, 'max_hp': 12, 'type': 'skeleton'})
        self.maps['cave']=cave_map
        self.objects['cave'].append({'type':'ladder','x':2,'y':2,'target_map':'world','target_pos':(lx,ly)}); occupied['cave'].add((2,2))
        # Clear walls around cave ladder (3x3 area) to ensure exit is accessible
        self.objects['cave'] = [o for o in self.objects['cave'] if not (o.get('type') == 'wall' and abs(o['x'] - 2) <= 1 and abs(o['y'] - 2) <= 1)]
        
        # Dungeon Generation
        dungeon_x, dungeon_y = find_unoccupied(lx - 5, ly + 5)
        self.objects['world'].append({'type':'ladder','x':dungeon_x,'y':dungeon_y,'target_map':'dungeon','target_pos':(2,2)}); occupied['world'].add((dungeon_x,dungeon_y))
        dungeon_floor_id = next((i for i, b in enumerate(self.block_definitions) if b['material'] == 'dungeon_floor'), 0)
        dungeon_map,conceptual_dungeon=np.full((CAVE_MAP_SIZE, CAVE_MAP_SIZE), dungeon_floor_id, dtype=int),[['wall'for _ in range(CAVE_MAP_SIZE)]for _ in range(CAVE_MAP_SIZE)]; px,py=CAVE_MAP_SIZE//2,CAVE_MAP_SIZE//2
        for _ in range(200): conceptual_dungeon[py][px]='floor'; dx,dy=random.choice([(0,1),(0,-1),(1,0),(-1,0)]); px,py=max(1,min(CAVE_MAP_SIZE-2,px+dx)),max(1,min(CAVE_MAP_SIZE-2,py+dy))
        for y in range(CAVE_MAP_SIZE):
            for x in range(CAVE_MAP_SIZE):
                if conceptual_dungeon[y][x]=='wall': self.objects['dungeon'].append({'type':'dungeon_wall','x':x,'y':y}); occupied['dungeon'].add((x,y))
                elif random.random() < 0.1 and (x!=2 or y!=2): self.npcs['dungeon'].append({'name': 'Goblin', 'x': x, 'y': y, 'hp': 15, 'max_hp': 15, 'type': 'goblin'})
        self.maps['dungeon']=dungeon_map
        self.objects['dungeon'].append({'type':'ladder','x':2,'y':2,'target_map':'world','target_pos':(dungeon_x,dungeon_y)}); occupied['dungeon'].add((2,2))
        self.objects['dungeon'] = [o for o in self.objects['dungeon'] if not (o.get('type') == 'dungeon_wall' and abs(o['x'] - 2) <= 1 and abs(o['y'] - 2) <= 1)]
        self._generate_world_map_texture()
        self._rebuild_collision_cache()
        
        # Create Player Trail Emitter
        self.player_emitter_id = self.ecs.create_entity()
        self.ecs.add_component(self.player_emitter_id, Transform(self.player['x'], self.player['y'], self.player['map']))
        self.ecs.add_component(self.player_emitter_id, ParticleEmitter(
            rate=20.0, 
            color=rl.Color(200, 200, 200, 100), 
            size=3.0, 
            life_range=(0.3, 0.6), 
            gravity=-10.0, 
            active=False
        ))

    def _rebuild_collision_cache(self):
        """Build a set of occupied coordinates for O(1) lookup."""
        self.collision_cache = {}
        for map_name, objs in self.objects.items():
            self.collision_cache[map_name] = set()
            for obj in objs:
                if obj['type'] not in ['ladder', 'chest', 'bush']: # Walkable objects
                    self.collision_cache[map_name].add((int(obj['x']), int(obj['y'])))

    def to_screen(self, gx, gy): return iso_to_screen(gx, gy, TILE_WIDTH, TILE_HEIGHT)
    def change_map(self, t_map, t_pos): self.player['map']=t_map; self.player['x'],self.player['y']=float(t_pos[0]),float(t_pos[1]); self.player['grid_x'],self.player['grid_y']=t_pos[0],t_pos[1]; self.player['moving']=False

    def gain_xp(self, amount):
        s=self.player['stats']; s['xp']=s.get('xp',0)+amount; nxt=s.get('next_level_xp',100)
        if s['xp']>=nxt:
            s['xp']-=nxt; s['level']=s.get('level',1)+1; s['next_level_xp']=int(nxt*1.5)
            s['str']+=1; s['dex']+=1; s['int']+=1; s['max_hp']+=5; s['hp']=s['max_hp']
            self.chat.log(f"LEVEL UP! You are now level {s['level']}!", rl.GOLD)

    def gain_farming_xp(self, amount):
        s=self.player['stats']; s['farming_xp']=s.get('farming_xp',0)+amount; nxt=s.get('farming_next_xp',100)
        if s['farming_xp']>=nxt:
            s['farming_xp']-=nxt; s['farming_level']=s.get('farming_level',1)+1; s['farming_next_xp']=int(nxt*1.2)
            self.chat.log(f"Farming Level Up! ({s['farming_level']})", rl.GOLD)

    def get_player_damage(self):
        base_damage = self.player['stats']['str']
        weapon_type = self.player['equipment'].get('weapon')
        if weapon_type and weapon_type in self.item_stats:
            base_damage += self.item_stats[weapon_type]['damage']
        return base_damage

    def get_player_defense(self):
        defense = 0
        for slot in ['head', 'chest', 'hands', 'legs', 'feet']:
            item = self.player['equipment'].get(slot)
            if item and item in self.item_stats: defense += self.item_stats[item].get('defense', 0)
        return defense
    
    def _create_particles(self, x, y, count, color, speed_range=60, life_range=(0.5, 1.0), size=4, vel_y_bias=0, gravity=200.0, drag=1.0):
        for _ in range(count):
            eid = self.ecs.create_entity()
            self.ecs.add_component(eid, Transform(x, y, self.player['map']))
            self.ecs.add_component(eid, Velocity(random.uniform(-speed_range, speed_range), random.uniform(-speed_range, speed_range) + vel_y_bias))
            self.ecs.add_component(eid, ParticleComp(color, size, gravity, drag))
            self.ecs.add_component(eid, Lifetime(random.uniform(*life_range)))

    def _spawn_particles(self, gx, gy, count, color, offset_y=-30):
        sx, sy = self.to_screen(gx, gy)
        self._create_particles(sx, sy + offset_y, count, color)

    def use_item(self, index):
        inv = self.player.get('inventory', [])
        if 0 <= index < len(inv):
            item = inv[index]; used = False; 
            if item is None: return
            match item['type']:
                case 'item_potion':
                    if self.player['stats']['hp'] < self.player['stats']['max_hp']:
                        self.player['stats']['hp'] = clamp(self.player['stats']['hp'] + 10, 0, self.player['stats']['max_hp'])
                        self._spawn_particles(self.player['x'], self.player['y'], 20, rl.RED)
                        self.chat.log("Used Potion (+10 HP)", rl.GREEN); used = True
                    else: self.chat.log("HP full!", rl.RED)
                case 'item_mega_potion':
                    if self.player['stats']['hp'] < self.player['stats']['max_hp']:
                        self.player['stats']['hp'] = clamp(self.player['stats']['hp'] + 50, 0, self.player['stats']['max_hp'])
                        self._spawn_particles(self.player['x'], self.player['y'], 30, rl.PURPLE)
                        self.chat.log("Used Mega Potion (+50 HP)", rl.GREEN); used = True
                    else: self.chat.log("HP full!", rl.RED)
                case 'item_scroll': self.chat.log("You read the scroll... It's blank.", rl.GRAY)
                case 'item_gem':
                    if self.player['stats']['weapon_durability'] < self.player['stats']['max_weapon_durability']:
                        self.player['stats']['weapon_durability'] = clamp(self.player['stats']['weapon_durability'] + 20, 0, self.player['stats']['max_weapon_durability'])
                        self.chat.log("Repaired Weapon (+20)", rl.BLUE); used = True
                    else: self.chat.log("Weapon Durability full!", rl.RED)
                case 'item_food':
                    if self.player['stats'].get('hunger', 0) < self.player['stats'].get('max_hunger', 100):
                        self.player['stats']['hunger'] = clamp(self.player['stats'].get('hunger', 0) + 20, 0, self.player['stats'].get('max_hunger', 100))
                        self.chat.log("Ate Food (+20 Hunger)", rl.GREEN); used = True
                case 'item_wheat':
                    if self.player['stats'].get('hunger', 0) < self.player['stats'].get('max_hunger', 100):
                        self.player['stats']['hunger'] = clamp(self.player['stats'].get('hunger', 0) + 5, 0, self.player['stats'].get('max_hunger', 100))
                        self.chat.log("Ate Wheat (+5 Hunger)", rl.GREEN); used = True
                case 'item_bread':
                    if self.player['stats'].get('hunger', 0) < self.player['stats'].get('max_hunger', 100):
                        self.player['stats']['hunger'] = clamp(self.player['stats'].get('hunger', 0) + 30, 0, self.player['stats'].get('max_hunger', 100))
                        self.chat.log("Ate Bread (+30 Hunger)", rl.GREEN); used = True
                case 'item_fish':
                    if self.player['stats'].get('hunger', 0) < self.player['stats'].get('max_hunger', 100):
                        self.player['stats']['hunger'] = clamp(self.player['stats'].get('hunger', 0) + 15, 0, self.player['stats'].get('max_hunger', 100))
                        self.chat.log("Ate Fish (+15 Hunger)", rl.GREEN); used = True
                    else: self.chat.log("Not hungry!", rl.RED)
                case 'item_bomb':
                    used = True
                    self.chat.log("Bomb used!", rl.ORANGE)
                    self._spawn_particles(self.player['x'], self.player['y'], 50, rl.ORANGE)
                    px, py = self.player['x'], self.player['y']
                    # Damage NPCs
                    for npc in self.npcs[self.player['map']][:]:
                        if np.hypot(npc['x'] - px, npc['y'] - py) < 3.0:
                            npc['hp'] -= 50
                            if npc['hp'] <= 0: self.npcs[self.player['map']].remove(npc); self.gain_xp(50)
                    # Destroy Objects
                    for obj in self.objects[self.player['map']][:]:
                        if np.hypot(obj['x'] - px, obj['y'] - py) < 3.0:
                            drop = None
                            if obj['type'] in ['tree', 'pine_tree']: drop = 'item_wood'
                            elif obj['type'] in ['rock', 'wall']: drop = 'item_stone'
                            elif obj['type'] == 'bush': drop = 'item_fiber'
                            
                            if drop:
                                self.objects[self.player['map']].remove(obj)
                                self.items[self.player['map']].append({'type': drop, 'x': obj['x'], 'y': obj['y']})
                                self._spawn_particles(obj['x'], obj['y'], 10, rl.GRAY)
            if used:
                rl.play_sound(self.fx_use)
                item['count'] -= 1; 
                if item['count'] <= 0: inv[index] = None

    def _update_gameplay(self):
        self.chat.update()
        
        if rl.is_key_pressed(rl.KEY_F11): rl.toggle_fullscreen()
        
        # Zoom Control
        wheel = rl.get_mouse_wheel_move()
        if wheel != 0:
            self.camera.zoom = clamp(self.camera.zoom + wheel * 0.1, 0.5, 3.0)

        # Camera follow when not moving (moving updates in _update_player_movement)
        if not self.player.get('moving'):
            px_scr, py_scr = self.to_screen(self.player['x'], self.player['y'])
            self.camera.target = rl.Vector2(px_scr, py_scr)

        if rl.is_key_pressed(rl.KEY_Z):
            spell_keys = list(self.spells.keys())
            curr_idx = spell_keys.index(self.current_spell)
            self.current_spell = spell_keys[(curr_idx + 1) % len(spell_keys)]
            self.chat.log(f"Spell: {self.current_spell.replace('_', ' ').title()}", rl.PURPLE)

        if not self.chat.is_active:
            for i, key in enumerate([rl.KEY_ONE, rl.KEY_TWO, rl.KEY_THREE, rl.KEY_FOUR, rl.KEY_FIVE]):
                if rl.is_key_pressed(key): self.use_item(i)
            
        dt = rl.get_frame_time()
        
        prev_day_time = self.day_time
        self.day_time = (self.day_time + dt / self.day_duration) % 1.0
        if self.day_time < prev_day_time: self._advance_day()

        self.weather_timer += dt
        if self.weather_timer > self.weather_duration:
            self.weather_timer = 0; self.weather_duration = random.uniform(60, 120)
            self.weather = random.choice(['sunny', 'sunny', 'rainy', 'stormy', 'snowy'])
            self.chat.log(f"Weather: {self.weather.title()}", rl.SKYBLUE)
        
        # Cloud movement
        for c in self.clouds:
            c['x'] += c['speed'] * dt
            if c['x'] > rl.get_screen_width(): c['x'] = -100; c['y'] = random.randint(0, rl.get_screen_height()//2)

        is_inside = self.player.get('map') in ['cave', 'dungeon']

        if not is_inside:
            if self.weather in ['rainy', 'stormy']:
                psx, psy = self.to_screen(self.player['x'], self.player['y'])
                for _ in range(4):
                    self._create_particles(psx + random.uniform(-500, 500), psy + random.uniform(-400, 400) - 300, 1, rl.BLUE, speed_range=0, life_range=(1.0, 1.0), vel_y_bias=500)
            elif self.weather == 'snowy':
                psx, psy = self.to_screen(self.player['x'], self.player['y'])
                for _ in range(2):
                    self._create_particles(psx + random.uniform(-500, 500), psy + random.uniform(-400, 400) - 300, 1, rl.WHITE, speed_range=10, life_range=(2.0, 2.0), vel_y_bias=100)
            
            if self.weather == 'stormy':
                self.lightning_timer -= dt
                if self.lightning_timer <= 0: 
                    self.lightning_timer = random.uniform(5, 15); self.lightning_active = True; rl.play_sound(self.fx_use)
                    
                    # Lightning strike logic
                    target_x, target_y = 0, 0
                    
                    # 0.05% chance to hit player
                    if random.random() < 0.0005:
                        target_x, target_y = self.player['x'], self.player['y']
                        self.player['stats']['hp'] -= 10
                        self.chat.log("Struck by Lightning!", rl.YELLOW)
                    else:
                        rx, ry = self.player['x'] + random.randint(-10, 10), self.player['y'] + random.randint(-10, 10)
                        candidates = []
                        if self.player['map'] in self.objects:
                            for obj in self.objects[self.player['map']]:
                                if abs(obj['x'] - rx) < 5 and abs(obj['y'] - ry) < 5:
                                    h = 2 if obj['type'] in ['tree', 'pine_tree'] else 1
                                    candidates.append((obj, h))
                        if candidates:
                            candidates.sort(key=lambda x: x[1], reverse=True)
                            hit_obj = candidates[0][0]
                            target_x, target_y = hit_obj['x'], hit_obj['y']
                            if hit_obj['type'] in ['tree', 'pine_tree']:
                                self.objects[self.player['map']].remove(hit_obj)
                                self.items[self.player['map']].append({'type': 'item_wood', 'x': target_x, 'y': target_y})
                                self._spawn_particles(target_x, target_y, 20, rl.ORANGE)
                        else: target_x, target_y = rx, ry; self._spawn_particles(target_x, target_y, 10, rl.GRAY)
                    
                    sx, sy = self.to_screen(target_x, target_y)
                    self.lightning_bolts.append({'x': sx, 'y': sy, 'life': 0.2})

                if self.lightning_active and random.random() < 0.1: self.lightning_active = False
        
        for b in self.lightning_bolts: b['life'] -= dt
        self.lightning_bolts = [b for b in self.lightning_bolts if b['life'] > 0]

        if random.random() < 0.05:
            for obj in self.objects.get(self.player['map'], []):
                if obj['type'] == 'campfire': self._spawn_particles(obj['x'], obj['y'], 1, rl.ORANGE)

        if 'hunger' in self.player['stats']:
            self.player['stats']['hunger'] = clamp(self.player['stats']['hunger'] - dt * 0.5, 0, self.player['stats']['max_hunger'])
            if self.player['stats']['hunger'] <= 0 and rl.get_time() % 3.0 < dt:
                self.player['stats']['hp'] = clamp(self.player['stats']['hp'] - 1, 0, self.player['stats']['max_hp'])
                self.chat.log("Starving! (-1 HP)", rl.RED)
        
        if 'mana' in self.player['stats']:
            self.player['stats']['mana'] = clamp(self.player['stats']['mana'] + dt * 0.5, 0, self.player['stats']['max_mana'])

        if 'stamina' in self.player['stats']:
            # Weather affects stamina regeneration
            regen_mult = 1.0
            if self.weather == 'rainy': regen_mult = 0.8
            elif self.weather == 'stormy': regen_mult = 0.6
            elif self.weather == 'sunny': regen_mult = 1.2
            is_running = self.player.get('moving', False) and self.player.get('move_duration', 0.2) < 0.2
            if not is_running and self.player['stats'].get('hunger', 100) > 0:
                self.player['stats']['stamina'] = clamp(self.player['stats']['stamina'] + dt * 10 * regen_mult, 0, self.player['stats']['max_stamina'])

        # Fishing Logic
        if self.fishing['active']:
            if rl.is_key_pressed(rl.KEY_SPACE):
                if self.fishing['state'] == 'bite':
                    self.fishing['active'] = False
                    self.add_inventory_item('item_fish')
                    self.chat.log("Caught a Fish!", rl.GREEN)
                    self.gain_xp(10)
                else:
                    self.fishing['active'] = False
                    self.chat.log("Pulled too early!", rl.GRAY)
            elif self.fishing['state'] == 'waiting' and rl.get_time() > self.fishing['timer']:
                self.fishing['state'] = 'bite'
                self.fishing['timer'] = rl.get_time() + 0.7
                self.chat.log("BITE! Press SPACE!", rl.RED)
                rl.play_sound(self.fx_use)
            elif self.fishing['state'] == 'bite' and rl.get_time() > self.fishing['timer']:
                self.fishing['active'] = False
                self.chat.log("It got away...", rl.GRAY)
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
                wait = 2.0  # Base fishing wait time
                if self.weather in ['rainy', 'stormy']: wait *= 0.5
                self.fishing = {'active': True, 'state': 'waiting', 'timer': rl.get_time() + wait}
                self.chat.log("Fishing... (Wait for BITE)", rl.BLUE)
            else: self.chat.log("No water nearby.", rl.RED)

        # Spell Casting
        if rl.is_key_pressed(rl.KEY_Q):
            spell = self.spells[self.current_spell]
            if self.player['stats']['mana'] >= spell['cost']:
                self.player['stats']['mana'] -= spell['cost']
                sp = self.to_screen(self.player['x'], self.player['y'])
                mp = rl.get_screen_to_world_2d(rl.get_mouse_position(), self.camera)
                dx, dy = mp.x - sp[0], mp.y - (sp[1] - 30)
                vx, vy = normalize(dx, dy)
                rot = get_angle(sp[0], sp[1]-30, mp.x, mp.y)
                if vx != 0 or vy != 0:
                    eid = self.ecs.create_entity()
                    self.ecs.add_component(eid, Transform(sp[0], sp[1]-30, self.player['map']))
                    self.ecs.add_component(eid, Velocity(vx*spell['speed'], vy*spell['speed']))
                    effect = 'slow' if 'ice' in self.current_spell else ('poison' if 'acid' in self.current_spell else None)
                    self.ecs.add_component(eid, ProjectileComp(spell['damage'], effect))
                    self.ecs.add_component(eid, Sprite(spell['tex'], rotation=math.degrees(rot)))
                    self.ecs.add_component(eid, ScreenSpace())
                    self.ecs.add_component(eid, Lifetime(2.0))
            else: self.chat.log("Not enough Mana!", rl.RED)

        # Update Projectiles
        self.ecs.process_removals()
        for system in self.systems:
            system.update(dt, self.ecs, self)

        # NPC Logic
        is_night = self.day_time < 0.25 or self.day_time > 0.75
        if self.player['map'] in self.npcs:
            for npc in self.npcs[self.player['map']]:
                if npc.get('nocturnal') and not is_night: continue
                # Status Effects
                if 'status' in npc:
                    npc['status']['duration'] -= dt
                    if npc['status']['type'] == 'poison':
                        npc['status']['tick'] -= dt
                        if npc['status']['tick'] <= 0:
                            npc['hp'] -= 1; npc['status']['tick'] = 1.0
                            self._spawn_particles(npc['x'], npc['y'], 3, rl.LIME)
                            if npc['hp'] <= 0: self.npcs[self.player['map']].remove(npc); self.gain_xp(20)
                    if npc['status']['duration'] <= 0: del npc['status']
                
                if npc.get('type') in ['goblin', 'bat', 'skeleton', 'wolf']:
                    dist = math.hypot(self.player['x'] - npc['x'], self.player['y'] - npc['y'])
                    
                    # Bat Detection System
                    if npc['type'] == 'bat':
                        if dist < 7.0:
                            if not npc.get('alerted', False):
                                npc['alerted'] = True
                                self._spawn_particles(npc['x'], npc['y'], 5, rl.RED)
                        else:
                            npc['alerted'] = False
                            continue # Bats stay idle if far

                    if (0.5 < dist < 10.0) or (npc['type'] == 'bat' and dist < 10.0):
                        base_speed = (3.5 if npc['type'] == 'bat' else 2.0)
                        if npc['type'] == 'wolf': base_speed = 4.0
                        if npc.get('status', {}).get('type') == 'slow': base_speed *= 0.5
                        move_amount = base_speed * dt
                        
                elif npc.get('behavior') == 'flee':
                    dist = math.hypot(self.player['x'] - npc['x'], self.player['y'] - npc['y'])
                    if dist < 6.0: # Flee range
                        move_amount = 2.5 * dt
                        dx, dy = npc['x'] - self.player['x'], npc['y'] - self.player['y']
                        d = math.hypot(dx, dy)
                        if d > 0:
                            nx = npc['x'] + (dx / d) * move_amount
                            ny = npc['y'] + (dy / d) * move_amount
                            if self.block_definitions[self.maps[self.player['map']][int(ny), int(nx)]]['walkable']:
                                npc['x'] = nx; npc['y'] = ny
                        if npc['type'] == 'bat':
                            # Bats keep simple direct movement (flying)
                            angle = rl.get_time() * 2.0 + (id(npc) % 100)
                            target_x = self.player['x'] + math.cos(angle) * 3.0
                            target_y = self.player['y'] + math.sin(angle) * 3.0
                            tdist = math.hypot(target_x - npc['x'], target_y - npc['y'])
                            if tdist > 0.1:
                                dx = (target_x - npc['x']) / tdist * move_amount
                                dy = (target_y - npc['y']) / tdist * move_amount
                            else: dx, dy = 0, 0
                            npc['x'] += dx; npc['y'] += dy
                        else:
                            # Ground NPCs use A* Pathfinding
                            start_pos = (int(npc['x'] + 0.5), int(npc['y'] + 0.5))
                            target_pos = (int(self.player['x'] + 0.5), int(self.player['y'] + 0.5))
                            
                            # Update path periodically or if no path
                            npc['path_timer'] = npc.get('path_timer', 0) - dt
                            if npc['path_timer'] <= 0:
                                npc['path_timer'] = random.uniform(0.5, 1.0) # Stagger updates
                                npc['path'] = a_star_search(start_pos, target_pos, lambda p: self._get_neighbors(p, self.player['map']))
                                if len(npc['path']) > 0: npc['path'].pop(0) # Remove current tile
                            
                            # Follow path
                            path = npc.get('path', [])
                            if path:
                                next_node = path[0]
                                ndx, ndy = next_node[0] - npc['x'], next_node[1] - npc['y']
                                ndist = math.hypot(ndx, ndy)
                                
                                if ndist < 0.1:
                                    npc['path'].pop(0)
                                else:
                                    npc['x'] += (ndx / ndist) * move_amount
                                    npc['y'] += (ndy / ndist) * move_amount

        # Planting Seeds (Right Click)
        if rl.is_mouse_button_pressed(rl.MOUSE_RIGHT_BUTTON) and not self.chat.is_active:
            inv = self.player.get('inventory', [])
            if 0 <= self.selected_item_index < len(inv) and inv[self.selected_item_index]:
                item = inv[self.selected_item_index]
                if item['type'] == 'item_seeds_wheat':
                    w_pos = rl.get_screen_to_world_2d(rl.get_mouse_position(), self.camera)
                    gx, gy = round(w_pos.x/TILE_WIDTH + w_pos.y/TILE_HEIGHT), round(w_pos.y/TILE_HEIGHT - w_pos.x/TILE_WIDTH)
                    if abs(gx - self.player['grid_x']) <= 2 and abs(gy - self.player['grid_y']) <= 2:
                        if self.player['map'] in self.maps:
                            current_map = self.maps[self.player['map']]
                            if 0 <= gx < len(current_map) and 0 <= gy < len(current_map):
                                mat = self.block_definitions[current_map[gy, gx]]['material']
                                if mat in ['dirt', 'grass']:
                                    occupied_tile = any(int(o['x']) == gx and int(o['y']) == gy for o in self.objects.get(self.player['map'], []))
                                    if not occupied_tile:
                                        self.objects[self.player['map']].append({'type': 'crop', 'x': gx, 'y': gy, 'crop_type': 'wheat', 'stage': 0, 'growth': 0})
                                        item['count'] -= 1; self._spawn_particles(gx, gy, 5, rl.BROWN)
                                        if item['count'] <= 0: inv[self.selected_item_index] = None; self.selected_item_index = -1

        if self.player.get('moving'): self._update_player_movement(); return
        
        # Combat & Interaction
        if rl.is_key_pressed(rl.KEY_SPACE) and not self.chat.is_active:
            if rl.get_time() - self.player.get('last_attack',0) > 0.5:
                has_weapon = self.player['equipment'].get('weapon') is not None
                if has_weapon and self.player['stats'].get('weapon_durability', 0) <= 0:
                    self.chat.log("Weapon broken!", rl.RED)
                else:
                    self.player['last_attack'] = rl.get_time()
                    if has_weapon: self.player['stats']['weapon_durability'] -= 1
                    px, py = self.player['grid_x'], self.player['grid_y']
                    inv_types = [i['type'] for i in self.player['inventory'] if i]
                    hit_npc = False
                    for npc in self.npcs[self.player['map']]:
                        if abs(int(npc['x'])-px) <= 1 and abs(int(npc['y'])-py) <= 1:
                            dmg = self.get_player_damage()
                            npc['hp'] -= dmg
                            self.chat.log(f"Hit {npc['name']} for {dmg} dmg!", rl.ORANGE)
                            if npc['hp'] <= 0:
                                if npc.get('type') == 'wolf': self.items[self.player['map']].append({'type': 'item_wolf_fur', 'x': npc['x'], 'y': npc['y']})
                                self.npcs[self.player['map']].remove(npc); self.gain_xp(50)
                                self.chat.log(f"Defeated {npc['name']}! (+50 XP)", rl.GOLD)
                            hit_npc = True
                            break
                    if not hit_npc:
                        for obj in self.objects[self.player['map']][:]:
                            if abs(obj['x']-px) <= 1 and abs(obj['y']-py) <= 1:
                                self._handle_object_harvest(obj, inv_types, px, py)
                                break

        if rl.is_key_pressed(rl.KEY_E) and not self.chat.is_active:
            px,py,cmap=self.player['grid_x'],self.player['grid_y'],self.player['map']
            for npc in self.npcs[cmap]:
                if abs(int(npc['x'])-px) <= 1 and abs(int(npc['y'])-py) <= 1:
                    self._handle_npc_interaction(npc); return
            for obj in self.objects[cmap]:
                if abs(obj['x']-px)<=1 and abs(obj['y']-py)<=1:
                    if self._handle_object_interaction(obj): return
        if rl.is_key_pressed(rl.KEY_G) and not self.chat.is_active:
            px,py,cmap=self.player['grid_x'],self.player['grid_y'],self.player['map']
            found = [i for i in self.items[cmap] if i['x']==px and i['y']==py]
            for item in found:
                if self.add_inventory_item(item['type']):
                    self.items[cmap].remove(item)
        if rl.is_mouse_button_pressed(rl.MOUSE_LEFT_BUTTON) and not self.chat.is_active:
            w_pos=rl.get_screen_to_world_2d(rl.get_mouse_position(),self.camera); gx,gy=round(w_pos.x/TILE_WIDTH+w_pos.y/TILE_HEIGHT),round(w_pos.y/TILE_HEIGHT-w_pos.x/TILE_WIDTH); self.attempt_move(gx,gy)
        
        if not self.chat.is_active:
            dx, dy = self._get_movement_input()
            if dx != 0 or dy != 0: self.attempt_move(self.player['grid_x']+dx, self.player['grid_y']+dy)

    def _update_player_movement(self):
        now=rl.get_time(); dur=self.player.get('move_duration', 0.2); el=now-self.player['move_start_time']; t=min(1.0,el/dur)
        if now-self.player.get('anim_time',0)>0.1: 
            self.player['anim_frame']=(self.player.get('anim_frame',0)+1)%2; self.player['anim_time']=now
            rl.play_sound(self.fx_step)
            # Footstep particles
            if self.player['map'] in self.maps:
                mx, my = int(self.player['x'] + 0.5), int(self.player['y'] + 0.5)
                current_map = self.maps[self.player['map']]
                if 0 <= mx < len(current_map) and 0 <= my < len(current_map):
                    mat = self.block_definitions[current_map[my, mx]]['material']
                    if 'grass' in mat:
                        self._spawn_particles(self.player['x'], self.player['y'], 3, rl.Color(50, 100, 50, 255), offset_y=0)
        sx,sy=self.player['start_pos']; tx,ty=self.player['target_pos']
        self.player['x'],self.player['y']=sx+(tx-sx)*t,sy+(ty-sy)*t
        if t>=1.0: self.player.update({'moving':False,'x':float(tx),'y':float(ty),'grid_x':tx,'grid_y':ty,'anim_frame':0})
        px_scr,py_scr=self.to_screen(self.player['x'],self.player['y']); self.camera.target=rl.Vector2(px_scr,py_scr)
        
        # Sync Player Emitter
        if hasattr(self, 'player_emitter_id'):
            t_comp = self.ecs.get_component(self.player_emitter_id, Transform)
            e_comp = self.ecs.get_component(self.player_emitter_id, ParticleEmitter)
            if t_comp and e_comp:
                t_comp.x, t_comp.y = self.player['x'], self.player['y']
                t_comp.map_name = self.player['map']
                e_comp.active = True

    def _get_movement_input(self):
        """Extract keyboard input using match statement instead of elif chain."""
        keys = [
            (rl.KEY_W, rl.KEY_UP, 0, -1),
            (rl.KEY_S, rl.KEY_DOWN, 0, 1),
            (rl.KEY_A, rl.KEY_LEFT, -1, 0),
            (rl.KEY_D, rl.KEY_RIGHT, 1, 0),
        ]
        for key1, key2, dx, dy in keys:
            if rl.is_key_down(key1) or rl.is_key_down(key2):
                return dx, dy
        return 0, 0

    def _get_neighbors(self, pos, map_name):
        """Get valid neighbor coordinates for A* pathfinding."""
        x, y = pos
        neighbors = []
        if map_name not in self.maps: return []
        current_map = self.maps[map_name]
        map_size = len(current_map)
        
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < map_size and 0 <= ny < map_size:
                if self.block_definitions[current_map[ny, nx]]['walkable']:
                    # O(1) lookup instead of O(N) loop
                    if (nx, ny) not in self.collision_cache.get(map_name, set()):
                        neighbors.append((nx, ny))
        return neighbors

    def _advance_day(self):
        self.calendar['day'] += 1
        if self.calendar['day'] > 7:
            self.calendar['day'] = 1; self.calendar['week'] += 1
            if self.calendar['week'] > 4:
                self.calendar['week'] = 1; self.calendar['month'] += 1
                if self.calendar['month'] > 12:
                    self.calendar['month'] = 1; self.calendar['year'] += 1
        m = self.calendar['month']
        if 1 <= m <= 3: self.calendar['season'] = 'Spring'
        elif 4 <= m <= 6: self.calendar['season'] = 'Summer'
        elif 7 <= m <= 9: self.calendar['season'] = 'Autumn'
        else: self.calendar['season'] = 'Winter'
        self.chat.log(f"New Day: {self.calendar['season']}, Day {self.calendar['day']}", rl.SKYBLUE)
        
        # Crop Growth
        for map_name in self.objects:
            for obj in self.objects[map_name]:
                if obj['type'] == 'crop' and obj['stage'] < 3:
                    growth = 1.0 + (1.0 if self.weather in ['rainy', 'stormy'] else 0.0)
                    obj['growth'] += growth
                    if obj['growth'] >= 1.0: obj['stage'] += 1; obj['growth'] = 0

    def _handle_object_harvest(self, obj, inv_types, px, py):
        """Handle object harvesting using match statement."""
        match obj['type']:
            case 'rock' if 'item_pickaxe' in inv_types:
                self.objects[self.player['map']].remove(obj)
                self.items[self.player['map']].append({'type': random.choice(['item_stone', 'item_gem']), 'x': obj['x'], 'y': obj['y']})
                self.chat.log("Mined rock!", rl.GRAY)
                self._spawn_particles(obj['x'], obj['y'], 10, rl.GRAY)
                self._rebuild_collision_cache() # Update cache
            case 'tree' | 'pine_tree' if 'item_axe' in inv_types:
                self.objects[self.player['map']].remove(obj)
                self.items[self.player['map']].append({'type': 'item_wood', 'x': obj['x'], 'y': obj['y']})
                self.chat.log("Chopped tree!", rl.BROWN)
                self._spawn_particles(obj['x'], obj['y'], 10, rl.BROWN)
                self._rebuild_collision_cache() # Update cache
            case 'bush':
                self.objects[self.player['map']].remove(obj)
                self.items[self.player['map']].append({'type': 'item_fiber', 'x': obj['x'], 'y': obj['y']})
                self.chat.log("Collected fiber!", rl.GREEN)
                self._spawn_particles(obj['x'], obj['y'], 5, rl.GREEN)
            case 'crop':
                if obj['stage'] == 3:
                    self.objects[self.player['map']].remove(obj)
                    self.items[self.player['map']].append({'type': f"item_{obj['crop_type']}", 'x': obj['x'], 'y': obj['y']})
                    if random.random() < 0.5: self.items[self.player['map']].append({'type': f"item_seeds_{obj['crop_type']}", 'x': obj['x'], 'y': obj['y']})
                    self.chat.log(f"Harvested {obj['crop_type']}!", rl.GOLD)
                    self._spawn_particles(obj['x'], obj['y'], 10, rl.GOLD); self.gain_xp(10); self.gain_farming_xp(20)
                else: self.chat.log("Not ready yet.", rl.GRAY)
                # Bush isn't in collision cache usually, but good practice if it was


    def _handle_npc_interaction(self, npc):
        """Handle NPC interactions using match statement."""
        match npc.get('name'):
            case 'Merchant':
                self.game_state = 'SHOP'
            case 'Guide':
                if 'quest' in npc and not npc['quest']['completed']:
                    # Convert dict to Quest object for checking
                    quest_obj = Quest.from_dict(npc['quest'])
                    if self.quest_system.check_requirements(quest_obj):
                        self.chat.show_options("Guide: Do you have the potion?", [
                            {'text': "Yes, here it is.", 'callback': '_complete_guide_quest', 'args': (npc,)},
                            {'text': "No, not yet.", 'callback': '_close_chat', 'args': ()}
                        ])
                    else:
                        self.chat.log(f"Guide: {npc['quest']['desc']}", rl.WHITE)
                else:
                    self.chat.log("Guide: Safe travels!", rl.WHITE)
            case _:
                # Generic quest handling
                if 'quest' in npc and not npc['quest']['completed']:
                    quest_obj = Quest.from_dict(npc['quest'])
                    if self.quest_system.complete_quest(quest_obj):
                        npc['quest']['completed'] = True
                    else:
                        self.chat.log(f"Quest: {npc['quest']['desc']}", rl.WHITE)
                else:
                    self.chat.log(f"{npc['name']}: Hello, traveler.", rl.WHITE)

    def _complete_guide_quest(self, npc):
        quest_obj = Quest.from_dict(npc['quest'])
        if self.quest_system.complete_quest(quest_obj):
            npc['quest']['completed'] = True
        self.chat.log("Guide: Thank you! Here is your reward.", rl.GOLD)

    def _close_chat(self):
        self.chat.is_active = False

    def _handle_object_interaction(self, obj):
        """Handle object interactions using match statement. Returns True if interaction was handled."""
        match obj['type']:
            case 'ladder':
                if obj['x'] == self.player['grid_x'] and obj['y'] == self.player['grid_y']:
                    self.change_map(obj['target_map'], obj['target_pos'])
                    return True
            case 'campfire':
                self.day_time = 0.25
                self.player['stats']['hp'] = self.player['stats']['max_hp']
                self.player['stats']['mana'] = self.player['stats']['max_mana']
                self.chat.log("Slept by the fire. Morning comes.", rl.YELLOW)
                return True
            case 'bed':
                self.day_time = 0.25
                self.player['stats']['hp'] = self.player['stats']['max_hp']
                self.player['stats']['mana'] = self.player['stats']['max_mana']
                self.chat.log("You sleep in the bed. Sweet dreams.", rl.PURPLE)
                return True
        return False

    def attempt_move(self, tx, ty):
        if self.player['map'] not in self.maps: return
        current_map=self.maps[self.player['map']]; map_size=len(current_map)
        if not (0<=tx<map_size and 0<=ty<map_size) or (tx==self.player['grid_x'] and ty==self.player['grid_y']): return
        b_id=current_map[ty, tx]
        if not self.block_definitions[b_id]['walkable']: return
        for e_list in[self.objects[self.player['map']],self.npcs[self.player['map']]]:
            for e in e_list:
                if e.get('type') not in['ladder','chest']and int(e['x'])==tx and int(e['y'])==ty: return
        
        is_running = rl.is_key_down(rl.KEY_LEFT_SHIFT) and self.player['stats'].get('stamina', 0) >= 4
        duration = 0.1 if is_running else 0.2
        if self.weather in ['snowy', 'stormy']: duration *= 1.2
        if is_running: self.player['stats']['stamina'] -= 4
        
        self.player.update({'moving':True,'start_pos':(self.player['x'],self.player['y']),'target_pos':(tx,ty),'move_start_time':rl.get_time(),'move_duration':duration})

    def _get_dynamic_block_tint(self, brightness):
        """Calculate dynamic tint based on time of day for moving shadows/highlights."""
        t = self.day_time
        # Light direction rotates throughout the day (0 to 2π)
        light_angle = (t - 0.25) * 2 * math.pi  # 0 at sunrise, π/2 at noon, π at sunset, 3π/2 at midnight
        
        # Calculate light direction (x, y) for 2D lighting
        light_x = math.cos(light_angle)  # Left/right: negative=left shadow, positive=right shadow
        light_y = math.sin(light_angle)  # Up/down: negative=top shadow, positive=bottom shadow
        
        # Base colors for lighting - more visible night darkening
        nc = (10, 10, 40)   # Night (darker)
        dc = (255, 255, 255) # Day (brighter)
        
        # Stronger interpolation based on brightness
        r = int(nc[0] + (dc[0] - nc[0]) * brightness)
        g = int(nc[1] + (dc[1] - nc[1]) * brightness)
        b = int(nc[2] + (dc[2] - nc[2]) * brightness)

        # Adjust tint based on light direction for dynamic shadows - increased effect
        # Add warm tint when sun is low (sunrise/sunset)
        d1, d2 = abs(t - 0.25), abs(t - 0.75)
        sunset_factor = max(0, 1.0 - min(d1, d2) * 8.0)
        
        if sunset_factor > 0:
            r = min(255, int(r + 120 * sunset_factor))  # Increased from 80
            g = max(0, int(g - 40 * sunset_factor))     # Increased from -10
            b = max(0, int(b - 60 * sunset_factor))     # Increased from -30
        
        # Apply directional lighting - brighten in light direction, darken opposite (increased effect)
        light_strength = 0.25  # Increased from 0.15
        r = max(0, min(255, int(r + light_x * 40 * light_strength)))  # Increased from 30
        g = max(0, min(255, int(g + light_y * 25 * light_strength)))  # Increased from 15
        b = max(0, min(255, int(b - light_y * 20 * light_strength))) # Increased from 10
        
        return rl.Color(r, g, b, 255)

    def _draw_gameplay(self, run_begin_end=True):
        # Handle input keys
        if run_begin_end:
            if rl.is_key_pressed(rl.KEY_ESCAPE):
                self._go_to_main_menu()
            elif rl.is_key_pressed(rl.KEY_TAB):
                self.game_state = 'PAUSED'
        
        sw, sh = rl.get_screen_width(), rl.get_screen_height()
        self.camera.offset = rl.Vector2(sw // 2, sh // 2)
        
        is_inside = self.player.get('map') in ['cave', 'dungeon']
        
        if is_inside:
            bg_color = COLOR_BG
            tint = rl.Color(100, 100, 120, 255)
            brightness = 0.2
        else:
            # Day/Night Cycle
            t = self.day_time
            brightness = (math.sin((t - 0.25) * math.pi * 2) + 1) / 2
            brightness = max(0.1, brightness)

            # Get dynamic tint with moving shadows
            tint = self._get_dynamic_block_tint(brightness)
            
            # Background color based on brightness
            bg_r = int(20 + 80 * brightness)
            bg_g = int(20 + 160 * brightness)
            bg_b = int(40 + 215 * brightness)
            
            d1, d2 = abs(t - 0.25), abs(t - 0.75)
            sunset_factor = max(0, 1.0 - min(d1, d2) * 8.0)
            if sunset_factor > 0:
                 bg_r = min(255, int(bg_r + 60 * sunset_factor))
                 bg_g = max(0, int(bg_g - 10 * sunset_factor))
            bg_color = rl.Color(bg_r, bg_g, bg_b, 255)
            
        if run_begin_end: rl.begin_drawing()
        rl.clear_background(bg_color)
        
        # Draw Celestial Bodies
        if not is_inside:
            # Sun
            if 0.2 < self.day_time < 0.8:
                sun_x = int((self.day_time - 0.2) / 0.6 * sw)
                sun_y = int(sh * 0.2 + (self.day_time - 0.5)**2 * 4 * sh)
                rl.draw_circle_gradient(sun_x, sun_y, 60, rl.Color(255, 255, 200, 255), rl.Color(255, 200, 50, 0))
            
            # Moon
            moon_t = (self.day_time + 0.5) % 1.0
            if 0.2 < moon_t < 0.8:
                moon_x = int((moon_t - 0.2) / 0.6 * sw)
                moon_y = int(sh * 0.2 + (moon_t - 0.5)**2 * 4 * sh)
                rl.draw_circle_gradient(moon_x, moon_y, 60, rl.Color(200, 200, 255, 100), rl.Color(200, 200, 255, 0))
                rl.draw_circle(moon_x, moon_y, 40, rl.Color(220, 220, 255, 255))
                rl.draw_circle(moon_x - 12, moon_y - 6, 36, bg_color)

        rl.begin_mode_2d(self.camera)
        if self.player.get('map')in self.maps:
            current_map=self.maps[self.player['map']]; map_size=len(current_map)
            
            # Optimization: Only draw visible tiles around the player
            px, py = int(self.player['x']), int(self.player['y'])
            render_radius = 24  # Adjust based on screen size/zoom
            render_radius = 8  # Reduced for fog effect
            min_x, max_x = max(0, px - render_radius), min(map_size, px + render_radius)
            min_y, max_y = max(0, py - render_radius), min(map_size, py + render_radius)

            for y in range(min_y, max_y):
                for x in range(min_x, max_x):
                    dist = math.hypot(x - px, y - py)
                    if dist > 7.0: continue # Fog cutoff
                    
                    if dist > 5.5: # Fade out edge
                        alpha = int(255 * (1.0 - (dist - 5.5) / 1.5))
                        alpha = max(0, min(255, alpha))
                        tile_tint = rl.Color(tint.r, tint.g, tint.b, alpha)
                    else:
                        tile_tint = tint

                    sx,sy=self.to_screen(x,y); b_id=current_map[y, x]
                    if b_id<len(self.assets['blocks']): rl.draw_texture(self.assets['blocks'][b_id],int(sx-TILE_WIDTH//2),int(sy-TILE_HEIGHT//2),tile_tint)
        
        # Optimization: Filter entities by distance before creating render list
        px, py = self.player['x'], self.player['y']
        entity_render_radius = 12.0
        
        is_night = self.day_time < 0.25 or self.day_time > 0.75
        render_list=[{'entity_type':'player',**self.player,'depth':self.player.get('x',0)+self.player.get('y',0)+0.6}]
        
        if self.player.get('map')in self.npcs: 
            render_list.extend([{'entity_type':'npc',**n,'depth':n['x']+n['y']+0.5}for n in self.npcs[self.player['map']] if abs(n['x']-px) < entity_render_radius and abs(n['y']-py) < entity_render_radius and (not n.get('nocturnal') or is_night)])
        if self.player.get('map')in self.objects: 
            render_list.extend([{'entity_type':'obj',**o,'depth':o['x']+o['y']-(0.5 if o['type']in['ladder','chest']else -0.5)}for o in self.objects[self.player['map']] if abs(o['x']-px) < entity_render_radius and abs(o['y']-py) < entity_render_radius])
        if self.player.get('map')in self.items: 
            render_list.extend([{'entity_type':'item',**i,'depth':i['x']+i['y']+0.1}for i in self.items[self.player['map']] if abs(i['x']-px) < entity_render_radius and abs(i['y']-py) < entity_render_radius])
            
        hovered_item = None
        mouse_world_pos = rl.get_screen_to_world_2d(rl.get_mouse_position(), self.camera)

        # Add ECS Sprites to render list for proper depth sorting
        for eid, (pos, sprite) in self.ecs.view(Transform, Sprite):
            if pos.map_name == self.player['map']:
                # Determine depth and screen position based on coordinate space
                if self.ecs.get_component(eid, ScreenSpace):
                    # Screen space entities (like projectiles)
                    # Approximate depth using screen Y, or draw on top
                    depth = 9999 # Draw on top of most things, or calculate based on iso conversion
                else:
                    # Grid space entities (mobs, items)
                    depth = pos.x + pos.y
                
                render_list.append({'entity_type': 'ecs_sprite', 'sprite': sprite, 'pos': pos, 'depth': depth})

        render_list.sort(key=lambda item:item['depth'])
        for item in render_list:
            dist = math.hypot(item.get('x',0) - px, item.get('y',0) - py)
            if dist > 7.0: continue
            
            if dist > 5.5:
                alpha = int(255 * (1.0 - (dist - 5.5) / 1.5))
                alpha = max(0, min(255, alpha))
                entity_tint = rl.Color(tint.r, tint.g, tint.b, alpha)
            else:
                entity_tint = tint

            if item['entity_type'] == 'ecs_sprite':
                # Handle coordinate conversion for ECS entities
                if self.ecs.get_component(eid, ScreenSpace): sx, sy = item['pos'].x, item['pos'].y
                else: sx, sy = self.to_screen(item['pos'].x, item['pos'].y)
            else:
                sx,sy=self.to_screen(item.get('x',0),item.get('y',0))
            
            if item['entity_type'] == 'item':
                if rl.check_collision_point_rec(mouse_world_pos, rl.Rectangle(sx - 16, sy - 16, 32, 32)):
                    hovered_item = item
            
            draw_func=self.draw_dispatch.get(item['entity_type'])
            if draw_func: draw_func(item,sx,sy,entity_tint)
        
        for system in self.render_systems:
            system.update(rl.get_frame_time(), self.ecs, self)
            
        # Draw Lightning Bolts
        for b in self.lightning_bolts:
             start = rl.Vector2(b['x'] + random.randint(-50, 50), b['y'] - 400)
             end = rl.Vector2(b['x'], b['y'])
             mid1 = rl.Vector2(start.x + (end.x - start.x)*0.3 + random.randint(-30, 30), start.y + (end.y - start.y)*0.3)
             mid2 = rl.Vector2(start.x + (end.x - start.x)*0.6 + random.randint(-30, 30), start.y + (end.y - start.y)*0.6)
             rl.draw_line_ex(start, mid1, 3, rl.WHITE); rl.draw_line_ex(mid1, mid2, 3, rl.WHITE); rl.draw_line_ex(mid2, end, 3, rl.WHITE)
             rl.draw_circle_v(end, 15, rl.fade(rl.WHITE, 0.5))

        rl.end_mode_2d()
        
        # Lighting System
        if brightness < 1.0:
            rl.begin_blend_mode(rl.BLEND_ADDITIVE)
            
            # Campfire lights
            if self.player.get('map') in self.objects:
                for obj in self.objects[self.player['map']]:
                    if obj['type'] == 'campfire':
                        wx, wy = self.to_screen(obj['x'], obj['y'])
                        screen_pos = rl.get_world_to_screen_2d(rl.Vector2(wx, wy - 16), self.camera)
                        if -200 < screen_pos.x < sw + 200 and -200 < screen_pos.y < sh + 200:
                            fire_radius = 150 + random.uniform(-5, 15)
                            rl.draw_circle_gradient(int(screen_pos.x), int(screen_pos.y), fire_radius, rl.Color(255, 100, 20, int(180 * (1.0 - brightness))), rl.Color(0, 0, 0, 0))

            torch_radius = 200 + random.uniform(-5, 5)
            rl.draw_circle_gradient(sw // 2, sh // 2 - 25, torch_radius, rl.Color(255, 170, 80, int(200 * (1.0 - brightness))), rl.Color(0, 0, 0, 0))
            rl.end_blend_mode()
            
        if self.lightning_active: rl.draw_rectangle(0, 0, sw, sh, rl.fade(rl.WHITE, 0.3))
        elif self.weather == 'stormy': rl.draw_rectangle(0, 0, sw, sh, rl.fade(rl.BLACK, 0.3))
        elif self.weather == 'rainy': rl.draw_rectangle(0, 0, sw, sh, rl.fade(rl.BLUE, 0.1))
        
        # Draw Clouds
        if not is_inside:
            cloud_color = rl.Color(255, 255, 255, 150)
            if self.weather == 'rainy': cloud_color = rl.Color(200, 200, 220, 180)
            elif self.weather == 'stormy': cloud_color = rl.Color(80, 80, 100, 220)
            elif self.weather == 'snowy': cloud_color = rl.Color(240, 240, 255, 180)
            for c in self.clouds: rl.draw_texture(self.assets['cloud'], int(c['x']), int(c['y']), cloud_color)
        
        rl.draw_texture_pro(self.vignette, rl.Rectangle(0, 0, self.vignette.width, self.vignette.height), rl.Rectangle(0, 0, sw, sh), rl.Vector2(0, 0), 0.0, rl.fade(rl.WHITE, 0.5))
            
        stats=self.player.get('stats',{}); rl.draw_rectangle(5,5,200,150,rl.fade(rl.BLACK,0.5)); rl.draw_text("Player",10,10,20,rl.WHITE)
        rl.draw_texture_ex(self.assets['icon_heart'], rl.Vector2(10, 30), 0, 0.8, rl.WHITE); rl.draw_text(f"{stats.get('hp',0)}/{stats.get('max_hp',0)}", 40, 35, 20, rl.LIME)
        rl.draw_texture_ex(self.assets['icon_mana'], rl.Vector2(110, 30), 0, 0.8, rl.WHITE); rl.draw_text(f"{int(stats.get('mana',0))}/{stats.get('max_mana',20)}", 140, 35, 20, rl.BLUE)
        rl.draw_text(f"STR:{stats.get('str',0)} DEX:{stats.get('dex',0)} INT:{stats.get('int',0)}",10,60,10,rl.LIGHTGRAY)
        rl.draw_texture_ex(self.assets['icon_sword'], rl.Vector2(10, 75), 0, 0.6, rl.WHITE); rl.draw_text(f"{stats.get('weapon_durability',0)}/{stats.get('max_weapon_durability',0)}", 35, 78, 10, rl.ORANGE)
        rl.draw_texture_ex(self.assets['icon_gold'], rl.Vector2(110, 75), 0, 0.6, rl.WHITE); rl.draw_text(f"{stats.get('gold',0)}", 135, 78, 10, rl.GOLD)
        
        hunger_val = stats.get('hunger', 0)
        hunger_col = rl.RED if hunger_val < 20 and int(rl.get_time() * 4) % 2 == 0 else rl.WHITE
        rl.draw_texture_ex(self.assets['icon_hunger'], rl.Vector2(10, 95), 0, 0.6, hunger_col); rl.draw_text(f"{int(hunger_val)}/{stats.get('max_hunger',100)}", 35, 98, 10, hunger_col if hunger_col == rl.RED else rl.ORANGE)
        
        is_day = 0.25 < self.day_time < 0.75; time_icon = self.assets['icon_sun'] if is_day else self.assets['icon_moon']
        rl.draw_texture_ex(time_icon, rl.Vector2(110, 95), 0, 0.6, rl.WHITE); rl.draw_text(f"{int(self.day_time*24):02d}:00", 135, 98, 10, rl.YELLOW)
        rl.draw_text(f"Day {self.calendar['day']} ({self.calendar['season']})", 110, 115, 10, rl.WHITE)
        rl.draw_texture_ex(self.assets['icon_stamina'], rl.Vector2(10, 115), 0, 0.6, rl.WHITE); rl.draw_text(f"{int(stats.get('stamina',0))}/{stats.get('max_stamina',100)}", 35, 118, 10, rl.YELLOW)
        rl.draw_text(f"Spell (Z): {self.current_spell.replace('_',' ').title()}", 10, 135, 10, rl.PURPLE)
        
        if hovered_item:
            item_type = hovered_item['type']
            name = item_type.replace('item_', '').replace('_', ' ').title()
            tooltip_lines = [name]
            if item_type in self.item_stats:
                s = self.item_stats[item_type]
                if 'damage' in s: tooltip_lines.append(f"Dmg: {s['damage']}")
                if 'defense' in s: tooltip_lines.append(f"Def: {s['defense']}")
            mp = rl.get_mouse_position()
            max_w = max(rl.measure_text(l, 10) for l in tooltip_lines)
            rl.draw_rectangle(int(mp.x + 10), int(mp.y + 10), max_w + 20, len(tooltip_lines) * 15 + 10, rl.fade(rl.BLACK, 0.8))
            for i, line in enumerate(tooltip_lines): rl.draw_text(line, int(mp.x + 15), int(mp.y + 15 + i * 15), 10, rl.YELLOW if i == 0 else rl.WHITE)

        # Hotbar
        hotbar_x = sw // 2 - 125; hotbar_y = sh - 60
        for i in range(5):
            rect = rl.Rectangle(hotbar_x + i * 50, hotbar_y, 45, 45)
            rl.draw_rectangle_rec(rect, rl.fade(rl.BLACK, 0.5)); rl.draw_rectangle_lines(int(rect.x), int(rect.y), int(rect.width), int(rect.height), rl.GRAY)
            rl.draw_text(str(i+1), int(rect.x + 2), int(rect.y + 2), 10, rl.WHITE)
            inv = self.player.get('inventory', [])
            if i < len(inv) and inv[i] and inv[i]['type'] in self.assets:
                tex = self.assets[inv[i]['type']]; rl.draw_texture_pro(tex, rl.Rectangle(0,0,tex.width,tex.height), rl.Rectangle(rect.x+5, rect.y+5, 35, 35), rl.Vector2(0,0), 0.0, rl.WHITE)
                if inv[i]['count'] > 1: rl.draw_text(str(inv[i]['count']), int(rect.x + 28), int(rect.y + 32), 10, rl.WHITE)

        rl.draw_fps(sw - 80, 10)
        
        if rl.get_time() - self.debug_stats['timer'] > 0.5:
            self.debug_stats['ram'] = self.process.memory_info().rss / 1024 / 1024
            self.debug_stats['cpu'] = self.process.cpu_percent()
            self.debug_stats['timer'] = rl.get_time()
        rl.draw_text(f"RAM: {self.debug_stats['ram']:.1f} MB", sw - 100, 30, 10, rl.LIME)
        rl.draw_text(f"CPU: {self.debug_stats['cpu']:.1f}%", sw - 100, 45, 10, rl.LIME)

        self.chat.draw()

        if run_begin_end: rl.end_drawing()

    def save_game(self):
        serializable_maps = {k: v.tolist() for k, v in self.maps.items()}
        data = {'player':self.player,'maps':serializable_maps,'objects':self.objects,'npcs':self.npcs,'items':self.items,'day_time':self.day_time,'chunk_grid':self.chunk_grid,'weather':self.weather,'calendar':self.calendar}
        try:
            with open('savegame.json','w')as f: json.dump(data,f)
        except Exception as e: print(f"Error saving: {e}")

    def load_game(self):
        if not os.path.exists('savegame.json'): return
        try:
            with open('savegame.json','r')as f:
                data=json.load(f); self.player=data['player']; self.maps={k: np.array(v, dtype=int) for k, v in data['maps'].items()}; self.objects=data['objects']; self.npcs=data['npcs']; self.items=data['items']; self.day_time=data['day_time']; self.weather=data.get('weather','sunny'); self.calendar=data.get('calendar', self.calendar)
                if 'weapon_durability' not in self.player['stats']: self.player['stats'].update({'weapon_durability':50,'max_weapon_durability':50})
                if 'gold' not in self.player['stats']: self.player['stats']['gold'] = 0
                if 'hunger' not in self.player['stats']: self.player['stats'].update({'hunger': 100, 'max_hunger': 100})
                if 'mana' not in self.player['stats']: self.player['stats'].update({'mana': 20, 'max_mana': 20})
                if 'stamina' not in self.player['stats']: self.player['stats'].update({'stamina': 100, 'max_stamina': 100})
                if 'farming_level' not in self.player['stats']: self.player['stats'].update({'farming_level':1,'farming_xp':0,'farming_next_xp':100})
                if 'equipment' not in self.player: self.player['equipment'] = {'head':None,'chest':None,'hands':None,'legs':None,'feet':None,'weapon':None}
               # Migrate inventory to fixed size format
                new_inv = [None] * 20
                idx = 0
                for i in self.player.get('inventory', []):
                    if idx >= 20: break
                    if isinstance(i, str):
                        found = next((s for s in new_inv if s['type'] == i), None)
                        if found: found['count'] += 1
                        else: new_inv[idx] = {'type': i, 'count': 1}; idx += 1
                    elif i is not None: new_inv[idx] = i; idx += 1
                self.player['inventory'] = new_inv
                self.chunk_grid=data.get('chunk_grid',[])
                if not self.chunk_grid: biomes=['temperate','desert','taiga','swamp']; self.chunk_grid=[[random.choice(biomes)for _ in range(WORLD_CHUNKS)]for _ in range(WORLD_CHUNKS)]
                self._generate_world_map_texture(); self.game_state='GAMEPLAY'
        except Exception as e: print(f"Error loading: {e}")

    def _draw_splash_screen(self):
        """Draw splash screen with fading animation."""
        sw, sh = rl.get_screen_width(), rl.get_screen_height()
        rl.begin_drawing()
        rl.clear_background(rl.BLACK)
        
        # Fade effect: fully visible for first 2 seconds, then fade out
        fade_start = 2.0
        if self.splash_timer > fade_start:
            alpha = 255
        else:
            alpha = int(255 * (self.splash_timer / fade_start))
        
        # Draw game title
        title = "🎮 IsoRPG Engine"
        font_size = 60
        title_color = rl.Color(100, 200, 255, alpha)
        title_x = (sw - rl.measure_text(title, font_size)) // 2
        rl.draw_text(title, title_x, sh // 3, font_size, title_color)
        
        # Draw subtitle
        subtitle = "A Procedural Isometric World"
        subtitle_size = 24
        subtitle_color = rl.Color(150, 200, 150, alpha)
        subtitle_x = (sw - rl.measure_text(subtitle, subtitle_size)) // 2
        rl.draw_text(subtitle, subtitle_x, sh // 3 + 80, subtitle_size, subtitle_color)
        
        # Draw loading indicator
        loading_y = sh * 2 // 3
        rl.draw_text("Loading...", (sw - rl.measure_text("Loading...", 20)) // 2, loading_y, 20, rl.Color(200, 200, 200, alpha))
        
        # Draw decorative elements
        for i in range(5):
            offset = int((rl.get_time() * 100 + i * 40) % (sw + 100))
            rl.draw_line(offset, sh // 2, offset + 20, sh // 2, rl.Color(100, 100, 200, int(alpha * 0.3)))
        
        rl.end_drawing()
        
        # Update splash timer
        dt = rl.get_frame_time()
        self.splash_timer -= dt
        if self.splash_timer <= 0:
            self.game_state = 'START_MENU'
            self.splash_timer = 0

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
        rl.begin_drawing()
        self._draw_gameplay(run_begin_end=False)
        rl.draw_rectangle(0,0,sw,sh,rl.Color(0,0,0,150))
        win_w,win_h=400,300; win_x,win_y=(sw-win_w)//2,(sh-win_h)//2
        rl.gui_window_box(rl.Rectangle(win_x,win_y,win_w,win_h),"Merchant Shop")
        rl.draw_text(f"Gold: {self.player['stats'].get('gold', 0)}", int(win_x+20), int(win_y+40), 20, rl.GOLD)
        inv = self.player.get('inventory', [])
        gems = [slot for slot in inv if slot and slot['type'] == 'item_gem']
        y = win_y + 80
        if not gems: rl.draw_text("No gems to sell.", int(win_x+20), int(y), 20, rl.GRAY)
        else:
            for slot in gems:
                rl.draw_text(f"Gem (x{slot['count']})", int(win_x+20), int(y), 20, rl.WHITE)
                if rl.gui_button(rl.Rectangle(win_x+250, y, 100, 25), "Sell (50G)"):
                    slot['count'] -= 1; self.player['stats']['gold'] = self.player['stats'].get('gold', 0) + 50
                    self.chat.log("Sold Gem for 50 Gold", rl.GOLD)
                    if slot['count'] <= 0: self.player['inventory'][self.player['inventory'].index(slot)] = None
                y += 35
        if rl.gui_button(rl.Rectangle(win_x+win_w//2-50, win_y+win_h-40, 100, 30), "Close"): self.game_state = 'GAMEPLAY'
        rl.end_drawing()

    def _draw_pause_menu(self):
        # Handle input keys
        if rl.is_key_pressed(rl.KEY_TAB) or rl.is_key_pressed(rl.KEY_ESCAPE):
            self._close_pause_menu()
        
        sw, sh = rl.get_screen_width(), rl.get_screen_height()
        
        # Arrow key navigation for tabs
        if rl.is_key_pressed(rl.KEY_RIGHT):
            self.pause_menu_active_tab = (self.pause_menu_active_tab + 1) % 7
        elif rl.is_key_pressed(rl.KEY_LEFT):
            self.pause_menu_active_tab = (self.pause_menu_active_tab - 1) % 7
        
        # Cache gameplay scene on first menu open
        if not self.gameplay_cache_valid:
            if self.gameplay_cache_texture is None:
                self.gameplay_cache_texture = rl.load_render_texture(sw, sh)
            
            rl.begin_texture_mode(self.gameplay_cache_texture)
            self._draw_gameplay(run_begin_end=False)
            rl.end_texture_mode()
            self.gameplay_cache_valid = True
        
        # Draw cached gameplay texture
        rl.begin_drawing()
        rl.draw_texture_rec(self.gameplay_cache_texture.texture, 
                           rl.Rectangle(0, 0, sw, -sh),  # Flip Y for texture mode
                           rl.Vector2(0, 0), rl.WHITE)
        
        # Draw semi-transparent overlay
        rl.draw_rectangle(0, 0, sw, sh, rl.Color(0, 0, 0, 150))
        
        # Draw menu window
        win_w, win_h = 900, 550
        win_x, win_y = (sw - win_w) // 2, (sh - win_h) // 2
        window_closed = rl.gui_window_box(rl.Rectangle(win_x, win_y, win_w, win_h), "Menu (Arrow Keys to Switch)")
        
        # Handle close button
        if window_closed:
            self._close_pause_menu()
            rl.end_drawing()
            return
        
        tabs = ["Character", "Inventory", "Equipment", "Crafting", "Map", "Options", "Farming"]
        active_tab = rl.ffi.new("int *", self.pause_menu_active_tab)
        rl.gui_tab_bar(rl.Rectangle(win_x + 10, win_y + 24, win_w - 20, 20), tabs, len(tabs), active_tab)
        self.pause_menu_active_tab = int(active_tab[0])
        
        content_rect = rl.Rectangle(win_x + 10, win_y + 54, win_w - 20, win_h - 74)
        match self.pause_menu_active_tab:
            case 0: self._draw_character_sheet_tab(content_rect)
            case 1: self._draw_inventory_tab(content_rect)
            case 2: self._draw_equipment_tab(content_rect)
            case 3: self._draw_crafting_tab(content_rect)
            case 4: self._draw_map_tab(content_rect)
            case 5: self._draw_options_tab(content_rect)
            case 6: self._draw_farming_tab(content_rect)
        rl.end_drawing()
    
    def _close_pause_menu(self):
        """Close the pause menu and return to gameplay."""
        self.game_state = 'GAMEPLAY'
        self.gameplay_cache_valid = False
    
    def _go_to_main_menu(self):
        """Go back to the main menu."""
        self.game_state = 'START_MENU'
        self.gameplay_cache_valid = False

    def _draw_character_sheet_tab(self, rect):
        stats=self.player.get('stats',{}); y_pos=int(rect.y); rl.draw_text("Character Stats",int(rect.x),y_pos,20,rl.BLACK); y_pos+=30
        rl.draw_text(f"Level: {stats.get('level',1)}",int(rect.x+20),y_pos,20,rl.DARKGRAY); y_pos+=25
        xp,nxp=stats.get('xp',0),stats.get('next_level_xp',100); rl.draw_text(f"XP: {xp}/{nxp}",int(rect.x+20),y_pos,20,rl.DARKGRAY); y_pos+=25
        rl.draw_rectangle_lines(int(rect.x+20),y_pos,200,10,rl.GRAY); rl.draw_rectangle(int(rect.x+20),y_pos,int((xp/nxp)*200) if nxp else 0,10,rl.BLUE); y_pos+=25
        for key in ['str','dex','int','hp','max_hp']:
            if key in stats: rl.draw_text(f"{key.upper()}: {stats[key]}",int(rect.x+20),y_pos,20,rl.DARKGRAY); y_pos+=25
        
        # Character customization
        y_pos += 20; rl.draw_text("Appearance (Arrow Keys to Change)", int(rect.x), y_pos, 18, rl.BLACK); y_pos += 30
        
        # Draw character preview
        if self.assets['player_sheet']:
            tex = self.assets['player_sheet']
            preview_x, preview_y = int(rect.x + 250), int(y_pos - 20)
            rl.draw_texture_pro(tex, rl.Rectangle(0, 0, tex.width, tex.height), rl.Rectangle(preview_x, preview_y, 100, 100), rl.Vector2(0, 0), 0.0, rl.WHITE)
        
        # Body color selector
        rl.draw_text("Body:", int(rect.x+20), y_pos, 16, rl.DARKGRAY)
        for i, color in enumerate(self.character_palettes['body']):
            btn_x = int(rect.x + 120 + i * 30)
            rl.draw_rectangle(btn_x, int(y_pos), 24, 24, color)
            if self.player_appearance['body_idx'] == i:
                rl.draw_rectangle_lines(btn_x, int(y_pos), 24, 24, rl.YELLOW)
            if rl.gui_button(rl.Rectangle(btn_x, int(y_pos), 24, 24), ""):
                self.player_appearance['body_idx'] = i
                rl.unload_texture(self.assets['player_sheet'])
                self.assets['player_sheet'] = self.character_sheet_constructor(self.player_appearance['body_idx'], self.player_appearance['skin_idx'], self.player_appearance['hair_idx'], self.player_appearance['pants_idx'])
        y_pos += 35
        
        # Skin color selector
        rl.draw_text("Skin:", int(rect.x+20), y_pos, 16, rl.DARKGRAY)
        for i, color in enumerate(self.character_palettes['skin']):
            btn_x = int(rect.x + 120 + i * 30)
            rl.draw_rectangle(btn_x, int(y_pos), 24, 24, color)
            if self.player_appearance['skin_idx'] == i:
                rl.draw_rectangle_lines(btn_x, int(y_pos), 24, 24, rl.YELLOW)
            if rl.gui_button(rl.Rectangle(btn_x, int(y_pos), 24, 24), ""):
                self.player_appearance['skin_idx'] = i
                rl.unload_texture(self.assets['player_sheet'])
                self.assets['player_sheet'] = self.character_sheet_constructor(self.player_appearance['body_idx'], self.player_appearance['skin_idx'], self.player_appearance['hair_idx'], self.player_appearance['pants_idx'])
        y_pos += 35
        
        # Hair color selector
        rl.draw_text("Hair:", int(rect.x+20), y_pos, 16, rl.DARKGRAY)
        for i, color in enumerate(self.character_palettes['hair']):
            btn_x = int(rect.x + 120 + i * 30)
            rl.draw_rectangle(btn_x, int(y_pos), 24, 24, color)
            if self.player_appearance['hair_idx'] == i:
                rl.draw_rectangle_lines(btn_x, int(y_pos), 24, 24, rl.YELLOW)
            if rl.gui_button(rl.Rectangle(btn_x, int(y_pos), 24, 24), ""):
                self.player_appearance['hair_idx'] = i
                rl.unload_texture(self.assets['player_sheet'])
                self.assets['player_sheet'] = self.character_sheet_constructor(self.player_appearance['body_idx'], self.player_appearance['skin_idx'], self.player_appearance['hair_idx'], self.player_appearance['pants_idx'])
        y_pos += 35
        
        # Pants color selector
        rl.draw_text("Pants:", int(rect.x+20), y_pos, 16, rl.DARKGRAY)
        for i, color in enumerate(self.character_palettes['pants']):
            btn_x = int(rect.x + 120 + i * 30)
            rl.draw_rectangle(btn_x, int(y_pos), 24, 24, color)
            if self.player_appearance['pants_idx'] == i:
                rl.draw_rectangle_lines(btn_x, int(y_pos), 24, 24, rl.YELLOW)
            if rl.gui_button(rl.Rectangle(btn_x, int(y_pos), 24, 24), ""):
                self.player_appearance['pants_idx'] = i
                rl.unload_texture(self.assets['player_sheet'])
                self.assets['player_sheet'] = self.character_sheet_constructor(self.player_appearance['body_idx'], self.player_appearance['skin_idx'], self.player_appearance['hair_idx'], self.player_appearance['pants_idx'])
        y_pos += 40
        
        rl.draw_text("Completed Quests", int(rect.x), y_pos, 20, rl.BLACK); y_pos += 30
        for q in self.player.get('quests', []):
            rl.draw_text(f"- {q['desc']}", int(rect.x+20), y_pos, 10, rl.DARKGRAY); y_pos += 15

    def _draw_inventory_tab(self, rect):
        rl.draw_text("Inventory (G to pickup)",int(rect.x),int(rect.y),20,rl.BLACK)
        inv = self.player.get('inventory', [])
        cols, rows, size, pad = 5, 4, 50, 10
        tooltip = None
        mp = rl.get_mouse_position()

        for i in range(cols * rows):
            c, r = i % cols, i // cols
            x, y = rect.x + c * (size + pad), rect.y + 30 + r * (size + pad)
            slot_rect = rl.Rectangle(x, y, size, size)
            
            # Slot interaction
            if rl.check_collision_point_rec(mp, slot_rect):
                if rl.is_mouse_button_pressed(rl.MOUSE_LEFT_BUTTON):
                    self.selected_item_index = i
                    if inv[i]:
                        self.drag_data = {'index': i, 'item': inv[i], 'off_x': mp.x - x, 'off_y': mp.y - y}
                
                # Split stack (Shift + Right Click)
                elif rl.is_mouse_button_pressed(rl.MOUSE_RIGHT_BUTTON) and (rl.is_key_down(rl.KEY_LEFT_SHIFT) or rl.is_key_down(rl.KEY_RIGHT_SHIFT)):
                    if inv[i] and inv[i]['count'] > 1:
                        # Find empty slot
                        empty_idx = next((idx for idx, s in enumerate(inv) if s is None), -1)
                        if empty_idx != -1:
                            split_amt = inv[i]['count'] // 2
                            inv[i]['count'] -= split_amt
                            inv[empty_idx] = {'type': inv[i]['type'], 'count': split_amt}
                            self.chat.log("Stack split!", rl.WHITE)
                        else:
                            self.chat.log("Inventory full!", rl.RED)
            
            # Draw Slot Background
            if i == self.selected_item_index: rl.draw_rectangle_lines(int(x), int(y), int(size), int(size), rl.YELLOW)
            else: rl.draw_rectangle_lines(int(x), int(y), int(size), int(size), rl.GRAY)
            
            if inv[i]:
                # Draw item if not being dragged
                if not (self.drag_data and self.drag_data['index'] == i):
                    item_data = inv[i]
                    if item_data['type'] in self.assets:
                        tex = self.assets[item_data['type']]
                        rl.draw_texture_pro(tex, rl.Rectangle(0,0,tex.width,tex.height), rl.Rectangle(x+5,y+5,size-10,size-10), rl.Vector2(0,0), 0.0, rl.WHITE)
                        if item_data['count'] > 1: rl.draw_text(str(item_data['count']), int(x+2), int(y+size-12), 10, rl.WHITE)
                    if rl.check_collision_point_rec(mp, slot_rect) and not self.drag_data:
                        item_type = item_data['type']
                        name = item_type.replace('item_', '').replace('_', ' ').title()
                        tooltip = [name]
                        if item_type in self.item_stats:
                            stats = self.item_stats[item_type]
                            if 'damage' in stats: tooltip.append(f"Damage: {stats['damage']}")
                            if 'defense' in stats: tooltip.append(f"Defense: {stats['defense']}")
                            if 'durability' in stats: tooltip.append(f"Durability: {stats['durability']}")
                            if 'weight' in stats: tooltip.append(f"Weight: {stats['weight'].title()}")

        # Handle Dragging
        if self.drag_data:
            item_data = self.drag_data['item']
            if item_data['type'] in self.assets:
                tex = self.assets[item_data['type']]
                dx, dy = mp.x - self.drag_data['off_x'], mp.y - self.drag_data['off_y']
                rl.draw_texture_pro(tex, rl.Rectangle(0,0,tex.width,tex.height), rl.Rectangle(dx+5, dy+5, size-10, size-10), rl.Vector2(0,0), 0.0, rl.fade(rl.WHITE, 0.8))
                if item_data['count'] > 1: rl.draw_text(str(item_data['count']), int(dx+2), int(dy+size-12), 10, rl.WHITE)
            
            if rl.is_mouse_button_released(rl.MOUSE_LEFT_BUTTON):
                for i in range(cols * rows):
                    c, r = i % cols, i // cols
                    x, y = rect.x + c * (size + pad), rect.y + 30 + r * (size + pad)
                    if rl.check_collision_point_rec(mp, rl.Rectangle(x, y, size, size)):
                        if i != self.drag_data['index']:
                            src = self.drag_data['index']
                            if inv[i] and inv[src]['type'] == inv[i]['type']:
                                inv[i]['count'] += inv[src]['count']
                                inv[src] = None
                                self.selected_item_index = -1
                            else:
                                inv[src], inv[i] = inv[i], inv[src]
                                self.selected_item_index = i
                        break
                self.drag_data = None

        if self.selected_item_index != -1 and inv[self.selected_item_index]:
            if rl.gui_button(rl.Rectangle(rect.x, rect.y + 30 + rows * (size + pad) + 10, 100, 30), "Drop"):
                slot = inv[self.selected_item_index]; slot['count'] -= 1
                if slot['count'] <= 0: inv[self.selected_item_index] = None; self.selected_item_index = -1
                self.items[self.player['map']].append({'type':slot['type'], 'x':self.player['grid_x'], 'y':self.player['grid_y']})
            if self.selected_item_index != -1 and inv[self.selected_item_index] and inv[self.selected_item_index]['type'] == 'item_gem':
                if rl.gui_button(rl.Rectangle(rect.x + 110, rect.y + 30 + rows * (size + pad) + 10, 100, 30), "Repair"):
                    self.use_item(self.selected_item_index)
            
            if self.selected_item_index != -1 and inv[self.selected_item_index]:
                selected_item = inv[self.selected_item_index]
                item_type = selected_item['type']
                # Equip Button
                if item_type in self.item_stats:
                    stats = self.item_stats[item_type]
                    if stats.get('type') in ['weapon', 'armor', 'tool']:
                        if rl.gui_button(rl.Rectangle(rect.x + 220, rect.y + 30 + rows * (size + pad) + 10, 100, 30), "Equip"):
                            slot = stats.get('slot', 'weapon') if stats['type'] == 'armor' else 'weapon'
                            current = self.player['equipment'].get(slot)
                            if current: self.add_inventory_item(current) # Unequip current
                            self.player['equipment'][slot] = item_type # Equip new
                            selected_item['count'] -= 1 # Remove from inventory
                            if selected_item['count'] <= 0: inv[self.selected_item_index] = None; self.selected_item_index = -1
                            self.chat.log(f"Equipped {item_type.replace('item_', '').title()}", rl.GREEN)

        if tooltip:
            mp = rl.get_mouse_position()
            max_w = 0
            for line in tooltip:
                w = rl.measure_text(line, 10)
                if w > max_w: max_w = w
            
            h = len(tooltip) * 15 + 10
            rl.draw_rectangle(int(mp.x + 10), int(mp.y + 10), max_w + 20, h, rl.fade(rl.BLACK, 0.8))
            for i, line in enumerate(tooltip):
                color = rl.YELLOW if i == 0 else rl.WHITE
                rl.draw_text(line, int(mp.x + 15), int(mp.y + 15 + i * 15), 10, color)

    def _draw_equipment_tab(self, rect):
        rl.draw_text("Equipment", int(rect.x), int(rect.y), 20, rl.BLACK)
        y_pos = rect.y + 40
        
        # Initialize equipment if not present
        if 'equipment' not in self.player:
            self.player['equipment'] = {'head': None, 'chest': None, 'hands': None, 'legs': None, 'feet': None, 'weapon': None}
        
        equipment_slots = self.player['equipment']
        
        # Draw character preview with equipment
        preview_x = int(rect.x + 400)
        preview_y = int(rect.y + 20)
        rl.draw_rectangle(preview_x - 5, preview_y - 5, 130, 160, rl.Color(50, 50, 50, 100))
        rl.draw_rectangle_lines(preview_x - 5, preview_y - 5, 130, 160, rl.DARKGRAY)
        rl.draw_text("Equipment Preview", preview_x - 5, preview_y - 25, 14, rl.BLACK)
        
        # Draw character sprite
        if self.assets['player_sheet']:
            tex = self.assets['player_sheet']
            rl.draw_texture_pro(tex, rl.Rectangle(0, 0, tex.width, tex.height), rl.Rectangle(preview_x, preview_y, 120, 120), rl.Vector2(0, 0), 0.0, rl.WHITE)
        
        # Render a screenshot placeholder on black screens
        rl.draw_rectangle(preview_x + 10, preview_y + 70, 100, 40, rl.BLACK)
        rl.draw_text("Render", preview_x + 30, preview_y + 78, 10, rl.GRAY)
        
        # Equipment slots list
        slot_names = ['Head', 'Chest', 'Hands', 'Legs', 'Feet', 'Weapon']
        slot_keys = list(equipment_slots.keys())
        
        for idx, (slot_name, slot_key) in enumerate(zip(slot_names, slot_keys)):
            y = y_pos + idx * 35
            rl.draw_text(f"{slot_name}:", int(rect.x + 20), int(y), 16, rl.DARKGRAY)
            
            # Display equipped item or empty
            equipped_item = equipment_slots[slot_key]
            if equipped_item:
                stats = self.item_stats.get(equipped_item, {})
                stat_text = f" (Dmg: {stats.get('damage',0)})" if stats.get('type') in ['weapon','tool'] else f" (Def: {stats.get('defense',0)})"
                weight_text = f" [{stats.get('weight','?').title()}]"
                rl.draw_text(f"→ {equipped_item.replace('item_','').title()}{stat_text}{weight_text}", int(rect.x + 150), int(y), 14, rl.GREEN)
                if rl.gui_button(rl.Rectangle(rect.x + 320, y, 60, 25), "Unequip"):
                    self.add_inventory_item(equipped_item)
                    equipment_slots[slot_key] = None
            else:
                rl.draw_text("Empty", int(rect.x + 150), int(y), 14, rl.GRAY)
        
        # Equipment tips
        tip_y = y_pos + 7 * 35
        rl.draw_rectangle(int(rect.x), int(tip_y), int(rect.width), 60, rl.Color(30, 30, 40, 100))
        rl.draw_text(f"Total Stats: Damage {self.get_player_damage()} | Defense {self.get_player_defense()}", int(rect.x + 10), int(tip_y + 5), 12, rl.YELLOW)
        rl.draw_text("Equip items from Inventory to boost stats.", int(rect.x + 10), int(tip_y + 25), 10, rl.WHITE)

    def _draw_crafting_tab(self, rect):
        rl.draw_text("Crafting Station", int(rect.x), int(rect.y), 20, rl.BLACK)
        y_pos = rect.y + 35
        inv_counts = {}
        for slot in self.player.get('inventory', []): 
            if slot: inv_counts[slot['type']] = inv_counts.get(slot['type'], 0) + slot['count']
        
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
                        slot = next((s for s in self.player['inventory'] if s and s['type'] == ing), None)
                        if slot: slot['count'] -= count
                        if slot and slot['count'] <= 0: self.player['inventory'][self.player['inventory'].index(slot)] = None
                    self.add_inventory_item(recipe['result'], recipe.get('count', 1))
            else: rl.gui_lock(); rl.gui_button(btn_rect, "Need Items"); rl.gui_unlock()
            y_pos += 35

    def _draw_map_tab(self, rect):
        rl.draw_text("World Map",int(rect.x),int(rect.y),20,rl.BLACK)
        if self.world_map_texture:
            brightness = (math.sin((self.day_time - 0.25) * math.pi * 2) + 1) / 2
            map_tint = rl.Color(int(255*max(0.4, brightness)), int(255*max(0.4, brightness)), int(255*max(0.4, brightness)), 255)
            map_tex=self.world_map_texture.texture; dest_w,dest_h=rect.width,rect.height-30; scale=min(dest_w/map_tex.width,dest_h/map_tex.height); draw_w,draw_h=map_tex.width*scale,map_tex.height*scale; draw_x,draw_y=rect.x+(dest_w-draw_w)/2,rect.y+30+(dest_h-draw_h)/2
            rl.draw_texture_pro(map_tex,rl.Rectangle(0,0,map_tex.width,-map_tex.height),rl.Rectangle(draw_x,draw_y,draw_w,draw_h),rl.Vector2(0,0),0.0,map_tint)
            player_chunk_x,player_chunk_y=self.player['grid_x']//CHUNK_SIZE,self.player['grid_y']//CHUNK_SIZE; chunk_pixel_size=(map_tex.width/WORLD_CHUNKS)*scale; marker_x,marker_y=draw_x+(player_chunk_x*chunk_pixel_size)+chunk_pixel_size/2,draw_y+(player_chunk_y*chunk_pixel_size)+chunk_pixel_size/2
            rl.draw_circle(int(marker_x),int(marker_y),5,rl.YELLOW); rl.draw_text("You are here",int(marker_x)-30,int(marker_y)-20,10,rl.RED)

    def _draw_options_tab(self, rect):
        """Draw options tab with better spacing."""
        y_pos = int(rect.y) + 10
        rl.draw_text("Options", int(rect.x), y_pos, 20, rl.BLACK)
        y_pos += 40
        
        # Save Game Button
        if rl.gui_button(rl.Rectangle(rect.x, y_pos, 250, 35), "Save Game"):
            self.save_game()
            self.chat.log("Game Saved!", rl.GREEN)
        y_pos += 45
        
        # Return to Main Menu Button
        if rl.gui_button(rl.Rectangle(rect.x, y_pos, 250, 35), "Return to Main Menu"):
            self._go_to_main_menu()
        y_pos += 45
        
        # Settings display (read-only info)
        settings_y = y_pos
        rl.draw_text("Game Settings", int(rect.x + 300), int(settings_y), 18, rl.BLACK)
        settings_y += 30
        rl.draw_text(f"Day Cycle: {self.day_duration:.0f}s", int(rect.x + 300), int(settings_y), 14, rl.DARKGRAY)
        settings_y += 25
        rl.draw_text(f"Time: {self.day_time * 24:.1f}h", int(rect.x + 300), int(settings_y), 14, rl.DARKGRAY)
        settings_y += 25
        rl.draw_text(f"Weather: {self.weather.title()}", int(rect.x + 300), int(settings_y), 14, rl.DARKGRAY)
        settings_y += 25
        rl.draw_text(f"Date: {self.calendar['season']}, Day {self.calendar['day']}", int(rect.x + 300), int(settings_y), 14, rl.DARKGRAY)

    def _draw_farming_tab(self, rect):
        rl.draw_text("Farming Skills", int(rect.x), int(rect.y), 20, rl.BLACK)
        y = int(rect.y + 40)
        stats = self.player.get('stats', {})
        rl.draw_text(f"Farming Level: {stats.get('farming_level', 1)}", int(rect.x + 20), y, 20, rl.DARKGRAY)
        y += 30
        xp, nxp = stats.get('farming_xp', 0), stats.get('farming_next_xp', 100)
        rl.draw_text(f"XP: {xp}/{nxp}", int(rect.x + 20), y, 20, rl.DARKGRAY)
        y += 25
        rl.draw_rectangle_lines(int(rect.x + 20), y, 300, 20, rl.GRAY)
        if nxp > 0: rl.draw_rectangle(int(rect.x + 20), y, int((xp/nxp)*300), 20, rl.GREEN)

    def run(self):
        while not self.should_close and not rl.window_should_close():
            if self.game_state=='GAMEPLAY': self._update_gameplay()
            
            match self.game_state:
                case 'SPLASH': self._draw_splash_screen()
                case 'START_MENU': self._draw_start_menu()
                case 'GAMEPLAY': self._draw_gameplay()
                case 'PAUSED': self._draw_pause_menu()
                case 'SHOP': self._draw_shop_menu()
        if self.world_map_texture: rl.unload_render_texture(self.world_map_texture)
        if self.gameplay_cache_texture: rl.unload_render_texture(self.gameplay_cache_texture)
        rl.unload_sound(self.fx_use); rl.unload_sound(self.fx_step)
        rl.close_audio_device()
        rl.close_window()
        rl.close_window()

    def _draw_player(self, item, sx, sy, color):
        # Draw shadow
        shadow_scale = 0.8
        rl.draw_ellipse(int(sx), int(sy + 8), int(20 * shadow_scale), int(6 * shadow_scale), rl.Color(0, 0, 0, 80))
        # Draw player sprite with lighting color
        rl.draw_texture_rec(self.assets['player_sheet'], self.assets['player_frames'][item.get('anim_frame', 0)], rl.Vector2(int(sx - 16), int(sy - 55)), color)
    
    def _draw_npc(self, item, sx, sy, color):
        # Draw shadow
        shadow_scale = 0.8
        rl.draw_ellipse(int(sx), int(sy + 8), int(20 * shadow_scale), int(6 * shadow_scale), rl.Color(0, 0, 0, 80))
        # Draw NPC sprite with lighting color
        if item.get('type') == 'slime': rl.draw_texture(self.assets['slime'], int(sx-16), int(sy-24), color)
        elif item.get('type') == 'goblin': rl.draw_texture(self.assets['goblin'], int(sx-16), int(sy-24), color)
        elif item.get('type') == 'bat': rl.draw_texture(self.assets['bat'], int(sx-32), int(sy-60), color)
        elif item.get('type') == 'skeleton': rl.draw_texture(self.assets['skeleton'], int(sx-16), int(sy-24), color)
        elif item.get('type') == 'sheep': rl.draw_texture(self.assets['sheep'], int(sx-16), int(sy-24), color)
        elif item.get('type') == 'wolf': rl.draw_texture(self.assets['wolf'], int(sx-16), int(sy-24), color)
        else: rl.draw_texture_rec(self.assets['npc_sheet'], self.assets['player_frames'][0], rl.Vector2(int(sx-16), int(sy-55)), color)
        rl.draw_text(item['name'], int(sx - rl.measure_text(item['name'], 10) / 2), int(sy - 65), 10, color)
        if item.get('hp') < item.get('max_hp'):
            ratio = item['hp'] / item['max_hp']
            rl.draw_rectangle(int(sx - 16), int(sy - 70), 32, 4, rl.RED)
            rl.draw_rectangle(int(sx - 16), int(sy - 70), int(32 * ratio), 4, rl.GREEN)
    def _draw_obj(self, item, sx, sy, color):
        if item['type']in self.assets: rl.draw_texture(self.assets[item['type']],int(sx-32),int(sy+self.object_draw_offsets.get(item['type'],0)),color)
        elif item['type'] == 'crop':
            tex_key = f"crop_{item['crop_type']}_{item['stage']}"
            if tex_key in self.assets: rl.draw_texture(self.assets[tex_key], int(sx - 16), int(sy - 16), color)

    def _draw_item(self, item, sx, sy, color):
        if item['type']in self.assets: rl.draw_texture(self.assets[item['type']],int(sx-16),int(sy-16),color)
    
    def _draw_ecs_sprite(self, item, sx, sy, color):
        sprite = item['sprite']
        if sprite.texture_key in self.assets:
            tex = self.assets[sprite.texture_key]
            # Combine environmental tint (color) with sprite tint
            if hasattr(sprite.tint, 'r'):
                sr, sg, sb, sa = sprite.tint.r, sprite.tint.g, sprite.tint.b, sprite.tint.a
            else:
                sr, sg, sb, sa = sprite.tint[0], sprite.tint[1], sprite.tint[2], sprite.tint[3] if len(sprite.tint) > 3 else 255
            
            final_color = rl.Color(int(color.r * sr / 255), int(color.g * sg / 255), int(color.b * sb / 255), int(color.a * sa / 255))
            
            src_rect = sprite.source_rect if sprite.source_rect else rl.Rectangle(0, 0, tex.width, tex.height)
            dest_rect = rl.Rectangle(sx + sprite.offset_x, sy + sprite.offset_y, src_rect.width * sprite.scale, src_rect.height * sprite.scale)
            origin = rl.Vector2(dest_rect.width / 2, dest_rect.height / 2)
            
            rl.draw_texture_pro(tex, src_rect, dest_rect, origin, sprite.rotation, final_color)

if __name__ == "__main__":
    IsoGame().run()
