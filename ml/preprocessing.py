import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer

BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_PATH = BASE_DIR / "ml" / "dataset" / "travel_dataset.csv"
MODEL_DIR = BASE_DIR / "ml" / "models"

def load_dataset(file_path=DATASET_PATH):
    """
    1. Loads dataset from CSV file.
    """
    if not file_path.exists():
        # Alternative fallback path
        alt_path = BASE_DIR / "ml" / "dataset" / "travel_time_prediction_dataset.csv"
        if alt_path.exists():
            file_path = alt_path
        else:
            raise FileNotFoundError(f"Dataset file not found at {file_path}")
    return pd.read_csv(file_path)

def get_preprocessor():
    """
    Creates Scikit-learn ColumnTransformer for numerical scaling and categorical encoding.
    """
    num_features = ["distance_km", "departure_hour", "temperature_c"]
    cat_features = ["traffic_condition", "weather", "day_of_week"]

    traffic_categories = ["Low", "Medium", "High"]
    weather_categories = ["Clear", "Cloudy", "Rainy", "Foggy"]
    day_categories = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), num_features),
            ("cat", OneHotEncoder(
                categories=[traffic_categories, weather_categories, day_categories],
                handle_unknown="ignore",
                sparse_output=False
            ), cat_features)
        ]
    )

def prepare_data(file_path=DATASET_PATH, test_size=0.2, random_state=42, save_preprocessor=True):
    """
    Executes full Phase 2 data preparation pipeline:
    - Loads dataset & checks duplicate rows
    - Selects features & target (travel_time_minutes)
    - Performs 80/20 train/test split
    - Fits preprocessor ONLY on X_train to prevent data leakage
    - Transforms X_train & X_test
    - Saves fitted preprocessor object to ml/models/preprocessor.pkl
    """
    df = load_dataset(file_path)
    
    # Remove duplicate rows if any exist
    df = df.drop_duplicates()
    
    # Target column
    target_col = "travel_time_minutes"
    
    # Input features X and target y
    X = df.drop(columns=[target_col])
    y = df[target_col]
    
    # 80/20 Train/Test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )
    
    # Initialize ColumnTransformer
    preprocessor = get_preprocessor()
    
    # Fit scaler & encoder ONLY on training data to avoid data leakage
    X_train_scaled = preprocessor.fit_transform(X_train)
    X_test_scaled = preprocessor.transform(X_test)
    
    # Save fitted preprocessor object into ml/models/
    if save_preprocessor:
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(preprocessor, MODEL_DIR / "preprocessor.pkl")
    
    return {
        "X_train": X_train_scaled,
        "X_test": X_test_scaled,
        "y_train": y_train,
        "y_test": y_test,
        "preprocessor": preprocessor,
        "raw_df": df,
        "feature_names": ["distance_km", "departure_hour", "temperature_c"] + list(preprocessor.named_transformers_["cat"].get_feature_names_out())
    }

if __name__ == "__main__":
    print("Testing Phase 2 Preprocessing Pipeline...")
    data = prepare_data()
    print(f"-> Preprocessing successful!")
    print(f"-> Total Rows: {len(data['raw_df'])}")
    print(f"-> Training Set X: {data['X_train'].shape}, y: {data['y_train'].shape}")
    print(f"-> Testing Set X: {data['X_test'].shape}, y: {data['y_test'].shape}")
    print(f"-> Preprocessor saved to {MODEL_DIR / 'preprocessor.pkl'}")
