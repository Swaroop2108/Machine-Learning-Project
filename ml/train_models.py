import joblib
import json
import numpy as np
from sklearn.linear_model import RidgeCV, LassoCV, Ridge, Lasso
from backend.config import MODEL_DIR
from ml.data_prep import prepare_data

def train_and_save_models():
    """
    Trains Ridge Regression and Lasso Regression models,
    tunes regularization hyperparameters, and persists model artifacts.
    """
    print("--- PHASE 3: Training Ridge and Lasso Regression Models ---")
    
    # 1. Prepare data
    data = prepare_data()
    X_train = data["X_train"]
    y_train = data["y_train"]
    X_test = data["X_test"]
    y_test = data["y_test"]
    preprocessor = data["preprocessor"]
    feature_names = data["feature_names"]
    
    # 2. Define alpha hyperparameter grid
    alphas = np.logspace(-3, 3, 100)
    
    # 3. Train Ridge Regression with Cross-Validation
    print("Fitting Ridge Regression model with cross-validation...")
    ridge_cv = RidgeCV(alphas=alphas, cv=5, scoring="neg_mean_squared_error")
    ridge_cv.fit(X_train, y_train)
    best_alpha_ridge = float(ridge_cv.alpha_)
    
    # Final Ridge Model
    ridge_model = Ridge(alpha=best_alpha_ridge, random_state=42)
    ridge_model.fit(X_train, y_train)
    print(f"-> Ridge Model trained. Optimal alpha: {best_alpha_ridge:.4f}")
    
    # 4. Train Lasso Regression with Cross-Validation
    print("Fitting Lasso Regression model with cross-validation...")
    lasso_cv = LassoCV(alphas=alphas, cv=5, max_iter=10000, random_state=42)
    lasso_cv.fit(X_train, y_train)
    best_alpha_lasso = float(lasso_cv.alpha_)
    
    # Final Lasso Model
    lasso_model = Lasso(alpha=best_alpha_lasso, max_iter=10000, random_state=42)
    lasso_model.fit(X_train, y_train)
    print(f"-> Lasso Model trained. Optimal alpha: {best_alpha_lasso:.4f}")
    
    # 5. Ensure MODEL_DIR exists and save artifacts
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    
    ridge_path = MODEL_DIR / "ridge_model.pkl"
    lasso_path = MODEL_DIR / "lasso_model.pkl"
    preprocessor_path = MODEL_DIR / "preprocessor.pkl"
    meta_path = MODEL_DIR / "model_meta.json"
    
    joblib.dump(ridge_model, ridge_path)
    joblib.dump(lasso_model, lasso_path)
    joblib.dump(preprocessor, preprocessor_path)
    
    metadata = {
        "feature_names": feature_names,
        "ridge": {
            "alpha": best_alpha_ridge,
            "intercept": float(ridge_model.intercept_),
            "coefficients": dict(zip(feature_names, [float(c) for c in ridge_model.coef_]))
        },
        "lasso": {
            "alpha": best_alpha_lasso,
            "intercept": float(lasso_model.intercept_),
            "coefficients": dict(zip(feature_names, [float(c) for c in lasso_model.coef_]))
        }
    }
    
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
        
    print(f"Model artifacts successfully saved to {MODEL_DIR}")
    return {
        "ridge_model": ridge_model,
        "lasso_model": lasso_model,
        "preprocessor": preprocessor,
        "data": data,
        "metadata": metadata
    }

if __name__ == "__main__":
    train_and_save_models()
