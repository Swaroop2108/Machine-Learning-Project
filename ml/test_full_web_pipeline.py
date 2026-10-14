import requests

BASE_URL = "http://127.0.0.1:8000"

def test_full_pipeline():
    print("=== TESTING VOYAGEML FULL WEB PIPELINE ===")

    # 1. Test HTML Root
    res_root = requests.get(f"{BASE_URL}/")
    assert res_root.status_code == 200
    html_content = res_root.text
    assert 'id="res-google-duration"' in html_content
    assert 'id="res-google-eta"' in html_content
    assert 'id="res-departure-time"' in html_content
    assert 'id="res-google-distance"' in html_content
    assert 'id="res-mode-badge"' in html_content
    assert 'id="google-error-banner"' in html_content
    assert 'id="map"' in html_content
    print("[SUCCESS] HTML root served and contains all required DOM element IDs!")

    # 2. Test JS script static file
    res_js = requests.get(f"{BASE_URL}/static/js/script.js?v=1.1.0")
    assert res_js.status_code == 200
    js_content = res_js.text
    assert 'data.google_route' in js_content
    assert 'duration_text' in js_content
    assert 'estimated_arrival_time' in js_content
    assert 'renderMapFallbackPlaceholder' in js_content
    print("[SUCCESS] JS script served and contains data.google_route data bindings!")

    # 3. Test /api/config endpoint
    res_cfg = requests.get(f"{BASE_URL}/api/config")
    assert res_cfg.status_code == 200
    print(f"[SUCCESS] /api/config endpoint returned: {res_cfg.json()}")

    # 4. Test /api/google-route endpoint
    res_gr = requests.post(f"{BASE_URL}/api/google-route", json={
        "source": "Hyderabad",
        "destination": "Vijayawada",
        "departure_datetime": "2026-09-03T09:00:00",
        "travel_mode": "DRIVE"
    })
    assert res_gr.status_code == 200
    print(f"[SUCCESS] /api/google-route returned: {res_gr.json()}")

    # 5. Test /api/predict ML endpoint
    res_ml = requests.post(f"{BASE_URL}/api/predict", json={
        "source": "Hyderabad",
        "destination": "Vijayawada",
        "departure_datetime": "2026-09-03T09:00:00",
        "traffic_condition": "Moderate"
    })
    assert res_ml.status_code == 200
    print(f"[SUCCESS] /api/predict returned Lasso prediction: {res_ml.json()['prediction']['lasso_prediction_minutes']} mins")

if __name__ == "__main__":
    test_full_pipeline()
