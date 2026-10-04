"""
LanternFire - Thermal simulation kernel and fire palette mapping.
Compatible with standard Python 3 and CircuitPython.
"""
import math
import random

# Hardware grid mapping: 4x4 matrix mapped to NeoTrellis key indices
GRID = [
    [15, 11, 7, 3],  # Row 0
    [14, 10, 6, 2],  # Row 1
    [13,  9, 5, 1],  # Row 2
    [12,  8, 4, 0]   # Row 3
]

INDEX_TO_XY = {}
for y in range(4):
    for x in range(4):
        INDEX_TO_XY[GRID[y][x]] = (x, y)

# Predefined brightness levels
BRIGHTNESS_LEVELS = [0.10, 0.25, 0.50, 0.80]

# Atmospheric fire vigor presets
VIGOR_PRESETS = {
    "GENTLE": {
        "baseline": 0.28,
        "cooling_rate": 0.04,
        "diffusion_rate": 0.12,
        "turbulence": 0.03,
        "drift_speed": 1.2
    },
    "CAMPFIRE": {
        "baseline": 0.42,
        "cooling_rate": 0.06,
        "diffusion_rate": 0.16,
        "turbulence": 0.07,
        "drift_speed": 2.0
    },
    "BLAZE": {
        "baseline": 0.58,
        "cooling_rate": 0.08,
        "diffusion_rate": 0.20,
        "turbulence": 0.12,
        "drift_speed": 3.2
    }
}
VIGOR_ORDER = ["GENTLE", "CAMPFIRE", "BLAZE"]

def _lerp_color(c1, c2, t):
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t)
    )

def heat_to_rgb(heat, brightness=1.0):
    """
    Maps heat value [0.0, 1.0] to an RGB tuple scaled by brightness [0.0, 1.0].
    Strictly clamps output channels to [0, 255].
    """
    h = max(0.0, min(1.0, float(heat)))
    b = max(0.0, min(1.0, float(brightness)))

    # Color stops
    # 0.00 -> 0.15: (15, 0, 0) -> (60, 4, 0)
    # 0.15 -> 0.45: (60, 4, 0) -> (190, 35, 0)
    # 0.45 -> 0.75: (190, 35, 0) -> (255, 110, 0)
    # 0.75 -> 1.00: (255, 110, 0) -> (255, 230, 130)
    if h <= 0.15:
        t = h / 0.15
        rgb = _lerp_color((15, 0, 0), (60, 4, 0), t)
    elif h <= 0.45:
        t = (h - 0.15) / 0.30
        rgb = _lerp_color((60, 4, 0), (190, 35, 0), t)
    elif h <= 0.75:
        t = (h - 0.45) / 0.30
        rgb = _lerp_color((190, 35, 0), (255, 110, 0), t)
    else:
        t = (h - 0.75) / 0.25
        rgb = _lerp_color((255, 110, 0), (255, 230, 130), t)

    return (
        max(0, min(255, int(rgb[0] * b))),
        max(0, min(255, int(rgb[1] * b))),
        max(0, min(255, int(rgb[2] * b)))
    )

class FireSimulation:
    def __init__(self, width=4, height=4):
        if width != 4 or height != 4:
            raise ValueError("Only 4x4 grids are currently supported by NeoTrellis hardware mapping")
        self.width = width
        self.height = height
        self.heat = [[0.3 for _ in range(width)] for _ in range(height)]
        self.phase = [[random.uniform(0, 2 * math.pi) for _ in range(width)] for _ in range(height)]
        self.elapsed_time = 0.0

        self.brightness_idx = 1  # Default 0.25 (cozy)
        self._brightness = BRIGHTNESS_LEVELS[self.brightness_idx]
        self.vigor = "CAMPFIRE"
        self._load_vigor_params()

    def _load_vigor_params(self):
        params = VIGOR_PRESETS[self.vigor]
        self.baseline = params["baseline"]
        self.cooling_rate = params["cooling_rate"]
        self.diffusion_rate = params["diffusion_rate"]
        self.turbulence = params["turbulence"]
        self.drift_speed = params["drift_speed"]

    @property
    def brightness(self):
        return self._brightness

    def set_brightness(self, level):
        self._brightness = max(0.0, min(1.0, float(level)))
        # Find closest level
        closest_idx = 0
        min_diff = 999.0
        for i, val in enumerate(BRIGHTNESS_LEVELS):
            diff = abs(val - self._brightness)
            if diff < min_diff:
                min_diff = diff
                closest_idx = i
        self.brightness_idx = closest_idx
        return self._brightness

    def cycle_brightness(self):
        self.brightness_idx = (self.brightness_idx + 1) % len(BRIGHTNESS_LEVELS)
        self._brightness = BRIGHTNESS_LEVELS[self.brightness_idx]
        return self.brightness

    def set_vigor(self, preset_name):
        if preset_name in VIGOR_PRESETS:
            self.vigor = preset_name
            self._load_vigor_params()
        return self.vigor

    def cycle_vigor(self):
        curr_idx = VIGOR_ORDER.index(self.vigor)
        next_idx = (curr_idx + 1) % len(VIGOR_ORDER)
        self.vigor = VIGOR_ORDER[next_idx]
        self._load_vigor_params()
        return self.vigor

    def stoke(self, key_index):
        """Injects heat at key_index and radiates to neighbors."""
        if key_index not in INDEX_TO_XY:
            return
        cx, cy = INDEX_TO_XY[key_index]
        self.heat[cy][cx] = 1.0

        for dy in range(-1, 2):
            for dx in range(-1, 2):
                nx = cx + dx
                ny = cy + dy
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    if abs(dx) + abs(dy) == 1:
                        self.heat[ny][nx] = min(1.0, self.heat[ny][nx] + 0.45)
                    elif abs(dx) == 1 and abs(dy) == 1:
                        self.heat[ny][nx] = min(1.0, self.heat[ny][nx] + 0.20)

    def gust(self):
        """Bellows / wind gust injecting random turbulence spikes."""
        for y in range(self.height):
            for x in range(self.width):
                if random.random() < 0.6:
                    self.heat[y][x] = min(1.0, self.heat[y][x] + random.uniform(0.3, 0.6))

    def step(self, dt=0.03):
        """
        Advances the simulation by dt seconds.
        Returns a list of 16 (R, G, B) tuples ordered by hardware pixel index [0..15].
        """
        self.elapsed_time += dt
        w, h = self.width, self.height
        alpha = self.diffusion_rate

        # 1. Diffusion step
        new_heat = [[0.0 for _ in range(w)] for _ in range(h)]
        for y in range(h):
            for x in range(w):
                neighbors = []
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h:
                        neighbors.append(self.heat[ny][nx])
                avg_neighbor = sum(neighbors) / len(neighbors)
                new_heat[y][x] = (1.0 - alpha) * self.heat[y][x] + alpha * avg_neighbor

        # 2. Wave breathing, turbulence, and decay
        for y in range(h):
            for x in range(w):
                val = new_heat[y][x]
                # Low-frequency wave
                wave = math.sin(self.elapsed_time * self.drift_speed + self.phase[y][x]) * 0.08
                # Random turbulence
                turb = random.uniform(-self.turbulence, self.turbulence)
                # Decay towards baseline
                decay = (self.baseline - val) * self.cooling_rate

                val += decay + wave + turb
                new_heat[y][x] = max(0.0, min(1.0, val))

        self.heat = new_heat

        # 3. Format output for hardware pixel indices 0..15
        output = [(0, 0, 0)] * (w * h)
        bright = self.brightness
        for y in range(h):
            for x in range(w):
                idx = GRID[y][x]
                output[idx] = heat_to_rgb(self.heat[y][x], bright)

        return output
