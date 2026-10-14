import requests
import json

def test_frontend_bugfix():
    print("=== TESTING CRITICAL BUG FIX FOR FRONTEND-BACKEND INTEGRATION ===")
    
    url = "http://127.0.0.1:8000/api/predict"
    
    # 1. Test Static JS Header
    js_res = requests.get("http://127.0.0.1:8000/static/js/script.js?v=1.0.2")
    print("\n--- 1. STATIC JS NO-CACHE HEADERS ---")
    print("Cache-Control Header:", js_res.headers.get("Cache-Control"))
    print("Script Content Length:", len(js_res.text))
    
    # 2. Test Hyderabad -> Vijayawada with Moderate Traffic
    payload1 = {
        "source": "Hyderabad",
        "destination": "Vijayawada",
        "departure_datetime": "2026-08-31T09:00:00",
        "traffic_condition": "Moderate"
    }
    print("\n--- 2. TEST 1: HYDERABAD -> VIJAYAWADA (Moderate Traffic) ---")
    r1 = requests.post(url, json=payload1).json()
    print("Success:", r1.get("success"))
    print("Source:", r1["journey"]["source"])
    print("Destination:", r1["journey"]["destination"])
    print("Distance:", r1["route"]["distance_km"], "km")
    print("ML Travel Time (Lasso):", r1["prediction"]["predicted_travel_time_minutes"], "mins")
    print("ETA:", r1["journey"]["estimated_arrival_time"])
    print("Traffic Condition:", r1["travel_conditions"]["traffic_condition"])
    print("Weather Condition:", r1["travel_conditions"]["weather_condition"])
    print("Temperature:", r1["travel_conditions"]["temperature_c"], "°C")
    print("Map Route First Point:", r1["route"]["route_geometry"][0])
    
    # 3. Test Bangalore -> Mysore
    payload2 = {
        "source": "Bangalore",
        "destination": "Mysore",
        "departure_datetime": "2026-09-01T09:00:00",
        "traffic_condition": "Low"
    }
    print("\n--- 3. TEST 2: BANGALORE -> MYSORE (Low Traffic) ---")
    r2 = requests.post(url, json=payload2).json()
    print("Source:", r2["journey"]["source"])
    print("Destination:", r2["journey"]["destination"])
    print("Distance:", r2["route"]["distance_km"], "km")
    print("ML Travel Time (Lasso):", r2["prediction"]["predicted_travel_time_minutes"], "mins")
    print("ETA:", r2["journey"]["estimated_arrival_time"])
    print("Map Route First Point:", r2["route"]["route_geometry"][0])

    # 4. Test Mumbai -> Pune
    payload3 = {
        "source": "Mumbai",
        "destination": "Pune",
        "departure_datetime": "2026-09-02T18:00:00",
        "traffic_condition": "High"
    }
    print("\n--- 4. TEST 3: MUMBAI -> PUNE (High Traffic) ---")
    r3 = requests.post(url, json=payload3).json()
    print("Source:", r3["journey"]["source"])
    print("Destination:", r3["journey"]["destination"])
    print("Distance:", r3["route"]["distance_km"], "km")
    print("ML Travel Time (Lasso):", r3["prediction"]["predicted_travel_time_minutes"], "mins")
    print("Map Route First Point:", r3["route"]["route_geometry"][0])

    # 5. Verify non-stale multi-route transition
    print("\n--- 5. STALE DATA TRANSITION CHECK ---")
    print(f"Hyderabad -> Vijayawada Dist: {r1['route']['distance_km']} km | Bangalore -> Mysore Dist: {r2['route']['distance_km']} km | Mumbai -> Pune Dist: {r3['route']['distance_km']} km")
    print("All routes return distinct non-stale data:", (r1['route']['distance_km'] != r2['route']['distance_km']) and (r2['route']['distance_km'] != r3['route']['distance_km']))

if __name__ == "__main__":
    test_frontend_bugfix()
