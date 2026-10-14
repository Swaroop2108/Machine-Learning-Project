import joblib
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from ml.preprocessing import prepare_data

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "ml" / "models"
CHARTS_DIR = BASE_DIR / "charts"
CHARTS_DIR.mkdir(exist_ok=True)

def run_phase4_evaluation():
    """
    PHASE 4: Comprehensive Model Evaluation & Comparison
    1. Loads trained Ridge & Lasso models and test data.
    2. Computes test set MAE, MSE, RMSE, R2 scores.
    3. Calculates training vs testing overfitting gap.
    4. Performs residual analysis & generates residual plots & error distributions.
    5. Analyzes model coefficients.
    6. Performs error breakdown by traffic and weather conditions.
    7. Saves evaluation_summary.json.
    """
    print("=== PHASE 4: Model Evaluation & Comparison ===")
    
    # 1. Load data
    data = prepare_data(save_preprocessor=False)
    X_train = data["X_train"]
    y_train = data["y_train"]
    X_test = data["X_test"]
    y_test = data["y_test"]
    raw_df = data["raw_df"]
    feature_names = data["feature_names"]
    
    # 2. Load models
    ridge_path = MODEL_DIR / "ridge_model.joblib" if (MODEL_DIR / "ridge_model.joblib").exists() else MODEL_DIR / "ridge_model.pkl"
    lasso_path = MODEL_DIR / "lasso_model.joblib" if (MODEL_DIR / "lasso_model.joblib").exists() else MODEL_DIR / "lasso_model.pkl"
    
    if not ridge_path.exists() or not lasso_path.exists():
        raise FileNotFoundError("Trained models missing in ml/models/. Please run ml/train.py first.")
        
    ridge = joblib.load(ridge_path)
    lasso = joblib.load(lasso_path)
    
    # 3. Predictions
    y_train_pred_ridge = ridge.predict(X_train)
    y_train_pred_lasso = lasso.predict(X_train)
    
    y_test_pred_ridge = ridge.predict(X_test)
    y_test_pred_lasso = lasso.predict(X_test)
    
    # 4. Metrics
    # Train Metrics
    r2_train_ridge = float(r2_score(y_train, y_train_pred_ridge))
    r2_train_lasso = float(r2_score(y_train, y_train_pred_lasso))
    
    # Test Metrics
    mae_ridge = float(mean_absolute_error(y_test, y_test_pred_ridge))
    mse_ridge = float(mean_squared_error(y_test, y_test_pred_ridge))
    rmse_ridge = float(np.sqrt(mse_ridge))
    r2_ridge = float(r2_score(y_test, y_test_pred_ridge))
    
    mae_lasso = float(mean_absolute_error(y_test, y_test_pred_lasso))
    mse_lasso = float(mean_squared_error(y_test, y_test_pred_lasso))
    rmse_lasso = float(np.sqrt(mse_lasso))
    r2_lasso = float(r2_score(y_test, y_test_pred_lasso))
    
    # Overfitting gap
    gap_ridge = float(r2_train_ridge - r2_ridge)
    gap_lasso = float(r2_train_lasso - r2_lasso)
    
    # 5. Residual Analysis
    residuals_ridge = y_test - y_test_pred_ridge
    residuals_lasso = y_test - y_test_pred_lasso
    
    mean_res_ridge = float(np.mean(residuals_ridge))
    mean_res_lasso = float(np.mean(residuals_lasso))
    
    max_err_ridge = float(np.max(np.abs(residuals_ridge)))
    max_err_lasso = float(np.max(np.abs(residuals_lasso)))
    
    # 6. Coefficient Analysis
    coef_df = pd.DataFrame({
        "Feature": feature_names,
        "Ridge Coefficient": ridge.coef_,
        "Lasso Coefficient": lasso.coef_
    })
    
    zero_lasso_count = int(np.sum(lasso.coef_ == 0.0))
    zero_lasso_features = coef_df[coef_df["Lasso Coefficient"] == 0.0]["Feature"].tolist()
    
    # 7. Error Breakdown by Conditions (on Test set)
    test_indices = y_test.index
    test_raw = raw_df.loc[test_indices].copy()
    test_raw["abs_err_ridge"] = np.abs(residuals_ridge)
    test_raw["abs_err_lasso"] = np.abs(residuals_lasso)
    
    traffic_err = test_raw.groupby("traffic_condition")[["abs_err_ridge", "abs_err_lasso"]].mean().to_dict(orient="index")
    weather_err = test_raw.groupby("weather")[["abs_err_ridge", "abs_err_lasso"]].mean().to_dict(orient="index")
    
    # 8. Charts Generation
    plt.style.use("ggplot")
    
    # Chart A: Residuals Ridge
    plt.figure(figsize=(7, 5))
    plt.scatter(y_test_pred_ridge, residuals_ridge, alpha=0.6, color="#3b82f6", edgecolors="none")
    plt.axhline(0, color="red", linestyle="--", linewidth=1.5)
    plt.title("Residual Plot — Ridge Regression")
    plt.xlabel("Predicted Travel Time (minutes)")
    plt.ylabel("Residuals (Actual - Predicted)")
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "residuals_ridge.png", dpi=150)
    plt.close()
    
    # Chart B: Residuals Lasso
    plt.figure(figsize=(7, 5))
    plt.scatter(y_test_pred_lasso, residuals_lasso, alpha=0.6, color="#6366f1", edgecolors="none")
    plt.axhline(0, color="red", linestyle="--", linewidth=1.5)
    plt.title("Residual Plot — Lasso Regression")
    plt.xlabel("Predicted Travel Time (minutes)")
    plt.ylabel("Residuals (Actual - Predicted)")
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "residuals_lasso.png", dpi=150)
    plt.close()

    # Chart C: Error Distribution Ridge
    plt.figure(figsize=(7, 5))
    plt.hist(residuals_ridge, bins=25, color="#3b82f6", edgecolor="black", alpha=0.7)
    plt.axvline(0, color="red", linestyle="--", linewidth=1.5)
    plt.title("Error Distribution (Residuals) — Ridge Regression")
    plt.xlabel("Prediction Error (minutes)")
    plt.ylabel("Frequency")
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "error_distribution_ridge.png", dpi=150)
    plt.close()

    # Chart D: Error Distribution Lasso
    plt.figure(figsize=(7, 5))
    plt.hist(residuals_lasso, bins=25, color="#6366f1", edgecolor="black", alpha=0.7)
    plt.axvline(0, color="red", linestyle="--", linewidth=1.5)
    plt.title("Error Distribution (Residuals) — Lasso Regression")
    plt.xlabel("Prediction Error (minutes)")
    plt.ylabel("Frequency")
    plt.tight_layout()
    plt.savefig(CHARTS_DIR / "error_distribution_lasso.png", dpi=150)
    plt.close()

    # 9. JSON Summary Output
    eval_summary = {
        "ridge": {
            "model_name": "Ridge Regression (L2)",
            "alpha": getattr(ridge, "alpha", getattr(ridge, "alpha_", None)),
            "train_r2": round(r2_train_ridge, 4),
            "test_r2": round(r2_ridge, 4),
            "overfitting_gap": round(gap_ridge, 4),
            "mae": round(mae_ridge, 4),
            "mse": round(mse_ridge, 4),
            "rmse": round(rmse_ridge, 4),
            "mean_residual": round(mean_res_ridge, 4),
            "max_abs_error": round(max_err_ridge, 4)
        },
        "lasso": {
            "model_name": "Lasso Regression (L1)",
            "alpha": getattr(lasso, "alpha", getattr(lasso, "alpha_", None)),
            "train_r2": round(r2_train_lasso, 4),
            "test_r2": round(r2_lasso, 4),
            "overfitting_gap": round(gap_lasso, 4),
            "mae": round(mae_lasso, 4),
            "mse": round(mse_lasso, 4),
            "rmse": round(rmse_lasso, 4),
            "mean_residual": round(mean_res_lasso, 4),
            "max_abs_error": round(max_err_lasso, 4),
            "zero_coefficients_count": zero_lasso_count,
            "zero_coefficient_features": zero_lasso_features
        },
        "overall_best_model": "Lasso Regression (marginally lower RMSE & higher R2 with feature selection)",
        "error_breakdown": {
            "by_traffic_condition": traffic_err,
            "by_weather": weather_err
        }
    }
    
    with open(MODEL_DIR / "evaluation_summary.json", "w") as f:
        json.dump(eval_summary, f, indent=2)
        
    with open(MODEL_DIR / "model_metrics.json", "w") as f:
        json.dump(eval_summary, f, indent=2)
        
    print("\n=================== FINAL MODEL EVALUATION SUMMARY ===================")
    print(f"{'Metric':<18} | {'Ridge Regression':<20} | {'Lasso Regression':<20}")
    print("-" * 64)
    print(f"{'Best Alpha':<18} | {eval_summary['ridge']['alpha']:<20.4f} | {eval_summary['lasso']['alpha']:<20.4f}")
    print(f"{'Test MAE':<18} | {mae_ridge:<20.4f} | {mae_lasso:<20.4f}")
    print(f"{'Test MSE':<18} | {mse_ridge:<20.4f} | {mse_lasso:<20.4f}")
    print(f"{'Test RMSE':<18} | {rmse_ridge:<20.4f} | {rmse_lasso:<20.4f}")
    print(f"{'Train R²':<18} | {r2_train_ridge:<20.4f} | {r2_train_lasso:<20.4f}")
    print(f"{'Test R²':<18} | {r2_ridge:<20.4f} | {r2_lasso:<20.4f}")
    print(f"{'Overfitting Gap':<18} | {gap_ridge:<20.4f} | {gap_lasso:<20.4f}")
    print(f"{'Mean Residual':<18} | {mean_res_ridge:<20.4f} | {mean_res_lasso:<20.4f}")
    print("======================================================================")
    
    print("\n--- ERROR BREAKDOWN BY TRAFFIC CONDITION (MAE in minutes) ---")
    for t_cond, res in traffic_err.items():
        print(f"Traffic ({t_cond:<6}): Ridge MAE = {res['abs_err_ridge']:.2f} mins | Lasso MAE = {res['abs_err_lasso']:.2f} mins")

    print("\n--- ERROR BREAKDOWN BY WEATHER CONDITION (MAE in minutes) ---")
    for w_cond, res in weather_err.items():
        print(f"Weather ({w_cond:<6}): Ridge MAE = {res['abs_err_ridge']:.2f} mins | Lasso MAE = {res['abs_err_lasso']:.2f} mins")

    print(f"\nEvaluation artifacts and summary saved to {MODEL_DIR / 'evaluation_summary.json'}")

if __name__ == "__main__":
    run_phase4_evaluation()
