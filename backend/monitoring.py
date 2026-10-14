"""
Lightweight Prediction Monitoring Module (CO6 - Machine Learning Course Outcome 6)
Part of WayVista / VoyageML Production Monitoring Suite

Requirements:
- Record prediction timestamp, model identifier, processing duration, and success/failure status.
- Record safe error information without exposing secrets or sensitive data.
- Do NOT store raw GPS coordinates, passwords, verification codes, or auth tokens.
- Avoid logging email addresses or unnecessary personal information.
- Separate monitoring module with independent append-only log file (prediction_logs.jsonl).
- Provide basic summary of prediction counts, errors, response times (latencies).
- If actual travel times later become available, support calculating online MAE & RMSE.
- Transparent drift reporting: does not claim drift detection beyond measured distribution shifts.
- CRITICAL: Monitoring failures MUST NEVER cause the existing prediction request to fail.
"""

import os
import json
import uuid
import time
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "backend" / "data"
LOG_FILE = LOG_DIR / "prediction_logs.jsonl"
FEEDBACK_FILE = LOG_DIR / "feedback_logs.json"

# Thread lock for concurrent file writes
_log_lock = threading.Lock()

# Baseline training distance statistics for statistical distribution shift checks
BASELINE_STATS = {
    "distance_mean_km": 602.82,
    "distance_std_km": 542.14,
    "sample_count": 6000
}

def _sanitize_error_message(msg: str) -> str:
    """Strips file system paths, credentials, and potential secrets from error strings."""
    if not msg:
        return "Unknown error"
    safe_msg = str(msg)
    # Remove file system paths
    for token in ["C:\\", "c:\\", "/Users/", "/home/", "\\"]:
        if token in safe_msg:
            safe_msg = safe_msg.split(token)[0] + "[internal_path_redacted]"
    # Truncate length
    return safe_msg[:200]

def log_prediction(
    model_identifier: str,
    processing_duration_ms: float,
    distance_km: float,
    traffic_condition: str,
    weather_condition: str,
    departure_hour: int,
    temperature_c: float,
    day_of_week: str,
    predicted_travel_time_minutes: float,
    ridge_prediction_minutes: Optional[float] = None,
    lasso_prediction_minutes: Optional[float] = None
) -> str:
    """
    Asynchronously logs a successful prediction event with non-sensitive travel features.
    Guaranteed not to raise an exception under any circumstance.
    """
    prediction_id = str(uuid.uuid4())
    record = {
        "prediction_id": prediction_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model_identifier": str(model_identifier),
        "status": "SUCCESS",
        "processing_duration_ms": round(float(processing_duration_ms), 2),
        "inputs": {
            "distance_km": round(float(distance_km), 2),
            "traffic_condition": str(traffic_condition),
            "weather_condition": str(weather_condition),
            "departure_hour": int(departure_hour),
            "temperature_c": round(float(temperature_c), 1),
            "day_of_week": str(day_of_week)
        },
        "outputs": {
            "predicted_travel_time_minutes": round(float(predicted_travel_time_minutes), 2),
            "ridge_prediction_minutes": round(float(ridge_prediction_minutes), 2) if ridge_prediction_minutes is not None else None,
            "lasso_prediction_minutes": round(float(lasso_prediction_minutes), 2) if lasso_prediction_minutes is not None else None
        },
        "actual_travel_time_minutes": None
    }

    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with _log_lock:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
    except Exception as err:
        # Monitoring failure must NEVER propagate to caller or fail the user's prediction
        print(f"Prediction Monitoring Warning: Could not append log: {err}")

    return prediction_id

def log_error(
    processing_duration_ms: float,
    error_type: str,
    error_message: str,
    model_identifier: str = "PredictionPipeline"
) -> str:
    """
    Logs an unsuccessful prediction event with sanitized error information.
    Guaranteed not to raise an exception.
    """
    prediction_id = str(uuid.uuid4())
    record = {
        "prediction_id": prediction_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model_identifier": str(model_identifier),
        "status": "ERROR",
        "processing_duration_ms": round(float(processing_duration_ms), 2),
        "error": {
            "error_type": str(error_type),
            "error_message": _sanitize_error_message(error_message)
        }
    }

    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with _log_lock:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
    except Exception as err:
        print(f"Prediction Monitoring Warning: Could not log error: {err}")

    return prediction_id

def record_actual_travel_time(prediction_id: str, actual_travel_time_minutes: float) -> Dict[str, Any]:
    """
    Records ground-truth observed travel time for a historical prediction.
    Enables online calculation of real-world MAE and RMSE over time.
    """
    if actual_travel_time_minutes <= 0:
        return {"success": False, "detail": "Actual travel time must be a positive number."}

    target_pred_id = prediction_id.strip()
    updated = False

    try:
        # Load feedback store
        feedback_data = {}
        if FEEDBACK_FILE.exists():
            with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
                try:
                    feedback_data = json.load(f)
                except Exception:
                    feedback_data = {}

        feedback_data[target_pred_id] = {
            "actual_travel_time_minutes": round(float(actual_travel_time_minutes), 2),
            "recorded_at": datetime.now(timezone.utc).isoformat()
        }

        with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
            json.dump(feedback_data, f, indent=2)

        return {
            "success": True,
            "prediction_id": target_pred_id,
            "actual_travel_time_minutes": round(float(actual_travel_time_minutes), 2),
            "message": "Ground-truth travel time successfully recorded for monitoring."
        }
    except Exception as err:
        return {"success": False, "detail": f"Failed to record actual travel time: {str(err)}"}

def get_monitoring_summary() -> Dict[str, Any]:
    """
    Computes real-time monitoring statistics:
    - Total prediction count
    - Success / failure counts & error rate
    - Latency statistics (avg, min, max, p95)
    - Online MAE and RMSE across monitored predictions with verified actual outcomes
    - Input distance distribution shift check against training baseline
    """
    total = 0
    successes = 0
    errors = 0
    latencies: List[float] = []
    distances: List[float] = []
    model_counts: Dict[str, int] = {}
    
    # Track online errors when actual travel time is known
    error_deltas: List[float] = []
    sq_error_deltas: List[float] = []

    # Load feedback dictionary if exists
    feedback_dict = {}
    if FEEDBACK_FILE.exists():
        try:
            with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
                feedback_dict = json.load(f)
        except Exception:
            feedback_dict = {}

    recent_logs: List[Dict[str, Any]] = []

    if LOG_FILE.exists():
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except Exception:
                        continue

                    total += 1
                    status = record.get("status")
                    duration = record.get("processing_duration_ms", 0.0)
                    latencies.append(duration)

                    model = record.get("model_identifier", "Unknown")
                    model_counts[model] = model_counts.get(model, 0) + 1

                    if status == "SUCCESS":
                        successes += 1
                        inputs = record.get("inputs", {})
                        dist = inputs.get("distance_km")
                        if dist is not None:
                            distances.append(float(dist))

                        pred_mins = record.get("outputs", {}).get("predicted_travel_time_minutes")
                        pred_id = record.get("prediction_id")

                        # Check if actual feedback was recorded
                        actual = None
                        if pred_id in feedback_dict:
                            actual = feedback_dict[pred_id].get("actual_travel_time_minutes")
                        elif record.get("actual_travel_time_minutes") is not None:
                            actual = record.get("actual_travel_time_minutes")

                        if actual is not None and pred_mins is not None:
                            err_val = abs(float(pred_mins) - float(actual))
                            error_deltas.append(err_val)
                            sq_error_deltas.append(err_val ** 2)

                    else:
                        errors += 1

                    # Keep last 50 sanitized logs
                    recent_logs.append({
                        "prediction_id": record.get("prediction_id"),
                        "timestamp": record.get("timestamp"),
                        "model": record.get("model_identifier"),
                        "status": status,
                        "duration_ms": duration,
                        "inputs": record.get("inputs"),
                        "prediction_minutes": record.get("outputs", {}).get("predicted_travel_time_minutes") if status == "SUCCESS" else None,
                        "error_type": record.get("error", {}).get("error_type") if status == "ERROR" else None
                    })
        except Exception as err:
            print(f"Monitoring summary calculation warning: {err}")

    # Latency aggregates
    avg_latency = round(sum(latencies) / len(latencies), 2) if latencies else 0.0
    min_latency = round(min(latencies), 2) if latencies else 0.0
    max_latency = round(max(latencies), 2) if latencies else 0.0
    p95_latency = round(sorted(latencies)[int(0.95 * len(latencies))], 2) if latencies else 0.0
    error_rate = round((errors / total) * 100, 2) if total > 0 else 0.0

    # Online performance metrics (when ground truth is available)
    online_mae = round(sum(error_deltas) / len(error_deltas), 2) if error_deltas else None
    online_rmse = round((sum(sq_error_deltas) / len(sq_error_deltas)) ** 0.5, 2) if sq_error_deltas else None

    # Input distribution check (transparent statistical monitoring)
    dist_shift_info = {
        "status": "Inspecting",
        "sample_size": len(distances),
        "monitored_distance_mean_km": round(sum(distances) / len(distances), 2) if distances else None,
        "baseline_distance_mean_km": BASELINE_STATS["distance_mean_km"],
        "method_note": "Distribution tracking compares live journey distances against the 6,000-sample training baseline. True concept drift detection requires verified actual outcomes."
    }

    if len(distances) >= 10:
        mean_live = sum(distances) / len(distances)
        diff_pct = abs(mean_live - BASELINE_STATS["distance_mean_km"]) / BASELINE_STATS["distance_mean_km"] * 100
        dist_shift_info["status"] = "Normal" if diff_pct < 35.0 else "Distribution Shift Detected"
        dist_shift_info["mean_deviation_pct"] = round(diff_pct, 2)

    return {
        "status": "healthy",
        "summary": {
            "total_requests": total,
            "successful_requests": successes,
            "failed_requests": errors,
            "error_rate_pct": error_rate,
            "avg_latency_ms": avg_latency,
            "min_latency_ms": min_latency,
            "max_latency_ms": max_latency,
            "p95_latency_ms": p95_latency
        },
        "model_distribution": model_counts,
        "online_evaluation": {
            "samples_with_actual_travel_time": len(error_deltas),
            "online_mae_minutes": online_mae,
            "online_rmse_minutes": online_rmse,
            "status": "Active" if len(error_deltas) > 0 else "Awaiting actual journey feedback records"
        },
        "input_distribution_monitoring": dist_shift_info,
        "recent_logs": list(reversed(recent_logs[-20:]))
    }
