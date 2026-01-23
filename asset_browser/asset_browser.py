import pyray as rl
import os
import ctypes

# --- POLYFILLS (Copied from utils/config for standalone safety) ---
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
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
ASSET_DIR = os.path.join(os.path.dirname(__file__), "../assets/img")

class AssetBrowser:
    def __init__(self):
        rl.init_window(SCREEN_WIDTH, SCREEN_HEIGHT, "Meow Asset Browser")
        rl.set_target_fps(60)
        rl.set_window_state(rl.FLAG_WINDOW_RESIZABLE)

        self.image_files = self.find_images(ASSET_DIR)
        self.current_index = 0
        self.current_texture = None
        self.texture_valid = False
        
        # Camera for zoom/pan
        self.camera = rl.Camera2D(rl.Vector2(SCREEN_WIDTH/2, SCREEN_HEIGHT/2), rl.Vector2(0, 0), 0.0, 1.0)
        self.drag_start = rl.Vector2(0, 0)
        self.dragging = False

        if self.image_files:
            self.load_image(0)
        else:
            print(f"No images found in {ASSET_DIR}")

    def find_images(self, root_dir):
        images = []
        valid_exts = ('.png', '.jpg', '.jpeg', '.bmp', '.tga')
        print(f"Scanning {root_dir}...")
        for root, dirs, files in os.walk(root_dir):
            for file in files:
                if file.lower().endswith(valid_exts):
                    images.append(os.path.join(root, file))
        print(f"Found {len(images)} images.")
        return sorted(images)

    def load_image(self, index):
        if not self.image_files:
            return

        if self.texture_valid:
            rl.unload_texture(self.current_texture)
            self.texture_valid = False

        filepath = self.image_files[index]
        try:
            # We load as image first to check validity if needed, but LoadTexture is fine
            self.current_texture = rl.load_texture(filepath.encode('utf-8'))
            
            # Simple check if texture loaded (id > 0)
            # Pyray structure might obscure id, but typically width > 0 means success
            if self.current_texture.width > 0:
                self.texture_valid = True
                # Reset camera
                self.camera.zoom = 1.0
                self.camera.target = rl.Vector2(self.current_texture.width/2, self.current_texture.height/2)
                self.camera.offset = rl.Vector2(rl.get_screen_width()/2, rl.get_screen_height()/2)
            else:
                print(f"Failed to load texture: {filepath}")
                
        except Exception as e:
            print(f"Error loading {filepath}: {e}")

    def update(self):
        # Navigation
        if rl.is_key_pressed(rl.KEY_RIGHT):
            self.current_index = (self.current_index + 1) % len(self.image_files)
            self.load_image(self.current_index)
        elif rl.is_key_pressed(rl.KEY_LEFT):
            self.current_index = (self.current_index - 1 + len(self.image_files)) % len(self.image_files)
            self.load_image(self.current_index)

        # Zoom
        wheel = rl.get_mouse_wheel_move()
        if wheel != 0:
            zoom_speed = 0.1
            mouse_world_pos = rl.get_screen_to_world_2d(rl.get_mouse_position(), self.camera)
            
            self.camera.offset = rl.get_mouse_position()
            self.camera.target = mouse_world_pos
            
            self.camera.zoom += wheel * zoom_speed
            if self.camera.zoom < 0.1: self.camera.zoom = 0.1
            if self.camera.zoom > 10.0: self.camera.zoom = 10.0

        # Pan
        if rl.is_mouse_button_pressed(rl.MOUSE_BUTTON_LEFT):
            self.dragging = True
            self.drag_start = rl.get_mouse_position()
        
        if rl.is_mouse_button_released(rl.MOUSE_BUTTON_LEFT):
            self.dragging = False

        if self.dragging:
            mouse_pos = rl.get_mouse_position()
            delta = rl.Vector2(self.drag_start.x - mouse_pos.x, self.drag_start.y - mouse_pos.y)
            # Adjust target based on zoom (screen space delta -> world space delta)
            self.camera.target.x += delta.x / self.camera.zoom
            self.camera.target.y += delta.y / self.camera.zoom
            self.drag_start = mouse_pos
            
        # Reset View
        if rl.is_key_pressed(rl.KEY_SPACE):
             if self.texture_valid:
                self.camera.zoom = 1.0
                self.camera.target = rl.Vector2(self.current_texture.width/2, self.current_texture.height/2)
                self.camera.offset = rl.Vector2(rl.get_screen_width()/2, rl.get_screen_height()/2)

    def draw(self):
        rl.begin_drawing()
        rl.clear_background(rl.Color(30, 30, 30, 255))

        # Draw Grid background for transparency
        # (Simplified grid)
        
        rl.begin_mode_2d(self.camera)
        if self.texture_valid:
            # Draw a checkerboard behind the image area
            rl.draw_rectangle(0, 0, self.current_texture.width, self.current_texture.height, rl.Color(50, 50, 50, 255))
            rl.draw_texture(self.current_texture, 0, 0, rl.WHITE)
            # Border
            rl.draw_rectangle_lines(0, 0, self.current_texture.width, self.current_texture.height, rl.GREEN)
        rl.end_mode_2d()

        # UI Overlay
        rl.draw_rectangle(0, 0, rl.get_screen_width(), 40, rl.Color(0, 0, 0, 200))
        if self.image_files:
            file_path = self.image_files[self.current_index]
            # Show relative path if possible
            try:
                display_path = os.path.relpath(file_path, os.path.dirname(ASSET_DIR))
            except:
                display_path = file_path
                
            info_text = f"[{self.current_index + 1}/{len(self.image_files)}] {display_path}"
            if self.texture_valid:
                info_text += f" ({self.current_texture.width}x{self.current_texture.height})"
            
            rl.draw_text(info_text, 10, 10, 20, rl.WHITE)
        else:
            rl.draw_text("No images found.", 10, 10, 20, rl.RED)

        rl.draw_text("ARROWS: Nav | SCROLL: Zoom | DRAG: Pan | SPACE: Reset", 10, rl.get_screen_height() - 30, 20, rl.GRAY)

        rl.end_drawing()

    def run(self):
        while not rl.window_should_close():
            self.update()
            self.draw()
        
        if self.texture_valid:
            rl.unload_texture(self.current_texture)
        rl.close_window()

if __name__ == "__main__":
    browser = AssetBrowser()
    browser.run()
