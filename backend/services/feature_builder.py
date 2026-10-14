from datetime import datetime
from typing import Dict, Any

def compute_rush_hour(departure_hour: int, day_of_week: str) -> bool:
    """
    Rush hour definition:
    - Weekdays only (Monday to Friday)
    - Morning Peak: 7 AM to 9 AM (hours 7, 8, 9)
    - Evening Peak: 4 PM to 7 PM (hours 16, 17, 18, 19)
    """
    is_weekday = day_of_week.capitalize() in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    is_morning_rush = 7 <= departure_hour <= 9
    is_evening_rush = 16 <= departure_hour <= 19
    return is_weekday and (is_morning_rush or is_evening_rush)

def estimate_traffic_condition(departure_hour: int, day_of_week: str) -> str:
    """
    Clearly named simple traffic estimation method based on departure time and day of week.
    Returns: 'High', 'Medium', or 'Low'.
    """
    is_rush = compute_rush_hour(departure_hour, day_of_week)
    if is_rush:
        return "High"
    
    is_weekend = day_of_week.capitalize() in ["Saturday", "Sunday"]
    is_night = departure_hour >= 21 or departure_hour < 7
    
    if is_night or is_weekend:
        return "Low"
    
    return "Medium"

def classify_route_type(distance_km: float) -> str:
    """
    Classifies route type based on distance.
    - distance > 50 km -> Highway / Expressway
    - distance < 15 km -> City / Urban
    - 15 - 50 km -> Mixed
    """
    if distance_km > 50.0:
        return "Highway"
    elif distance_km < 15.0:
        return "City/Urban"
    return "Mixed"

def build_ml_feature_dictionary(distance_km: float, traffic_condition: str, weather_condition: str,
                                day_of_week: str, departure_hour: int, temperature_c: float) -> Dict[str, Any]:
    """
    Constructs exact feature dictionary required by trained ML preprocessor pipeline:
    - distance_km
    - traffic_condition ('Low', 'Medium', 'High')
    - weather ('Clear', 'Cloudy', 'Rainy', 'Foggy')
    - day_of_week ('Monday' - 'Sunday')
    - departure_hour (0 - 23)
    - temperature_c
    """
    return {
        "distance_km": float(distance_km),
        "traffic_condition": str(traffic_condition).capitalize(),
        "weather": str(weather_condition).capitalize(),
        "day_of_week": str(day_of_week).capitalize(),
        "departure_hour": int(departure_hour),
        "temperature_c": float(temperature_c)
    }
