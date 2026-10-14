import unittest
import json
import os
import urllib.request
import urllib.error

class TestMapFix(unittest.TestCase):
    BASE_URL = "http://127.0.0.1:8000"

    def test_01_backend_google_route_valid(self):
        """Test valid route search returns real coordinates, distance, and geometry."""
        payload = {
            "source": "Hyderabad",
            "destination": "Vijayawada",
            "departure_datetime": "2026-10-14T09:00:00",
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
            self.assertTrue(res.get("success"), "Route request should succeed")
            gr = res.get("google_route", {})
            self.assertEqual(gr.get("source"), "Hyderabad")
            self.assertEqual(gr.get("destination"), "Vijayawada")
            self.assertGreater(gr.get("distance_km", 0), 200)
            self.assertGreater(gr.get("duration_minutes", 0), 100)
            
            # Check source and destination coordinates
            src_coords = gr.get("source_coordinates")
            dest_coords = gr.get("destination_coordinates")
            self.assertEqual(len(src_coords), 2)
            self.assertEqual(len(dest_coords), 2)
            self.assertAlmostEqual(src_coords[0], 17.3850, places=2)
            self.assertAlmostEqual(dest_coords[0], 16.5062, places=2)
            
            # Check route geometry coordinates format [[lat, lon], ...]
            geom = gr.get("route_geometry", [])
            self.assertGreater(len(geom), 10)
            for pt in geom[:5]:
                self.assertIsInstance(pt, list)
                self.assertEqual(len(pt), 2)
                self.assertTrue(-90 <= pt[0] <= 90, f"Invalid latitude: {pt[0]}")
                self.assertTrue(-180 <= pt[1] <= 180, f"Invalid longitude: {pt[1]}")

    def test_02_backend_google_route_repeated_search(self):
        """Test repeated search with different cities returns updated coordinates."""
        payload = {
            "source": "Hyderabad",
            "destination": "Bengaluru",
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
        with urllib.request.urlopen(req, timeout=10) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(res.get("success"))
            gr = res.get("google_route", {})
            self.assertEqual(gr.get("destination"), "Bengaluru")
            self.assertGreater(gr.get("distance_km", 0), 450)
            dest_coords = gr.get("destination_coordinates")
            self.assertAlmostEqual(dest_coords[0], 12.9716, places=2)

    def test_03_backend_route_error_handling(self):
        """Test backend handles identical locations or invalid inputs cleanly without crashing."""
        # Identical location
        payload = {
            "source": "Hyderabad",
            "destination": "Hyderabad",
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
        try:
            urllib.request.urlopen(req, timeout=10)
            self.fail("Identical locations should return HTTP 400")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 400)

    def test_04_html_map_structure_and_leaflet_assets(self):
        """Test frontend/index.html includes Leaflet CSS, Leaflet JS, and #map container."""
        with open("frontend/index.html", "r", encoding="utf-8") as f:
            html = f.read()
        
        self.assertIn("leaflet@1.9.4/dist/leaflet.css", html, "Leaflet CSS must be linked in index.html")
        self.assertIn("leaflet@1.9.4/dist/leaflet.js", html, "Leaflet JS must be linked in index.html")
        self.assertIn('id="map"', html, "#map container element must exist in index.html")
        self.assertIn('class="google-map-container"', html, "Map container class must be present")
        self.assertNotIn("maps.googleapis.com", html, "No Google Maps API allowed")

    def test_05_css_map_dimensions(self):
        """Test frontend/css/style.css explicitly sets non-zero height and width on map container."""
        with open("frontend/css/style.css", "r", encoding="utf-8") as f:
            css = f.read()
        
        self.assertIn("#map", css, "CSS must style #map")
        self.assertIn("min-height: 440px", css, "CSS must define min-height for map")
        self.assertIn("height: 440px", css, "CSS must define explicit height for map")
        self.assertIn("width: 100%", css, "CSS must define width for map")

    def test_06_script_map_invalidation_and_route_rendering(self):
        """Test frontend/js/script.js includes invalidateSize, tile error handling, and bounds fitting."""
        with open("frontend/js/script.js", "r", encoding="utf-8") as f:
            js = f.read()
        
        self.assertIn("leafletMap.invalidateSize(true)", js, "script.js must call invalidateSize(true)")
        self.assertIn("initLeafletMap()", js, "script.js must contain initLeafletMap function")
        self.assertIn("renderLeafletMapRoute", js, "script.js must contain renderLeafletMapRoute function")
        self.assertIn("handleRouteCalculationError", js, "script.js must handle route calculation errors")
        self.assertIn("tileerror", js, "script.js must handle tile loading errors separately")
        self.assertIn("fitBounds", js, "script.js must fit bounds to route/markers")
        self.assertIn("L.tileLayer", js, "script.js must create OpenStreetMap tile layer")
        self.assertIn("openstreetmap.org", js, "script.js must use OpenStreetMap tile URL")

    def test_07_auth_view_map_invalidation(self):
        """Test frontend/js/auth.js invalidates map size when switching to planner or navigation."""
        with open("frontend/js/auth.js", "r", encoding="utf-8") as f:
            js = f.read()
        
        self.assertIn("leafletMap.invalidateSize(true)", js, "auth.js must call invalidateSize when container is displayed")

    def test_08_openstreetmap_tile_reachability(self):
        """Test OpenStreetMap tile server is reachable with HTTP 200."""
        req = urllib.request.Request(
            "https://tile.openstreetmap.org/0/0/0.png",
            headers={"User-Agent": "WayVista-RoutePredictor/1.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            self.assertEqual(resp.getcode(), 200)

if __name__ == "__main__":
    unittest.main()
