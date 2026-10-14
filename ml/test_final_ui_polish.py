import requests
import json

def run_final_ui_tests():
    print("=== FINAL UI POLISH & QUALITY VERIFICATION ===")

    # 1. Health check
    h = requests.get("http://127.0.0.1:8000/health").json()
    print("Health Check:", h)

    # 2. Static file headers
    js = requests.get("http://127.0.0.1:8000/static/js/script.js?v=1.0.4")
    print("Static JS Status:", js.status_code, "| Cache-Control:", js.headers.get("Cache-Control"))

    url = "http://127.0.0.1:8000/api/predict"

    # TEST A: Hyderabad -> Vijayawada
    pA = {"source": "Hyderabad", "destination": "Vijayawada", "departure_datetime": "2026-08-31T09:00:00", "traffic_condition": "Moderate"}
    rA = requests.post(url, json=pA).json()
    print("\n--- TEST A: Hyderabad -> Vijayawada ---")
    print("Success:", rA.get("success"))
    print("Source -> Dest:", rA["journey"]["source"], "->", rA["journey"]["destination"])
    print("Distance:", rA["route"]["distance_km"], "km | Route:", rA["route"]["route_type"])
    print("Primary Model:", rA["prediction"]["primary_model"])
    print("ML Duration (Lasso):", rA["prediction"]["predicted_travel_time_minutes"], "mins")
    print("OSRM Baseline:", rA["route"]["route_api_duration_minutes"], "mins")
    print("ETA:", rA["journey"]["estimated_arrival_time"])
    print("Weather:", rA["travel_conditions"]["weather_condition"], f"({rA['travel_conditions']['temperature_c']}°C)")
    print("Traffic:", rA["travel_conditions"]["traffic_condition"])
    print("Out-of-Distribution Warning (>50km):", rA["route"]["distance_km"] > 50.0)

    # TEST B: Bangalore -> Mysore
    pB = {"source": "Bangalore", "destination": "Mysore", "departure_datetime": "2026-09-01T09:00:00", "traffic_condition": "Low"}
    rB = requests.post(url, json=pB).json()
    print("\n--- TEST B: Bangalore -> Mysore ---")
    print("Source -> Dest:", rB["journey"]["source"], "->", rB["journey"]["destination"])
    print("Distance:", rB["route"]["distance_km"], "km | Route:", rB["route"]["route_type"])
    print("ML Duration (Lasso):", rB["prediction"]["predicted_travel_time_minutes"], "mins | OSRM:", rB["route"]["route_api_duration_minutes"], "mins")
    print("ETA:", rB["journey"]["estimated_arrival_time"])
    print("Out-of-Distribution Warning (>50km):", rB["route"]["distance_km"] > 50.0)

    # TEST C: Mumbai -> Pune
    pC = {"source": "Mumbai", "destination": "Pune", "departure_datetime": "2026-09-02T18:00:00", "traffic_condition": "High"}
    rC = requests.post(url, json=pC).json()
    print("\n--- TEST C: Mumbai -> Pune ---")
    print("Source -> Dest:", rC["journey"]["source"], "->", rC["journey"]["destination"])
    print("Distance:", rC["route"]["distance_km"], "km | Traffic:", rC["travel_conditions"]["traffic_condition"])
    print("ML Duration (Lasso):", rC["prediction"]["predicted_travel_time_minutes"], "mins")
    print("ETA:", rC["journey"]["estimated_arrival_time"])

    # INVALID INPUT TESTS
    print("\n--- INVALID INPUT TESTS ---")
    err_empty = requests.post(url, json={"source": "", "destination": "Pune"}).json()
    print("Empty Source Error:", err_empty.get("detail"))

    err_same = requests.post(url, json={"source": "Mumbai", "destination": "Mumbai"}).json()
    print("Same Location Error:", err_same.get("detail"))

if __name__ == "__main__":
    run_final_ui_tests()
