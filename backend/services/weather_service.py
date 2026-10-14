import requests
from backend.config import OPENWEATHER_API_KEY

# Trained dataset weather categories
TRAINED_WEATHER_CATEGORIES = ["Clear", "Cloudy", "Rainy", "Foggy"]

def map_openmeteo_wmo_code(wmo_code: int) -> str:
    """
    Maps Open-Meteo WMO Weather Interpretation Codes to ML dataset categories.
    """
    if wmo_code in [0, 1]:
        return "Clear"
    elif wmo_code in [2, 3]:
        return "Cloudy"
    elif wmo_code in [45, 48]:
        return "Foggy"
    elif wmo_code in [51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99]:
        return "Rainy"
    return "Cloudy"

def map_openweather_condition(main_condition: str) -> str:
    """
    Maps OpenWeather condition strings to ML dataset categories.
    """
    cond_map = {
        "Clear": "Clear",
        "Clouds": "Cloudy",
        "Rain": "Rainy",
        "Drizzle": "Rainy",
        "Thunderstorm": "Rainy",
        "Snow": "Rainy",
        "Mist": "Foggy",
        "Fog": "Foggy",
        "Haze": "Foggy",
        "Smoke": "Foggy"
    }
    return cond_map.get(main_condition, "Cloudy")

def get_weather_data(lat: float, lon: float, location_name: str = ""):
    """
    Fetches real-time weather details (temperature in °C, precipitation in mm, and mapped weather condition)
    using Open-Meteo API or OpenWeather API, with fallback generator.
    """
    # 1. Try Open-Meteo API (Free, no API key required)
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m"
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            data = response.json()
            current = data.get("current", {})
            temp_c = round(current.get("temperature_2m", 25.0), 1)
            precip_mm = round(current.get("precipitation", 0.0), 1)
            wmo_code = current.get("weather_code", 0)
            weather_condition = map_openmeteo_wmo_code(wmo_code)
            return {
                "location": location_name,
                "temperature_c": temp_c,
                "precipitation_mm": precip_mm,
                "weather_condition": weather_condition,
                "raw_condition": f"WMO Code {wmo_code}",
                "humidity": current.get("relative_humidity_2m", 60),
                "wind_speed_kmh": round(current.get("wind_speed_10m", 5.0), 1),
                "source": "Open-Meteo API"
            }
    except Exception as err:
        print(f"Open-Meteo API notice: {err}")

    # 2. Try OpenWeather API if OPENWEATHER_API_KEY is available
    if OPENWEATHER_API_KEY:
        try:
            url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric"
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                data = response.json()
                temp_c = round(data["main"]["temp"], 1)
                main_condition = data["weather"][0]["main"]
                rain_dict = data.get("rain", {})
                precip_mm = round(rain_dict.get("1h", 0.0), 1)
                weather_condition = map_openweather_condition(main_condition)
                return {
                    "location": location_name,
                    "temperature_c": temp_c,
                    "precipitation_mm": precip_mm,
                    "weather_condition": weather_condition,
                    "raw_condition": main_condition,
                    "humidity": data["main"].get("humidity", 60),
                    "wind_speed_kmh": round(data["wind"].get("speed", 3.0) * 3.6, 1),
                    "source": "OpenWeather API"
                }
        except Exception as err:
            print(f"OpenWeather API notice: {err}")

    # 3. Deterministic Fallback weather generator based on location coordinates
    hash_val = int(abs(lat * 100 + lon * 100))
    temp_c = round(20.0 + (hash_val % 180) / 10.0, 1)  # Range 20.0°C - 38.0°C
    precip_mm = round((hash_val % 50) / 10.0, 1) if (hash_val % 4 == 0) else 0.0
    cond_index = hash_val % len(TRAINED_WEATHER_CATEGORIES)
    weather_condition = TRAINED_WEATHER_CATEGORIES[cond_index]

    return {
        "location": location_name,
        "temperature_c": temp_c,
        "precipitation_mm": precip_mm,
        "weather_condition": weather_condition,
        "raw_condition": weather_condition,
        "humidity": 55 + (hash_val % 35),
        "wind_speed_kmh": round(8.0 + (hash_val % 150) / 10.0, 1),
        "source": "Weather Engine Estimator"
    }
