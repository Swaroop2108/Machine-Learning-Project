import os
import glob
import json
import joblib
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

def check_file_stats(file_path):
    path = Path(file_path)
    if not path.exists():
        return None
    df = pd.read_csv(path)
    stat = path.stat()
    return {
        "path": str(path),
        "size_bytes": stat.st_size,
        "mtime": pd.to_datetime(stat.st_mtime, unit="s").isoformat(),
        "rows": len(df),
        "cols_count": len(df.columns),
        "cols": list(df.columns),
        "dist_min": float(df["distance_km"].min()) if "distance_km" in df else None,
        "dist_max": float(df["distance_km"].max()) if "distance_km" in df else None,
        "dist_mean": float(df["distance_km"].mean()) if "distance_km" in df else None,
        "target_col": "travel_time_minutes" if "travel_time_minutes" in df else ("travel_time" if "travel_time" in df else None),
        "target_min": float(df["travel_time_minutes"].min()) if "travel_time_minutes" in df else None,
        "target_max": float(df["travel_time_minutes"].max()) if "travel_time_minutes" in df else None,
        "target_mean": float(df["travel_time_minutes"].mean()) if "travel_time_minutes" in df else None,
        "target_median": float(df["travel_time_minutes"].median()) if "travel_time_minutes" in df else None,
    }

def run_consistency_investigation():
    print("=== CRITICAL DATASET & MODEL CONSISTENCY INVESTIGATION ===")

    # 1. Inspect exact physical file: ml/dataset/travel_dataset.csv
    target_csv = BASE_DIR / "ml" / "dataset" / "travel_dataset.csv"
    print(f"\n--- 1. PHYSICAL FILE INSPECTION: {target_csv} ---")
    st1 = check_file_stats(target_csv)
    print(json.dumps(st1, indent=2))

    # Read first 5 and last 5 rows of target CSV
    df_curr = pd.read_csv(target_csv)
    print("\nFirst 5 rows of ml/dataset/travel_dataset.csv:")
    print(df_curr.head(5).to_string())
    print("\nLast 5 rows of ml/dataset/travel_dataset.csv:")
    print(df_curr.tail(5).to_string())

    # 2. Search for ALL CSV files across the project
    print("\n--- 2. ALL CSV FILES FOUND IN WORKSPACE ---")
    csv_files = glob.glob(str(BASE_DIR / "**/*.csv"), recursive=True)
    csv_reports = []
    for csv_p in csv_files:
        info = check_file_stats(csv_p)
        if info:
            csv_reports.append(info)
            print(f"Found CSV: {info['path']} | Rows: {info['rows']} | Cols: {info['cols_count']} | Dist Range: [{info['dist_min']}, {info['dist_max']}]")

    # 3 & 4. Inspect Model Files in ml/models/ and ml/saved_models/
    print("\n--- 3. MODEL ARTIFACTS & METADATA INSPECTION ---")
    model_dirs = [BASE_DIR / "ml" / "models", BASE_DIR / "ml" / "saved_models"]
    for m_dir in model_dirs:
        if m_dir.exists():
            print(f"\nDirectory: {m_dir}")
            for f in m_dir.glob("*"):
                print(f"  - {f.name} ({f.stat().st_size} bytes, modified: {pd.to_datetime(f.stat().st_mtime, unit='s').isoformat()})")

    # Load metadata JSON files
    meta_files = [
        BASE_DIR / "ml" / "models" / "model_metrics.json",
        BASE_DIR / "ml" / "models" / "evaluation_summary.json",
        BASE_DIR / "ml" / "models" / "lasso_model_metadata.json",
        BASE_DIR / "ml" / "saved_models" / "model_meta.json",
        BASE_DIR / "ml" / "saved_models" / "model_metrics.json"
    ]
    for mf in meta_files:
        if mf.exists():
            print(f"\nMetadata Content ({mf}):")
            with open(mf, "r") as json_f:
                print(json_f.read())

    # 4 & 5. Inspect Model Expected Features & Preprocessor Parameters
    prep_path = BASE_DIR / "ml" / "models" / "preprocessor.joblib"
    if not prep_path.exists():
        prep_path = BASE_DIR / "ml" / "saved_models" / "preprocessor.pkl"

    if prep_path.exists():
        prep = joblib.load(prep_path)
        print(f"\n--- 4 & 5. PREPROCESSOR INSPECTION ({prep_path.name}) ---")
        num_cols = ["distance_km", "departure_hour", "temperature_c"]
        cat_cols = ["traffic_condition", "weather", "day_of_week"]
        cat_transformer = prep.named_transformers_["cat"]
        cat_feature_names = list(cat_transformer.get_feature_names_out(cat_cols))
        all_features = num_cols + cat_feature_names
        print(f"Total encoded features expected by preprocessor: {len(all_features)}")
        print("Feature Names:", all_features)
        
        num_scaler = prep.named_transformers_["num"]
        print("Distance mean in preprocessor scaler:", num_scaler.mean_[0])
        print("Distance scale (std) in preprocessor scaler:", num_scaler.scale_[0])

    # 6. Check Model Loader runtime loading path
    print("\n--- 6. RUNTIME MODEL LOADER CONFIGURATION ---")
    from backend.model_loader import model_loader
    print(f"ModelLoader is_loaded: {model_loader.is_loaded}")
    print(f"Ridge Model Class: {type(model_loader.ridge_model)}")
    print(f"Lasso Model Class: {type(model_loader.lasso_model)}")
    print(f"Loaded Metrics Summary: {json.dumps(model_loader.metrics, indent=2)}")

if __name__ == "__main__":
    run_consistency_investigation()
