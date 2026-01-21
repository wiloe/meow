import pyray as rl
from dataclasses import dataclass, field
from typing import List, Tuple, Any, Set, Dict

class Component: pass

@dataclass
class Transform(Component):
    x: float
    y: float
    map_name: str

@dataclass
class Velocity(Component):
    vx: float
    vy: float

@dataclass
class Lifetime(Component):
    amount: float

@dataclass
class Health(Component):
    current: int
    max: int

@dataclass
class ProjectileComp(Component):
    damage: int
    effect_type: str = None

@dataclass
class ParticleComp(Component):
    color: rl.Color
    size: float = 4.0
    gravity: float = 0.0
    drag: float = 0.0

@dataclass
class ParticleEmitter(Component):
    rate: float = 10.0
    timer: float = 0.0
    color: rl.Color = rl.WHITE
    life_range: Tuple[float, float] = (0.5, 1.0)
    speed_range: float = 60.0
    size: float = 4.0
    gravity: float = 0.0
    drag: float = 0.0
    active: bool = True
    burst_count: int = 0

@dataclass
class Sprite(Component):
    texture_key: str
    offset_x: float = 0
    offset_y: float = 0
    rotation: float = 0.0
    scale: float = 1.0
    tint: rl.Color = rl.WHITE
    source_rect: rl.Rectangle = None

class ScreenSpace(Component):
    pass

@dataclass
class AIComponent(Component):
    behavior: str = 'hostile'
    detect_range: float = 8.0
    speed: float = 2.0
    path: list = field(default_factory=list)
    path_timer: float = 0.0

@dataclass
class Animation(Component):
    frames: List[rl.Rectangle] = field(default_factory=list)
    frame_duration: float = 0.2
    timer: float = 0.0
    current_frame: int = 0

class ECSRegistry:
    def __init__(self):
        self.next_id = 0
        self.components = {}
        self.entities = set()
        self.dead_entities = set()
        self.archetypes = {}
        self.entity_archetype = {}
        self.query_cache = {}

    def create_entity(self):
        eid = self.next_id
        self.next_id += 1
        self.entities.add(eid)
        empty_arch = frozenset()
        self.entity_archetype[eid] = empty_arch
        if empty_arch not in self.archetypes:
            self.archetypes[empty_arch] = set()
            self._update_queries_for_new_archetype(empty_arch)
        self.archetypes[empty_arch].add(eid)
        return eid

    def _update_queries_for_new_archetype(self, new_arch):
        for query_key, matching_archs in self.query_cache.items():
            if set(query_key).issubset(new_arch):
                matching_archs.append(new_arch)

    def add_component(self, eid, component):
        ctype = type(component)
        if ctype not in self.components: self.components[ctype] = {}
        self.components[ctype][eid] = component
        old_arch = self.entity_archetype.get(eid, frozenset())
        if old_arch in self.archetypes:
            self.archetypes[old_arch].discard(eid)
        new_arch = old_arch | {ctype}
        self.entity_archetype[eid] = new_arch
        if new_arch not in self.archetypes:
            self.archetypes[new_arch] = set()
            self._update_queries_for_new_archetype(new_arch)
        self.archetypes[new_arch].add(eid)

    def get_component(self, eid, ctype):
        return self.components.get(ctype, {}).get(eid)

    def destroy_entity(self, eid):
        self.dead_entities.add(eid)

    def process_removals(self):
        for eid in self.dead_entities:
            if eid in self.entities:
                self.entities.remove(eid)
                if eid in self.entity_archetype:
                    arch = self.entity_archetype[eid]
                    if arch in self.archetypes:
                        self.archetypes[arch].discard(eid)
                    del self.entity_archetype[eid]
                for store in self.components.values():
                    if eid in store: del store[eid]
        self.dead_entities.clear()

    def view(self, *ctypes):
        if not ctypes: return
        key = tuple(sorted(ctypes, key=id))
        if key not in self.query_cache:
            matching_archs = []
            query_set = set(ctypes)
            for arch in self.archetypes:
                if query_set.issubset(arch):
                    matching_archs.append(arch)
            self.query_cache[key] = matching_archs
        for arch in self.query_cache[key]:
            for eid in self.archetypes[arch]:
                yield eid, [self.components[t][eid] for t in ctypes]

class System:
    def update(self, dt, registry, game): pass
