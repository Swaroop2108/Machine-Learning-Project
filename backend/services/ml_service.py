import joblib
import json
import pandas as pd
from backend.config import MODEL_DIR

class MLPredictionService:
    def __init__(self):
        self.ridge_model = None
        self.lasso_model = None
        self.preprocessor = None
        self.metrics = {}
        self.metadata = {}
        self.is_loaded = False
        self.load_artifacts()

    def load_artifacts(self):
        """Loads trained Ridge, Lasso models, preprocessor, and metrics from disk."""
        ridge_path = MODEL_DIR / "ridge_model.pkl"
        lasso_path = MODEL_DIR / "lasso_model.pkl"
        preprocessor_path = MODEL_DIR / "preprocessor.pkl"
        metrics_path = MODEL_DIR / "metrics.json"
        meta_path = MODEL_DIR / "model_meta.json"

        if not (ridge_path.exists() and lasso_path.exists() and preprocessor_path.exists()):
            raise FileNotFoundError(
                f"Model artifacts missing in {MODEL_DIR}. Please run ml/train_models.py first."
            )

        self.ridge_model = joblib.load(ridge_path)
        self.lasso_model = joblib.load(lasso_path)
        self.preprocessor = joblib.load(preprocessor_path)

        if metrics_path.exists():
            with open(metrics_path, "r") as f:
                self.metrics = json.load(f)

        if meta_path.exists():
            with open(meta_path, "r") as f:
                self.metadata = json.load(f)

        self.is_loaded = True
        print("ML models and preprocessor successfully loaded into memory.")

    def predict(self, distance_km: float, traffic_condition: str, weather: str,
                day_of_week: str, departure_hour: int, temperature_c: float):
        """
        Runs ML prediction pipeline for both Ridge and Lasso models.
        """
        if not self.is_loaded:
            self.load_artifacts()

        # Construct single-row DataFrame matching training column names
        input_data = pd.DataFrame([{
            "distance_km": float(distance_km),
            "traffic_condition": str(traffic_condition).capitalize(),
            "weather": str(weather).capitalize(),
            "day_of_week": str(day_of_week).capitalize(),
            "departure_hour": int(departure_hour),
            "temperature_c": float(temperature_c)
        }])

        # Transform inputs using fitted preprocessor
        X_scaled = self.preprocessor.transform(input_data)

        # Generate predictions (ensure non-negative outputs)
        ridge_pred_val = float(self.ridge_model.predict(X_scaled)[0])
        lasso_pred_val = float(self.lasso_model.predict(X_scaled)[0])

        ridge_pred_minutes = round(max(ridge_pred_val, 1.0), 2)
        lasso_pred_minutes = round(max(lasso_pred_val, 1.0), 2)

        return {
            "inputs": {
                "distance_km": distance_km,
                "traffic_condition": traffic_condition,
                "weather": weather,
                "day_of_week": day_of_week,
                "departure_hour": departure_hour,
                "temperature_c": temperature_c
            },
            "ridge_prediction_minutes": ridge_pred_minutes,
            "lasso_prediction_minutes": lasso_pred_minutes,
            "difference_minutes": round(abs(ridge_pred_minutes - lasso_pred_minutes), 2)
        }

# Global service instance
ml_service = MLPredictionService()
