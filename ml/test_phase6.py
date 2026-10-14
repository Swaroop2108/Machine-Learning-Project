import joblib
import pandas as pd
import requests
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "ml" / "models"

def run_phase6_tests():
    print("=== PHASE 6: END-TO-END PREDICTION SYSTEM TESTS ===")

    # 1. Test 1: Hyderabad -> Vijayawada
    url = "http://127.0.0.1:8000/api/predict"
    payload1 = {
        "source": "Hyderabad",
        "destination": "Vijayawada",
        "departure_datetime": "2026-08-31T08:30:00"
    }
    
    print("\n--- TEST 1: Hyderabad -> Vijayawada ---")
    r1 = requests.post(url, json=payload1).json()
    print("Success:", r1.get("success"))
    print("Source -> Dest:", r1["journey"]["source"], "->", r1["journey"]["destination"])
    print("Distance:", r1["route"]["distance_km"], "km")
    print("Traffic:", r1["travel_conditions"]["traffic_condition"], f"({r1['travel_conditions']['traffic_source']})")
    print("Weather:", r1["travel_conditions"]["weather_condition"], f"({r1['travel_conditions']['temperature_c']}°C)")
    print("Primary Model:", r1["prediction"]["primary_model"])
    print("Predicted Travel Time:", r1["prediction"]["predicted_travel_time_minutes"], "mins")
    print("Ridge Pred:", r1["prediction"]["ridge_prediction_minutes"], "mins | Lasso Pred:", r1["prediction"]["lasso_prediction_minutes"], "mins")
    print("Estimated Arrival Time:", r1["journey"]["estimated_arrival_time"])

    # 2. Test 2: Bangalore -> Mysore
    payload2 = {
        "source": "Bangalore",
        "destination": "Mysore",
        "departure_datetime": "2026-09-01T09:00:00"
    }
    print("\n--- TEST 2: Bangalore -> Mysore ---")
    r2 = requests.post(url, json=payload2).json()
    print("Source -> Dest:", r2["journey"]["source"], "->", r2["journey"]["destination"])
    print("Distance:", r2["route"]["distance_km"], "km | Route Type:", r2["route"]["route_type"])
    print("Predicted Travel Time:", r2["prediction"]["predicted_travel_time_minutes"], "mins | ETA:", r2["journey"]["estimated_arrival_time"])

    # 3. Test 3: Mumbai -> Pune
    payload3 = {
        "source": "Mumbai",
        "destination": "Pune",
        "departure_datetime": "2026-09-02T18:00:00",
        "traffic_condition": "High"
    }
    print("\n--- TEST 3: Mumbai -> Pune (Traffic Override: High) ---")
    r3 = requests.post(url, json=payload3).json()
    print("Distance:", r3["route"]["distance_km"], "km | Traffic:", r3["travel_conditions"]["traffic_condition"])
    print("Predicted Travel Time:", r3["prediction"]["predicted_travel_time_minutes"], "mins | ETA:", r3["journey"]["estimated_arrival_time"])

    # 4. Invalid Input Tests
    print("\n--- INVALID INPUT TESTS ---")
    # Empty source
    err1 = requests.post(url, json={"source": "", "destination": "Pune"}).json()
    print("Empty Source Error:", err1.get("detail"))

    # Same source and dest
    err2 = requests.post(url, json={"source": "Mumbai", "destination": "Mumbai"}).json()
    print("Same Location Error:", err2.get("detail"))

    # Invalid traffic condition
    err3 = requests.post(url, json={"source": "Mumbai", "destination": "Pune", "traffic_condition": "Extreme"}).json()
    print("Invalid Traffic Error:", err3.get("detail"))

    # 5. Model Consistency Test
    print("\n--- MODEL CONSISTENCY TEST ---")
    # Extract features from Test 1
    api_dist = r1["route"]["distance_km"]
    api_traffic = r1["travel_conditions"]["traffic_condition"]
    api_weather = r1["travel_conditions"]["weather_condition"]
    api_day = "Monday" # 2026-08-31 is Monday
    api_dep_hour = 8
    api_temp = r1["travel_conditions"]["temperature_c"]
    api_lasso_pred = r1["prediction"]["lasso_prediction_minutes"]

    # Direct offline model evaluation
    prep = joblib.load(MODEL_DIR / "preprocessor.joblib")
    lasso = joblib.load(MODEL_DIR / "lasso_model.joblib")

    direct_df = pd.DataFrame([{
        "distance_km": float(api_dist),
        "traffic_condition": str(api_traffic).capitalize(),
        "weather": str(api_weather).capitalize(),
        "day_of_week": str(api_day).capitalize(),
        "departure_hour": int(api_dep_hour),
        "temperature_c": float(api_temp)
    }])

    X_direct = prep.transform(direct_df)
    direct_pred = round(float(lasso.predict(X_direct)[0]), 2)

    print(f"API Lasso Prediction:    {api_lasso_pred} minutes")
    print(f"Direct Model Prediction: {direct_pred} minutes")
    print("Consistency Test Passed:", abs(api_lasso_pred - direct_pred) < 0.01)

if __name__ == "__main__":
    run_phase6_tests()
