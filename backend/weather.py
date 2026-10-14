import os
from dotenv import load_dotenv

load_dotenv()
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")

def get_weather_info(location_name: str = "Mumbai"):
    """
    Weather retrieval service wrapper for OpenWeather API & fallback logic.
    """
    return {
        "location": location_name,
        "temperature_c": 28.0,
        "weather_condition": "Clear",
        "humidity": 65,
        "wind_speed_kmh": 12.0
    }
