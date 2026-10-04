# LanternFire 🏮🔥

> **Autonomous glowing embers and fire simulation for Adafruit NeoTrellis 4×4 running CircuitPython, accompanied by a photorealistic web simulator.**

LanternFire transforms an Adafruit NeoTrellis 4×4 keypad into the glowing bed of coals at the bottom of an iron lantern. Rather than relying on simple looping flame animations or hardcoded color frames, LanternFire runs an autonomous 2D thermal simulation kernel with natural heat diffusion, desynchronized wave breathing, micro-draft turbulence, and interactive tactile "stoking."

Pressing any key feeds fuel and heat into that coal, radiating warmth outwards across neighboring embers before gradually cooling back down into rich ruby-orange embers.

---

## Features

- **Continuous Thermal Physics Engine**: A $4 \times 4$ cellular heat model calculating real-time diffusion, baseline cooling decay, harmonic sine breathing waves, and atmospheric micro-turbulence at ~35 FPS.
- **Organic Ember Color Palette**: 4-stop piecewise linear interpolation reproducing authentic glowing ember hues—from deep ruby coals (`#5A0200`) through smoldering flame red (`#DC1900`), fiery orange (`#FF5500`), and warm amber (`#FF9B00`) up to radiant incandescent gold (`#FFD70F`) with no washed-out white.
- **Tactile Stoking**: Tapping any key instantly ignites that cell to peak heat ($1.0$) and conducts thermal energy to adjacent orthogonal ($+0.45$) and diagonal ($+0.20$) neighbors.
- **Atmospheric Fire Vigor Presets**:
  - **Gentle Hearth**: Soft, soothing smolder with low turbulence and quiet breathing.
  - **Campfire**: Lively dancing embers with balanced convection and crackling drafts.
  - **Windblown Blaze**: Vibrant, energetic blaze with high turbulence and fast diffusion.
- **Top-Row Quick Controls**: Instant hardware shortcuts for Brightness, Fire Vigor presets, Wind Gust / Bellows, and Sleep / Standby mode.
- **Graceful Sleep & Wake**: Standby mode fades coals to black and switches to low-power polling (~10 Hz); tapping *any* key gently wakes the lantern back to life.
- **Zero-Dependency Web Simulator**: A standalone HTML5/CSS3/JavaScript browser simulator (`simulator/index.html`) featuring frosted elastomer keycaps, interactive stoking, live physics sliders, and debug heat overlays.
- **Robust Hardware Fault Tolerance**: Protected I2C reconnection loop, I2C bus error recovery, and strict channel clamping `[0, 255]`.

---

## Hardware Bill of Materials (BOM)

| Component | Description | Source / Notes |
|---|---|---|
| **Microcontroller** | Adafruit Feather M4 Express (ATSAMD51 Cortex-M4) or any CircuitPython board with I2C | Runs CircuitPython 8.x or 9.x |
| **Keypad & LEDs** | Adafruit NeoTrellis 4×4 Keypad (PID 3954) | 16 RGB NeoPixels + 16 elastomer buttons (I2C address `0x2E`) |
| **Keycaps** | Silicone Elastomer 4×4 Button Keypad (PID 1611) | Frosted silicone pad fitting directly over NeoTrellis |
| **Wiring** | 4-pin JST-PH / STEMMA / Qwiic cable or 4 female-to-female jumper wires | SDA, SCL, 3.3V/5V, GND |
| **Power** | Micro-USB or USB-C cable (or 3.7V LiPo battery for portable lantern) | Powers microcontroller and NeoPixels |
| **Enclosure** *(Optional)* | Vintage glass-paned lantern, hurricane lamp, or 3D-printed housing | Mounts keypad horizontally at lantern base |

---

## Wiring & Pinout Guide

Connect the 4-pin I2C header on the Adafruit NeoTrellis to your Feather / microcontroller board:

```
+------------------------+                 +------------------------+
|  Adafruit NeoTrellis   |                 | Adafruit Feather M4    |
|          4x4           |                 |        Express         |
|                        |                 |                        |
|   [VIN] ---------------+-----------------> [3.3V] or [USB / 5V]   |
|   [GND] ---------------+-----------------> [GND]                  |
|   [SDA] ---------------+-----------------> [SDA]                  |
|   [SCL] ---------------+-----------------> [SCL]                  |
|   [INT] (optional)     |                 | (Unused - polling)     |
+------------------------+                 +------------------------+
```

### Pinout Table

| NeoTrellis Pin | Feather M4 Pin | Signal Description |
|---|---|---|
| **`VIN`** | **`3.3V`** or **`USB` (5V)** | Power input (3.3V logic compatible, 5V for brighter LEDs) |
| **`GND`** | **`GND`** | Common ground |
| **`SDA`** | **`SDA`** (`board.SDA`) | I2C Data line (default seesaw address `0x2E`) |
| **`SCL`** | **`SCL`** (`board.SCL`) | I2C Clock line |
| **`INT`** | *Not connected* | Hardware interrupt (optional, polling mode used) |

> [!NOTE]
> The Adafruit NeoTrellis comes preconfigured with default I2C address `0x2E`. If you have bridged any address jumpers on the back of the board, adjust the `NeoTrellis(i2c_bus, addr=...)` call in `code.py`.

---

## CircuitPython Installation & Quick Deploy

### Option A: One-Command Copy Script (Easiest)
With your CircuitPython board plugged in over USB:
```bash
./copy_to_circuitpy.sh
```
This automatically detects `/Volumes/CIRCUITPY`, copies `code.py`, `fire_sim.py`, and all required libraries (`adafruit_bus_device`, `adafruit_neotrellis`, `adafruit_seesaw`) into `CIRCUITPY/lib/`, flushes the disk buffers, and restarts the fire animation!

### Option B: Drag-and-Drop via Finder / Explorer
All code and dependencies are pre-assembled in [`deploy/CIRCUITPY/`](file:///Users/andy/development/projects/active/LanternFire/deploy/CIRCUITPY).
Simply open the folder:
```bash
open deploy/CIRCUITPY
```
Select everything inside (`code.py`, `fire_sim.py`, and `lib/`) and drag it directly onto your `CIRCUITPY` drive.

### Directory Layout on CIRCUITPY
```text
CIRCUITPY/
├── code.py              <-- Firmware entry point & I2C/keypad handler
├── fire_sim.py          <-- Thermal simulation kernel & color mapper
└── lib/
    ├── adafruit_bus_device/
    ├── adafruit_neotrellis/
    └── adafruit_seesaw/
```

Once copied, CircuitPython automatically soft-reboots and immediately begins illuminating the lantern!

### 4. Monitor via Serial Console (Optional)
Connect via any serial terminal at `115200` baud to view diagnostic messages:
```bash
# macOS / Linux screen
screen /dev/cu.usbmodem* 115200

# or tio
tio /dev/cu.usbmodem*
```

---

## Keypad Controls & Spatial Layout

The physical 4×4 NeoTrellis hardware indices are mapped into a coordinate grid $(x, y) \in [0..3] \times [0..3]$:

```
                  +--------+--------+--------+--------+
      Row 0 (y=0) | Key 15 | Key 11 | Key  7 | Key  3 |  <-- Control Bar
                  +--------+--------+--------+--------+
      Row 1 (y=1) | Key 14 | Key 10 | Key  6 | Key  2 |  <-- Ember Bed
                  +--------+--------+--------+--------+
      Row 2 (y=2) | Key 13 | Key  9 | Key  5 | Key  1 |  <-- Ember Bed
                  +--------+--------+--------+--------+
      Row 3 (y=3) | Key 12 | Key  8 | Key  4 | Key  0 |  <-- Ember Bed
                  +--------+--------+--------+--------+
                     x=0      x=1      x=2      x=3
```

### Controls Cheatsheet

| Key | Position | Function | Behavior |
|---|---|---|---|
| **Key 15** | Row 0, Col 0 (Top-Left) | **Brightness Cycle** | Cycles brightness: **35%** (dim) $\to$ **60%** (warm) $\to$ **85%** (high) $\to$ **100%** (full radiant default). Brief gold flash confirms change. |
| **Key 11** | Row 0, Col 1 (Top-Second) | **Vigor Preset Cycle** | Cycles atmospheric mode: **Gentle Hearth** $\to$ **Campfire** $\to$ **Windblown Blaze**. Brief amber flash confirms change. |
| **Key 7** | Row 0, Col 2 (Top-Third) | **Wind Gust / Bellows** | Sweeps a sudden gust across the fire, injecting random heat spikes into ~60% of the coals. |
| **Key 3** | Row 0, Col 3 (Top-Right) | **Sleep / Standby Mode** | Smoothly fades the lantern to black over ~1.5 seconds. Switches to low-frequency power-save polling. |
| **Any Key** | Keys 0 – 15 | **Stoke Coals & Revive** | **When burning:** Stokes that coordinate to $1.0$ incandescent flare and radiates warmth to neighbors.<br>**When asleep:** Instantly awakens the lantern back to glowing embers! |

---

## Thermal Simulation & Color Science

LanternFire combines cellular automata principles with harmonic physics to avoid repetitive canned loops:

### 1. Thermal Physics Pipeline
Every frame (~35 FPS):
1. **Thermal Diffusion**: Heat spreads outward to orthogonal neighbors according to $\alpha = \text{diffusion\_rate}$:
   $$H_{\text{diffused}}(x, y) = (1 - \alpha) \cdot H(x, y) + \frac{\alpha}{|N|} \sum_{n \in N} H(n)$$
2. **Sine Breathing**: Desynchronized phase offsets $\phi(x, y)$ create gentle, breathing swells:
   $$\Delta_{\text{wave}} = \sin(\text{time} \cdot \text{drift\_speed} + \phi(x, y)) \cdot 0.08$$
3. **Draft Turbulence**: Randomized micro-turbulences simulate moving air drafts:
   $$\Delta_{\text{turb}} = \text{random}(-\text{turbulence}, +\text{turbulence})$$
4. **Baseline Cooling**: Heat gently decays toward the atmospheric preset baseline:
   $$H(x, y) \leftarrow H(x, y) + (\text{baseline} - H(x, y)) \cdot \text{cooling\_rate} + \Delta_{\text{wave}} + \Delta_{\text{turb}}$$
5. **Clamping**: Heat values are strictly bounded within $[0.0, 1.0]$.

### 2. Multi-Stop Optical Color Palette
Heat values $T \in [0.0, 1.0]$ are mapped to RGB through 4 color stops, scaled by global brightness:

| Heat Range $T$ | State / Appearance | Stop 1 RGB $\to$ Stop 2 RGB | Hex Swatch |
|---|---|---|---|
| `0.00 – 0.25` | Deep Ruby Ember $\to$ Vibrant Fire Red | `(90, 2, 0)` $\to$ `(220, 25, 0)` | `#5A0200` $\to$ `#DC1900` |
| `0.25 – 0.55` | Vibrant Fire Red $\to$ Fiery Orange | `(220, 25, 0)` $\to$ `(255, 85, 0)` | `#DC1900` $\to$ `#FF5500` |
| `0.55 – 0.80` | Fiery Orange $\to$ Warm Golden Amber | `(255, 85, 0)` $\to$ `(255, 155, 0)` | `#FF5500` $\to$ `#FF9B00` |
| `0.80 – 1.00` | Golden Amber $\to$ Incandescent Radiant Gold | `(255, 155, 0)` $\to$ `(255, 215, 15)` | `#FF9B00` $\to$ `#FFD70F` |

---

## Interactive Web Simulator

The project includes a standalone web simulator located in `simulator/index.html`. It runs the exact same mathematical model and color lookup in JavaScript, wrapped in an interactive lantern-styled UI.

### Launching the Simulator

#### Option A: Direct Browser File
Open `simulator/index.html` in any modern web browser:
```bash
# macOS
open simulator/index.html

# Linux
xdg-open simulator/index.html

# Windows
start simulator/index.html
```

#### Option B: Local HTTP Server
Run Python's built-in web server:
```bash
python3 -m http.server 8000 --directory simulator
```
Then navigate to: [http://localhost:8000](http://localhost:8000)

### Web Simulator Capabilities
- **Tactile Keypad Grid**: Photorealistic frosted silicone keycaps with dynamic diffused glow and lantern floor shadows. Click or drag to stoke coals.
- **Top Row Controls**: Click the top keys or use the on-screen buttons to cycle brightness, switch vigor presets, blow bellows gusts, or sleep/wake.
- **Interactive Tuning Drawer**: Live sliders to experiment with simulation parameters in real time:
  - Global Brightness (`0% - 100%`)
  - Vigor Presets dropdown (*Gentle Hearth*, *Campfire*, *Windblown Blaze*)
  - Baseline Heat, Cooling Rate, Diffusion Rate, Turbulence Amount, and Drift Speed
- **Debug Heat Values Overlay**: Toggle the **"Show Heat Values"** checkbox to display live numerical heat coordinates ($0.00 - 1.00$) directly on each keypad button.
- **Diagnostics Panel**: Displays live FPS (~60 FPS), active mode, heat energy average, and elapsed simulation time.

---

## Verification & Unit Testing

The core thermal simulation and color mapper can be tested on standard desktop Python 3 without requiring hardware or CircuitPython libraries:

```bash
python3 -m unittest discover tests -v
```

### Test Suite Coverage
- **`test_grid_mappings`**: Validates the spatial matrix mapping and $O(1)$ hardware index bidirectional translation.
- **`test_heat_to_rgb_clamping_and_stops`**: Confirms color boundary fidelity, channel clamping `[0, 255]`, and brightness scaling.
- **`test_stoke_injects_heat_and_diffuses`**: Verifies thermal conductance to orthogonal ($+0.45$) and diagonal ($+0.20$) neighbors.
- **`test_simulation_step_returns_16_clamped_pixels`**: Checks frame step dimensions, data types, and bounds.
- **`test_brightness_and_vigor_cycles`**: Validates state transitions across presets.
- **`test_setters_and_edge_cases`**: Tests out-of-bounds keys, invalid vigor names, and bellows gust energy injection.

---

## Repository Structure

```
LanternFire/
├── code.py                # CircuitPython hardware entrypoint & NeoTrellis loop
├── fire_sim.py            # Thermal simulation kernel & color palette
├── simulator/
│   └── index.html         # Interactive zero-dependency HTML5/CSS3 simulator
├── tests/
│   └── test_simulation.py # Comprehensive unit test suite
├── docs/                  # Architecture & design specifications
├── .gitignore             # Git ignore patterns
└── README.md              # Project documentation and setup guide
```

---

## License

MIT License. Designed with warm embers and crackling fires for the maker community.
