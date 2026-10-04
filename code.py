"""
LanternFire - CircuitPython Fire Simulation for Adafruit NeoTrellis 4x4
Simulates organic glowing coals and breathing embers inside a lantern.
"""
import time
import board
from adafruit_neotrellis.neotrellis import NeoTrellis
from fire_sim import FireSimulation

# Initialize I2C Bus for NeoTrellis with safe retry
print("LanternFire starting up...")
i2c_bus = None
trellis = None

while trellis is None:
    try:
        if i2c_bus is None:
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
            sleep_fade = 1.0
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
            sleep_fade = 1.0
            return

        # Default action for all keys: Stoke the coals!
        sim.stoke(key_num)

# Register callbacks for all 16 keys (only EDGE_RISING needed)
for i in range(16):
    trellis.activate_key(i, NeoTrellis.EDGE_RISING)
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
            if sleep_fade == 0.0:
                for i in range(16):
                    trellis.pixels[i] = (0, 0, 0)
        else:
            time.sleep(0.1)  # Low-power polling
