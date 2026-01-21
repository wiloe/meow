import pyray as rl
import math
import random
from ecs import System, Transform, Velocity, ParticleComp, ParticleEmitter, Lifetime, AIComponent, Animation, Sprite, Health, ProjectileComp, ScreenSpace
from utils import a_star_search, check_circle_collision, screen_to_iso
from config import TILE_WIDTH, TILE_HEIGHT

class PhysicsSystem(System):
    def update(self, dt, registry, game):
        for eid, (pos, vel) in registry.view(Transform, Velocity):
            pos.x += vel.vx * dt
            pos.y += vel.vy * dt

class ParticleUpdateSystem(System):
    def update(self, dt, registry, game):
        for eid, (vel, part) in registry.view(Velocity, ParticleComp):
            vel.vy += part.gravity * dt
            if part.drag > 0:
                vel.vx *= (1.0 - part.drag * dt)
                vel.vy *= (1.0 - part.drag * dt)

class ParticleEmitterSystem(System):
    def update(self, dt, registry, game):
        for eid, (pos, emit) in registry.view(Transform, ParticleEmitter):
            if not emit.active: continue
            if emit.burst_count > 0:
                for _ in range(emit.burst_count):
                    self._spawn_particle(registry, pos, emit)
                registry.destroy_entity(eid)
                continue
            emit.timer += dt
            if emit.rate > 0:
                interval = 1.0 / emit.rate
                while emit.timer >= interval:
                    emit.timer -= interval
                    self._spawn_particle(registry, pos, emit)

    def _spawn_particle(self, registry, pos, emit):
        p_eid = registry.create_entity()
        registry.add_component(p_eid, Transform(pos.x, pos.y, pos.map_name))
        vx = random.uniform(-emit.speed_range, emit.speed_range)
        vy = random.uniform(-emit.speed_range, emit.speed_range)
        registry.add_component(p_eid, Velocity(vx, vy))
        registry.add_component(p_eid, ParticleComp(emit.color, emit.size, emit.gravity, emit.drag))
        registry.add_component(p_eid, Lifetime(random.uniform(*emit.life_range)))

class LifetimeSystem(System):
    def update(self, dt, registry, game):
        for eid, (life,) in registry.view(Lifetime):
            life.amount -= dt
            if life.amount <= 0:
                registry.destroy_entity(eid)

class MobSystem(System):
    def update(self, dt, registry, game):
        player_pos = (game.player['x'], game.player['y'])
        for eid, (pos, vel, ai) in registry.view(Transform, Velocity, AIComponent):
            if pos.map_name != game.player['map']: continue
            dist = math.hypot(player_pos[0] - pos.x, player_pos[1] - pos.y)
            vel.vx, vel.vy = 0, 0
            if ai.behavior == 'hostile':
                if dist < ai.detect_range:
                    ai.path_timer -= dt
                    if ai.path_timer <= 0:
                        ai.path_timer = random.uniform(0.5, 1.0)
                        start = (int(pos.x + 0.5), int(pos.y + 0.5))
                        goal = (int(player_pos[0] + 0.5), int(player_pos[1] + 0.5))
                        ai.path = a_star_search(start, goal, lambda p: game._get_neighbors(p, pos.map_name))
                        if ai.path: ai.path.pop(0)
                    if ai.path:
                        next_node = ai.path[0]
                        dx, dy = next_node[0] - pos.x, next_node[1] - pos.y
                        d = math.hypot(dx, dy)
                        if d < 0.1: ai.path.pop(0)
                        else:
                            vel.vx = (dx / d) * ai.speed
                            vel.vy = (dy / d) * ai.speed

class AnimationSystem(System):
    def update(self, dt, registry, game):
        for eid, (anim, sprite, vel) in registry.view(Animation, Sprite, Velocity):
            is_moving = abs(vel.vx) > 0.1 or abs(vel.vy) > 0.1
            if is_moving:
                anim.timer += dt
                if anim.timer >= anim.frame_duration:
                    anim.timer = 0
                    anim.current_frame = (anim.current_frame + 1) % len(anim.frames)
            else:
                anim.current_frame = 0
                anim.timer = 0
            if anim.frames:
                sprite.source_rect = anim.frames[anim.current_frame]

class RenderSystem(System):
    def update(self, dt, registry, game):
        for eid, (pos, part, life) in registry.view(Transform, ParticleComp, Lifetime):
            if pos.map_name != game.player['map']: continue
            rl.draw_circle(int(pos.x), int(pos.y), part.size / 2, rl.fade(part.color, min(1.0, life.amount)))

class ProjectileSystem(System):
    def update(self, dt, registry, game):
        for eid, (pos, proj) in registry.view(Transform, ProjectileComp):
            gx, gy = screen_to_iso(pos.x, pos.y, TILE_WIDTH, TILE_HEIGHT)
            igx, igy = int(gx + 0.5), int(gy + 0.5)
            hit_wall = False
            if pos.map_name in game.maps:
                current_map = game.maps[pos.map_name]
                if not (0 <= igx < len(current_map) and 0 <= igy < len(current_map)): hit_wall = True
                elif not game.block_definitions[current_map[igy, igx]]['walkable']: hit_wall = True
                else:
                    for obj in game.objects.get(pos.map_name, []):
                        if obj.get('type') in ['tree', 'pine_tree', 'rock', 'wall'] and int(obj['x']) == igx and int(obj['y']) == igy:
                            hit_wall = True; break
            if hit_wall:
                registry.destroy_entity(eid)
                game._create_particles(pos.x, pos.y, 10, rl.GRAY, life_range=(0.3, 0.6))
                continue
            hit_ecs = False
            for t_eid, (t_pos, t_health) in registry.view(Transform, Health):
                if t_eid == eid: continue
                if t_pos.map_name != pos.map_name: continue
                if registry.get_component(t_eid, ScreenSpace): tx, ty = t_pos.x, t_pos.y
                else: 
                    tx, ty = game.to_screen(t_pos.x, t_pos.y)
                    ty -= 30
                if check_circle_collision(pos.x, pos.y, 10, tx, ty, 20):
                    t_health.current -= proj.damage
                    game._spawn_particles(tx, ty, 5, rl.ORANGE)
                    hit_ecs = True
                    break
            if hit_ecs:
                registry.destroy_entity(eid)
                continue
            if pos.map_name in game.npcs:
                for npc in game.npcs[pos.map_name]:
                    nsx, nsy = game.to_screen(npc['x'], npc['y'])
                    if check_circle_collision(pos.x, pos.y, 10, nsx, nsy - 30, 20):
                        npc['hp'] -= proj.damage
                        registry.destroy_entity(eid)
                        if proj.effect_type == 'slow': npc['status'] = {'type': 'slow', 'duration': 3.0}
                        elif proj.effect_type == 'poison': npc['status'] = {'type': 'poison', 'duration': 5.0, 'tick': 0}
                        color = rl.SKYBLUE if proj.effect_type == 'slow' else (rl.LIME if proj.effect_type == 'poison' else rl.ORANGE)
                        game._spawn_particles(npc['x'], npc['y'], 10, color)
                        if npc['hp'] <= 0: game.npcs[pos.map_name].remove(npc); game.gain_xp(50)
                        break
