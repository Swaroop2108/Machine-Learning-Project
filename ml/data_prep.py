import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from backend.config import DATASET_PATH

BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_PATH_ML = BASE_DIR / "ml" / "dataset" / "travel_dataset.csv"
DATASET_PATH_ALT = BASE_DIR / "ml" / "dataset" / "travel_time_prediction_dataset.csv"
DATASET_PATH_ROOT = BASE_DIR / "travel_time_prediction_dataset.csv"

def generate_expanded_dataset(seed=42):
    np.random.seed(seed)
    
    bin_configs = [
        (1.0, 50.0, 1000),       # 1-50 km
        (50.0, 100.0, 800),      # 50-100 km
        (100.0, 250.0, 1000),    # 100-250 km
        (250.0, 500.0, 1000),    # 250-500 km
        (500.0, 1000.0, 1000),   # 500-1000 km
        (1000.0, 1500.0, 600),   # 1000-1500 km
        (1500.0, 2000.0, 600)    # 1500-2000 km
    ]
    
    distances = []
    for low, high, count in bin_configs:
        dist_samples = np.random.uniform(low, high, size=count)
        distances.extend(dist_samples)
        
    distances = np.array(distances)
    np.random.shuffle(distances)
    num_samples = len(distances)
    
    traffic_options = ["Low", "Medium", "High"]
    weather_options = ["Clear", "Cloudy", "Rainy", "Foggy"]
    day_options = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    traffic_choices = np.random.choice(traffic_options, size=num_samples, p=[0.35, 0.45, 0.20])
    weather_choices = np.random.choice(weather_options, size=num_samples, p=[0.50, 0.25, 0.15, 0.10])
    day_choices = np.random.choice(day_options, size=num_samples)
    dep_hours = np.random.randint(0, 24, size=num_samples)
    temps_c = np.round(np.random.uniform(15.0, 42.0, size=num_samples), 1)
    
    travel_times = []
    traffic_mult = {"Low": 0.90, "Medium": 1.12, "High": 1.35}
    weather_mult = {"Clear": 1.00, "Cloudy": 1.04, "Rainy": 1.20, "Foggy": 1.28}
    
    for i in range(num_samples):
        dist = distances[i]
        traffic = traffic_choices[i]
        wtr = weather_choices[i]
        hr = dep_hours[i]
        
        if dist <= 15.0:
            base_speed = 32.0
        elif dist <= 50.0:
            base_speed = 48.0
        elif dist <= 250.0:
            base_speed = 68.0
        elif dist <= 1000.0:
            base_speed = 78.0
        else:
            base_speed = 84.0
            
        t_mult = traffic_mult[traffic]
        w_mult = weather_mult[wtr]
        
        if (8 <= hr <= 10) or (17 <= hr <= 19):
            hour_mult = 1.15
        elif (23 <= hr or hr <= 5):
            hour_mult = 0.92
        else:
            hour_mult = 1.00
            
        effective_speed = (base_speed / (t_mult * w_mult * hour_mult))
        raw_driving_minutes = (dist / effective_speed) * 60.0
        
        rest_stop_minutes = 0.0
        if dist > 300.0:
            num_stops = dist / 350.0
            rest_stop_minutes = num_stops * 35.0
            
        total_travel_time = raw_driving_minutes + rest_stop_minutes
        noise = np.random.normal(1.0, 0.03)
        final_time = round(max(total_travel_time * noise, 2.0), 2)
        travel_times.append(final_time)
        
    df = pd.DataFrame({
        "distance_km": np.round(distances, 2),
        "traffic_condition": traffic_choices,
        "weather": weather_choices,
        "day_of_week": day_choices,
        "departure_hour": dep_hours,
        "temperature_c": temps_c,
        "travel_time_minutes": travel_times
    })
    
    DATASET_PATH_ML.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(DATASET_PATH_ML, index=False)
    df.to_csv(DATASET_PATH_ALT, index=False)
    df.to_csv(DATASET_PATH_ROOT, index=False)
    return df

def load_and_explore_dataset(file_path=DATASET_PATH):
    """
    Loads dataset and prints exploratory data analysis details.
    """
    if not file_path.exists():
        generate_expanded_dataset()
    
    df = pd.read_csv(file_path)
    
    summary = {
        "num_rows": len(df),
        "columns": list(df.columns),
        "missing_values": df.isnull().sum().to_dict(),
        "categorical_unique": {
            "traffic_condition": list(df["traffic_condition"].unique()),
            "weather": list(df["weather"].unique()),
            "day_of_week": list(df["day_of_week"].unique())
        },
        "target_stats": {
            "min": float(df["travel_time_minutes"].min()),
            "max": float(df["travel_time_minutes"].max()),
            "mean": float(df["travel_time_minutes"].mean()),
            "std": float(df["travel_time_minutes"].std())
        }
    }
    return df, summary

def get_preprocessor():
    """
    Constructs ColumnTransformer for numerical scaling and categorical encoding.
    """
    num_features = ["distance_km", "departure_hour", "temperature_c"]
    cat_features = ["traffic_condition", "weather", "day_of_week"]

    # Order categories to ensure consistent OneHot encoding
    traffic_categories = ["Low", "Medium", "High"]
    weather_categories = ["Clear", "Cloudy", "Rainy", "Foggy"]
    day_categories = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), num_features),
            ("cat", OneHotEncoder(
                categories=[traffic_categories, weather_categories, day_categories],
                handle_unknown="ignore",
                sparse_output=False
            ), cat_features)
        ]
    )
    return preprocessor

def prepare_data(file_path=DATASET_PATH, test_size=0.2, random_state=42):
    """
    Loads dataset, handles missing values, applies scaling & encoding,
    and returns train/test split.
    """
    df, summary = load_and_explore_dataset(file_path)
    
    # Handle missing values if any exist
    df = df.dropna()
    
    X = df.drop(columns=["travel_time_minutes"])
    y = df["travel_time_minutes"]
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )
    
    preprocessor = get_preprocessor()
    X_train_scaled = preprocessor.fit_transform(X_train)
    X_test_scaled = preprocessor.transform(X_test)
    
    # Extract feature names after encoding
    cat_encoder = preprocessor.named_transformers_["cat"]
    encoded_cat_names = list(cat_encoder.get_feature_names_out(["traffic_condition", "weather", "day_of_week"]))
    feature_names = ["distance_km", "departure_hour", "temperature_c"] + encoded_cat_names
    
    return {
        "X_train": X_train_scaled,
        "X_test": X_test_scaled,
        "y_train": y_train,
        "y_test": y_test,
        "preprocessor": preprocessor,
        "feature_names": feature_names,
        "raw_df": df,
        "summary": summary
    }

if __name__ == "__main__":
    print("Testing Data Preparation Workflow...")
    data = prepare_data()
    print(f"Dataset successfully loaded. Total rows: {data['summary']['num_rows']}")
    print(f"X_train shape: {data['X_train'].shape}, X_test shape: {data['X_test'].shape}")
    print(f"Features ({len(data['feature_names'])}): {data['feature_names']}")
