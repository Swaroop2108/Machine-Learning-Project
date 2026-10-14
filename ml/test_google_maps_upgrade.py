import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_google_maps_upgrade():
    print("=== VOYAGEML GOOGLE MAPS UPGRADE VERIFICATION ===")

    # 1. Test /api/config endpoint
    print("\n1. Testing /api/config endpoint...")
    try:
        res = requests.get(f"{BASE_URL}/api/config")
        print(f"Status Code: {res.status_code}")
        data = res.json()
        print(f"Config Response: {data}")
        assert res.status_code == 200
        assert "google_maps_api_key" in data
        print("[SUCCESS] /api/config verified successfully!")
    except Exception as e:
        print(f"[FAIL] /api/config failed: {e}")
        raise e

    # 2. Test Predictions for standard test routes
    test_routes = [
        {"source": "Hyderabad", "destination": "Vijayawada", "label": "Hyderabad -> Vijayawada"},
        {"source": "Bangalore", "destination": "Mysore", "label": "Bangalore -> Mysore"},
        {"source": "Mumbai", "destination": "Pune", "label": "Mumbai -> Pune"}
    ]

    for item in test_routes:
        print(f"\n2. Testing Route: {item['label']}...")
        payload = {
            "source": item["source"],
            "destination": item["destination"],
            "departure_datetime": "2026-09-03T09:00:00",
            "traffic_condition": "Moderate"
        }
        try:
            res = requests.post(f"{BASE_URL}/api/predict", json=payload)
            print(f"Status Code: {res.status_code}")
            assert res.status_code == 200
            data = res.json()
            assert data["success"] is True
            journey = data["journey"]
            route = data["route"]
            pred = data["prediction"]
            print(f"  Source -> Dest: {journey['source']} -> {journey['destination']}")
            print(f"  Distance: {route['distance_km']} km")
            print(f"  Primary Model: {pred['primary_model']}")
            print(f"  Predicted Travel Time (Lasso): {pred['predicted_travel_time_minutes']} mins")
            print(f"  Ridge Prediction: {pred['ridge_prediction_minutes']} mins")
            print(f"  ETA: {journey['estimated_arrival_time']}")
            print("  [SUCCESS] Route prediction verified!")
        except Exception as e:
            print(f"[FAIL] Route test failed for {item['label']}: {e}")
            raise e

if __name__ == "__main__":
    test_google_maps_upgrade()
