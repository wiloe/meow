import numpy as np

def iso_to_screen(grid_x, grid_y, tile_width, tile_height):
    """
    Converts grid coordinates to isometric screen coordinates.
    """
    screen_x = (grid_x - grid_y) * (tile_width / 2)
    screen_y = (grid_x + grid_y) * (tile_height / 2)
    return screen_x, screen_y

def screen_to_iso(screen_x, screen_y, tile_width, tile_height):
    """
    Converts screen coordinates to grid coordinates.
    """
    half_w = tile_width / 2
    half_h = tile_height / 2
    
    grid_x = (screen_x / half_w + screen_y / half_h) / 2
    grid_y = (screen_y / half_h - screen_x / half_w) / 2
    return grid_x, grid_y

def get_distance(x1, y1, x2, y2):
    """
    Calculates Euclidean distance between two points.
    """
    return np.hypot(x2 - x1, y2 - y1)

def check_aabb_collision(x1, y1, w1, h1, x2, y2, w2, h2):
    """
    Checks for Axis-Aligned Bounding Box collision.
    """
    return (x1 < x2 + w2 and
            x1 + w1 > x2 and
            y1 < y2 + h2 and
            y1 + h1 > y2)

def lerp(start, end, amount):
    """
    Linear interpolation.
    """
    return start + amount * (end - start)

def clamp(value, min_val, max_val):
    """
    Restricts a value to be within a specified range.
    """
    return max(min_val, min(value, max_val))

def get_angle(x1, y1, x2, y2):
    """
    Calculates the angle in radians between two points.
    """
    return np.arctan2(y2 - y1, x2 - x1)

def normalize(x, y):
    """
    Normalizes a 2D vector.
    """
    m = np.hypot(x, y)
    if m == 0:
        return 0.0, 0.0
    return x / m, y / m

def check_circle_collision(x1, y1, r1, x2, y2, r2):
    """
    Checks for collision between two circles.
    """
    return get_distance(x1, y1, x2, y2) < (r1 + r2)