import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_google_routes_integration():
    print("=== VOYAGEML GOOGLE ROUTES API INTEGRATION VERIFICATION ===")

    # 1. Test /api/config endpoint
    print("\n1. Testing /api/config...")
    res_cfg = requests.get(f"{BASE_URL}/api/config")
    print(f"Status Code: {res_cfg.status_code}")
    cfg_data = res_cfg.json()
    print(f"Config Response: {cfg_data}")
    assert res_cfg.status_code == 200, "Config endpoint failed!"

    # 2. Test Car Drive Mode Routes
    car_test_routes = [
        {"source": "Hyderabad", "destination": "Vijayawada", "label": "Hyderabad -> Vijayawada"},
        {"source": "Bangalore", "destination": "Mysore", "label": "Bangalore -> Mysore"},
        {"source": "Mumbai", "destination": "Pune", "label": "Mumbai -> Pune"}
    ]

    for item in car_test_routes:
        print(f"\n2. Testing Google Route (CAR): {item['label']}...")
        payload = {
            "source": item["source"],
            "destination": item["destination"],
            "departure_datetime": "2026-09-03T09:00:00",
            "travel_mode": "DRIVE"
        }
        res = requests.post(f"{BASE_URL}/api/google-route", json=payload)
        print(f"Status Code: {res.status_code}")
        g_data = res.json()
        print(f"Google Route Response: {g_data}")

    # 3. Test Travel Modes: Two-Wheeler, Transit, Walk
    other_modes = ["TWO_WHEELER", "TRANSIT", "WALK"]
    for m in other_modes:
        print(f"\n3. Testing Google Route ({m}): Hyderabad -> Vijayawada...")
        payload = {
            "source": "Hyderabad",
            "destination": "Vijayawada",
            "departure_datetime": "2026-09-03T09:00:00",
            "travel_mode": m
        }
        res = requests.post(f"{BASE_URL}/api/google-route", json=payload)
        print(f"Status Code: {res.status_code}")
        print(f"Response: {res.json()}")

    # 4. Test ML Prediction Pipeline (must remain separate and working)
    print("\n4. Testing ML Model Inference Pipeline...")
    ml_payload = {
        "source": "Hyderabad",
        "destination": "Vijayawada",
        "departure_datetime": "2026-09-03T09:00:00",
        "traffic_condition": "Moderate"
    }
    res_ml = requests.post(f"{BASE_URL}/api/predict", json=ml_payload)
    print(f"Status Code: {res_ml.status_code}")
    ml_data = res_ml.json()
    assert res_ml.status_code == 200 and ml_data["success"] is True
    print(f"  Primary Model: {ml_data['prediction']['primary_model']}")
    print(f"  Lasso Prediction: {ml_data['prediction']['lasso_prediction_minutes']} mins")
    print(f"  Ridge Prediction: {ml_data['prediction']['ridge_prediction_minutes']} mins")
    print("[SUCCESS] ML prediction pipeline verified successfully!")

if __name__ == "__main__":
    test_google_routes_integration()
