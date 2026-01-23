import pyray as pr
from dataclasses import dataclass
from typing import List, Dict, Any
import math
import json
import os
import psutil
import ctypes

# --- POLYFILLS FOR MISSING RAYLIB STRUCTS ---
if not hasattr(pr, 'Color'):
    class Color(ctypes.Structure):
        _fields_ = [("r", ctypes.c_ubyte), ("g", ctypes.c_ubyte), ("b", ctypes.c_ubyte), ("a", ctypes.c_ubyte)]
    pr.Color = Color

if not hasattr(pr, 'Rectangle'):
    class Rectangle(ctypes.Structure):
        _fields_ = [("x", ctypes.c_float), ("y", ctypes.c_float), ("width", ctypes.c_float), ("height", ctypes.c_float)]
    pr.Rectangle = Rectangle

if not hasattr(pr, 'Vector2'):
    class Vector2(ctypes.Structure):
        _fields_ = [("x", ctypes.c_float), ("y", ctypes.c_float)]
    pr.Vector2 = Vector2

if not hasattr(pr, 'Font'):
    class Font(ctypes.Structure):
        _fields_ = [("baseSize", ctypes.c_int), ("glyphCount", ctypes.c_int), ("glyphPadding", ctypes.c_int), ("texture", ctypes.c_void_p), ("recs", ctypes.c_void_p), ("glyphs", ctypes.c_void_p)]
    pr.Font = Font

# -------------------------------------------------------------------------
# 1. Define the Stylesheet (The "CSS" of your application)
# -------------------------------------------------------------------------
@dataclass
class UITheme:
    """
    Defines the color palette and sizing for the UI.
    Think of this like a CSS class definition.
    """
    name: str
    background_color: pr.Color
    surface_color: pr.Color      # Color for panels/cards
    text_primary: pr.Color
    text_secondary: pr.Color
    accent_color: pr.Color
    button_hover: pr.Color
    font_size_header: int = 40
    font_size_body: int = 20
    font: pr.Font = None

# -------------------------------------------------------------------------
# 2. Create Specific Themes
# -------------------------------------------------------------------------

# A "Solarized Light" style theme
LIGHT_THEME = UITheme(
    name="Solarized Light",
    background_color=pr.Color(253, 246, 227, 255),  # Creamy white
    surface_color=pr.Color(238, 232, 213, 255),     # Slightly darker beige
    text_primary=pr.Color(101, 123, 131, 255),      # Dark gray/blue
    text_secondary=pr.Color(147, 161, 161, 255),    # Light gray/blue
    accent_color=pr.Color(38, 139, 210, 255),       # Blue
    button_hover=pr.Color(133, 153, 0, 255)         # Green
)

# A "Cyberpunk Dark" style theme
DARK_THEME = UITheme(
    name="Cyberpunk Dark",
    background_color=pr.Color(10, 10, 15, 255),     # Almost black
    surface_color=pr.Color(25, 25, 35, 255),        # Dark gray
    text_primary=pr.Color(240, 240, 240, 255),      # White
    text_secondary=pr.Color(100, 255, 218, 255),    # Cyan
    accent_color=pr.Color(255, 0, 110, 255),        # Neon Pink
    button_hover=pr.Color(100, 255, 218, 255)       # Cyan
)

# "NeoTokyo Moon" theme
NEOTOKYO_THEME = UITheme(
    name="NeoTokyo Moon",
    background_color=pr.Color(12, 16, 33, 255),     # Deep Blue/Black
    surface_color=pr.Color(23, 28, 50, 255),        # Dark Blue
    text_primary=pr.Color(200, 210, 255, 255),      # Pale Blue
    text_secondary=pr.Color(100, 110, 160, 255),    # Muted Blue
    accent_color=pr.Color(255, 0, 100, 255),        # Neon Pink
    button_hover=pr.Color(0, 255, 200, 255)         # Neon Cyan
)

# "Gruvbox" theme
GRUVBOX_THEME = UITheme(
    name="Gruvbox",
    background_color=pr.Color(40, 40, 40, 255),     # Dark0
    surface_color=pr.Color(60, 56, 54, 255),        # Dark1
    text_primary=pr.Color(235, 219, 178, 255),      # Light1
    text_secondary=pr.Color(168, 153, 132, 255),    # Gray
    accent_color=pr.Color(254, 128, 25, 255),       # Orange
    button_hover=pr.Color(184, 187, 38, 255)        # Green
)

# -------------------------------------------------------------------------
# 3. UI Components (Widgets that use the theme)
# -------------------------------------------------------------------------

def draw_styled_button(rect: pr.Rectangle, text: str, theme: UITheme) -> bool:
    """
    Draws a button using the current theme colors.
    Returns True if clicked.
    """
    mouse_point = pr.get_mouse_position()
    is_hovered = pr.check_collision_point_rec(mouse_point, rect)
    is_clicked = False

    # Determine color based on state (Hover vs Normal)
    if is_hovered:
        color = theme.button_hover
        text_color = theme.background_color # Invert text on hover for contrast
        if pr.is_mouse_button_pressed(pr.MOUSE_BUTTON_LEFT):
            is_clicked = True
    else:
        color = theme.accent_color
        text_color = pr.WHITE

    # Draw Button Body
    pr.draw_rectangle_rec(rect, color)
    pr.draw_rectangle_lines_ex(rect, 2, theme.text_primary)

    # Draw Button Text (Centered)
    if theme.font:
        spacing = 1.0
        text_size = pr.measure_text_ex(theme.font, text, theme.font_size_body, spacing)
        text_x = rect.x + (rect.width - text_size.x) / 2
        text_y = rect.y + (rect.height - text_size.y) / 2
        pr.draw_text_ex(theme.font, text, pr.Vector2(text_x, text_y), theme.font_size_body, spacing, text_color)
    else:
        text_width = pr.measure_text(text, theme.font_size_body)
        text_x = int(rect.x + (rect.width - text_width) / 2)
        text_y = int(rect.y + (rect.height - theme.font_size_body) / 2)
        pr.draw_text(text, text_x, text_y, theme.font_size_body, text_color)

    return is_clicked

def wrap_text(font, text, max_width, font_size, spacing):
    """Wraps text to fit within max_width."""
    if not text: return ""
    lines = []
    for paragraph in text.split('\n'):
        words = paragraph.split(' ')
        current_line = []
        for word in words:
            test_line = ' '.join(current_line + [word])
            if font:
                size = pr.measure_text_ex(font, test_line, float(font_size), spacing)
                width = size.x
            else:
                width = pr.measure_text(test_line, int(font_size))
            
            if width > max_width:
                if current_line: lines.append(' '.join(current_line))
                current_line = [word]
            else:
                current_line.append(word)
        if current_line:
            lines.append(' '.join(current_line))
    return '\n'.join(lines)

def draw_card(rect: pr.Rectangle, item: Dict[str, Any], index: int, theme: UITheme, edit_state: Dict[str, Any], alpha: float = 1.0, interactive: bool = True) -> str:
    """Draws a 'card'. Returns 'delete', 'modified', or None."""
    # Resolve custom color if present
    base_color = theme.surface_color
    if 'color' in item:
        c = item['color']
        base_color = pr.Color(c[0], c[1], c[2], 255)
    
    # Resolve custom text color
    custom_text_col = theme.text_primary
    if 'text_color' in item:
        tc = item['text_color']
        custom_text_col = pr.Color(tc[0], tc[1], tc[2], 255)

    # Apply alpha for fade-in effect
    bg_color = pr.fade(base_color, alpha)
    
    # Calculate gradient bottom color (slightly darker)
    bottom_color = pr.fade(pr.Color(max(0, base_color.r - 40), max(0, base_color.g - 40), max(0, base_color.b - 40), 255), alpha)
    
    border_color = pr.fade(theme.text_secondary, alpha)
    title_color = pr.fade(theme.accent_color, alpha)
    content_color = pr.fade(custom_text_col, alpha)

    # Draw Drop Shadow
    shadow_offset = 5
    shadow_color = pr.fade(pr.BLACK, 0.3 * alpha)
    pr.draw_rectangle_rec(pr.Rectangle(rect.x + shadow_offset, rect.y + shadow_offset, rect.width, rect.height), shadow_color)

    # Draw Card Background (Gradient)
    pr.draw_rectangle_gradient_v(int(rect.x), int(rect.y), int(rect.width), int(rect.height), bg_color, bottom_color)
    pr.draw_rectangle_lines_ex(rect, 1, border_color)

    # --- Layout & Image Drawing ---
    content_y_offset = 60
    
    if 'texture' in item:
        tex = item['texture']
        # Draw image centered within card width
        img_h = 80
        aspect = tex.width / tex.height
        img_w = img_h * aspect
        if img_w > rect.width - 20:
            img_w = rect.width - 20
            img_h = img_w / aspect
            
        img_x = rect.x + (rect.width - img_w) / 2
        img_y = rect.y + 50
        
        pr.draw_texture_pro(tex, pr.Rectangle(0, 0, tex.width, tex.height), pr.Rectangle(img_x, img_y, img_w, img_h), pr.Vector2(0, 0), 0.0, pr.fade(pr.WHITE, alpha))
        content_y_offset = int(img_y - rect.y + img_h + 10)

    # --- Interaction Logic (Editing) ---
    result = None
    if interactive:
        mouse_point = pr.get_mouse_position()
        
        # Title Click Area
        title_rect = pr.Rectangle(rect.x + 20, rect.y + 20, rect.width - 50, 30)
        if pr.check_collision_point_rec(mouse_point, title_rect) and pr.is_mouse_button_pressed(pr.MOUSE_BUTTON_LEFT):
            edit_state['index'] = index
            edit_state['field'] = 'title'
            edit_state['buffer'] = item['title']

        # Content Click Area
        content_rect = pr.Rectangle(rect.x + 20, rect.y + content_y_offset, rect.width - 40, rect.height - content_y_offset - 10)
        if pr.check_collision_point_rec(mouse_point, content_rect) and pr.is_mouse_button_pressed(pr.MOUSE_BUTTON_LEFT):
            edit_state['index'] = index
            edit_state['field'] = 'content'
            edit_state['buffer'] = item['content']

    # --- Input Handling ---
    if edit_state['index'] == index:
        key = pr.get_char_pressed()
        while key > 0:
            if 32 <= key <= 125: edit_state['buffer'] += chr(key)
            key = pr.get_char_pressed()
        
        if pr.is_key_pressed(pr.KEY_BACKSPACE) and len(edit_state['buffer']) > 0:
            edit_state['buffer'] = edit_state['buffer'][:-1]
            
        if pr.is_key_pressed(pr.KEY_ENTER):
            item[edit_state['field']] = edit_state['buffer']
            edit_state['index'] = -1
            result = "modified"
        
        if pr.is_key_pressed(pr.KEY_ESCAPE):
            edit_state['index'] = -1

    # --- Determine Display Text ---
    display_title = item['title']
    display_content = item['content']
    
    if edit_state['index'] == index:
        if edit_state['field'] == 'title':
            display_title = edit_state['buffer'] + "_"
            title_color = pr.RED # Highlight while editing
        elif edit_state['field'] == 'content':
            display_content = edit_state['buffer'] + "_"
            content_color = pr.RED

    # Draw Title & Content (Bounded)
    # We use a scissor mode to ensure text stays inside the card visually
    pr.begin_scissor_mode(int(rect.x), int(rect.y), int(rect.width), int(rect.height))
    
    # Wrap Content
    wrapped_content = wrap_text(theme.font, display_content, rect.width - 40, 18, 1.0)
    
    if theme.font:
        pr.draw_text_ex(theme.font, display_title, pr.Vector2(rect.x + 20, rect.y + 20), theme.font_size_body, 1.0, title_color)
        pr.draw_text_ex(theme.font, wrapped_content, pr.Vector2(rect.x + 20, rect.y + content_y_offset), 18, 1.0, content_color)
    else:
        pr.draw_text(display_title, int(rect.x + 20), int(rect.y + 20), theme.font_size_body, title_color)
        pr.draw_text(wrapped_content, int(rect.x + 20), int(rect.y + content_y_offset), 18, content_color)
    
    pr.end_scissor_mode()

    # Draw Interactive Elements
    if interactive:
        # 1. Color Swatches (Bottom Left)
        swatches = [
            (theme.surface_color.r, theme.surface_color.g, theme.surface_color.b), # Default
            (255, 200, 200), (200, 255, 200), (200, 200, 255), (255, 255, 200)
        ]
        swatch_size = 12
        for i, col in enumerate(swatches):
            swatch_rect = pr.Rectangle(rect.x + 20 + i * (swatch_size + 5), rect.y + rect.height - 25, swatch_size, swatch_size)
            swatch_color = pr.Color(col[0], col[1], col[2], 255)
            
            if pr.check_collision_point_rec(mouse_point, swatch_rect):
                pr.draw_rectangle_lines_ex(pr.Rectangle(swatch_rect.x-2, swatch_rect.y-2, swatch_rect.width+4, swatch_rect.height+4), 1, theme.accent_color)
                if pr.is_mouse_button_pressed(pr.MOUSE_BUTTON_LEFT):
                    item['color'] = col
                    result = "modified"
            
            pr.draw_rectangle_rec(swatch_rect, pr.fade(swatch_color, alpha))

        # 2. Text Color Swatches (Bottom Right)
        text_swatches = [
            (theme.text_primary.r, theme.text_primary.g, theme.text_primary.b), # Default
            (0, 0, 0), (255, 255, 255)
        ]
        for i, col in enumerate(text_swatches):
            ts_rect = pr.Rectangle(rect.x + rect.width - 20 - (len(text_swatches)-i) * (swatch_size + 5), rect.y + rect.height - 25, swatch_size, swatch_size)
            ts_color = pr.Color(col[0], col[1], col[2], 255)
            if pr.check_collision_point_rec(mouse_point, ts_rect):
                pr.draw_rectangle_lines_ex(pr.Rectangle(ts_rect.x-2, ts_rect.y-2, ts_rect.width+4, ts_rect.height+4), 1, theme.text_secondary)
                if pr.is_mouse_button_pressed(pr.MOUSE_BUTTON_LEFT):
                    item['text_color'] = col
            pr.draw_rectangle_rec(ts_rect, pr.fade(ts_color, alpha))

        # 3. Delete Button (Top Right)
        btn_size = 20
        btn_rect = pr.Rectangle(rect.x + rect.width - btn_size - 10, rect.y + 10, btn_size, btn_size)
        mouse_point = pr.get_mouse_position()
        is_hovered = pr.check_collision_point_rec(mouse_point, btn_rect)
        
        btn_color = pr.RED if is_hovered else pr.fade(pr.RED, 0.7 * alpha)
        pr.draw_rectangle_rec(btn_rect, btn_color)
        pr.draw_text("X", int(btn_rect.x + 6), int(btn_rect.y + 2), 10, pr.WHITE)

        if is_hovered and pr.is_mouse_button_pressed(pr.MOUSE_BUTTON_LEFT):
            return "delete"
            
    return result

def save_cards(items: List[Dict[str, Any]]):
    """Saves the list of cards to a JSON file."""
    try:
        with open("cards.json", "w") as f:
            json.dump(items, f, indent=4)
    except Exception as e:
        print(f"Error saving cards: {e}")

def load_cards() -> List[Dict[str, Any]]:
    """Loads cards from a JSON file."""
    if os.path.exists("cards.json"):
        try:
            with open("cards.json", "r") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def draw_grid_layout(area: pr.Rectangle, items: List[Dict[str, Any]], cols: int, gap: float, theme: UITheme, drag_state: Dict[str, Any], scroll_state: Dict[str, float], edit_state: Dict[str, Any]) -> bool:
    """
    Draws a list of items in a grid layout. Returns True if the list was modified (reordered/deleted).
    """
    if cols < 1: cols = 1
    # Calculate width of a single item based on available width and gaps
    # Reserve space for scrollbar
    scrollbar_width = 12
    content_width = area.width - scrollbar_width - 5
    item_width = (content_width - (cols - 1) * gap) / cols
    item_height = 150 # Fixed height for cards
    modified = False
    
    # Calculate Scroll
    total_rows = math.ceil(len(items) / cols)
    content_height = total_rows * (item_height + gap) - gap
    view_height = area.height
    max_scroll = max(0, content_height - view_height)

    # Mouse Wheel Scrolling
    if pr.check_collision_point_rec(pr.get_mouse_position(), area):
        scroll_state['offset'] -= pr.get_mouse_wheel_move() * 20
        scroll_state['offset'] = max(0, min(scroll_state['offset'], max_scroll))

    # Handle Drag Release
    if drag_state['dragging']:
        if pr.is_mouse_button_released(pr.MOUSE_BUTTON_LEFT):
            drag_state['dragging'] = False
            drag_state['item'] = None
            drag_state['index'] = -1

    items_to_remove = []
    mouse_pos = pr.get_mouse_position()

    # Clip content to grid area
    pr.begin_scissor_mode(int(area.x), int(area.y), int(area.width), int(area.height))

    for i, item in enumerate(items):
        # Skip drawing the placeholder for the dragged item
        if drag_state['dragging'] and drag_state['index'] == i:
            continue

        col = i % cols
        row = i // cols
        
        x = area.x + col * (item_width + gap)
        y = area.y + row * (item_height + gap) - scroll_state['offset']
        
        # Animation Logic
        progress = item.get("anim_progress", 1.0)
        # Cubic ease-out: starts fast, slows down at the end
        ease = 1.0 - pow(1.0 - progress, 3)
        offset_y = (1.0 - ease) * 50  # Slide up from 50px below
        
        rect = pr.Rectangle(x, y + offset_y, item_width, item_height)
        
        # Disable interaction if dragging
        action = draw_card(rect, item, i, theme, edit_state, alpha=progress, interactive=not drag_state['dragging'])
        if action == "delete":
            items_to_remove.append(item)
        elif action == "modified":
            modified = True
        
        # Handle Drag Start (Only if mouse is inside the visible grid area)
        if not drag_state['dragging'] and item not in items_to_remove:
             if pr.check_collision_point_rec(mouse_pos, area):
                 if pr.is_mouse_button_pressed(pr.MOUSE_BUTTON_LEFT) and pr.check_collision_point_rec(mouse_pos, rect):
                     drag_state['dragging'] = True
                     drag_state['index'] = i
                     drag_state['item'] = item
                     drag_state['offset_x'] = rect.x - mouse_pos.x
                     drag_state['offset_y'] = rect.y - mouse_pos.y
        
        # Handle Swap while Dragging
        if drag_state['dragging'] and drag_state['index'] != i:
             # Check collision with the slot's rect (without animation offset for stability)
             slot_rect = pr.Rectangle(x, y, item_width, item_height)
             if pr.check_collision_point_rec(mouse_pos, slot_rect):
                 # Swap in list
                 items[drag_state['index']], items[i] = items[i], items[drag_state['index']]
                 # Update index to track the item
                 drag_state['index'] = i
                 modified = True

    pr.end_scissor_mode()

    # Draw Scrollbar
    if max_scroll > 0:
        bar_x = area.x + area.width - scrollbar_width
        bar_y = area.y
        # Track
        pr.draw_rectangle(int(bar_x), int(bar_y), scrollbar_width, int(view_height), pr.fade(theme.surface_color, 0.5))
        # Handle
        handle_height = max(30, (view_height / content_height) * view_height)
        handle_y = bar_y + (scroll_state['offset'] / max_scroll) * (view_height - handle_height)
        pr.draw_rectangle(int(bar_x), int(handle_y), scrollbar_width, int(handle_height), theme.accent_color)

    # Draw Floating Card
    if drag_state['dragging'] and drag_state['item']:
        drag_rect = pr.Rectangle(
            mouse_pos.x + drag_state['offset_x'], 
            mouse_pos.y + drag_state['offset_y'], 
            item_width, 
            item_height
        )
        draw_card(drag_rect, drag_state['item'], -1, theme, edit_state, alpha=0.9, interactive=False)

    for item in items_to_remove:
        items.remove(item)
        modified = True
        
    return modified

# -------------------------------------------------------------------------
# 4. Main Application Loop
# -------------------------------------------------------------------------

def main():
    SCREEN_WIDTH = 800
    SCREEN_HEIGHT = 600
    
    if hasattr(pr, 'set_config_flags'):
        pr.set_config_flags(pr.FLAG_WINDOW_RESIZABLE)
    pr.init_window(SCREEN_WIDTH, SCREEN_HEIGHT, "Raylib Python Stylesheet Demo")
    pr.set_target_fps(60)

    # --- Nerd Font / Custom Font Loading ---
    # To use a Nerd Font, provide the path to the .ttf file.
    # Raylib's load_font_ex can load glyphs. If you need specific icons, you might need to specify codepoints.
    # For general text, just loading it works.
    font_path = "resources/nerd_font.ttf" # Replace with your actual font path
    if os.path.exists(font_path):
        # Load font with size 32. Passing None/0 loads default char set.
        # To load icons, you would pass a list of codepoints (ints) as the 3rd argument.
        custom_font = pr.load_font_ex(font_path, 32, None, 0)
        pr.set_texture_filter(custom_font.texture, pr.TEXTURE_FILTER_BILINEAR)
        LIGHT_THEME.font = custom_font
        DARK_THEME.font = custom_font

    themes = [LIGHT_THEME, DARK_THEME, NEOTOKYO_THEME, GRUVBOX_THEME]
    current_theme_idx = 0
    # State
    current_theme = themes[current_theme_idx]
    drag_state = {"dragging": False, "index": -1, "item": None, "offset_x": 0.0, "offset_y": 0.0}
    scroll_state = {"offset": 0.0}
    edit_state = {"index": -1, "field": "", "buffer": ""}
    confirm_clear = False
    
    # Mock Data for Grid
    grid_items = load_cards()
    if not grid_items:
        grid_items = [
            {"title": "Dashboard", "content": "Stats: \n- CPU: 45%\n- RAM: 2.1GB"},
            {"title": "Notifications", "content": "You have 3 new messages.\nCheck your inbox."},
            {"title": "Tasks", "content": "- Fix bugs\n- Write docs\n- Deploy"},
            {"title": "Calendar", "content": "Meeting at 2:00 PM\nTeam sync"},
        ]

    # --- System Monitor Card Setup ---
    # Ensure a card for system stats exists at the top
    sys_card = next((item for item in grid_items if item.get("title") == "System Monitor"), None)
    if not sys_card:
        sys_card = {"title": "System Monitor", "content": "Initializing...", "anim_progress": 0.0}
        grid_items.insert(0, sys_card)

    # --- Image Loading ---
    # Load an image from a file path instead of generating one
    image_path = "resources/my_image.png" # Replace with your actual file path
    if os.path.exists(image_path):
        demo_tex = pr.load_texture(image_path)
    else:
        # Fallback if file doesn't exist
        demo_img = pr.gen_image_checked(128, 128, 16, 16, pr.LIME, pr.DARKGRAY)
        demo_tex = pr.load_texture_from_image(demo_img)
        pr.unload_image(demo_img)

    if grid_items: grid_items[0]['texture'] = demo_tex

    stats_timer = 0.0

    while not pr.window_should_close():
        # Get dynamic screen dimensions
        sw = pr.get_screen_width()
        sh = pr.get_screen_height()

        # Update Animation Progress
        dt = pr.get_frame_time()
        for item in grid_items:
            if item.get("anim_progress", 1.0) < 1.0:
                item["anim_progress"] = min(1.0, item.get("anim_progress", 0.0) + dt * 3.0) # 3.0 speed = ~0.33s duration

        # Update System Stats (every 0.5s)
        stats_timer += dt
        if stats_timer > 0.5:
            stats_timer = 0
            if sys_card in grid_items:
                cpu = psutil.cpu_percent()
                ram = psutil.virtual_memory().percent
                fps = pr.get_fps()
                sys_card["content"] = f"FPS: {fps}\nCPU: {cpu}%\nRAM: {ram}%"

        # --- Update Logic ---
        # Switch themes with Arrow Keys (Left/Right)
        if pr.is_key_pressed(pr.KEY_RIGHT):
            current_theme_idx = (current_theme_idx + 1) % len(themes)
            current_theme = themes[current_theme_idx]
        elif pr.is_key_pressed(pr.KEY_LEFT):
            current_theme_idx = (current_theme_idx - 1) % len(themes)
            current_theme = themes[current_theme_idx]

        # --- Drawing Logic ---
        pr.begin_drawing()
        
        # 1. Apply Background Style
        pr.clear_background(current_theme.background_color)

        # 2. Draw Header
        if current_theme.font:
            pr.draw_text_ex(current_theme.font, f"Theme: {current_theme.name}", pr.Vector2(20, 20), current_theme.font_size_header, 1.0, current_theme.text_primary)
            pr.draw_text_ex(current_theme.font, "Use LEFT/RIGHT arrows to switch themes", pr.Vector2(20, 70), current_theme.font_size_body, 1.0, current_theme.text_secondary)
        else:
            pr.draw_text(f"Theme: {current_theme.name}", 20, 20, current_theme.font_size_header, current_theme.text_primary)
            pr.draw_text("Use LEFT/RIGHT arrows to switch themes", 20, 70, current_theme.font_size_body, current_theme.text_secondary)

        # 3. Draw Grid System
        # Define area for the grid (below header, with margins)
        grid_area = pr.Rectangle(20, 120, sw - 40, sh - 200)
        
        # Responsive columns: 1 col if small, 2 if medium, 3 if large
        cols = 1
        if sw > 500: cols = 2
        if sw > 900: cols = 3
        
        # Only process grid interaction if not showing confirmation
        if not confirm_clear:
            if draw_grid_layout(grid_area, grid_items, cols, 20, current_theme, drag_state, scroll_state, edit_state):
                save_cards(grid_items)

        # 4. Draw a Button Component (Fixed at bottom)
        button_rect = pr.Rectangle(20, sh - 70, 200, 50)
        if draw_styled_button(button_rect, "Add Card", current_theme):
            grid_items.append({"title": f"Card {len(grid_items)+1}", "content": "New dynamically added card.", "anim_progress": 0.0})
            save_cards(grid_items)
            
        # 5. Clear All Button
        clear_rect = pr.Rectangle(240, sh - 70, 200, 50)
        if draw_styled_button(clear_rect, "Clear All", current_theme):
            confirm_clear = True

        # 6. Confirmation Dialog Overlay
        if confirm_clear:
            # Dim background
            pr.draw_rectangle(0, 0, sw, sh, pr.fade(pr.BLACK, 0.5))
            
            # Dialog Box
            dialog_w, dialog_h = 300, 150
            dx, dy = (sw - dialog_w)//2, (sh - dialog_h)//2
            pr.draw_rectangle(dx, dy, dialog_w, dialog_h, current_theme.surface_color)
            pr.draw_rectangle_lines(dx, dy, dialog_w, dialog_h, current_theme.accent_color)
            
            text = "Delete all cards?"
            tw = pr.measure_text(text, 20)
            pr.draw_text(text, dx + (dialog_w - tw)//2, dy + 30, 20, current_theme.text_primary)
            
            # Yes Button
            if draw_styled_button(pr.Rectangle(dx + 20, dy + 90, 100, 40), "Yes", current_theme):
                grid_items.clear()
                save_cards(grid_items)
                confirm_clear = False
            
            # No Button
            if draw_styled_button(pr.Rectangle(dx + 180, dy + 90, 100, 40), "No", current_theme):
                confirm_clear = False

        pr.end_drawing()

    # Cleanup
    pr.unload_texture(demo_tex)
    if LIGHT_THEME.font:
        pr.unload_font(LIGHT_THEME.font)

    pr.close_window()

if __name__ == "__main__":
    main()
