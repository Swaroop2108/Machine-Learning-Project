from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import time
import json
from pathlib import Path

from backend.schemas import (
    FeaturePrepRequest, PredictRequest, PredictResponse, GoogleRouteRequest,
    JourneyDetails, RouteDetails, TravelConditions, PredictionDetails, ModelInfo,
    MonitoringFeedbackRequest
)
from backend import monitoring
from backend.services.route_service import get_route_details, geocode_location
from backend.services.google_route_service import compute_google_route
from backend.services.weather_service import get_weather_data
from backend.services.feature_builder import (
    estimate_traffic_condition,
    classify_route_type,
    compute_rush_hour,
    build_ml_feature_dictionary
)
from backend.prediction import run_model_inference

import requests

router = APIRouter()

VALID_TRAFFIC_CONDITIONS = ["low", "medium", "moderate", "high", "severe"]

@router.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}

@router.get("/api/config")
def get_config():
    """Return environment configuration for frontend integration."""
    return {
        "status": "ok",
        "routing_engine": "OSRM / OpenStreetMap",
        "weather_engine": "Open-Meteo"
    }

@router.get("/api/search-place")
def search_place_endpoint(q: str = Query(..., description="Place, shop, landmark, or business name search query")):
    """
    Nominatim Place Search Endpoint:
    Searches for shop names, business names, landmarks, restaurants, hospitals, colleges, malls, or small places.
    Returns matching places with place_name, display_address, latitude, longitude, and place_type.
    """
    query_str = q.strip()
    if not query_str:
        return {"success": False, "results": [], "detail": "Search query cannot be empty."}

    try:
        url = f"https://nominatim.openstreetmap.org/search?q={requests.utils.quote(query_str)}&format=json&addressdetails=1&limit=10"
        headers = {"User-Agent": "WayVista-JourneyPredictor/1.0"}
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            results = []
            for item in data:
                try:
                    lat = float(item["lat"])
                    lon = float(item["lon"])
                except (ValueError, KeyError):
                    continue
                
                disp_name = item.get("display_name", "")
                addr = item.get("address", {})
                
                # Extract place name
                place_name = (
                    addr.get("amenity") or
                    addr.get("shop") or
                    addr.get("building") or
                    addr.get("tourism") or
                    addr.get("leisure") or
                    addr.get("hospital") or
                    addr.get("school") or
                    addr.get("university") or
                    addr.get("mall") or
                    item.get("name") or
                    disp_name.split(",")[0]
                )
                
                # Extract address parts
                addr_parts = []
                for k in ["road", "suburb", "neighbourhood", "city_district", "city", "town", "village", "county", "state"]:
                    val = addr.get(k)
                    if val and val not in addr_parts and val != place_name:
                        addr_parts.append(val)
                display_address = ", ".join(addr_parts) if addr_parts else disp_name

                place_type = item.get("type", item.get("class", "location"))

                results.append({
                    "place_name": place_name,
                    "display_name": disp_name,
                    "display_address": display_address,
                    "latitude": lat,
                    "longitude": lon,
                    "place_type": place_type,
                    "category": item.get("class", "")
                })

            return {
                "success": True,
                "count": len(results),
                "results": results
            }
    except Exception as e:
        print(f"Nominatim place search notice: {e}")

    return {
        "success": False,
        "results": [],
        "detail": "Place search notice."
    }

@router.post("/api/google-route")
def google_route_endpoint(payload: GoogleRouteRequest):
    """
    Route API Endpoint (OSRM / OpenStreetMap Engine).
    Returns real-time road route duration, distance & geometry without API keys.
    """
    source = payload.source.strip()
    destination = payload.destination.strip()

    if not source:
        raise HTTPException(status_code=400, detail="Please enter a starting location.")
    if not destination:
        raise HTTPException(status_code=400, detail="Please enter a destination.")
    if source.lower() == destination.lower():
        raise HTTPException(status_code=400, detail="Source and destination cannot be identical locations.")

    route_res = compute_google_route(
        source=source,
        destination=destination,
        departure_datetime_str=payload.departure_datetime,
        travel_mode=payload.travel_mode,
        traffic_condition=payload.traffic_condition
    )

    if not route_res.get("success"):
        return {
            "success": False,
            "provider": "OSRM Routing Engine",
            "detail": route_res.get("detail", "Route information could not be loaded."),
            "error_code": route_res.get("error_code", "ROUTE_ERROR")
        }

    return route_res

@router.get("/api/route")
@router.get("/route")
def get_route_endpoint(
    source: str = Query(..., examples=["Hyderabad"]),
    destination: str = Query(..., examples=["Vijayawada"])
):
    """
    Route API Endpoint:
    Obtains coordinates, road distance (km), estimated duration, and path geometry via OSRM.
    """
    if not source.strip():
        raise HTTPException(status_code=400, detail="Please enter a starting location.")
    if not destination.strip():
        raise HTTPException(status_code=400, detail="Please enter a destination.")
    if source.strip().lower() == destination.strip().lower():
        raise HTTPException(status_code=400, detail="Source and destination cannot be identical locations.")

    try:
        route_info = get_route_details(source, destination)
        return route_info
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        print(f"Route API error: {e}")
        raise HTTPException(status_code=503, detail="Route information is temporarily unavailable.")

@router.get("/api/weather")
@router.get("/weather")
def get_weather_endpoint(location: str = Query(..., examples=["Hyderabad"])):
    """
    Weather API Endpoint:
    Obtains real-time/estimated temperature (°C), precipitation (mm), and mapped weather condition via Open-Meteo.
    """
    if not location.strip():
        raise HTTPException(status_code=400, detail="Please enter a location name.")

    try:
        lat, lon, clean_name = geocode_location(location)
        weather_info = get_weather_data(lat, lon, clean_name)
        return weather_info
    except Exception as e:
        print(f"Weather API error: {e}")
        raise HTTPException(status_code=503, detail="Weather information is temporarily unavailable.")

@router.post("/api/feature-prep")
def prepare_features_endpoint(payload: FeaturePrepRequest):
    """
    Feature Preparation API Endpoint.
    """
    try:
        route_info = get_route_details(payload.source, payload.destination)
        dist_km = route_info["distance_km"]
        source_lat, source_lon = route_info["source_coordinates"]
        
        weather_info = get_weather_data(source_lat, source_lon, route_info["source"])
        
        dep_time = payload.departure_time if payload.departure_time else "08:30"
        try:
            dep_hour = int(dep_time.split(":")[0])
        except Exception:
            dep_hour = 8
            
        day = payload.day_of_week if payload.day_of_week else "Monday"
        
        estimated_traffic = payload.traffic_condition if payload.traffic_condition else estimate_traffic_condition(dep_hour, day)
        weather_cond = payload.weather_condition if payload.weather_condition else weather_info["weather_condition"]
        temp_c = weather_info["temperature_c"]
        precip_mm = weather_info["precipitation_mm"]
        
        is_rush = compute_rush_hour(dep_hour, day)
        r_type = classify_route_type(dist_km)
        
        ml_features = build_ml_feature_dictionary(
            distance_km=dist_km,
            traffic_condition=estimated_traffic,
            weather_condition=weather_cond,
            day_of_week=day,
            departure_hour=dep_hour,
            temperature_c=temp_c
        )
        
        return {
            "status": "success",
            "route_info": route_info,
            "weather_info": weather_info,
            "computed_context": {
                "route_type": r_type,
                "is_rush_hour": is_rush,
                "traffic_estimation_method": "Estimated Traffic (based on departure time & day)",
                "precipitation_mm": precip_mm
            },
            "ml_feature_dictionary": ml_features
        }
    except Exception as e:
        print(f"Feature prep error: {e}")
        raise HTTPException(status_code=500, detail=f"Feature preparation failed: {str(e)}")

@router.post("/api/predict")
@router.post("/predict")
def predict_travel_time_endpoint(payload: PredictRequest):
    """
    Phase 6 Real-Time Prediction Endpoint with Lightweight CO6 Monitoring:
    1. Validates user input (source, destination, departure datetime, traffic override).
    2. Geocodes origin & destination and retrieves route information via OSRM / Routing API.
    3. Retrieves weather information via Open-Meteo / Weather API.
    4. Builds feature dictionary and executes ML inference using saved Ridge & Lasso models.
    5. Calculates estimated arrival time (ETA) and returns clean JSON response.
    6. Asynchronously records lightweight monitoring event without exposing sensitive data.
    """
    start_time = time.perf_counter()
    source = payload.source.strip()
    destination = payload.destination.strip()

    # 1. Validate Input
    if not source:
        raise HTTPException(status_code=400, detail="Please enter a starting location.")
    if not destination:
        raise HTTPException(status_code=400, detail="Please enter a destination.")
    if source.lower() == destination.lower():
        raise HTTPException(status_code=400, detail="Source and destination cannot be identical locations.")

    # Validate departure datetime
    dep_dt_str = payload.departure_datetime if payload.departure_datetime else datetime.now().isoformat()
    try:
        # Handle ISO strings with T or space
        clean_dt_str = dep_dt_str.replace("T", " ")
        if ":" in clean_dt_str:
            parts = clean_dt_str.split(" ")
            date_part = parts[0]
            time_part = parts[1]
            dep_datetime = datetime.strptime(f"{date_part} {time_part[:5]}", "%Y-%m-%d %H:%M")
        else:
            dep_datetime = datetime.now()
    except Exception:
        raise HTTPException(status_code=400, detail="Please provide a valid departure time in ISO format (e.g. YYYY-MM-DDTHH:MM:SS).")

    # Validate traffic override if provided
    traffic_override = payload.traffic_condition.strip() if payload.traffic_condition else None
    if traffic_override:
        if traffic_override.lower() not in VALID_TRAFFIC_CONDITIONS:
            raise HTTPException(status_code=400, detail=f"Invalid traffic condition. Allowed values: Low, Medium, Moderate, High, Severe.")

    try:
        # 2. Route Service Lookup
        route_info = get_route_details(source, destination)
        dist_km = route_info["distance_km"]
        route_api_duration = route_info["route_duration_minutes"]
        src_lat, src_lon = route_info["source_coordinates"]

        # 3. Weather Service Lookup
        weather_info = get_weather_data(src_lat, src_lon, route_info["source"])
        temp_c = weather_info["temperature_c"]
        precip_mm = weather_info["precipitation_mm"]
        weather_cond = weather_info["weather_condition"]

        # 4. Process Departure Datetime
        dep_hour = dep_datetime.hour
        day_of_week = dep_datetime.strftime("%A")

        # 5. Traffic Condition & Traffic Source
        if traffic_override:
            mapped_traffic = "Medium" if traffic_override.lower() == "moderate" else traffic_override.capitalize()
            traffic_source = "User Specified"
        else:
            mapped_traffic = estimate_traffic_condition(dep_hour, day_of_week)
            traffic_source = "Estimated Traffic"

        route_type = classify_route_type(dist_km)

        # 6. ML Model Inference
        inference_res = run_model_inference(
            distance_km=dist_km,
            traffic_condition=mapped_traffic,
            weather=weather_cond,
            day_of_week=day_of_week,
            departure_hour=dep_hour,
            temperature_c=temp_c
        )

        pred_mins = inference_res["predicted_travel_time_minutes"]

        # 7. Calculate ETA
        eta_datetime = dep_datetime + timedelta(minutes=pred_mins)
        eta_display_str = eta_datetime.strftime("%I:%M %p")
        eta_iso_str = eta_datetime.isoformat()

        # 8. CO6 Lightweight Monitoring Log (guaranteed never to crash request)
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        pred_id = None
        try:
            pred_id = monitoring.log_prediction(
                model_identifier=inference_res.get("primary_model", "Lasso Regression"),
                processing_duration_ms=duration_ms,
                distance_km=dist_km,
                traffic_condition=mapped_traffic,
                weather_condition=weather_cond,
                departure_hour=dep_hour,
                temperature_c=temp_c,
                day_of_week=day_of_week,
                predicted_travel_time_minutes=pred_mins,
                ridge_prediction_minutes=inference_res.get("ridge_prediction_minutes", pred_mins),
                lasso_prediction_minutes=inference_res.get("lasso_prediction_minutes", pred_mins)
            )
        except Exception as mon_err:
            print(f"Monitoring notice: {mon_err}")

        # 9. Return Clean JSON Response (strictly preserving existing structure)
        return {
            "success": True,
            "journey": {
                "source": route_info["source"],
                "destination": route_info["destination"],
                "departure_datetime": dep_datetime.isoformat(),
                "estimated_arrival_time": eta_display_str,
                "iso_arrival_time": eta_iso_str
            },
            "route": {
                "distance_km": dist_km,
                "route_type": route_type,
                "route_api_duration_minutes": route_api_duration,
                "route_geometry": route_info["route_geometry"],
                "service_used": route_info["service_used"],
                "steps": route_info.get("steps", [])
            },
            "travel_conditions": {
                "traffic_condition": mapped_traffic,
                "traffic_source": traffic_source,
                "weather_condition": weather_cond,
                "temperature_c": temp_c,
                "precipitation_mm": precip_mm
            },
            "prediction": {
                "prediction_id": pred_id,
                "primary_model": inference_res["primary_model"],
                "predicted_travel_time_minutes": pred_mins,
                "ridge_prediction_minutes": inference_res["ridge_prediction_minutes"],
                "lasso_prediction_minutes": inference_res["lasso_prediction_minutes"]
            },
            "model_info": {
                "ridge_r2": inference_res["ridge_r2"],
                "lasso_r2": inference_res["lasso_r2"],
                "training_distance_min_km": inference_res.get("training_distance_min_km", 1.0),
                "training_distance_max_km": inference_res.get("training_distance_max_km", 2000.0)
            }
        }

    except HTTPException as he:
        try:
            monitoring.log_error(
                processing_duration_ms=round((time.perf_counter() - start_time) * 1000, 2),
                error_type="HTTPException",
                error_message=str(he.detail)
            )
        except Exception:
            pass
        raise he
    except ValueError as ve:
        try:
            monitoring.log_error(
                processing_duration_ms=round((time.perf_counter() - start_time) * 1000, 2),
                error_type="ValueError",
                error_message=str(ve)
            )
        except Exception:
            pass
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        try:
            monitoring.log_error(
                processing_duration_ms=round((time.perf_counter() - start_time) * 1000, 2),
                error_type=type(e).__name__,
                error_message=str(e)
            )
        except Exception:
            pass
        print(f"Prediction Pipeline Error: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction system error: {str(e)}")


# =====================================================================
# CO6 PREDICTION MONITORING & CO1–CO6 EXPERIMENT ENDPOINTS
# =====================================================================

@router.get("/api/monitoring/summary")
def get_monitoring_summary_endpoint():
    """
    CO6 Monitoring Endpoint:
    Returns prediction counts, success/failure status, latency aggregates,
    online MAE & RMSE, and input distribution tracking.
    """
    return monitoring.get_monitoring_summary()

@router.get("/api/monitoring/logs")
def get_monitoring_logs_endpoint():
    """
    CO6 Sanitized Logs Endpoint:
    Returns the latest safe monitoring logs stripped of personal information and coordinates.
    """
    summary = monitoring.get_monitoring_summary()
    return {
        "status": "success",
        "total_requests": summary["summary"]["total_requests"],
        "logs": summary.get("recent_logs", [])
    }

@router.post("/api/monitoring/feedback")
def submit_actual_travel_time_endpoint(payload: MonitoringFeedbackRequest):
    """
    CO6 Feedback Endpoint:
    Records verified ground-truth travel time for a historical prediction.
    Enables online tracking of MAE & RMSE over real-world journeys.
    """
    res = monitoring.record_actual_travel_time(
        prediction_id=payload.prediction_id,
        actual_travel_time_minutes=payload.actual_travel_time_minutes
    )
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("detail", "Failed to record feedback."))
    return res

@router.get("/api/ml-experiments")
def get_ml_experiments_summary():
    """
    Academic ML Experiments API:
    Returns consolidated findings for all 6 Course Outcomes (CO1-CO6):
    - CO1: End-to-End Pipeline lifecycle architecture
    - CO2: Ridge and Lasso regularized regression results & coefficients
    - CO3: Decision Tree regression with 5-Fold cross-validation & feature importances
    - CO4: K-Means unsupervised journey clustering profiles & metrics
    - CO5: Comprehensive multi-model evaluation comparison table
    - CO6: Live prediction monitoring summary
    """
    base_dir = Path(__file__).resolve().parent.parent
    reports_dir = base_dir / "ml" / "reports"
    models_dir = base_dir / "ml" / "models"

    # Load comparison report (CO2, CO3, CO5)
    comparison_data = {}
    comp_file = reports_dir / "model_comparison_report.json"
    if comp_file.exists():
        with open(comp_file, "r") as f:
            comparison_data = json.load(f)

    # Load K-means report (CO4)
    kmeans_data = {}
    km_file = reports_dir / "kmeans_clustering_report.json"
    if km_file.exists():
        with open(km_file, "r") as f:
            kmeans_data = json.load(f)

    # Load Decision Tree details (CO3)
    dt_data = {}
    dt_file = reports_dir / "decision_tree_results.json"
    if dt_file.exists():
        with open(dt_file, "r") as f:
            dt_data = json.load(f)

    # Load Ridge metadata
    ridge_data = {}
    rf = models_dir / "ridge_model_metadata.json"
    if rf.exists():
        with open(rf, "r") as f:
            ridge_data = json.load(f)

    # Load Lasso metadata
    lasso_data = {}
    lf = models_dir / "lasso_model_metadata.json"
    if lf.exists():
        with open(lf, "r") as f:
            lasso_data = json.load(f)

    monitoring_summary = monitoring.get_monitoring_summary()

    return {
        "success": True,
        "course_outcomes": {
            "CO1": {
                "title": "End-to-End ML Lifecycle",
                "status": "Operational",
                "dataset_samples": 6000,
                "features_count": 6,
                "preprocessed_feature_dims": 17,
                "deployment": "FastAPI REST API + Leaflet Web Application"
            },
            "CO2": {
                "title": "Ridge and Lasso Regularized Regression",
                "ridge": ridge_data,
                "lasso": lasso_data
            },
            "CO3": {
                "title": "Decision Tree Regression with 5-Fold Cross-Validation",
                "best_hyperparameters": dt_data.get("best_hyperparameters", {}),
                "cv_5fold_metrics": dt_data.get("cv_5fold_metrics", {}),
                "test_metrics": dt_data.get("test_metrics", {}),
                "feature_importances": dt_data.get("feature_importances", {})
            },
            "CO4": {
                "title": "K-Means Unsupervised Journey Clustering",
                "selected_k": kmeans_data.get("selected_k", 3),
                "evaluation_metrics": kmeans_data.get("evaluated_k_metrics", []),
                "cluster_profiles": kmeans_data.get("cluster_profiles", [])
            },
            "CO5": {
                "title": "Model Evaluation & Comparative Analysis",
                "comparison_matrix": comparison_data
            },
            "CO6": {
                "title": "Lightweight Production Monitoring",
                "monitoring_summary": monitoring_summary
            }
        }
    }
