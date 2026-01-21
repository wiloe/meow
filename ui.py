import pyray as rl

class ChatSystem:
    def __init__(self, game):
        self.game = game
        self.messages = []
        self.input_buffer = ""
        self.is_active = False
        self.max_messages = 100
        self.width = 400
        self.height = 250
        self.scroll_offset = 0
        self.options = []

    def log(self, text, color=rl.WHITE):
        self.messages.append({'text': text, 'color': color})
        if len(self.messages) > self.max_messages:
            self.messages.pop(0)
        self.scroll_offset = 0

    def show_options(self, prompt, options):
        self.log(prompt, rl.YELLOW)
        self.options = options
        self.is_active = True

    def update(self):
        if rl.is_key_pressed(rl.KEY_ENTER) or rl.is_key_pressed(rl.KEY_SLASH):
            self.is_active = not self.is_active
            if self.is_active and rl.is_key_pressed(rl.KEY_SLASH):
                self.input_buffer = "/"
            elif not self.is_active:
                if self.input_buffer: self._process_input()
                self.options = []

        if self.is_active:
            key = rl.get_char_pressed()
            while key > 0:
                if 32 <= key <= 125: self.input_buffer += chr(key)
                key = rl.get_char_pressed()
            if rl.is_key_pressed(rl.KEY_BACKSPACE) and len(self.input_buffer) > 0:
                self.input_buffer = self.input_buffer[:-1]
            
            wheel = rl.get_mouse_wheel_move()
            if wheel != 0:
                self.scroll_offset -= int(wheel)
                self.scroll_offset = max(0, min(self.scroll_offset, max(0, len(self.messages) - 10)))

            if self.options:
                sw, sh = rl.get_screen_width(), rl.get_screen_height()
                base_x, base_y = sw - self.width - 10, sh - self.height - 10
                opt_h = 30
                opt_start_y = base_y - (len(self.options) * opt_h) - 10
                mp = rl.get_mouse_position()
                
                if rl.is_mouse_button_pressed(rl.MOUSE_LEFT_BUTTON):
                    for i, opt in enumerate(self.options):
                        rect = rl.Rectangle(base_x, opt_start_y + i * opt_h, self.width, opt_h - 5)
                        if rl.check_collision_point_rec(mp, rect):
                            # Call the method on the game instance
                            if hasattr(self.game, opt['callback']):
                                getattr(self.game, opt['callback'])(*opt.get('args', ()))
                            self.options = []
                            self.is_active = False
                            break

    def _process_input(self):
        msg = self.input_buffer.strip(); self.input_buffer = ""
        if not msg: return
        self.log(f"> {msg}", rl.GRAY)
        if msg.startswith('/'): self._handle_command(msg[1:])

    def _handle_command(self, cmd_str):
        parts = cmd_str.split(); cmd = parts[0].lower(); args = parts[1:]
        if cmd == 'help': self.log("Cmds: /tp x y, /give item [n], /heal, /time 0-1, /debug", rl.GREEN)
        elif cmd == 'tp' and len(args) == 2:
            try:
                x, y = int(args[0]), int(args[1])
                self.game.player['x'], self.game.player['y'] = float(x), float(y)
                self.game.player['grid_x'], self.game.player['grid_y'] = x, y
                self.log(f"Teleported to {x}, {y}", rl.GREEN)
            except: self.log("Usage: /tp x y", rl.RED)
        elif cmd == 'give' and len(args) >= 1:
            item, count = args[0], int(args[1]) if len(args) > 1 else 1
            if self.game.add_inventory_item(item, count): self.log(f"Gave {count} {item}", rl.GREEN)
            else: self.log("Inventory full", rl.RED)
        elif cmd == 'heal':
            self.game.player['stats']['hp'] = self.game.player['stats']['max_hp']
            self.game.player['stats']['mana'] = self.game.player['stats']['max_mana']
            self.log("Healed!", rl.GREEN)
        elif cmd == 'time' and len(args) == 1:
            try: self.game.day_time = float(args[0]); self.log(f"Time set to {args[0]}", rl.GREEN)
            except: self.log("Usage: /time 0.0-1.0", rl.RED)
        elif cmd == 'debug': self.log(f"FPS: {rl.get_fps()} Ents: {len(self.game.ecs.entities)}", rl.GREEN)
        else: self.log("Unknown command.", rl.RED)

    def draw(self):
        sw, sh = rl.get_screen_width(), rl.get_screen_height()
        x, y = sw - self.width - 10, sh - self.height - 10
        rl.draw_rectangle(x, y, self.width, self.height, rl.fade(rl.BLACK, 0.95))
        rl.draw_rectangle_lines(x, y, self.width, self.height, rl.GRAY)
        
        msgs = self.messages[::-1][self.scroll_offset:]
        draw_y = y + self.height - 35
        for msg in msgs:
            if draw_y < y + 10: break
            rl.draw_text(msg['text'], x + 10, draw_y, 10, msg['color'])
            draw_y -= 20
            
        if self.is_active:
            rl.draw_rectangle(x, y + self.height - 25, self.width, 25, rl.fade(rl.WHITE, 0.1))
            rl.draw_rectangle_lines(x, y + self.height - 25, self.width, 25, rl.WHITE)
            rl.draw_text(self.input_buffer + "_", x + 5, y + self.height - 20, 10, rl.WHITE)
            
            if self.options:
                opt_h = 30
                opt_start_y = y - (len(self.options) * opt_h) - 10
                for i, opt in enumerate(self.options):
                    rect = rl.Rectangle(x, opt_start_y + i * opt_h, self.width, opt_h - 5)
                    hover = rl.check_collision_point_rec(rl.get_mouse_position(), rect)
                    rl.draw_rectangle_rec(rect, rl.fade(rl.BLUE, 0.6) if hover else rl.fade(rl.BLACK, 0.8))
                    rl.draw_rectangle_lines_ex(rect, 1, rl.WHITE)
                    rl.draw_circle(int(rect.x + 15), int(rect.y + 12), 5, rl.YELLOW)
                    rl.draw_text(opt['text'], int(rect.x + 30), int(rect.y + 8), 10, rl.WHITE)