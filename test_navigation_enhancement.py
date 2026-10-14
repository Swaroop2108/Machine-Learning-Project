import unittest
import json
import urllib.request

class TestNavigationEnhancement(unittest.TestCase):
    BASE_URL = "http://127.0.0.1:8000"

    def test_multi_turn_route_steps(self):
        """Test a multi-turn route returns human-readable instructions with road names and maneuvers."""
        payload = {
            "source": "Miyapur",
            "destination": "Kukatpally",
            "departure_datetime": "2026-10-14T10:00:00",
            "travel_mode": "DRIVE",
            "traffic_condition": "Moderate"
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.BASE_URL}/api/google-route",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            self.assertEqual(resp.getcode(), 200)
            res = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(res.get("success"))
            gr = res.get("google_route", {})
            steps = gr.get("steps", [])
            geom = gr.get("route_geometry", [])

            self.assertGreater(len(geom), 50, "Route geometry must be a rich continuous polyline")
            self.assertGreater(len(steps), 3, "Route should have multiple turn-by-turn steps")

            # Check instructions quality
            for s in steps:
                instr = s.get("instruction", "")
                self.assertTrue(len(instr) > 0, "Instruction cannot be empty")
                # Must NOT contain vague phrasing
                self.assertNotIn("Travel towards destination", instr)
                # Verify coordinates
                loc = s.get("location")
                self.assertIsInstance(loc, list)
                self.assertEqual(len(loc), 2)
                self.assertTrue(-90 <= loc[0] <= 90)
                self.assertTrue(-180 <= loc[1] <= 180)

            # Check arrival instruction
            last_step = steps[-1]
            self.assertIn("arrived", last_step["instruction"].lower())

            # Check first step heading / compass
            first_step = steps[0]
            self.assertTrue(
                "Head" in first_step["instruction"] or "Continue" in first_step["instruction"],
                f"First step should be departure: {first_step['instruction']}"
            )

    def test_highway_route_geometry_and_steps(self):
        """Test long-distance highway route (Hyderabad to Vijayawada) has detailed polyline and steps."""
        payload = {
            "source": "Hyderabad",
            "destination": "Vijayawada",
            "departure_datetime": "2026-10-14T09:00:00",
            "travel_mode": "DRIVE",
            "traffic_condition": "Low"
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.BASE_URL}/api/google-route",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            self.assertEqual(resp.getcode(), 200)
            res = json.loads(resp.read().decode("utf-8"))
            gr = res.get("google_route", {})
            geom = gr.get("route_geometry", [])
            steps = gr.get("steps", [])

            self.assertGreater(len(geom), 500, "Highway route should have high-resolution polyline")
            self.assertGreater(len(steps), 5, "Highway route should contain sequential maneuvers")

            # Check for road names in highway route (e.g. NH 65, Vijayawada Road, etc.)
            road_names = [s.get("road_name") for s in steps if s.get("road_name")]
            self.assertGreater(len(road_names), 0, "Steps should identify actual road names")

if __name__ == "__main__":
    unittest.main()
