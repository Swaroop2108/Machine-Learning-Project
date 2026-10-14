import pandas as pd
import numpy as np
import joblib
import json
import matplotlib.pyplot as plt
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_PATH = BASE_DIR / "ml" / "dataset" / "travel_dataset.csv"
MODEL_DIR = BASE_DIR / "ml" / "models"
CHARTS_DIR = BASE_DIR / "charts"
CHARTS_DIR.mkdir(exist_ok=True)

def run_diagnostics():
    print("=== ML SANITY CHECK DIAGNOSTIC REPORT ===")

    # 1. Dataset Statistics
    df = pd.read_csv(DATASET_PATH)
    print(f"\n--- 1. DATASET OVERVIEW ({len(df)} rows) ---")
    print(f"Columns: {list(df.columns)}")
    
    dist_stats = {
        "min": float(df["distance_km"].min()),
        "max": float(df["distance_km"].max()),
        "mean": float(df["distance_km"].mean()),
        "median": float(df["distance_km"].median()),
        "std": float(df["distance_km"].std())
    }
    
    time_stats = {
        "min": float(df["travel_time_minutes"].min()),
        "max": float(df["travel_time_minutes"].max()),
        "mean": float(df["travel_time_minutes"].mean()),
        "median": float(df["travel_time_minutes"].median()),
        "std": float(df["travel_time_minutes"].std())
    }
    
    print("\nDistance (km) Stats:", json.dumps({k: round(v, 2) for k, v in dist_stats.items()}, indent=2))
    print("Travel Time (mins) Stats:", json.dumps({k: round(v, 2) for k, v in time_stats.items()}, indent=2))

    # 2. Implied Speed Calculation
    df["implied_speed_kmh"] = df["distance_km"] / (df["travel_time_minutes"] / 60.0)
    
    speed_stats = {
        "min": float(df["implied_speed_kmh"].min()),
        "max": float(df["implied_speed_kmh"].max()),
        "mean": float(df["implied_speed_kmh"].mean()),
        "median": float(df["implied_speed_kmh"].median()),
        "std": float(df["implied_speed_kmh"].std())
    }
    print("\nImplied Speed (km/h) Stats:", json.dumps({k: round(v, 2) for k, v in speed_stats.items()}, indent=2))

    print("\nImplied Speed by Traffic Condition (km/h):")
    print(df.groupby("traffic_condition")["implied_speed_kmh"].agg(["mean", "median", "min", "max"]).round(2))

    print("\nImplied Speed by Weather (km/h):")
    print(df.groupby("weather")["implied_speed_kmh"].agg(["mean", "median", "min", "max"]).round(2))

    # 3. Correlation & Scatter Plot
    corr = float(df["distance_km"].corr(df["travel_time_minutes"]))
    print(f"\n--- 3. DISTANCE VS TRAVEL TIME CORRELATION: {corr:.4f} ---")

    # Plot distance vs travel time using matplotlib
    plt.figure(figsize=(8, 5))
    plt.scatter(df["distance_km"], df["travel_time_minutes"], c="#3b82f6", alpha=0.6, edgecolors="none")
    plt.title(f"Dataset: Distance vs Travel Time (Correlation = {corr:.3f})")
    plt.xlabel("Distance (km)")
    plt.ylabel("Travel Time (minutes)")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()
    chart_path = CHARTS_DIR / "dataset_distance_vs_travel_time_sanity.png"
    plt.savefig(chart_path, dpi=150)
    plt.close()
    print(f"Chart saved to: {chart_path}")

    # 4. Training Distance Range Check
    print("\n--- 4. TRAINING RANGE CHECK FOR LIVE TEST CASES ---")
    live_case_1 = {"name": "Bangalore -> Mysore", "distance_km": 141.1}
    live_case_2 = {"name": "Hyderabad -> Vijayawada", "distance_km": 273.51}

    for case in [live_case_1, live_case_2]:
        d = case["distance_km"]
        in_range = dist_stats["min"] <= d <= dist_stats["max"]
        exceed_ratio = d / dist_stats["max"]
        print(f"Case '{case['name']}': Distance = {d} km")
        print(f"  Inside Training Range [{dist_stats['min']} km - {dist_stats['max']} km]?: {in_range}")
        print(f"  Exceeds Training Max Distance by factor of: {exceed_ratio:.2f}x")

    # 5 & 8. Load Preprocessor and Models & Inspect Coefficients
    prep = joblib.load(MODEL_DIR / "preprocessor.joblib")
    ridge = joblib.load(MODEL_DIR / "ridge_model.joblib")
    lasso = joblib.load(MODEL_DIR / "lasso_model.joblib")

    # Get feature names after ColumnTransformer transformation
    num_cols = ["distance_km", "departure_hour", "temperature_c"]
    cat_cols = ["traffic_condition", "weather", "day_of_week"]

    cat_transformer = prep.named_transformers_["cat"]
    cat_feature_names = list(cat_transformer.get_feature_names_out(cat_cols))
    all_feature_names = num_cols + cat_feature_names

    print(f"\n--- 5 & 8. MODEL COEFFICIENTS & PREPROCESSOR DETAILS ---")
    print(f"Total Features after Preprocessing: {len(all_feature_names)}")
    print(f"Ridge Intercept: {ridge.intercept_:.4f}")
    print(f"Lasso Intercept: {lasso.intercept_:.4f}")

    coef_df = pd.DataFrame({
        "Feature": all_feature_names,
        "Ridge_Coef": ridge.coef_,
        "Lasso_Coef": lasso.coef_
    })
    print("\nCoefficient Summary Table:")
    print(coef_df.to_string(index=False))

    # Inspect scaler parameters
    num_scaler = prep.named_transformers_["num"]
    print("\nStandardScaler Mean (Num cols):", dict(zip(num_cols, num_scaler.mean_.round(4))))
    print("StandardScaler Scale (Std dev):", dict(zip(num_cols, num_scaler.scale_.round(4))))

    # Calculate marginal increase in travel time per km of distance
    dist_scale = num_scaler.scale_[0]
    ridge_mins_per_km = ridge.coef_[0] / dist_scale
    lasso_mins_per_km = lasso.coef_[0] / dist_scale
    print(f"\nMarginal Travel Time per km (Distance Coefficient / Scale):")
    print(f"  Ridge: {ridge_mins_per_km:.4f} mins per km")
    print(f"  Lasso: {lasso_mins_per_km:.4f} mins per km")

    # 6 & 7. Live Feature Dictionaries & Predictions Check
    print("\n--- 6 & 7. LIVE TEST CASES INFERENCE BREAKDOWN ---")

    test_dicts = [
        {
            "name": "Bangalore -> Mysore",
            "distance_km": 141.1,
            "traffic_condition": "Medium",
            "weather": "Cloudy",
            "day_of_week": "Tuesday",
            "departure_hour": 9,
            "temperature_c": 25.0,
            "osrm_duration_mins": 190.0
        },
        {
            "name": "Hyderabad -> Vijayawada",
            "distance_km": 273.51,
            "traffic_condition": "Medium",
            "weather": "Cloudy",
            "day_of_week": "Monday",
            "departure_hour": 8,
            "temperature_c": 24.9,
            "osrm_duration_mins": 217.1
        }
    ]

    for item in test_dicts:
        print(f"\n>>> Live Case: {item['name']}")
        full_live_features = {
            "distance_km": item["distance_km"],
            "route_type": "Highway",
            "departure_hour": item["departure_hour"],
            "day_of_week": item["day_of_week"],
            "is_rush_hour": 1 if item["departure_hour"] in [7, 8, 9, 16, 17, 18, 19] else 0,
            "traffic_condition": item["traffic_condition"],
            "weather_condition": item["weather"],
            "temperature_c": item["temperature_c"],
            "precipitation_mm": 0.0
        }
        print("  Exact 9 Live Context Features:", json.dumps(full_live_features, indent=4))

        input_df = pd.DataFrame([{
            "distance_km": item["distance_km"],
            "traffic_condition": item["traffic_condition"],
            "weather": item["weather"],
            "day_of_week": item["day_of_week"],
            "departure_hour": item["departure_hour"],
            "temperature_c": item["temperature_c"]
        }])

        X_trans = prep.transform(input_df)
        ridge_pred = float(ridge.predict(X_trans)[0])
        lasso_pred = float(lasso.predict(X_trans)[0])

        print(f"  Ridge Direct Prediction: {ridge_pred:.2f} mins")
        print(f"  Lasso Direct Prediction: {lasso_pred:.2f} mins")
        print(f"  OSRM Baseline Duration:  {item['osrm_duration_mins']:.2f} mins")
        print(f"  Difference (Lasso ML - OSRM): {lasso_pred - item['osrm_duration_mins']:.2f} mins")

        # Feature level mathematical decomposition for Lasso
        scaled_vals = X_trans[0]
        contributions = scaled_vals * lasso.coef_
        print("\n  Lasso Mathematical Value Breakdown (Feature * Weight):")
        print(f"    Intercept = {lasso.intercept_:.2f}")
        for feat, val, weight, contrib in zip(all_feature_names, scaled_vals, lasso.coef_, contributions):
            if abs(contrib) > 0.01:
                print(f"    {feat:30s}: Scaled Value = {val:7.3f} | Weight = {weight:7.3f} | Contrib = {contrib:7.2f} mins")

if __name__ == "__main__":
    run_diagnostics()
