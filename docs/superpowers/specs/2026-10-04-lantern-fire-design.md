# Design Specification: LanternFire (CircuitPython & HTML Simulator)

**Date:** 2026-10-04  
**Project:** LanternFire  
**Target Hardware:** Adafruit Feather M4 Express (or standard CircuitPython board) + Adafruit NeoTrellis (4x4 Keypad / 16 NeoPixels)  
**Companion Artifact:** Interactive HTML5 Canvas/CSS Simulator (`simulator/index.html`)

---

## 1. Overview & Objectives

LanternFire simulates the organic, warm glow of a small fire and glowing ember bed resting at the bottom of a lantern. Using a 4×4 Adafruit NeoTrellis keypad with 16 RGB NeoPixels, the device runs an autonomous thermal simulation that models natural coal breathing, micro-drafts, heat diffusion across adjacent coals, and tactile "stoking" interactions when the user presses any key.

In addition to the CircuitPython firmware (`code.py`), the project includes a standalone web simulator (`simulator/index.html`) that replicates the identical physics and color palette in the browser, providing a visual playground and design testbed.

---

## 2. Hardware Architecture & Pinout

* **Microcontroller:** Adafruit Feather M4 Express (Microchip ATSAMD51 Cortex M4 running CircuitPython 8.x / 9.x).
* **Display / Keypad:** Adafruit NeoTrellis 4×4 (seesaw driver chip I2C address `0x2E` default, controlling 16 WS2812B NeoPixels and 16 elastomer key switches).
* **Wiring Interface:**
  * `SDA` -> `board.SDA`
  * `SCL` -> `board.SCL`
  * `VIN` -> `3.3V` or `5V` (USB power)
  * `GND` -> `GND`
  * Optional `INT` pin (unused in polling mode for simplicity).

### 2.1 Coordinate & Grid Mapping
The physical NeoTrellis pixel index sequence runs from 0 to 15 mapped into a 4×4 spatial matrix $(x, y) \in [0..3] \times [0..3]$:

```text
Row 0 (y=0):  Key 15 (x=0)   Key 11 (x=1)   Key 7 (x=2)   Key 3 (x=3)
Row 1 (y=1):  Key 14 (x=0)   Key 10 (x=1)   Key 6 (x=2)   Key 2 (x=3)
Row 2 (y=2):  Key 13 (x=0)   Key  9 (x=1)   Key 5 (x=2)   Key 1 (x=3)
Row 3 (y=3):  Key 12 (x=0)   Key  8 (x=1)   Key 4 (x=2)   Key 0 (x=3)
```

Lookup mappings:
* `GRID_XY_TO_INDEX[y][x]` maps $(x, y)$ to the hardware pixel index.
* `INDEX_TO_XY[pixel_index]` maps the 1D index directly back to $(x, y)$ in $O(1)$ time.

---

## 3. Thermal Simulation Engine

Both the CircuitPython firmware and the JavaScript web simulator implement the same continuous thermal model:

### 3.1 State Representation
* A $4 \times 4$ array of floating point values: $H(x, y) \in [0.0, 1.0]$.
* Per-pixel phase offsets $\phi(x, y)$ initialized with pseudo-random offsets for desynchronized breathing.
* System parameters governed by the active **Vigor Preset**:
  * `baseline`: average steady-state heat ($0.25$ to $0.55$).
  * `cooling_rate`: decay factor per frame towards baseline ($0.03$ to $0.08$).
  * `diffusion_rate`: thermal bleed fraction to orthogonal neighbors ($0.12$ to $0.20$).
  * `turbulence`: random jitter range added per tick ($\pm 0.04$ to $\pm 0.12$).
  * `drift_speed`: angular velocity of low-frequency sine breathing.

### 3.2 Frame Update Step (~30–40 Hz)
1. **Diffusion Step:**
   For each cell $(x, y)$, calculate the average heat of its orthogonal in-bounds neighbors $N(x, y)$:
   $$H_{\text{diffused}}(x, y) = (1 - \alpha) \cdot H(x, y) + \frac{\alpha}{|N(x, y)|} \sum_{(nx, ny) \in N(x, y)} H(nx, ny)$$
   where $\alpha$ is `diffusion_rate`.
2. **Breathing & Turbulence:**
   Add sinusoidal oscillation: $\Delta_{\text{wave}} = \sin(\text{time} \cdot \text{drift\_speed} + \phi(x, y)) \cdot 0.08$.
   Add random noise: $\Delta_{\text{turb}} = \text{random}(-1, 1) \cdot \text{turbulence}$.
3. **Cooling & Clamping:**
   Apply linear decay pulling the cell toward `baseline`:
   $$H(x, y) \leftarrow H(x, y) + ( \text{baseline} - H(x, y) ) \cdot \text{cooling\_rate} + \Delta_{\text{wave}} + \Delta_{\text{turb}}$$
   Clamp result strictly to $[0.0, 1.0]$.

### 3.3 Interactive Stoking (Key Press Events)
When a key $(x_0, y_0)$ is pressed (`NeoTrellis.EDGE_RISING` or web `click`/`pointerdown`):
* The impacted cell is immediately set to peak incandescent heat: $H(x_0, y_0) = 1.0$.
* Direct orthogonal neighbors $(x_0 \pm 1, y_0)$ and $(x_0, y_0 \pm 1)$ receive a heat boost: $H(nx, ny) \leftarrow \min(1.0, H(nx, ny) + 0.45)$.
* Diagonals receive a minor heat boost: $H(dx, dy) \leftarrow \min(1.0, H(dx, dy) + 0.20)$.
* The animation frame updates immediately, rendering a brilliant flash that gradually cools through orange into embers.

---

## 4. Color Palette & Optical Mapping

To reproduce genuine blackbody radiation / charcoal fire hues without heavy floating-point color curves, the engine uses multi-stop piecewise linear RGB interpolation:

| Temperature Range $T$ | Visual Appearance | Stop 1 RGB $\to$ Stop 2 RGB |
|---|---|---|
| `0.00 – 0.15` | Dormant Coal / Deep Ruby Ember | `(15, 0, 0)` $\to$ `(60, 4, 0)` |
| `0.15 – 0.45` | Smoldering Ember / Red-Orange | `(60, 4, 0)` $\to$ `(190, 35, 0)` |
| `0.45 – 0.75` | Active Flame / Warm Amber Gold | `(190, 35, 0)` $\to$ `(255, 110, 0)` |
| `0.75 – 1.00` | Incandescent Core / Stoke Flare | `(255, 110, 0)` $\to$ `(255, 230, 130)` |

All final RGB channels are multiplied by the global brightness scale $[0.0, 1.0]$ and rounded to integer values in $[0, 255]$.

---

## 5. Controls & Interaction Scheme

### 5.1 Physical Keypad Shortcuts
While any button can be tapped to stoke coals, the top row keys (Row 0, indices `[15, 11, 7, 3]`) serve functional purposes when pressed:
* **Key 15 (Top-Left): Brightness Cycle**  
  Cycles global brightness through `0.10` (nightlight) $\to$ `0.25` (cozy) $\to$ `0.50` (standard) $\to$ `0.80` (bright).
* **Key 11 (Top-Second): Vigor Preset Cycle**  
  Cycles through 3 atmospheric profiles:
  1. *Gentle Hearth*: Slow breathing, subtle turbulence, lower baseline ($0.28$).
  2. *Campfire*: Active dancing embers, moderate draft ($0.42$).
  3. *Windblown Blaze*: Fast convection, high turbulence, bright vibrant coals ($0.58$).
* **Key 7 (Top-Third): Wind Gust / Bellows**  
  Injects a sweeping gust of heat across multiple random cells, mimicking a sudden breeze in the lantern.
* **Key 3 (Top-Right): Sleep / Standby Toggle**  
  Toggles standby mode. When entering sleep, coals smoothly fade to black over 1.5 seconds. When asleep, `trellis.sync()` runs in low-frequency power-save loop (~10 Hz). Pressing *any* key gently revives the fire back to life.

---

## 6. HTML-Based Simulator (`simulator/index.html`)

A zero-dependency, self-contained single-page application:
* **Visual Presentation:**
  * Photorealistic styling mimicking the physical 4×4 Adafruit NeoTrellis rubber elastomer keypad.
  * Frosted silicone keycap texture with dynamic box-shadow diffusion blur representing light casting onto the lantern floor.
  * Ambient vignette and warm glow reflection on surrounding lantern casing.
* **Interactive Capabilities:**
  * Click/tap keys to stoke individual embers or drag across the grid.
  * Live control drawer with sliders for:
    * Brightness (`0.0` - `1.0`)
    * Vigor presets dropdown (*Gentle Hearth*, *Campfire*, *Windblown Blaze*)
    * Custom sliders: Decay Rate, Diffusion Speed, Turbulence Amount
  * "Gust of Wind" button and "Sleep/Wake" toggle button.
  * Optional "Show Heat Values" overlay toggle (displays float values $0.00 - 1.00$ on each key for debugging).

---

## 7. Verification & Testing

1. **Unit Testing (`tests/test_simulation.py`):**
   * Verifies $4 \times 4$ neighbor calculations on corners, edges, and center cells.
   * Verifies temperature decay and convergence to baseline.
   * Tests RGB interpolation at boundaries ($T=0.0$, $T=0.15$, $T=0.45$, $T=0.75$, $T=1.0$) ensuring outputs stay within $[0, 255]$ with no negative values or overflow.
2. **CircuitPython Compatibility Check:**
   * Syntactically validated against standard Python 3.
   * Asserts absence of non-CircuitPython dependencies.
3. **HTML Simulator Verification:**
   * Verifies clean rendering, responsive event handling, and 60fps animation loop using `requestAnimationFrame`.
