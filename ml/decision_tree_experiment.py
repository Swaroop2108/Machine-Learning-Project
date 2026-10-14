"""
Decision Tree Regression Experiment (CO3 - Machine Learning Course Outcome 3)
Part of WayVista / VoyageML ML Experiments Suite

Requirements:
- Use existing travel dataset (ml/dataset/travel_dataset.csv).
- Reuse existing feature definitions & preprocessing approach where appropriate.
- Use same reproducible train/test split (test_size=0.2, random_state=42).
- Fit preprocessing pipeline on training data only (no data leakage).
- Train DecisionTreeRegressor with cross-validation hyperparameter tuning on training data only.
- Evaluate model on held-out test set (MAE, RMSE, R2).
- Record feature importance.
- Save model & preprocessing objects separately from Ridge and Lasso.
- Save results to a separate report/JSON file.
"""

import json
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.tree import DecisionTreeRegressor
from sklearn.model_selection import train_test_split, GridSearchCV, cross_validate, KFold
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from ml.preprocessing import get_preprocessor, load_dataset

BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_PATH = BASE_DIR / "ml" / "dataset" / "travel_dataset.csv"
MODEL_DIR = BASE_DIR / "ml" / "models"
REPORTS_DIR = BASE_DIR / "ml" / "reports"

def run_decision_tree_experiment():
    print("==================================================================")
    print("  CO3 EXPERIMENT: Decision Tree Regression with Cross-Validation  ")
    print("==================================================================")

    # 1. Load dataset (preserving existing dataset)
    df = load_dataset(DATASET_PATH)
    df = df.drop_duplicates()
    print(f"Loaded dataset from: {DATASET_PATH}")
    print(f"Dataset shape: {df.shape}")

    # 2. Features and Target
    target_col = "travel_time_minutes"
    X = df.drop(columns=[target_col])
    y = df[target_col]

    # 3. Same reproducible train/test split (80/20, random_state=42)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    print(f"Train samples: {len(X_train)}, Test samples: {len(X_test)}")

    # 4. Fit preprocessing pipeline on training data ONLY
    preprocessor = get_preprocessor()
    X_train_scaled = preprocessor.fit_transform(X_train)
    X_test_scaled = preprocessor.transform(X_test)

    # Feature names
    cat_encoder = preprocessor.named_transformers_["cat"]
    encoded_cat_names = list(cat_encoder.get_feature_names_out(["traffic_condition", "weather", "day_of_week"]))
    feature_names = ["distance_km", "departure_hour", "temperature_c"] + encoded_cat_names
    print(f"Total features after preprocessing: {len(feature_names)}")

    # 5. Hyperparameter tuning using 5-Fold Cross-Validation on TRAINING data only
    print("\nStarting GridSearchCV for DecisionTreeRegressor...")
    param_grid = {
        "max_depth": [4, 6, 8, 10, 12, 15, None],
        "min_samples_split": [2, 5, 10, 20],
        "min_samples_leaf": [1, 2, 4, 8, 16],
        "max_features": [None, "sqrt"]
    }

    base_dt = DecisionTreeRegressor(random_state=42)
    cv = KFold(n_splits=5, shuffle=True, random_state=42)

    grid_search = GridSearchCV(
        estimator=base_dt,
        param_grid=param_grid,
        scoring="neg_mean_squared_error",
        cv=cv,
        n_jobs=-1,
        refit=True,
        verbose=0
    )

    grid_search.fit(X_train_scaled, y_train)

    best_params = grid_search.best_params_
    best_model: DecisionTreeRegressor = grid_search.best_estimator_
    print(f"Best Hyperparameters found: {best_params}")

    # 6. Detailed 5-fold CV evaluation on training set with best parameters
    cv_results = cross_validate(
        best_model,
        X_train_scaled,
        y_train,
        cv=cv,
        scoring=["r2", "neg_mean_absolute_error", "neg_root_mean_squared_error"],
        return_train_score=True
    )

    cv_r2_mean = float(np.mean(cv_results["test_r2"]))
    cv_r2_std = float(np.std(cv_results["test_r2"]))
    cv_mae_mean = float(-np.mean(cv_results["test_neg_mean_absolute_error"]))
    cv_mae_std = float(np.std(cv_results["test_neg_mean_absolute_error"]))
    cv_rmse_mean = float(-np.mean(cv_results["test_neg_root_mean_squared_error"]))
    cv_rmse_std = float(np.std(cv_results["test_neg_root_mean_squared_error"]))

    # 7. Model Predictions
    y_train_pred = best_model.predict(X_train_scaled)
    y_test_pred = best_model.predict(X_test_scaled)

    # 8. Training Set Metrics
    train_mae = float(mean_absolute_error(y_train, y_train_pred))
    train_mse = float(mean_squared_error(y_train, y_train_pred))
    train_rmse = float(np.sqrt(train_mse))
    train_r2 = float(r2_score(y_train, y_train_pred))

    # 9. Held-Out Test Set Metrics
    test_mae = float(mean_absolute_error(y_test, y_test_pred))
    test_mse = float(mean_squared_error(y_test, y_test_pred))
    test_rmse = float(np.sqrt(test_mse))
    test_r2 = float(r2_score(y_test, y_test_pred))

    # Overfitting gap (Train R2 - Test R2)
    overfitting_gap = float(train_r2 - test_r2)

    # 10. Feature Importance
    importances = best_model.feature_importances_
    feature_importance_dict = {
        feat: round(float(imp), 6)
        for feat, imp in sorted(zip(feature_names, importances), key=lambda x: x[1], reverse=True)
    }

    # 11. Print comprehensive results
    print("\n---------------- MODEL PERFORMANCE SUMMARY ----------------")
    print(f"Train R²:        {train_r2:.4f}")
    print(f"Train MAE:       {train_mae:.4f} mins")
    print(f"Train RMSE:      {train_rmse:.4f} mins")
    print("-----------------------------------------------------------")
    print(f"5-Fold CV R²:    {cv_r2_mean:.4f} (+/- {cv_r2_std:.4f})")
    print(f"5-Fold CV MAE:   {cv_mae_mean:.4f} mins (+/- {cv_mae_std:.4f})")
    print(f"5-Fold CV RMSE:  {cv_rmse_mean:.4f} mins (+/- {cv_rmse_std:.4f})")
    print("-----------------------------------------------------------")
    print(f"Test R²:         {test_r2:.4f}")
    print(f"Test MAE:        {test_mae:.4f} mins")
    print(f"Test MSE:        {test_mse:.4f}")
    print(f"Test RMSE:       {test_rmse:.4f} mins")
    print(f"Overfitting Gap: {overfitting_gap:.4f}")
    print("-----------------------------------------------------------")
    print("Top Feature Importances:")
    for k, v in list(feature_importance_dict.items())[:6]:
        print(f"  - {k:<25}: {v:.4f}")

    # 12. Save Model & Preprocessor separately (NEVER overwrite Ridge/Lasso files)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    dt_model_path_joblib = MODEL_DIR / "decision_tree_model.joblib"
    dt_model_path_pkl = MODEL_DIR / "decision_tree_model.pkl"
    dt_preprocessor_path = MODEL_DIR / "decision_tree_preprocessor.joblib"

    joblib.dump(best_model, dt_model_path_joblib)
    joblib.dump(best_model, dt_model_path_pkl)
    joblib.dump(preprocessor, dt_preprocessor_path)

    # 13. Save Metadata and Detailed Report
    dist_min = float(df["distance_km"].min())
    dist_max = float(df["distance_km"].max())

    dt_metadata = {
        "model_name": "Decision Tree Regressor (CART)",
        "course_outcome": "CO3 — Decision Tree Regression",
        "random_state": 42,
        "best_hyperparameters": best_params,
        "tree_depth": int(best_model.get_depth()),
        "leaf_count": int(best_model.get_n_leaves()),
        "train_metrics": {
            "mae": round(train_mae, 4),
            "mse": round(train_mse, 4),
            "rmse": round(train_rmse, 4),
            "r2": round(train_r2, 4)
        },
        "cv_5fold_metrics": {
            "r2_mean": round(cv_r2_mean, 4),
            "r2_std": round(cv_r2_std, 4),
            "mae_mean": round(cv_mae_mean, 4),
            "mae_std": round(cv_mae_std, 4),
            "rmse_mean": round(cv_rmse_mean, 4),
            "rmse_std": round(cv_rmse_std, 4)
        },
        "test_metrics": {
            "mae": round(test_mae, 4),
            "mse": round(test_mse, 4),
            "rmse": round(test_rmse, 4),
            "r2": round(test_r2, 4)
        },
        "overfitting_gap": round(overfitting_gap, 4),
        "feature_importances": feature_importance_dict,
        "training_distance_min_km": round(dist_min, 2),
        "training_distance_max_km": round(dist_max, 2),
        "total_samples": len(df),
        "train_samples": len(X_train),
        "test_samples": len(X_test)
    }

    metadata_file = MODEL_DIR / "decision_tree_metadata.json"
    with open(metadata_file, "w") as f:
        json.dump(dt_metadata, f, indent=2)

    report_file = REPORTS_DIR / "decision_tree_results.json"
    with open(report_file, "w") as f:
        json.dump(dt_metadata, f, indent=2)

    print(f"\n[SUCCESS] Model artifacts saved to:")
    print(f"  - {dt_model_path_joblib}")
    print(f"  - {dt_model_path_pkl}")
    print(f"  - {dt_preprocessor_path}")
    print(f"  - {metadata_file}")
    print(f"  - {report_file}")

    return dt_metadata

if __name__ == "__main__":
    run_decision_tree_experiment()
