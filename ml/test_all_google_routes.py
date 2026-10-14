import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"

TEST_CASES = [
    {"id": "A1", "source": "Miyapur, Telangana", "destination": "L. B. Nagar, Hyderabad, Telangana", "mode": "DRIVE", "label": "Miyapur -> L. B. Nagar (Car - NOW)"},
    {"id": "A2", "source": "Miyapur, Telangana", "destination": "L. B. Nagar, Hyderabad, Telangana", "mode": "TWO_WHEELER", "label": "Miyapur -> L. B. Nagar (Two-Wheeler - NOW)"},
    {"id": "A3", "source": "Miyapur, Telangana", "destination": "L. B. Nagar, Hyderabad, Telangana", "mode": "WALK", "label": "Miyapur -> L. B. Nagar (Walk - NOW)"},
    {"id": "A4", "source": "Miyapur, Telangana", "destination": "L. B. Nagar, Hyderabad, Telangana", "mode": "TRANSIT", "label": "Miyapur -> L. B. Nagar (Transit - NOW)"},
    {"id": "B", "source": "Miyapur", "destination": "Kukatpally", "mode": "TWO_WHEELER", "label": "Miyapur -> Kukatpally (Two-Wheeler)"},
    {"id": "C", "source": "Hyderabad", "destination": "Vijayawada", "mode": "DRIVE", "label": "Hyderabad -> Vijayawada (Car - Planned)"},
    {"id": "D", "source": "Bangalore", "destination": "Mysore", "mode": "DRIVE", "label": "Bangalore -> Mysore (Car)"},
    {"id": "E", "source": "Mumbai", "destination": "Pune", "mode": "DRIVE", "label": "Mumbai -> Pune (Car)"},
]

def run_tests():
    print("==========================================================================")
    print("       VOYAGEML GOOGLE ROUTES & ML INTEGRATION SUITE — 9 TEST CASES")
    print("==========================================================================")

    # 1. Check Config & API key loading
    print("\n[CHECK] Fetching /api/config...")
    try:
        cfg_res = requests.get(f"{BASE_URL}/api/config", timeout=5)
        print(f"Status Code: {cfg_res.status_code}")
        cfg = cfg_res.json()
        key_present = bool(cfg.get("google_maps_api_key"))
        key_len = len(cfg.get("google_maps_api_key", ""))
        print(f"Google Maps API Key Loaded: {'YES' if key_present else 'NO'} | Length: {key_len}")
    except Exception as e:
        print(f"FAILED to connect to backend: {e}")
        return

    results = []

    for tc in TEST_CASES:
        print(f"\n--------------------------------------------------------------------------")
        print(f"Test {tc['id']}: {tc['label']}")
        print(f"--------------------------------------------------------------------------")

        payload = {
            "source": tc["source"],
            "destination": tc["destination"],
            "departure_datetime": "2026-09-11T09:00:00",
            "travel_mode": tc["mode"]
        }

        start_t = time.time()
        try:
            res = requests.post(f"{BASE_URL}/api/google-route", json=payload, timeout=10)
            elapsed = round(time.time() - start_t, 2)
            print(f"HTTP Status: {res.status_code} ({elapsed}s)")
            
            data = res.json()
            if res.status_code == 200 and data.get("success"):
                gr = data["google_route"]
                print(f"  [PASS] Google Maps Route Received")
                print(f"    Google Distance: {gr['distance_km']} km ({gr.get('distance_meters', 0)} meters)")
                print(f"    Google Duration: {gr['duration_text']} ({gr['duration_seconds']} seconds)")
                print(f"    Google ETA:      {gr['estimated_arrival_time']}")
                print(f"    Travel Mode:     {gr['travel_mode']}")
                results.append({
                    "id": tc["id"],
                    "label": tc["label"],
                    "status": "PASS",
                    "distance_km": gr["distance_km"],
                    "duration_text": gr["duration_text"],
                    "eta": gr["estimated_arrival_time"],
                    "detail": "Google Route Success"
                })
            else:
                err_detail = data.get("detail", "Unknown error")
                print(f"  [NOTICE] Google Route Failed / Unavailable")
                print(f"    Error Detail: {err_detail}")
                results.append({
                    "id": tc["id"],
                    "label": tc["label"],
                    "status": "FAIL/EXPECTED",
                    "distance_km": "--",
                    "duration_text": "Unavailable",
                    "eta": "--",
                    "detail": err_detail
                })
        except Exception as err:
            print(f"  [ERROR] Exception calling endpoint: {err}")
            results.append({
                "id": tc["id"],
                "label": tc["label"],
                "status": "ERROR",
                "distance_km": "--",
                "duration_text": "Error",
                "eta": "--",
                "detail": str(err)
            })

    print("\n==========================================================================")
    print("                         SUMMARY OF TEST RESULTS")
    print("==========================================================================")
    for r in results:
        print(f"[{r['id']}] {r['label']:<40} | Status: {r['status']:<13} | Dist: {r['distance_km']} | Dur: {r['duration_text']} | Detail: {r['detail']}")
    print("==========================================================================")

if __name__ == "__main__":
    run_tests()
