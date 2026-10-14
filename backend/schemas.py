from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class RouteRequest(BaseModel):
    source: str = Field(..., examples=["Hyderabad"])
    destination: str = Field(..., examples=["Vijayawada"])

class RouteResponse(BaseModel):
    source: str
    destination: str
    distance_km: float
    route_duration_minutes: float
    source_coordinates: List[float]
    destination_coordinates: List[float]
    route_geometry: List[List[float]]
    service_used: str
    steps: Optional[List[Dict[str, Any]]] = None

class WeatherResponse(BaseModel):
    location: str
    temperature_c: float
    precipitation_mm: float
    weather_condition: str
    raw_condition: str
    humidity: int
    wind_speed_kmh: float
    source: str

class FeaturePrepRequest(BaseModel):
    source: str = Field(..., examples=["Hyderabad"])
    destination: str = Field(..., examples=["Vijayawada"])
    departure_time: Optional[str] = Field(default="08:30", examples=["08:30"])
    day_of_week: Optional[str] = Field(default="Monday", examples=["Monday"])
    traffic_condition: Optional[str] = None
    weather_condition: Optional[str] = None

class PredictRequest(BaseModel):
    source: str = Field(..., examples=["Hyderabad"])
    destination: str = Field(..., examples=["Vijayawada"])
    departure_datetime: Optional[str] = Field(default="2026-08-31T08:30:00", examples=["2026-08-31T08:30:00"])
    traffic_condition: Optional[str] = Field(default=None, examples=["High"])

class GoogleRouteRequest(BaseModel):
    source: str = Field(..., examples=["Hyderabad"])
    destination: str = Field(..., examples=["Vijayawada"])
    departure_datetime: Optional[str] = Field(default=None, examples=["2026-09-03T09:00:00"])
    travel_mode: Optional[str] = Field(default="DRIVE", examples=["DRIVE", "TWO_WHEELER", "TRANSIT", "WALK"])
    traffic_condition: Optional[str] = Field(default="Moderate", examples=["Low", "Moderate", "High", "Severe"])


class JourneyDetails(BaseModel):
    source: str
    destination: str
    departure_datetime: str
    estimated_arrival_time: str
    iso_arrival_time: str

class RouteDetails(BaseModel):
    distance_km: float
    route_type: str
    route_api_duration_minutes: float
    route_geometry: List[List[float]]
    service_used: str
    steps: Optional[List[Dict[str, Any]]] = None

class TravelConditions(BaseModel):
    traffic_condition: str
    traffic_source: str
    weather_condition: str
    temperature_c: float
    precipitation_mm: float

class PredictionDetails(BaseModel):
    primary_model: str
    predicted_travel_time_minutes: float
    ridge_prediction_minutes: float
    lasso_prediction_minutes: float
    prediction_id: Optional[str] = None

class MonitoringFeedbackRequest(BaseModel):
    prediction_id: str = Field(..., examples=["728db551-f68f-4e75-ae53-6dbce6015b23"])
    actual_travel_time_minutes: float = Field(..., gt=0, examples=[118.5])

class ModelInfo(BaseModel):
    ridge_r2: float
    lasso_r2: float

class PredictResponse(BaseModel):
    success: bool
    journey: JourneyDetails
    route: RouteDetails
    travel_conditions: TravelConditions
    prediction: PredictionDetails
    model_info: ModelInfo

# ================= AUTHENTICATION & TRIPS SCHEMAS =================

class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, examples=["User Name"])
    email: str = Field(..., examples=["user@example.com"])
    password: str = Field(..., min_length=6, examples=["Password123"])
    confirm_password: str = Field(..., min_length=6, examples=["Password123"])

class VerifyEmailRequest(BaseModel):
    email: str = Field(..., examples=["user@example.com"])
    code: str = Field(..., min_length=6, max_length=6, examples=["482731"])

class ResendCodeRequest(BaseModel):
    email: str = Field(..., examples=["user@example.com"])

class LoginRequest(BaseModel):
    email: str = Field(..., examples=["user@example.com"])
    password: str = Field(..., examples=["Password123"])

class SaveTripRequest(BaseModel):
    source: str = Field(..., examples=["Hyderabad"])
    destination: str = Field(..., examples=["Vijayawada"])
    distance_km: float = Field(..., examples=[275.5])
    travel_mode: str = Field(default="DRIVE", examples=["DRIVE"])
    estimated_duration: str = Field(..., examples=["4h 30m"])
    traffic_condition: str = Field(default="Moderate", examples=["Moderate"])
    departure_time: str = Field(..., examples=["09:00 AM"])
    eta: str = Field(..., examples=["01:30 PM"])

