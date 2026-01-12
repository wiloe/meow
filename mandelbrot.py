import pyray as rl
import os
import math
import random

def main():
    # Configuration
    SCREEN_WIDTH = 800
    SCREEN_HEIGHT = 600
    
    rl.set_config_flags(rl.FLAG_WINDOW_RESIZABLE)
    rl.init_window(SCREEN_WIDTH, SCREEN_HEIGHT, "Mandelbrot Set - Raylib Python")
    rl.set_target_fps(60)

    # Create a blank texture for rendering shaders with proper UVs
    blank_img = rl.gen_image_color(1, 1, rl.WHITE)
    blank_tex = rl.load_texture_from_image(blank_img)
    rl.unload_image(blank_img)

    # --- Shader Generation ---
    # We write the shaders to temporary files to load them with Raylib
    vs_code = """#version 330
    in vec3 vertexPosition;
    in vec2 vertexTexCoord;
    in vec4 vertexColor;
    out vec2 fragTexCoord;
    out vec4 fragColor;
    uniform mat4 mvp;
    void main() {
        fragTexCoord = vertexTexCoord;
        fragColor = vertexColor;
        gl_Position = mvp * vec4(vertexPosition, 1.0);
    }
    """

    fs_code = """#version 330
    in vec2 fragTexCoord;
    in vec4 fragColor;
    out vec4 finalColor;

    uniform vec2 resolution;
    uniform vec2 center;
    uniform float zoom;
    uniform int mode;
    uniform vec2 julia_c;
    uniform int palette;
    uniform int max_iter;

    // Helper for coloring
    vec3 hsv2rgb(vec3 c) {
        vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
        vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
        return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
    }

    void main() {
        // Use fragTexCoord for UVs to support drawing in sub-rectangles
        // Invert Y to match standard complex plane orientation (Y up) relative to screen (Y down)
        vec2 uv = vec2(fragTexCoord.x, 1.0 - fragTexCoord.y);
        float aspect = resolution.x / resolution.y;
        
        // Map screen to complex plane
        // (uv - 0.5) centers the view
        vec2 p = (uv - 0.5) * vec2(aspect, 1.0);
        
        vec2 z;
        vec2 c;
        
        if (mode == 0) {
            z = vec2(0.0);
            c = p / zoom + center;
        } else {
            z = p / zoom + center;
            c = julia_c;
        }
        
        int iter = 0;
        
        for (int i = 0; i < max_iter; i++) {
            float x = (z.x * z.x - z.y * z.y) + c.x;
            float y = (2.0 * z.x * z.y) + c.y;
            
            if ((x * x + y * y) > 4.0) break;
            
            z.x = x;
            z.y = y;
            iter++;
        }
        
        if (iter == max_iter) {
            finalColor = vec4(0.0, 0.0, 0.0, 1.0);
        } else {
            // Smooth coloring based on iteration count
            float t = float(iter) / float(max_iter);
            vec3 col;
            if (palette == 0) col = hsv2rgb(vec3(t * 5.0 + 0.5, 0.8, 1.0));
            else if (palette == 1) col = vec3(sqrt(t));
            else if (palette == 2) col = vec3(t * 4.0, t * 2.0, t * 0.5);
            else if (palette == 3) col = vec3(t * 0.5, t * 1.5, t * 3.0);
            else col = hsv2rgb(vec3(t * 20.0, 1.0, 1.0));
            finalColor = vec4(col, 1.0);
        }
    }
    """

    vs_path = "mandelbrot_temp.vs"
    fs_path = "mandelbrot_temp.fs"
    
    try:
        with open(vs_path, "w") as f: f.write(vs_code)
        with open(fs_path, "w") as f: f.write(fs_code)

        # --- Initialization ---
        shader = rl.load_shader(vs_path, fs_path)
        
        loc_res = rl.get_shader_location(shader, "resolution")
        loc_center = rl.get_shader_location(shader, "center")
        loc_zoom = rl.get_shader_location(shader, "zoom")
        loc_mode = rl.get_shader_location(shader, "mode")
        loc_julia_c = rl.get_shader_location(shader, "julia_c")
        loc_palette = rl.get_shader_location(shader, "palette")
        loc_max_iter = rl.get_shader_location(shader, "max_iter")

        center = [-0.75, 0.0]
        target_center = list(center)
        zoom = 0.5
        target_zoom = 0.5
        last_mouse = rl.get_mouse_position()
        dragging = False
        
        mode = 0 # 0: Mandelbrot, 1: Julia
        julia_c = [0.0, 0.0]
        saved_mandelbrot_view = {'center': list(center), 'zoom': zoom}
        palette = 0
        palette_names = ["Classic", "Grayscale", "Fire", "Ice", "Rainbow"]
        auto_zoom = False
        
        interesting_points = [
            ([-0.74364388703, 0.13182590421], 3000.0), # Seahorse Valley
            ([-1.76938317919, 0.00423684791], 2000.0), # Mini Mandelbrot
            ([-0.16070135, 1.0375665], 500.0),         # Triple Spiral
            ([0.42884, -0.231345], 500.0),             # Elephant Valley area
            ([-0.7492, 0.1], 100.0),                   # East Valley
            ([-0.75, 0.0], 0.5)                        # Default
        ]

        # --- Main Loop ---
        while not rl.window_should_close():
            w = float(rl.get_screen_width())
            h = float(rl.get_screen_height())
            
            # --- Mini-map Configuration ---
            mm_w, mm_h = 200, 150
            mm_x, mm_y = int(w) - mm_w - 10, int(h) - mm_h - 10
            mm_rect = rl.Rectangle(mm_x, mm_y, mm_w, mm_h)
            mm_zoom = 0.3
            mm_center = [-0.75, 0.0] if mode == 0 else [0.0, 0.0]
            
            # Input: Zoom
            wheel = rl.get_mouse_wheel_move()
            if wheel != 0:
                mx = rl.get_mouse_x()
                my = rl.get_mouse_y()
                aspect = w / h
                
                # Calculate complex point under mouse
                u = mx / w
                v = (h - my) / h
                px = (u - 0.5) * aspect
                py = (v - 0.5)
                c_ref_x = px / zoom + center[0]
                c_ref_y = py / zoom + center[1]

                scale = 1.1
                if wheel > 0: target_zoom *= scale
                else: target_zoom /= scale
                
                # Adjust target center to keep point under mouse stable
                target_center[0] = c_ref_x - px / target_zoom
                target_center[1] = c_ref_y - py / target_zoom

            # Input: Toggle Auto Zoom
            if rl.is_key_pressed(rl.KEY_A):
                auto_zoom = not auto_zoom

            if auto_zoom:
                target_zoom *= 1.01
                if target_zoom > 1.0e6: # Loop back before precision loss
                    target_zoom = 0.5
                    zoom = 0.5

            # Smooth zoom interpolation
            zoom += (target_zoom - zoom) * 0.1
            center[0] += (target_center[0] - center[0]) * 0.1
            center[1] += (target_center[1] - center[1]) * 0.1

            # Input: Toggle Mode
            if rl.is_key_pressed(rl.KEY_SPACE):
                if mode == 0:
                    # Switch to Julia
                    # Calculate c from mouse position
                    mx = rl.get_mouse_x()
                    my = rl.get_mouse_y()
                    aspect = w / h
                    # Map mouse to complex plane (gl_FragCoord.y is inverted relative to mouse.y)
                    u = mx / w
                    v = (h - my) / h
                    px = (u - 0.5) * aspect
                    py = (v - 0.5)
                    julia_c = [px / zoom + center[0], py / zoom + center[1]]
                    
                    saved_mandelbrot_view = {'center': list(center), 'zoom': zoom}
                    center = [0.0, 0.0]
                    target_center = [0.0, 0.0]
                    zoom = 0.5
                    target_zoom = 0.5
                    mode = 1
                else:
                    # Switch to Mandelbrot
                    center = saved_mandelbrot_view['center']
                    target_center = list(center)
                    zoom = saved_mandelbrot_view['zoom']
                    target_zoom = zoom
                    mode = 0

            # Input: Cycle Palette
            if rl.is_key_pressed(rl.KEY_C):
                palette = (palette + 1) % len(palette_names)

            # Input: Home (Reset View)
            if rl.is_key_pressed(rl.KEY_H):
                target_zoom = 0.5
                if mode == 0:
                    target_center = [-0.75, 0.0]
                else:
                    target_center = [0.0, 0.0]

            # Input: Random Destination (R)
            if rl.is_key_pressed(rl.KEY_R):
                dest = random.choice(interesting_points)
                target_center = list(dest[0])
                target_zoom = dest[1]
                mode = 0
                auto_zoom = False

            # Input: Pan / Mini-map Click
            if rl.is_mouse_button_pressed(rl.MOUSE_LEFT_BUTTON):
                mouse_pos = rl.get_mouse_position()
                if rl.check_collision_point_rec(mouse_pos, mm_rect):
                    # Mini-map click
                    uv_x = (mouse_pos.x - mm_x) / mm_w
                    uv_y = (mouse_pos.y - mm_y) / mm_h
                    mm_aspect = mm_w / mm_h
                    
                    # Map to complex plane
                    p_x = (uv_x - 0.5) * mm_aspect
                    p_y = (1.0 - uv_y) - 0.5
                    
                    click_c_x = p_x / mm_zoom + mm_center[0]
                    click_c_y = p_y / mm_zoom + mm_center[1]
                    
                    target_center = [click_c_x, click_c_y]
                    center = [click_c_x, click_c_y]
                    dragging = False
                else:
                    dragging = True
                    last_mouse = rl.get_mouse_position()
            elif rl.is_mouse_button_released(rl.MOUSE_LEFT_BUTTON):
                dragging = False
                
            if dragging:
                curr_mouse = rl.get_mouse_position()
                dx = curr_mouse.x - last_mouse.x
                dy = curr_mouse.y - last_mouse.y
                
                aspect = w / h
                target_center[0] -= (dx / w) * (aspect / zoom)
                target_center[1] += (dy / h) * (1.0 / zoom)
                center[0] = target_center[0]
                center[1] = target_center[1]
                last_mouse = curr_mouse

            # Update Uniforms
            rl.set_shader_value(shader, loc_res, rl.ffi.new("float[]", [w, h]), rl.SHADER_UNIFORM_VEC2)
            rl.set_shader_value(shader, loc_center, rl.ffi.new("float[]", center), rl.SHADER_UNIFORM_VEC2)
            rl.set_shader_value(shader, loc_zoom, rl.ffi.new("float[]", [zoom]), rl.SHADER_UNIFORM_FLOAT)
            rl.set_shader_value(shader, loc_mode, rl.ffi.new("int[]", [mode]), rl.SHADER_UNIFORM_INT)
            rl.set_shader_value(shader, loc_julia_c, rl.ffi.new("float[]", julia_c), rl.SHADER_UNIFORM_VEC2)
            rl.set_shader_value(shader, loc_palette, rl.ffi.new("int[]", [palette]), rl.SHADER_UNIFORM_INT)
            
            # Dynamic max iterations based on zoom
            current_max_iter = max(100, int(300 + 40 * math.log10(zoom)))
            rl.set_shader_value(shader, loc_max_iter, rl.ffi.new("int[]", [current_max_iter]), rl.SHADER_UNIFORM_INT)

            # Draw
            rl.begin_drawing()
            rl.clear_background(rl.BLACK)
            
            rl.begin_shader_mode(shader)
            rl.draw_texture_pro(blank_tex, rl.Rectangle(0, 0, 1, 1), rl.Rectangle(0, 0, w, h), rl.Vector2(0, 0), 0.0, rl.WHITE)
            rl.end_shader_mode()
            
            # UI
            rl.draw_rectangle(0, 0, int(w), 100, rl.fade(rl.BLACK, 0.5))
            rl.draw_text(f"Zoom: {zoom:.4e} Iter: {current_max_iter}", 10, 10, 20, rl.GREEN)
            rl.draw_text(f"Center: {center[0]:.6f}, {center[1]:.6f}", 250, 10, 20, rl.GREEN)
            mode_text = f"Mode: {'Julia' if mode == 1 else 'Mandelbrot'}"
            if mode == 1: mode_text += f" C: {julia_c[0]:.4f}, {julia_c[1]:.4f}"
            rl.draw_text(mode_text, 10, 40, 20, rl.WHITE)
            rl.draw_text(f"Palette: {palette_names[palette]} (C) | Reset (H) | Anim (A) | Random (R)", 10, 70, 20, rl.YELLOW)
            
            # --- Mini-map ---
            
            # Draw Mini-map Background (Mandelbrot)
            rl.begin_shader_mode(shader)
            rl.set_shader_value(shader, loc_res, rl.ffi.new("float[]", [float(mm_w), float(mm_h)]), rl.SHADER_UNIFORM_VEC2)
            rl.set_shader_value(shader, loc_center, rl.ffi.new("float[]", mm_center), rl.SHADER_UNIFORM_VEC2)
            rl.set_shader_value(shader, loc_zoom, rl.ffi.new("float[]", [mm_zoom]), rl.SHADER_UNIFORM_FLOAT)
            rl.set_shader_value(shader, loc_mode, rl.ffi.new("int[]", [mode]), rl.SHADER_UNIFORM_INT)
            rl.set_shader_value(shader, loc_max_iter, rl.ffi.new("int[]", [100]), rl.SHADER_UNIFORM_INT) # Low iter for speed
            rl.draw_texture_pro(blank_tex, rl.Rectangle(0, 0, 1, 1), mm_rect, rl.Vector2(0, 0), 0.0, rl.WHITE)
            rl.end_shader_mode()
            
            rl.draw_rectangle_lines(int(mm_x), int(mm_y), int(mm_w), int(mm_h), rl.WHITE)
            
            # Draw Indicator
            mm_aspect = mm_w / mm_h
            
            # Function to map complex point to minimap screen coords
            def complex_to_minimap(cx, cy):
                uv_x = (cx - mm_center[0]) * mm_zoom / mm_aspect + 0.5
                uv_y = (cy - mm_center[1]) * mm_zoom + 0.5
                sx = mm_x + uv_x * mm_w
                sy = mm_y + (1.0 - uv_y) * mm_h
                return sx, sy

            # Show View Rect
            view_w_c = (w/h) / zoom
            view_h_c = 1.0 / zoom
            ix, iy = complex_to_minimap(center[0], center[1])
            iw, ih = view_w_c * mm_zoom / mm_aspect * mm_w, view_h_c * mm_zoom * mm_h
            rl.draw_rectangle_lines(int(ix - iw/2), int(iy - ih/2), max(1, int(iw)), max(1, int(ih)), rl.RED)

            rl.draw_fps(int(w) - 80, 10)
            
            rl.end_drawing()

    except KeyboardInterrupt:
        pass
    finally:
        # --- Cleanup ---
        if 'shader' in locals(): rl.unload_shader(shader)
        if 'blank_tex' in locals(): rl.unload_texture(blank_tex)
        rl.close_window()
        
        if os.path.exists(vs_path): os.remove(vs_path)
        if os.path.exists(fs_path): os.remove(fs_path)

if __name__ == "__main__":
    main()