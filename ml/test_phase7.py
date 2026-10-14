import requests
import json

def run_phase7_tests():
    print("=== PHASE 7 VERIFICATION TEST SUITE ===")
    
    # 1. Health check
    h_res = requests.get("http://127.0.0.1:8000/health").json()
    print("Health Check:", h_res)

    # 2. Static Asset check
    js_res = requests.get("http://127.0.0.1:8000/static/js/script.js?v=1.0.3")
    print("Static JS Status:", js_res.status_code, "| Cache-Control:", js_res.headers.get("Cache-Control"))

    url = "http://127.0.0.1:8000/api/predict"

    # TEST 1: Hyderabad -> Vijayawada
    p1 = {"source": "Hyderabad", "destination": "Vijayawada", "departure_datetime": "2026-08-31T09:00:00", "traffic_condition": "Moderate"}
    r1 = requests.post(url, json=p1).json()
    print("\n--- TEST 1: Hyderabad -> Vijayawada ---")
    print("Success:", r1.get("success"))
    print("Journey:", r1["journey"]["source"], "->", r1["journey"]["destination"])
    print("Distance:", r1["route"]["distance_km"], "km")
    print("Primary Model:", r1["prediction"]["primary_model"])
    print("ML Duration:", r1["prediction"]["predicted_travel_time_minutes"], "mins | OSRM Duration:", r1["route"]["route_api_duration_minutes"], "mins")
    print("ETA:", r1["journey"]["estimated_arrival_time"])
    print("Out-of-Distribution (>50km)?:", r1["route"]["distance_km"] > 50.0)

    # TEST 2: Bangalore -> Mysore
    p2 = {"source": "Bangalore", "destination": "Mysore", "departure_datetime": "2026-09-01T09:00:00", "traffic_condition": "Low"}
    r2 = requests.post(url, json=p2).json()
    print("\n--- TEST 2: Bangalore -> Mysore ---")
    print("Journey:", r2["journey"]["source"], "->", r2["journey"]["destination"])
    print("Distance:", r2["route"]["distance_km"], "km")
    print("ML Duration:", r2["prediction"]["predicted_travel_time_minutes"], "mins | OSRM Duration:", r2["route"]["route_api_duration_minutes"], "mins")
    print("ETA:", r2["journey"]["estimated_arrival_time"])
    print("Out-of-Distribution (>50km)?:", r2["route"]["distance_km"] > 50.0)

    # TEST 3: Mumbai -> Pune
    p3 = {"source": "Mumbai", "destination": "Pune", "departure_datetime": "2026-09-02T18:00:00", "traffic_condition": "High"}
    r3 = requests.post(url, json=p3).json()
    print("\n--- TEST 3: Mumbai -> Pune ---")
    print("Journey:", r3["journey"]["source"], "->", r3["journey"]["destination"])
    print("Distance:", r3["route"]["distance_km"], "km")
    print("ML Duration:", r3["prediction"]["predicted_travel_time_minutes"], "mins | OSRM Duration:", r3["route"]["route_api_duration_minutes"], "mins")
    print("ETA:", r3["journey"]["estimated_arrival_time"])

    # TEST 4: Short City Trip (In-range check)
    p4 = {"source": "Hyderabad", "destination": "Secunderabad", "departure_datetime": "2026-08-31T10:00:00"}
    r4 = requests.post(url, json=p4).json()
    print("\n--- TEST 4: Hyderabad -> Secunderabad (Short Trip) ---")
    print("Journey:", r4["journey"]["source"], "->", r4["journey"]["destination"])
    print("Distance:", r4["route"]["distance_km"], "km")
    print("ML Duration:", r4["prediction"]["predicted_travel_time_minutes"], "mins")
    print("Within Training Range (<=50km)?:", r4["route"]["distance_km"] <= 50.0)

if __name__ == "__main__":
    run_phase7_tests()
