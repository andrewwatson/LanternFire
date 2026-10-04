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
        self.assertEqual(c0, (90, 2, 0))

        c_mid = heat_to_rgb(0.55, 1.0)
        self.assertEqual(c_mid, (255, 85, 0))

        c_max = heat_to_rgb(1.0, 1.0)
        self.assertEqual(c_max, (255, 215, 15))

        # Test out of bounds inputs get clamped
        c_under = heat_to_rgb(-0.5, 1.0)
        self.assertEqual(c_under, (90, 2, 0))

        c_over = heat_to_rgb(1.5, 1.0)
        self.assertEqual(c_over, (255, 215, 15))

        # Test brightness scaling
        c_dim = heat_to_rgb(1.0, 0.5)
        self.assertEqual(c_dim, (127, 107, 7))

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

    def test_grid_dimension_validation(self):
        # Default 4x4 works
        sim = FireSimulation()
        self.assertEqual(sim.width, 4)
        self.assertEqual(sim.height, 4)

        # Non-4x4 raises ValueError
        with self.assertRaises(ValueError):
            FireSimulation(width=5, height=5)
        with self.assertRaises(ValueError):
            FireSimulation(width=3, height=4)
        with self.assertRaises(ValueError):
            FireSimulation(width=4, height=5)

    def test_setters_and_edge_cases(self):
        sim = FireSimulation()
        # continuous set_brightness
        sim.set_brightness(0.20)
        self.assertAlmostEqual(sim.brightness, 0.20, places=2)
        # Closest preset to 0.20 is index 0 (0.35). Next cycle should pick up index 1 (0.60).
        next_b = sim.cycle_brightness()
        self.assertEqual(next_b, 0.60)
        self.assertEqual(sim.brightness, 0.60)

        # Clamping
        sim.set_brightness(1.5)
        self.assertEqual(sim.brightness, 1.0)
        sim.set_brightness(-0.2)
        self.assertEqual(sim.brightness, 0.0)

        # set_vigor
        sim.set_vigor("BLAZE")
        self.assertEqual(sim.vigor, "BLAZE")
        self.assertEqual(sim.cooling_rate, VIGOR_PRESETS["BLAZE"]["cooling_rate"])
        # invalid vigor ignored
        sim.set_vigor("INVALID_PRESET")
        self.assertEqual(sim.vigor, "BLAZE")

        # stoke with invalid key index should not error
        sim.stoke(99)
        sim.stoke(-1)

        # gust increases heat in at least some cells
        for y in range(4):
            for x in range(4):
                sim.heat[y][x] = 0.1
        sim.gust()
        # total heat should have increased
        total_heat = sum(sim.heat[y][x] for y in range(4) for x in range(4))
        self.assertGreater(total_heat, 1.6)

if __name__ == '__main__':
    unittest.main()
