# Travel Time Prediction Using Ridge and Lasso Regression

**VoyageML — Smart Journey Predictor** is a machine learning web application that predicts travel time and arrival ETA between locations using regularised Ridge Regression ($L_2$) and Lasso Regression ($L_1$).

---

## 🎨 Travel-Themed UI & Frontend Features (Phase 7 Integration)

The web frontend (`frontend/index.html`, `style.css`, `script.js`) provides a modern travel planner experience:

1. **Header & Navigation**: Brand title **VoyageML — Smart Travel Time Predictor** with quick links (`Plan a Trip`, `Live Route`, `Model Results`, `How It Works`).
2. **Hero Section**: Travel-focused introduction highlighting automated real-time feature extraction (distance, traffic density, weather, departure time).
3. **Trip Planner Card**:
   - `From` (Origin Location)
   - `To` (Destination Location)
   - `Departure Date` & `Departure Time`
   - `Traffic Condition` (`Low`, `Moderate`, `High`, `Severe`)
   - `Weather Condition` (Automatic real-time weather with manual override support)
   - Action Button: **Predict My Journey** with dynamic loading state (`Calculating your journey...`).
4. **Primary Journey Result Display**:
   - Estimated Travel Time (e.g. `12h 04m`) and Estimated Arrival Time (ETA e.g. `09:04 PM`).
   - Real-time travel condition cards: Distance (km), Weather (Clear/Cloudy/Rainy/Foggy), Temperature (°C), Traffic density, Route type (`Highway`).
5. **Out-of-Distribution Warning Badge**:
   - Automatically detects if trip distance $> 50$ km (exceeding the model's training range of $1 - 50$ km) and displays an educational ML limitation alert explaining linear extrapolation.
6. **OSRM vs ML Result Comparison**:
   - Side-by-side display of the **ML Model Estimate** (Lasso Regression) alongside the **Routing Engine Baseline** (OSRM API).
7. **Live Interactive Route Map**:
   - Leaflet map rendering exact route geometry waypoints, start/end markers, and automatic bounds fitting (`map.fitBounds()`).

---

## ⚡ Prediction API Specifications

`POST /api/predict` (or `/predict`)

### Request Body
```json
{
  "source": "Hyderabad",
  "destination": "Vijayawada",
  "departure_datetime": "2026-08-31T09:00:00",
  "traffic_condition": "Moderate"
}
```

### Response Payload
```json
{
  "success": true,
  "journey": {
    "source": "Hyderabad",
    "destination": "Vijayawada",
    "departure_datetime": "2026-08-31T09:00:00",
    "estimated_arrival_time": "09:04 PM",
    "iso_arrival_time": "2026-08-31T21:04:14"
  },
  "route": {
    "distance_km": 273.51,
    "route_type": "Highway",
    "route_api_duration_minutes": 217.1,
    "route_geometry": [[17.384885, 78.486691], ...],
    "service_used": "OSRM Routing API"
  },
  "travel_conditions": {
    "traffic_condition": "Medium",
    "traffic_source": "User Specified",
    "weather_condition": "Cloudy",
    "temperature_c": 24.5,
    "precipitation_mm": 0.0
  },
  "prediction": {
    "primary_model": "Lasso Regression",
    "predicted_travel_time_minutes": 724.25,
    "ridge_prediction_minutes": 722.78,
    "lasso_prediction_minutes": 724.25
  },
  "model_info": {
    "ridge_r2": 0.9104,
    "lasso_r2": 0.9105
  }
}
```

---

## 🌐 Integrated Services

| Service Type | Primary Provider | Fallback Engine | API Key Required? |
| :--- | :--- | :--- | :--- |
| **Geocoding Service** | OpenStreetMap Nominatim API | Pre-cached City Coordinates (`CITY_COORDINATES`) | No |
| **Route Service** | OSRM Routing API | OpenRouteService / Haversine Distance Estimator | Optional |
| **Weather Service** | Open-Meteo API | OpenWeatherMap API / Weather Engine Estimator | Optional |

---

## 📈 Model Performance & Results (Phase 4 Evaluation)

| Metric | Ridge Regression ($L_2$) | Lasso Regression ($L_1$) | Interpretation |
| :--- | :--- | :--- | :--- |
| **Best Alpha ($\alpha$)** | `2.1544` | `0.0187` | Optimal regularisation weight tuned via 5-fold CV |
| **MAE** (Mean Absolute Error) | **9.6254 mins** | `9.6355 mins` | **Lower is better**: Average error in predicted travel time |
| **MSE** (Mean Squared Error) | `164.5600` | **164.3555** | **Lower is better**: Penalty for larger prediction deviations |
| **RMSE** (Root Mean Squared Error)| `12.8281 mins` | **12.8201 mins** | **Lower is better**: Standard deviation of prediction residuals |
| **Test $R^2$ Score** | `0.9104` | **0.9105** | **Higher is better**: 91.05% of travel time variance explained |

---

## 🚀 How to Run the Project

### 1. Create & Activate Virtual Environment
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
```

### 2. Install Requirements
```bash
pip install -r requirements.txt
```

### 3. Start the FastAPI Server
```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### 4. Open Application & API Documentation
- **Web UI**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **ML Experiments & Outcomes UI (CO1–CO6)**: [http://127.0.0.1:8000/experiments](http://127.0.0.1:8000/experiments)
- **Interactive Swagger API Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health Check**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## 🎓 Course Outcomes Coverage (CO1–CO6)

| Outcome | Title | Implementation / Artifacts | Key Metrics / Findings |
| :--- | :--- | :--- | :--- |
| **CO1** | **End-to-End ML Lifecycle** | [`docs/CO1_ML_LIFECYCLE.md`](docs/CO1_ML_LIFECYCLE.md) | Full 6-stage lifecycle documented with Mermaid sequence diagram tracing requests from UI to model inference and back. |
| **CO2** | **Ridge & Lasso Regression** | [`ml/train.py`](ml/train.py), [`ml/models/`](ml/models/) | Ridge ($L_2$, $\alpha=1.2328$) & Lasso ($L_1$, $\alpha=0.3054$); Test $R^2 = 0.9662$, MAE = $71.12$ mins; Lasso zeros 4 redundant features. |
| **CO3** | **Decision Tree Regression** | [`ml/decision_tree_experiment.py`](ml/decision_tree_experiment.py) | 5-Fold CV tuned CART regressor (`max_depth=10, min_samples_leaf=2, min_samples_split=10`); CV $R^2 = 0.9819$, Test $R^2 = 0.9856$, Test MAE = $37.91$ mins. Top predictor: `distance_km` (94.89%). |
| **CO4** | **K-Means Clustering** | [`ml/kmeans_experiment.py`](ml/kmeans_experiment.py) | Unsupervised journey profiling on scaled features ($k=2..6$ evaluated). $k=3$ elbow forms natural Short ($161.3$ km, $62.1\%$), Medium ($809.3$ km, $22.5\%$), and Long ($1605.6$ km, $15.5\%$) tiers. |
| **CO5** | **Model Evaluation** | [`ml/model_comparison.py`](ml/model_comparison.py) | Rigorous comparative matrix evaluating Train, CV, and Test metrics on identical 80/20 split; objective trade-off analysis of linear smooth extrapolation vs non-linear step-splits. |
| **CO6** | **Prediction Monitoring** | [`backend/monitoring.py`](backend/monitoring.py) | Non-blocking telemetry tracking latency, error rates, safe inputs/outputs; privacy protection excluding coordinates/PII; online feedback endpoint for live MAE/RMSE calculation. |

