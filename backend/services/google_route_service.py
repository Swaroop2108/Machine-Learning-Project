from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from backend.services.route_service import get_route_details

def format_duration(seconds: float) -> str:
    """Format duration in seconds into clean human-readable text (e.g. '1h 27m' or '45 mins')."""
    total_minutes = int(round(seconds / 60.0))
    hrs = total_minutes // 60
    mins = total_minutes % 60
    if hrs > 0:
        return f"{hrs}h {mins:02d}m" if mins > 0 else f"{hrs}h"
    return f"{total_minutes} mins"

def compute_google_route(
    source: str,
    destination: str,
    departure_datetime_str: Optional[str] = None,
    travel_mode: Optional[str] = "DRIVE",
    traffic_condition: Optional[str] = "Moderate"
) -> Dict[str, Any]:
    """
    Computes real-time road route using OSRM Routing Engine (no API keys required).
    Returns standardized route object with duration, distance, ETA, and geometry adjusted by traffic condition.
    """
    # 1. Parse Departure Datetime
    now = datetime.now()
    if departure_datetime_str:
        try:
            clean_dt = departure_datetime_str.replace("T", " ")
            if ":" in clean_dt:
                parts = clean_dt.split(" ")
                d_part, t_part = parts[0], parts[1]
                dep_dt = datetime.strptime(f"{d_part} {t_part[:5]}", "%Y-%m-%d %H:%M")
            else:
                dep_dt = now
        except Exception:
            dep_dt = now
    else:
        dep_dt = now

    departure_time_display = dep_dt.strftime("%I:%M %p")

    # 2. Query OSRM Routing Engine with mode and traffic condition
    try:
        route_info = get_route_details(source, destination, travel_mode=travel_mode, traffic_condition=traffic_condition)
    except ValueError as ve:
        return {
            "success": False,
            "provider": "OSRM Routing Engine",
            "error_code": "LOCATION_NOT_FOUND",
            "detail": str(ve)
        }

    if not route_info.get("success", True):
        return {
            "success": False,
            "provider": "OSRM Routing Engine",
            "error_code": route_info.get("error_code", "ROUTE_ERROR"),
            "detail": route_info.get("detail", "Route information unavailable.")
        }

    duration_seconds = float(route_info["duration_seconds"])
    duration_minutes = float(route_info["route_duration_minutes"])
    duration_text = format_duration(duration_seconds)
    distance_km = float(route_info["distance_km"])
    distance_meters = float(route_info["distance_meters"])

    eta_dt = dep_dt + timedelta(seconds=duration_seconds)
    eta_display = eta_dt.strftime("%I:%M %p")
    eta_iso = eta_dt.isoformat()

    return {
        "success": True,
        "google_route": {
            "provider": route_info.get("service_used", "OSRM Routing Engine"),
            "source": route_info["source"],
            "destination": route_info["destination"],
            "source_coordinates": route_info.get("source_coordinates", []),
            "destination_coordinates": route_info.get("destination_coordinates", []),
            "travel_mode": travel_mode,
            "traffic_condition": traffic_condition or "Moderate",
            "distance_km": distance_km,
            "distance_meters": distance_meters,
            "duration_seconds": duration_seconds,
            "duration_minutes": duration_minutes,
            "duration_text": duration_text,
            "departure_time": departure_time_display,
            "departure_datetime": dep_dt.isoformat(),
            "estimated_arrival_time": eta_display,
            "iso_arrival_time": eta_iso,
            "encoded_polyline": "",
            "route_geometry": route_info["route_geometry"],
            "steps": route_info.get("steps", [])
        }
    }
