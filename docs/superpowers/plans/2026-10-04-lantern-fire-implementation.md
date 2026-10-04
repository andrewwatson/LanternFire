# LanternFire Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create LanternFire, a CircuitPython 4×4 NeoTrellis application and companion web simulator that simulates glowing fire and breathing embers at the bottom of a lantern with interactive touch-stoking.

**Architecture:** A shared mathematical thermal model (diffusion, low-frequency drift, turbulence, cooling) mapped to a blackbody fire color palette. On hardware, `code.py` handles I2C NeoTrellis events and driving 16 NeoPixels. On the web, `simulator/index.html` provides a standalone zero-dependency interactive simulator with photorealistic silicone key aesthetics.

**Tech Stack:** CircuitPython (Adafruit NeoTrellis, Adafruit BusDevice), Python 3 (unit tests), Vanilla HTML5/CSS3/JavaScript (Simulator).

**Spec:** [`docs/superpowers/specs/2026-10-04-lantern-fire-design.md`](file:///Users/andy/development/projects/active/LanternFire/docs/superpowers/specs/2026-10-04-lantern-fire-design.md)

## Global Constraints

- Hardware: Adafruit NeoTrellis 4×4 keypad (16 NeoPixels, seesaw I2C address `0x2E`) + Feather M4 Express (or standard CircuitPython board with `board.I2C()`).
- Grid orientation: 4×4 horizontal coal bed mapped from hardware indices: Row 0 `[15, 11, 7, 3]`, Row 1 `[14, 10, 6, 2]`, Row 2 `[13, 9, 5, 1]`, Row 3 `[12, 8, 4, 0]`.
- Top-row controls: Key 15 = Brightness cycle, Key 11 = Vigor cycle, Key 7 = Wind gust, Key 3 = Sleep/Wake toggle.
- Color palette stops:
  - $0.00 \to 0.15$: `(15, 0, 0)` to `(60, 4, 0)` (dormant ruby ember)
  - $0.15 \to 0.45$: `(60, 4, 0)` to `(190, 35, 0)` (smoldering orange)
  - $0.45 \to 0.75$: `(190, 35, 0)` to `(255, 110, 0)` (warm flame yellow)
  - $0.75 \to 1.00$: `(255, 110, 0)` to `(255, 230, 130)` (incandescent white-yellow flare)
- Strict bounds: All thermal calculations clamped to $[0.0, 1.0]$, RGB channels clamped to $[0, 255]$ integer values.

---

### Task 1: Thermal Simulation Core & Color Palette (Pure Python & Tests)

**Files:**
- Create: `fire_sim.py`
- Test: `tests/test_simulation.py`

**Interfaces:**
- Produces:
  - `class FireSimulation(width=4, height=4)`:
    - `step(dt: float) -> list[tuple[int, int, int]]`: advances thermal physics and returns 16 RGB tuples mapped to hardware indices `[0..15]`.
    - `stoke(key_index: int)`: injects max heat at key coordinate and radiates heat to neighbors.
    - `gust()`: injects a wave of heat across random cells.
    - `set_brightness(level: float)`: updates global brightness scaler `[0.0, 1.0]`.
    - `cycle_brightness() -> float`: cycles brightness presets.
    - `set_vigor(preset_name: str)`: updates simulation parameters (`GENTLE`, `CAMPFIRE`, `BLAZE`).
    - `cycle_vigor() -> str`: cycles through vigor presets.
    - `heat_to_rgb(heat: float, brightness: float) -> tuple[int, int, int]`: maps heat to clamped RGB tuple.
    - `GRID`: 2D list `[[15, 11, 7, 3], ...]`.
    - `INDEX_TO_XY`: dict mapping hardware pixel index to `(x, y)`.

- [ ] **Step 1: Write the failing unit tests for coordinate mapping, thermal decay, and color interpolation**

Create `tests/test_simulation.py`:
```python
import unittest
from fire_sim import (
    FireSimulation,
    heat_to_rgb,
    INDEX_TO_XY,
    GRID,
    VIGOR_PRESETS
)

class TestFireSimulation(unittest.TestCase):
    def test_grid_mappings(self):
        self.assertEqual(GRID[0], [15, 11, 7, 3])
        self.assertEqual(GRID[3], [12, 8, 4, 0])
        self.assertEqual(INDEX_TO_XY[15], (0, 0))
        self.assertEqual(INDEX_TO_XY[0], (3, 3))
        self.assertEqual(len(INDEX_TO_XY), 16)

    def test_heat_to_rgb_clamping_and_stops(self):
        # Test boundary values
        c0 = heat_to_rgb(0.0, 1.0)
        self.assertEqual(c0, (15, 0, 0))

        c_mid = heat_to_rgb(0.45, 1.0)
        self.assertEqual(c_mid, (190, 35, 0))

        c_max = heat_to_rgb(1.0, 1.0)
        self.assertEqual(c_max, (255, 230, 130))

        # Test out of bounds inputs get clamped
        c_under = heat_to_rgb(-0.5, 1.0)
        self.assertEqual(c_under, (15, 0, 0))

        c_over = heat_to_rgb(1.5, 1.0)
        self.assertEqual(c_over, (255, 230, 130))

        # Test brightness scaling
        c_dim = heat_to_rgb(1.0, 0.5)
        self.assertEqual(c_dim, (127, 115, 65))

        # Channel bounds
        for heat in [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0]:
            r, g, b = heat_to_rgb(heat, 0.8)
            self.assertTrue(0 <= r <= 255)
            self.assertTrue(0 <= g <= 255)
            self.assertTrue(0 <= b <= 255)

    def test_stoke_injects_heat_and_diffuses(self):
        sim = FireSimulation()
        # Set all heat to 0
        for y in range(4):
            for x in range(4):
                sim.heat[y][x] = 0.0

        # Stoke center key 6 (x=2, y=1)
        sim.stoke(6)
        # Center should be 1.0
        self.assertEqual(sim.heat[1][2], 1.0)
        # Direct neighbors should have heat ~0.45
        self.assertAlmostEqual(sim.heat[1][1], 0.45, places=2)
        self.assertAlmostEqual(sim.heat[1][3], 0.45, places=2)
        self.assertAlmostEqual(sim.heat[0][2], 0.45, places=2)
        self.assertAlmostEqual(sim.heat[2][2], 0.45, places=2)

    def test_simulation_step_returns_16_clamped_pixels(self):
        sim = FireSimulation()
        pixels = sim.step(dt=0.03)
        self.assertEqual(len(pixels), 16)
        for rgb in pixels:
            self.assertEqual(len(rgb), 3)
            for ch in rgb:
                self.assertTrue(0 <= ch <= 255)

    def test_brightness_and_vigor_cycles(self):
        sim = FireSimulation()
        b_init = sim.brightness
        b_next = sim.cycle_brightness()
        self.assertNotEqual(b_init, b_next)

        v_init = sim.vigor
        v_next = sim.cycle_vigor()
        self.assertNotEqual(v_init, v_next)
        self.assertIn(v_next, VIGOR_PRESETS)

if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests/test_simulation.py`  
Expected: FAIL with `ModuleNotFoundError: No module named 'fire_sim'`

- [ ] **Step 3: Implement `fire_sim.py`**

Create `fire_sim.py`:
```python
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
        self.width = width
        self.height = height
        self.heat = [[0.3 for _ in range(width)] for _ in range(height)]
        self.phase = [[random.uniform(0, 2 * math.pi) for _ in range(width)] for _ in range(height)]
        self.elapsed_time = 0.0

        self.brightness_idx = 1  # Default 0.25 (cozy)
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
        return BRIGHTNESS_LEVELS[self.brightness_idx]

    def set_brightness(self, level):
        # Find closest level
        closest_idx = 0
        min_diff = 999.0
        for i, val in enumerate(BRIGHTNESS_LEVELS):
            diff = abs(val - level)
            if diff < min_diff:
                min_diff = diff
                closest_idx = i
        self.brightness_idx = closest_idx
        return self.brightness

    def cycle_brightness(self):
        self.brightness_idx = (self.brightness_idx + 1) % len(BRIGHTNESS_LEVELS)
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests/test_simulation.py`  
Expected: `Ran 5 tests in ...s OK`

- [ ] **Step 5: Commit**

```bash
git add fire_sim.py tests/test_simulation.py
git commit -m "feat: implement fire simulation core and unit tests"
```

---

### Task 2: CircuitPython Firmware (`code.py`)

**Files:**
- Create: `code.py`

**Interfaces:**
- Consumes:
  - `fire_sim.py` (`FireSimulation`, `INDEX_TO_XY`, `GRID`)
  - `adafruit_neotrellis.neotrellis.NeoTrellis`
  - `board.I2C()`
- Produces:
  - Microcontroller main execution loop running at ~30–40 Hz.
  - Event callbacks for key stoking and control keys (Keys 15, 11, 7, 3).
  - Standby / sleep mode with low-power polling and wake-on-any-key.

- [ ] **Step 1: Write `code.py`**

Create `code.py`:
```python
"""
LanternFire - CircuitPython Fire Simulation for Adafruit NeoTrellis 4x4
Simulates organic glowing coals and breathing embers inside a lantern.
"""
import time
import board
from adafruit_neotrellis.neotrellis import NeoTrellis
from fire_sim import FireSimulation, INDEX_TO_XY, heat_to_rgb

# Initialize I2C Bus for NeoTrellis with safe retry
print("LanternFire starting up...")
i2c_bus = None
trellis = None

while trellis is None:
    try:
        i2c_bus = board.I2C()  # uses board.SCL and board.SDA
        trellis = NeoTrellis(i2c_bus)
        print("NeoTrellis connected successfully on I2C address 0x2E.")
    except Exception as err:
        print(f"Waiting for NeoTrellis on I2C... ({err})")
        time.sleep(1.0)

# Hardware brightness is kept at 1.0; brightness is controlled via color scaling in fire_sim
trellis.brightness = 1.0

# Initialize Fire Simulation
sim = FireSimulation()
is_sleeping = False
sleep_fade = 1.0

def handle_key(event):
    global is_sleeping, sleep_fade
    # Catch key on initial press (EDGE_RISING)
    if event.edge == NeoTrellis.EDGE_RISING:
        key_num = event.number
        print(f"Key press: {key_num}")

        # If asleep, ANY key press wakes the lantern
        if is_sleeping:
            is_sleeping = False
            print("Lantern waking up!")
            return

        # Top-Row Shortcut Controls
        if key_num == 15:  # Top-Left: Brightness cycle
            b = sim.cycle_brightness()
            print(f"Brightness set to: {int(b * 100)}%")
            # Quick flash at key 15
            trellis.pixels[15] = (255, 255, 255)
            time.sleep(0.05)
            return

        elif key_num == 11:  # Top-Second: Vigor cycle
            v = sim.cycle_vigor()
            print(f"Fire vigor set to: {v}")
            # Quick flash at key 11
            trellis.pixels[11] = (255, 180, 50)
            time.sleep(0.05)
            return

        elif key_num == 7:  # Top-Third: Wind gust / bellows
            print("Bellows gust!")
            sim.gust()
            return

        elif key_num == 3:  # Top-Right: Sleep / Standby toggle
            print("Lantern going to sleep...")
            is_sleeping = True
            return

        # Default action for all keys: Stoke the coals!
        sim.stoke(key_num)

# Register callbacks for all 16 keys
for i in range(16):
    trellis.activate_key(i, NeoTrellis.EDGE_RISING)
    trellis.activate_key(i, NeoTrellis.EDGE_FALLING)
    trellis.callbacks[i] = handle_key

# Warm startup flare sequence
print("Lighting lantern...")
for i in range(16):
    trellis.pixels[i] = (20, 2, 0)
time.sleep(0.3)
sim.gust()

last_tick = time.monotonic()

while True:
    try:
        # Sync keypad events
        trellis.sync()
    except OSError as e:
        # Gracefully handle momentary I2C bus glitch
        time.sleep(0.05)
        continue

    now = time.monotonic()
    dt = now - last_tick
    last_tick = now

    if not is_sleeping:
        # Active burning animation
        pixel_colors = sim.step(dt if dt < 0.1 else 0.03)
        for i in range(16):
            trellis.pixels[i] = pixel_colors[i]
        time.sleep(0.025)  # Target ~35 FPS
    else:
        # Sleep mode: fade to black and idle slowly
        if sleep_fade > 0.0:
            sleep_fade = max(0.0, sleep_fade - 0.1)
            for i in range(16):
                c = trellis.pixels[i]
                trellis.pixels[i] = (int(c[0] * 0.7), int(c[1] * 0.7), int(c[2] * 0.7))
            time.sleep(0.05)
        else:
            for i in range(16):
                trellis.pixels[i] = (0, 0, 0)
            time.sleep(0.1)  # Low-power polling
            sleep_fade = 1.0  # Reset for when awakened
```

- [ ] **Step 2: Validate syntax and imports**

Run: `python3 -m py_compile code.py`  
Expected: Successful compile with exit code 0.

- [ ] **Step 3: Commit**

```bash
git add code.py
git commit -m "feat: implement CircuitPython firmware main loop and event handling"
```

---

### Task 3: Interactive HTML/CSS/JS Simulator (`simulator/index.html`)

**Files:**
- Create: `simulator/index.html`

**Features:**
- Responsive dark lantern enclosure styling with realistic frosted silicone rubber keycaps.
- 4×4 grid matching the NeoTrellis physical coordinates and layout.
- Photorealistic glow with radial ambient backlight spreading into the lantern base.
- Identical thermal physics (diffusion, breathing wave, turbulence, cooling) and color palette in JavaScript.
- Direct pointer/mouse interaction: click any key to stoke coals, click top-row keys for shortcuts.
- Control drawer: Brightness slider, Vigor preset selector, custom parameter sliders, "Gust of Wind" button, "Sleep/Wake" button, and "Show Heat Values" debug overlay.

- [ ] **Step 1: Create `simulator/index.html`**

Create `simulator/index.html` containing HTML, CSS, and JS in a clean, self-contained single-page application.

- [ ] **Step 2: Verify HTML simulator locally**

Run: `python3 -m http.server 8000 --directory simulator & PID=$!; sleep 1; curl -I http://localhost:8000/; kill $PID`  
Expected: `HTTP/1.0 200 OK`

- [ ] **Step 3: Commit**

```bash
git add simulator/index.html
git commit -m "feat: add interactive HTML5/CSS3 NeoTrellis lantern fire simulator"
```

---

### Task 4: Documentation, Setup Guide, and Git Ignore

**Files:**
- Create: `README.md`
- Create: `.gitignore`

**Contents:**
- `README.md`:
  - Overview & Lantern aesthetic.
  - Hardware bill of materials (Adafruit Feather M4 Express, NeoTrellis 4×4).
  - Pinout & Wiring diagram.
  - CircuitPython library installation (`adafruit_neotrellis`, `adafruit_bus_device`).
  - Keypad controls guide (Stoking, Brightness, Vigor presets, Wind gust, Sleep).
  - Web simulator usage.
- `.gitignore`: Ignore `.DS_Store`, `__pycache__/`, `*.pyc`.

- [ ] **Step 1: Write `README.md` and `.gitignore`**
- [ ] **Step 2: Run all tests to ensure complete project health**

Run: `python3 -m unittest discover tests`  
Expected: All tests pass.

- [ ] **Step 3: Commit**

```bash
git add README.md .gitignore
git commit -m "docs: add setup instructions, hardware guide, and controls documentation"
```

---

## Plan Review Checklist

1. **Spec Coverage:**
   - Thermal simulation engine: Task 1 (`fire_sim.py`).
   - Hardware mapping & NeoTrellis callbacks: Task 2 (`code.py`).
   - Color stops ($0.00$ to $1.00$): Task 1 (`heat_to_rgb`).
   - Top-row controls (Keys 15, 11, 7, 3): Task 2 & Task 3.
   - HTML web simulator: Task 3 (`simulator/index.html`).
   - Unit tests & verification: Task 1 & Task 4.
2. **No Placeholders:** All equations, color stops, methods, and files fully written out.
3. **Type and interface consistency:** `FireSimulation`, `heat_to_rgb`, `INDEX_TO_XY`, `GRID` match identically across test, code, and web simulator.
