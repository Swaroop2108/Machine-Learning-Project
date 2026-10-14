import numpy as np
import pandas as pd
from typing import Dict, Any
from backend.model_loader import model_loader

def run_model_inference(distance_km: float, traffic_condition: str, weather: str,
                        day_of_week: str, departure_hour: int, temperature_c: float) -> Dict[str, Any]:
    """
    Executes ML inference using pre-loaded preprocessor and trained Ridge & Lasso models.
    Performs sanity checks (finite, non-NaN, positive values) on prediction outputs.
    """
    if not model_loader.is_loaded or not model_loader.preprocessor:
        model_loader.load_models()

    if not model_loader.is_loaded:
        raise RuntimeError("ML model artifacts are not loaded. Run ml/train.py first.")

    # 1. Format single-row DataFrame matching training features
    input_df = pd.DataFrame([{
        "distance_km": float(distance_km),
        "traffic_condition": str(traffic_condition).capitalize(),
        "weather": str(weather).capitalize(),
        "day_of_week": str(day_of_week).capitalize(),
        "departure_hour": int(departure_hour),
        "temperature_c": float(temperature_c)
    }])

    # 2. Transform using pre-loaded ColumnTransformer
    X_scaled = model_loader.preprocessor.transform(input_df)

    # 3. Model Predictions
    ridge_pred_val = float(model_loader.ridge_model.predict(X_scaled)[0])
    lasso_pred_val = float(model_loader.lasso_model.predict(X_scaled)[0])

    # 4. Sanity Checks: finite, non-NaN, positive value
    if not np.isfinite(ridge_pred_val) or np.isnan(ridge_pred_val) or ridge_pred_val <= 0:
        raise ValueError(f"Invalid Ridge prediction result: {ridge_pred_val}")

    if not np.isfinite(lasso_pred_val) or np.isnan(lasso_pred_val) or lasso_pred_val <= 0:
        raise ValueError(f"Invalid Lasso prediction result: {lasso_pred_val}")

    ridge_mins = round(max(ridge_pred_val, 1.0), 2)
    lasso_mins = round(max(lasso_pred_val, 1.0), 2)

    # Primary model selection: Lasso Regression (performed marginally better on test R2 & RMSE)
    primary_pred_mins = lasso_mins

    return {
        "primary_model": "Lasso Regression",
        "predicted_travel_time_minutes": primary_pred_mins,
        "ridge_prediction_minutes": ridge_mins,
        "lasso_prediction_minutes": lasso_mins,
        "ridge_r2": model_loader.metrics.get("ridge", {}).get("test_r2", 0.9662),
        "lasso_r2": model_loader.metrics.get("lasso", {}).get("test_r2", 0.9662),
        "training_distance_min_km": getattr(model_loader, "training_distance_min_km", 1.0),
        "training_distance_max_km": getattr(model_loader, "training_distance_max_km", 2000.0)
    }
