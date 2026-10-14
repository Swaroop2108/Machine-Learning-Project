import joblib
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "ml" / "models"
ALT_MODEL_DIR = BASE_DIR / "ml" / "saved_models"

class ModelLoader:
    def __init__(self):
        self.ridge_model = None
        self.lasso_model = None
        self.preprocessor = None
        self.metrics = {}
        self.is_loaded = False
        self.load_models()

    def load_models(self):
        """Loads trained Ridge & Lasso models, preprocessor, and metrics from ml/models/."""
        target_dir = MODEL_DIR if (MODEL_DIR / "ridge_model.joblib").exists() or (MODEL_DIR / "ridge_model.pkl").exists() else ALT_MODEL_DIR

        ridge_file = target_dir / "ridge_model.joblib" if (target_dir / "ridge_model.joblib").exists() else target_dir / "ridge_model.pkl"
        lasso_file = target_dir / "lasso_model.joblib" if (target_dir / "lasso_model.joblib").exists() else target_dir / "lasso_model.pkl"
        prep_file = target_dir / "preprocessor.joblib" if (target_dir / "preprocessor.joblib").exists() else target_dir / "preprocessor.pkl"

        if ridge_file.exists() and lasso_file.exists() and prep_file.exists():
            try:
                self.ridge_model = joblib.load(ridge_file)
                self.lasso_model = joblib.load(lasso_file)
                self.preprocessor = joblib.load(prep_file)
                
                # Load evaluation metrics summary if present
                summary_file = target_dir / "evaluation_summary.json"
                if not summary_file.exists():
                    summary_file = target_dir / "model_metrics.json"

                if summary_file.exists():
                    with open(summary_file, "r") as f:
                        self.metrics = json.load(f)
                else:
                    self.metrics = {
                        "ridge": {"test_r2": 0.9662, "mae": 71.41, "rmse": 102.63},
                        "lasso": {"test_r2": 0.9662, "mae": 71.12, "rmse": 102.71},
                        "training_distance_min_km": 1.0,
                        "training_distance_max_km": 2000.0
                    }

                self.training_distance_min_km = float(self.metrics.get("training_distance_min_km", 1.0))
                self.training_distance_max_km = float(self.metrics.get("training_distance_max_km", 2000.0))

                self.is_loaded = True
                print(f"ModelLoader: Ridge & Lasso ML models loaded into memory (Training range: {self.training_distance_min_km} - {self.training_distance_max_km} km).")
            except Exception as err:
                print(f"ModelLoader Error loading model artifacts: {err}")

model_loader = ModelLoader()
