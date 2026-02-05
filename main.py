from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import Color, Rectangle, Ellipse, Line, Triangle
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.vector import Vector
import random
import math
import json
import os

# Game Constants
SAVE_FILE = "zombie_monkeys.json"

class Powerup:
    def __init__(self, x, y, type):
        self.x = x
        self.y = y
        self.type = type  # 'health', 'ammo', 'speed', 'damage'
        self.alive = True
        self.lifetime = 15.0
        
    def update(self, dt):
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.alive = False

class Bullet:
    def __init__(self, x, y, angle, damage=10):
        self.x = x
        self.y = y
        self.angle = angle
        self.speed = 500
        self.damage = damage
        self.alive = True
        
    def update(self, dt):
        self.x += math.cos(self.angle) * self.speed * dt
        self.y += math.sin(self.angle) * self.speed * dt
        
        if self.x < 0 or self.x > 800 or self.y < 0 or self.y > 600:
            self.alive = False

class Monkey:
    def __init__(self, spawn_x, spawn_y, wave_num, monkey_type='normal'):
        self.x = spawn_x
        self.y = spawn_y
        self.type = monkey_type
        
        # Different monkey types
        if monkey_type == 'fast':
            self.health = 20 + (wave_num * 5)
            self.speed = 100 + (wave_num * 8)
            self.damage = 3 + wave_num
            self.size = 15
            self.color = (0.8, 0.3, 0.3)
        elif monkey_type == 'tank':
            self.health = 60 + (wave_num * 20)
            self.speed = 30 + (wave_num * 2)
            self.damage = 10 + (wave_num * 2)
            self.size = 30
            self.color = (0.2, 0.6, 0.2)
        else:  # normal
            self.health = 30 + (wave_num * 10)
            self.speed = 50 + (wave_num * 5)
            self.damage = 5 + wave_num
            self.size = 20
            self.color = (0.3, 0.5, 0.2)
        
        self.max_health = self.health
        self.alive = True
        self.attack_cooldown = 0
        self.animation_frame = 0
        
    def move_towards_player(self, player_x, player_y, dt):
        dx = player_x - self.x
        dy = player_y - self.y
        dist = math.sqrt(dx*dx + dy*dy)
        
        if dist > 35:
            self.x += (dx / dist) * self.speed * dt
            self.y += (dy / dist) * self.speed * dt
        elif self.attack_cooldown <= 0:
            self.attack_cooldown = 1.0
            return True
        
        self.attack_cooldown -= dt
        self.animation_frame = (self.animation_frame + dt * 10) % 4
        return False
    
    def take_damage(self, damage):
        self.health -= damage
        if self.health <= 0:
            self.alive = False
            return True
        return False

class Player:
    def __init__(self):
        self.x = 400
        self.y = 300
        self.health = 100
        self.max_health = 100
        self.speed = 180
        self.angle = 0
        self.points = 0
        self.kills = 0
        self.ammo = 30
        self.max_ammo = 30
        self.reload_time = 0
        self.fire_cooldown = 0
        self.damage = 10
        self.speed_boost = 1.0
        self.speed_boost_time = 0
        self.damage_boost = 1.0
        self.damage_boost_time = 0
        
    def shoot(self):
        if self.ammo > 0 and self.fire_cooldown <= 0:
            self.ammo -= 1
            self.fire_cooldown = 0.15
            return Bullet(self.x, self.y, self.angle, self.damage * self.damage_boost)
        return None
    
    def reload(self):
        if self.reload_time <= 0 and self.ammo < self.max_ammo:
            self.reload_time = 2.0
    
    def pickup_powerup(self, powerup):
        if powerup.type == 'health':
            self.health = min(self.max_health, self.health + 30)
        elif powerup.type == 'ammo':
            self.ammo = self.max_ammo
        elif powerup.type == 'speed':
            self.speed_boost = 1.5
            self.speed_boost_time = 10.0
        elif powerup.type == 'damage':
            self.damage_boost = 2.0
            self.damage_boost_time = 10.0
    
    def update(self, dt):
        if self.reload_time > 0:
            self.reload_time -= dt
            if self.reload_time <= 0:
                self.ammo = self.max_ammo
        
        if self.fire_cooldown > 0:
            self.fire_cooldown -= dt
        
        if self.speed_boost_time > 0:
            self.speed_boost_time -= dt
            if self.speed_boost_time <= 0:
                self.speed_boost = 1.0
        
        if self.damage_boost_time > 0:
            self.damage_boost_time -= dt
            if self.damage_boost_time <= 0:
                self.damage_boost = 1.0

class GameWidget(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.player = Player()
        self.monkeys = []
        self.bullets = []
        self.powerups = []
        self.wave = 1
        self.wave_active = False
        self.monkeys_to_spawn = 0
        self.spawn_timer = 0
        self.game_over = False
        self.paused = False
        self.powerup_spawn_timer = 0
        
        self.touch_start = None
        self.is_shooting = False
        
        # Enhanced map with more strategic elements
        self.obstacles = [
            # Central bunker
            {'x': 400, 'y': 300, 'w': 120, 'h': 120, 'type': 'bunker'},
            
            # Corner fortifications
            {'x': 150, 'y': 150, 'w': 100, 'h': 100, 'type': 'fort'},
            {'x': 650, 'y': 150, 'w': 100, 'h': 100, 'type': 'fort'},
            {'x': 150, 'y': 450, 'w': 100, 'h': 100, 'type': 'fort'},
            {'x': 650, 'y': 450, 'w': 100, 'h': 100, 'type': 'fort'},
            
            # Scattered crates
            {'x': 300, 'y': 200, 'w': 60, 'h': 60, 'type': 'crate'},
            {'x': 500, 'y': 200, 'w': 60, 'h': 60, 'type': 'crate'},
            {'x': 300, 'y': 400, 'w': 60, 'h': 60, 'type': 'crate'},
            {'x': 500, 'y': 400, 'w': 60, 'h': 60, 'type': 'crate'},
            
            # Walls for cover
            {'x': 400, 'y': 100, 'w': 150, 'h': 30, 'type': 'wall'},
            {'x': 400, 'y': 500, 'w': 150, 'h': 30, 'type': 'wall'},
            {'x': 100, 'y': 300, 'w': 30, 'h': 150, 'type': 'wall'},
            {'x': 700, 'y': 300, 'w': 30, 'h': 150, 'type': 'wall'},
        ]
        
        with self.canvas:
            self.draw_background()
        
        Clock.schedule_interval(self.update, 1/60)
        
    def draw_background(self):
        # Dark military ground
        Color(0.12, 0.15, 0.12)
        Rectangle(pos=(0, 0), size=(800, 600))
        
        # Grid pattern
        Color(0.18, 0.22, 0.18, 0.4)
        for i in range(0, 800, 40):
            Line(points=[i, 0, i, 600], width=1)
        for i in range(0, 600, 40):
            Line(points=[0, i, 800, i], width=1)
        
        # Dirt patches for atmosphere
        Color(0.15, 0.12, 0.1, 0.5)
        for _ in range(20):
            x = random.randint(0, 800)
            y = random.randint(0, 600)
            Ellipse(pos=(x, y), size=(random.randint(30, 60), random.randint(20, 40)))
    
    def start_wave(self):
        self.wave_active = True
        self.monkeys_to_spawn = 5 + (self.wave * 4)
        
        # Add special monkeys in later waves
        if self.wave >= 3:
            self.monkeys_to_spawn += 2  # Add fast monkeys
        if self.wave >= 5:
            self.monkeys_to_spawn += 1  # Add tank monkeys
        
        self.spawn_timer = 0
    
    def spawn_monkey(self):
        side = random.randint(0, 3)
        if side == 0:
            x, y = random.randint(0, 800), 600
        elif side == 1:
            x, y = random.randint(0, 800), 0
        elif side == 2:
            x, y = 0, random.randint(0, 600)
        else:
            x, y = 800, random.randint(0, 600)
        
        # Spawn special monkeys based on wave
        monkey_type = 'normal'
        if self.wave >= 5 and random.random() < 0.15:
            monkey_type = 'tank'
        elif self.wave >= 3 and random.random() < 0.25:
            monkey_type = 'fast'
        
        self.monkeys.append(Monkey(x, y, self.wave, monkey_type))
        self.monkeys_to_spawn -= 1
    
    def spawn_powerup(self):
        x = random.randint(100, 700)
        y = random.randint(100, 500)
        powerup_type = random.choice(['health', 'ammo', 'speed', 'damage'])
        self.powerups.append(Powerup(x, y, powerup_type))
    
    def update(self, dt):
        if self.game_over or self.paused:
            return
        
        self.player.update(dt)
        
        # Powerup spawning
        self.powerup_spawn_timer += dt
        if self.powerup_spawn_timer > 15.0 and len(self.powerups) < 3:
            self.spawn_powerup()
            self.powerup_spawn_timer = 0
        
        # Update powerups
        for powerup in self.powerups[:]:
            powerup.update(dt)
            if not powerup.alive:
                self.powerups.remove(powerup)
            else:
                # Check pickup
                dist = math.sqrt((powerup.x - self.player.x)**2 + (powerup.y - self.player.y)**2)
                if dist < 25:
                    self.player.pickup_powerup(powerup)
                    self.powerups.remove(powerup)
        
        # Wave spawning
        if self.wave_active and self.monkeys_to_spawn > 0:
            self.spawn_timer += dt
            spawn_rate = max(0.5, 1.5 - (self.wave * 0.1))
            if self.spawn_timer > spawn_rate:
                self.spawn_monkey()
                self.spawn_timer = 0
        
        # Check wave complete
        if self.wave_active and self.monkeys_to_spawn == 0 and len(self.monkeys) == 0:
            self.wave_active = False
            self.wave += 1
            self.player.points += 200 * self.wave
            self.player.health = min(self.player.max_health, self.player.health + 20)
        
        # Update monkeys
        for monkey in self.monkeys[:]:
            if monkey.move_towards_player(self.player.x, self.player.y, dt):
                self.player.health -= monkey.damage
                if self.player.health <= 0:
                    self.game_over = True
        
        # Update bullets
        for bullet in self.bullets[:]:
            bullet.update(dt)
            if not bullet.alive:
                self.bullets.remove(bullet)
                continue
            
            for monkey in self.monkeys[:]:
                dist = math.sqrt((bullet.x - monkey.x)**2 + (bullet.y - monkey.y)**2)
                if dist < monkey.size:
                    if monkey.take_damage(bullet.damage):
                        points = 10 if monkey.type == 'normal' else 20 if monkey.type == 'fast' else 30
                        self.player.points += points * self.wave
                        self.player.kills += 1
                        self.monkeys.remove(monkey)
                    bullet.alive = False
                    break
        
        self.canvas.clear()
        self.draw_game()
    
    def draw_game(self):
        with self.canvas:
            self.draw_background()
            
            # Draw obstacles
            for obs in self.obstacles:
                if obs['type'] == 'bunker':
                    Color(0.25, 0.25, 0.3)
                    Rectangle(pos=(obs['x']-obs['w']//2, obs['y']-obs['h']//2), 
                             size=(obs['w'], obs['h']))
                    Color(0.4, 0.4, 0.45)
                    Line(rectangle=(obs['x']-obs['w']//2, obs['y']-obs['h']//2, 
                                   obs['w'], obs['h']), width=3)
                elif obs['type'] == 'fort':
                    Color(0.3, 0.25, 0.2)
                    Rectangle(pos=(obs['x']-obs['w']//2, obs['y']-obs['h']//2), 
                             size=(obs['w'], obs['h']))
                    Color(0.2, 0.15, 0.1)
                    Line(rectangle=(obs['x']-obs['w']//2, obs['y']-obs['h']//2, 
                                   obs['w'], obs['h']), width=2)
                elif obs['type'] == 'crate':
                    Color(0.4, 0.3, 0.2)
                    Rectangle(pos=(obs['x']-obs['w']//2, obs['y']-obs['h']//2), 
                             size=(obs['w'], obs['h']))
                    Color(0.3, 0.2, 0.1)
                    Line(rectangle=(obs['x']-obs['w']//2, obs['y']-obs['h']//2, 
                                   obs['w'], obs['h']), width=2)
                else:  # wall
                    Color(0.3, 0.3, 0.35)
                    Rectangle(pos=(obs['x']-obs['w']//2, obs['y']-obs['h']//2), 
                             size=(obs['w'], obs['h']))
            
            # Draw powerups
            for powerup in self.powerups:
                # Pulsing effect
                pulse = 1 + math.sin(Clock.get_time() * 5) * 0.2
                size = 20 * pulse
                
                if powerup.type == 'health':
                    Color(0, 1, 0, 0.8)
                elif powerup.type == 'ammo':
                    Color(1, 1, 0, 0.8)
                elif powerup.type == 'speed':
                    Color(0, 0.5, 1, 0.8)
                elif powerup.type == 'damage':
                    Color(1, 0.3, 0, 0.8)
                
                Ellipse(pos=(powerup.x-size//2, powerup.y-size//2), 
                       size=(size, size))
                
                # Symbol
                Color(1, 1, 1)
                if powerup.type == 'health':
                    Line(points=[powerup.x-8, powerup.y, powerup.x+8, powerup.y], width=3)
                    Line(points=[powerup.x, powerup.y-8, powerup.x, powerup.y+8], width=3)
                elif powerup.type == 'ammo':
                    Rectangle(pos=(powerup.x-5, powerup.y-8), size=(10, 16))
            
            # Draw bullets
            Color(1, 1, 0)
            for bullet in self.bullets:
                Ellipse(pos=(bullet.x-4, bullet.y-4), size=(8, 8))
            
            # Draw monkeys
            for monkey in self.monkeys:
                Color(*monkey.color)
                Ellipse(pos=(monkey.x-monkey.size, monkey.y-monkey.size), 
                       size=(monkey.size*2, monkey.size*2))
                
                # Eyes
                Color(1, 0, 0)
                eye_offset = monkey.size * 0.4
                Ellipse(pos=(monkey.x-eye_offset-3, monkey.y+5), size=(6, 6))
                Ellipse(pos=(monkey.x+eye_offset-3, monkey.y+5), size=(6, 6))
                
                # Type indicator
                if monkey.type == 'tank':
                    Color(0.8, 0.8, 0)
                    Line(circle=(monkey.x, monkey.y, monkey.size+3), width=2)
                elif monkey.type == 'fast':
                    Color(1, 0.5, 0)
                    for i in range(3):
                        Line(points=[monkey.x-monkey.size-i*3, monkey.y, 
                                    monkey.x-monkey.size-10-i*3, monkey.y], width=2)
                
                # Health bar
                bar_width = monkey.size * 2
                Color(0.8, 0, 0)
                Rectangle(pos=(monkey.x-bar_width//2, monkey.y+monkey.size+5), 
                         size=(bar_width, 4))
                Color(0, 0.8, 0)
                Rectangle(pos=(monkey.x-bar_width//2, monkey.y+monkey.size+5), 
                         size=(bar_width * (monkey.health/monkey.max_health), 4))
            
            # Draw player
            if self.player.speed_boost > 1.0:
                Color(0, 0.8, 1, 0.5)
                Ellipse(pos=(self.player.x-20, self.player.y-20), size=(40, 40))
            
            if self.player.damage_boost > 1.0:
                Color(1, 0.3, 0, 0.5)
                Ellipse(pos=(self.player.x-20, self.player.y-20), size=(40, 40))
            
            Color(0.2, 0.4, 0.9)
            Ellipse(pos=(self.player.x-15, self.player.y-15), size=(30, 30))
            
            # Gun
            Color(0.5, 0.5, 0.5)
            gun_end_x = self.player.x + math.cos(self.player.angle) * 25
            gun_end_y = self.player.y + math.sin(self.player.angle) * 25
            Line(points=[self.player.x, self.player.y, gun_end_x, gun_end_y], width=4)
    
    def on_touch_down(self, touch):
        if self.game_over:
            return
        self.touch_start = touch.pos
        self.is_shooting = True
        return True
    
    def on_touch_move(self, touch):
        if not self.touch_start:
            return
        
        dx = touch.x - self.player.x
        dy = touch.y - self.player.y
        self.player.angle = math.atan2(dy, dx)
        
        if self.touch_start:
            move_dx = touch.x - self.touch_start[0]
            move_dy = touch.y - self.touch_start[1]
            dist = math.sqrt(move_dx**2 + move_dy**2)
            
            if dist > 20:
                self.player.x += (move_dx / dist) * self.player.speed * self.player.speed_boost * (1/60)
                self.player.y += (move_dy / dist) * self.player.speed * self.player.speed_boost * (1/60)
                
                self.player.x = max(20, min(780, self.player.x))
                self.player.y = max(20, min(580, self.player.y))
    
    def on_touch_up(self, touch):
        self.touch_start = None
        self.is_shooting = False

class ZombieMonkeysApp(App):
    def build(self):
        Window.size = (800, 600)
        Window.clearcolor = (0.08, 0.08, 0.08, 1)
        
        self.layout = FloatLayout()
        self.game = GameWidget(size=(800, 600))
        self.layout.add_widget(self.game)
        
        # HUD
        self.wave_label = Label(
            text='[b]WAVE 1[/b]',
            markup=True,
            pos_hint={'x': 0.37, 'y': 0.92},
            size_hint=(0.26, 0.06),
            font_size='22sp',
            color=(1, 0.2, 0.2, 1)
        )
        self.layout.add_widget(self.wave_label)
        
        self.health_label = Label(
            text='HP: 100/100',
            pos_hint={'x': 0.02, 'y': 0.94},
            size_hint=(0.18, 0.05),
            font_size='16sp',
            color=(0, 1, 0, 1)
        )
        self.layout.add_widget(self.health_label)
        
        self.ammo_label = Label(
            text='AMMO: 30/30',
            pos_hint={'x': 0.8, 'y': 0.94},
            size_hint=(0.18, 0.05),
            font_size='16sp',
            color=(1, 1, 0, 1)
        )
        self.layout.add_widget(self.ammo_label)
        
        self.points_label = Label(
            text='POINTS: 0',
            pos_hint={'x': 0.02, 'y': 0.02},
            size_hint=(0.2, 0.05),
            font_size='16sp',
            color=(1, 1, 1, 1)
        )
        self.layout.add_widget(self.points_label)
        
        self.kills_label = Label(
            text='KILLS: 0',
            pos_hint={'x': 0.25, 'y': 0.02},
            size_hint=(0.15, 0.05),
            font_size='16sp',
            color=(1, 0.5, 0, 1)
        )
        self.layout.add_widget(self.kills_label)
        
        self.monkeys_label = Label(
            text='MONKEYS: 0',
            pos_hint={'x': 0.75, 'y': 0.02},
            size_hint=(0.23, 0.05),
            font_size='16sp',
            color=(1, 0.3, 0.3, 1)
        )
        self.layout.add_widget(self.monkeys_label)
        
        # Buttons
        self.start_btn = Button(
            text='[b]START WAVE[/b]',
            markup=True,
            pos_hint={'x': 0.38, 'y': 0.45},
            size_hint=(0.24, 0.1),
            background_color=(0.8, 0, 0, 1),
            font_size='20sp'
        )
        self.start_btn.bind(on_press=self.start_wave)
        self.layout.add_widget(self.start_btn)
        
        reload_btn = Button(
            text='[b]R[/b]',
            markup=True,
            pos_hint={'x': 0.02, 'y': 0.1},
            size_hint=(0.08, 0.08),
            background_color=(0.3, 0.3, 0.8, 1),
            font_size='18sp'
        )
        reload_btn.bind(on_press=lambda x: self.game.player.reload())
        self.layout.add_widget(reload_btn)
        
        self.shoot_btn = Button(
            text='[b]FIRE[/b]',
            markup=True,
            pos_hint={'x': 0.88, 'y': 0.15},
            size_hint=(0.1, 0.2),
            background_color=(0.9, 0.1, 0.1, 1),
            font_size='20sp'
        )
        self.shoot_btn.bind(on_press=self.shoot)
        self.layout.add_widget(self.shoot_btn)
        
        self.game_over_label = Label(
            text='',
            pos_hint={'x': 0.2, 'y': 0.35},
            size_hint=(0.6, 0.3),
            font_size='28sp',
            color=(1, 0, 0, 1),
            markup=True
        )
        self.layout.add_widget(self.game_over_label)
        
        Clock.schedule_interval(self.update_hud, 1/30)
        Window.bind(on_key_down=self.on_keyboard_down)
        
        return self.layout
    
    def shoot(self, *args):
        bullet = self.game.player.shoot()
        if bullet:
            self.game.bullets.append(bullet)
    
    def on_keyboard_down(self, window, key, scancode, codepoint, modifier):
        if key == 32:
            self.shoot()
        elif key == 114:
            self.game.player.reload()
        elif key == 119:
            self.game.player.y = min(580, self.game.player.y + 15)
        elif key == 115:
            self.game.player.y = max(20, self.game.player.y - 15)
        elif key == 97:
            self.game.player.x = max(20, self.game.player.x - 15)
        elif key == 100:
            self.game.player.x = min(780, self.game.player.x + 15)
    
    def start_wave(self, *args):
        if not self.game.wave_active:
            self.game.start_wave()
            self.start_btn.opacity = 0
            self.start_btn.disabled = True
    
    def update_hud(self, dt):
        self.wave_label.text = f'[b]WAVE {self.game.wave}[/b]'
        self.health_label.text = f'HP: {int(self.game.player.health)}/{self.game.player.max_health}'
        
        health_pct = self.game.player.health / self.game.player.max_health
        if health_pct > 0.5:
            self.health_label.color = (0, 1, 0, 1)
        elif health_pct > 0.25:
            self.health_label.color = (1, 1, 0, 1)
        else:
            self.health_label.color = (1, 0, 0, 1)
        
        self.ammo_label.text = f'AMMO: {self.game.player.ammo}/{self.game.player.max_ammo}'
        self.points_label.text = f'POINTS: {self.game.player.points}'
        self.kills_label.text = f'KILLS: {self.game.player.kills}'
        self.monkeys_label.text = f'MONKEYS: {len(self.game.monkeys)}'
        
        if self.game.player.reload_time > 0:
            self.ammo_label.text = f'RELOADING... {self.game.player.reload_time:.1f}s'
            self.ammo_label.color = (1, 0.5, 0, 1)
        else:
            self.ammo_label.color = (1, 1, 0, 1)
        
        if not self.game.wave_active and not self.game.game_over and len(self.game.monkeys) == 0:
            self.start_btn.opacity = 1
            self.start_btn.disabled = False
        
        if self.game.game_over:
            self.game_over_label.text = (f'[b][color=ff0000]GAME OVER![/color][/b]\n\n'
                                        f'Wave: {self.game.wave}\n'
                                        f'Kills: {self.game.player.kills}\n'
                                        f'Points: {self.game.player.points}')

if __name__ == '__main__':
    ZombieMonkeysApp().run()
