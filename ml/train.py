import joblib
import json
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.linear_model import RidgeCV, LassoCV, Ridge, Lasso
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from ml.preprocessing import prepare_data

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "ml" / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

def train_and_evaluate():
    """
    Phase 3: Ridge & Lasso Model Development Workflow:
    1. Loads dataset & preprocessing pipeline without data leakage.
    2. Performs 5-fold cross-validation tuning for Ridge & Lasso.
    3. Computes training & testing metrics (MAE, MSE, RMSE, R2).
    4. Analyzes feature coefficients and Lasso zero-coefficient selection.
    5. Saves joblib model artifacts and JSON metadata.
    """
    print("=== PHASE 3: Ridge & Lasso Model Development ===")
    
    # 1. Load prepared data
    data = prepare_data(save_preprocessor=True)
    X_train = data["X_train"]
    y_train = data["y_train"]
    X_test = data["X_test"]
    y_test = data["y_test"]
    feature_names = data["feature_names"]
    
    # Save preprocessor as preprocessor.joblib & preprocessor.pkl
    joblib.dump(data["preprocessor"], MODEL_DIR / "preprocessor.joblib")
    joblib.dump(data["preprocessor"], MODEL_DIR / "preprocessor.pkl")
    
    # Define range of alphas across log space
    alphas = np.logspace(-3, 3, 100)
    
    # 2. Ridge Regression Training (L2 Regularization)
    print("\n--- Training Ridge Regression (L2) ---")
    ridge_cv = RidgeCV(alphas=alphas, cv=5, scoring="neg_mean_squared_error")
    ridge_cv.fit(X_train, y_train)
    best_alpha_ridge = float(ridge_cv.alpha_)
    
    ridge_model = Ridge(alpha=best_alpha_ridge, random_state=42)
    ridge_model.fit(X_train, y_train)
    print(f"Optimal Ridge Alpha (L2): {best_alpha_ridge:.4f}")
    
    # 3. Lasso Regression Training (L1 Regularization)
    print("\n--- Training Lasso Regression (L1) ---")
    lasso_cv = LassoCV(alphas=alphas, cv=5, max_iter=20000, tol=1e-4, random_state=42)
    lasso_cv.fit(X_train, y_train)
    best_alpha_lasso = float(lasso_cv.alpha_)
    
    lasso_model = Lasso(alpha=best_alpha_lasso, max_iter=20000, tol=1e-4, random_state=42)
    lasso_model.fit(X_train, y_train)
    print(f"Optimal Lasso Alpha (L1): {best_alpha_lasso:.4f}")
    
    # 4. Model Predictions
    # Training Set Predictions
    y_train_pred_ridge = ridge_model.predict(X_train)
    y_train_pred_lasso = lasso_model.predict(X_train)
    
    # Test Set Predictions
    y_test_pred_ridge = ridge_model.predict(X_test)
    y_test_pred_lasso = lasso_model.predict(X_test)
    
    # 5. Metrics Calculation
    # Ridge Metrics
    train_mae_ridge = float(mean_absolute_error(y_train, y_train_pred_ridge))
    train_r2_ridge = float(r2_score(y_train, y_train_pred_ridge))
    
    test_mae_ridge = float(mean_absolute_error(y_test, y_test_pred_ridge))
    test_mse_ridge = float(mean_squared_error(y_test, y_test_pred_ridge))
    test_rmse_ridge = float(np.sqrt(test_mse_ridge))
    test_r2_ridge = float(r2_score(y_test, y_test_pred_ridge))
    
    # Lasso Metrics
    train_mae_lasso = float(mean_absolute_error(y_train, y_train_pred_lasso))
    train_r2_lasso = float(r2_score(y_train, y_train_pred_lasso))
    
    test_mae_lasso = float(mean_absolute_error(y_test, y_test_pred_lasso))
    test_mse_lasso = float(mean_squared_error(y_test, y_test_pred_lasso))
    test_rmse_lasso = float(np.sqrt(test_mse_lasso))
    test_r2_lasso = float(r2_score(y_test, y_test_pred_lasso))
    
    # 6. Coefficient Analysis
    ridge_coefs = dict(zip(feature_names, [float(c) for c in ridge_model.coef_]))
    lasso_coefs = dict(zip(feature_names, [float(c) for c in lasso_model.coef_]))
    
    zero_lasso_features = [feat for feat, coef in lasso_coefs.items() if abs(coef) == 0.0]
    nonzero_lasso_features = [feat for feat, coef in lasso_coefs.items() if abs(coef) > 0.0]
    
    # 7. Print Performance Summary
    print("\n=================== MODEL PERFORMANCE EVALUATION ===================")
    print(f"{'Metric':<15} | {'Ridge Regression':<20} | {'Lasso Regression':<20}")
    print("-" * 62)
    print(f"{'Train MAE':<15} | {train_mae_ridge:<20.4f} | {train_mae_lasso:<20.4f}")
    print(f"{'Test MAE':<15} | {test_mae_ridge:<20.4f} | {test_mae_lasso:<20.4f}")
    print(f"{'Test MSE':<15} | {test_mse_ridge:<20.4f} | {test_mse_lasso:<20.4f}")
    print(f"{'Test RMSE':<15} | {test_rmse_ridge:<20.4f} | {test_rmse_lasso:<20.4f}")
    print(f"{'Train R²':<15} | {train_r2_ridge:<20.4f} | {train_r2_lasso:<20.4f}")
    print(f"{'Test R²':<15} | {test_r2_ridge:<20.4f} | {test_r2_lasso:<20.4f}")
    print("====================================================================")
    
    print("\n--- LASSO FEATURE SELECTION ---")
    print(f"Total Features: {len(feature_names)}")
    print(f"Non-Zero Lasso Features ({len(nonzero_lasso_features)}): {nonzero_lasso_features}")
    print(f"Zero Lasso Features ({len(zero_lasso_features)}): {zero_lasso_features}")
    
    # 8. Save Models & Metadata (in both ml/models/ and ml/saved_models/)
    ALT_MODEL_DIR = BASE_DIR / "ml" / "saved_models"
    ALT_MODEL_DIR.mkdir(parents=True, exist_ok=True)

    dist_min = float(data["raw_df"]["distance_km"].min())
    dist_max = float(data["raw_df"]["distance_km"].max())

    for target_dir in [MODEL_DIR, ALT_MODEL_DIR]:
        joblib.dump(ridge_model, target_dir / "ridge_model.joblib")
        joblib.dump(ridge_model, target_dir / "ridge_model.pkl")
        joblib.dump(lasso_model, target_dir / "lasso_model.joblib")
        joblib.dump(lasso_model, target_dir / "lasso_model.pkl")
        joblib.dump(data["preprocessor"], target_dir / "preprocessor.joblib")
        joblib.dump(data["preprocessor"], target_dir / "preprocessor.pkl")

    ridge_meta = {
        "model_name": "Ridge Regression (L2 Regularization)",
        "best_alpha": best_alpha_ridge,
        "intercept": float(ridge_model.intercept_),
        "train_mae": round(train_mae_ridge, 4),
        "test_mae": round(test_mae_ridge, 4),
        "test_mse": round(test_mse_ridge, 4),
        "test_rmse": round(test_rmse_ridge, 4),
        "train_r2": round(train_r2_ridge, 4),
        "test_r2": round(test_r2_ridge, 4),
        "training_distance_min_km": round(dist_min, 2),
        "training_distance_max_km": round(dist_max, 2),
        "coefficients": ridge_coefs
    }
    
    lasso_meta = {
        "model_name": "Lasso Regression (L1 Regularization)",
        "best_alpha": best_alpha_lasso,
        "intercept": float(lasso_model.intercept_),
        "train_mae": round(train_mae_lasso, 4),
        "test_mae": round(test_mae_lasso, 4),
        "test_mse": round(test_mse_lasso, 4),
        "test_rmse": round(test_rmse_lasso, 4),
        "train_r2": round(train_r2_lasso, 4),
        "test_r2": round(test_r2_lasso, 4),
        "training_distance_min_km": round(dist_min, 2),
        "training_distance_max_km": round(dist_max, 2),
        "coefficients": lasso_coefs,
        "zero_coefficient_features": zero_lasso_features,
        "nonzero_coefficient_count": len(nonzero_lasso_features)
    }

    summary_metrics = {
        "ridge": {
            "test_r2": round(test_r2_ridge, 4),
            "train_r2": round(train_r2_ridge, 4),
            "mae": round(test_mae_ridge, 4),
            "mse": round(test_mse_ridge, 4),
            "rmse": round(test_rmse_ridge, 4),
            "alpha": best_alpha_ridge
        },
        "lasso": {
            "test_r2": round(test_r2_lasso, 4),
            "train_r2": round(train_r2_lasso, 4),
            "mae": round(test_mae_lasso, 4),
            "mse": round(test_mse_lasso, 4),
            "rmse": round(test_rmse_lasso, 4),
            "alpha": best_alpha_lasso
        },
        "training_distance_min_km": round(dist_min, 2),
        "training_distance_max_km": round(dist_max, 2),
        "total_samples": len(data["raw_df"])
    }
    
    for target_dir in [MODEL_DIR, ALT_MODEL_DIR]:
        with open(target_dir / "ridge_model_metadata.json", "w") as f:
            json.dump(ridge_meta, f, indent=2)
        with open(target_dir / "lasso_model_metadata.json", "w") as f:
            json.dump(lasso_meta, f, indent=2)
        with open(target_dir / "evaluation_summary.json", "w") as f:
            json.dump(summary_metrics, f, indent=2)
        with open(target_dir / "model_metrics.json", "w") as f:
            json.dump(summary_metrics, f, indent=2)
        with open(target_dir / "model_meta.json", "w") as f:
            json.dump(summary_metrics, f, indent=2)
        
    print(f"\nModel artifacts and metadata saved in {MODEL_DIR} and {ALT_MODEL_DIR}")
    
    return {
        "ridge_model": ridge_model,
        "lasso_model": lasso_model,
        "ridge_meta": ridge_meta,
        "lasso_meta": lasso_meta,
        "X_test": X_test,
        "y_test": y_test,
        "y_test_pred_ridge": y_test_pred_ridge,
        "y_test_pred_lasso": y_test_pred_lasso
    }

if __name__ == "__main__":
    train_and_evaluate()
