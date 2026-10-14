from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from backend.routes import router
from backend.auth_routes import auth_router

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(
    title="VoyageML — Smart Journey Predictor",
    description="Travel Time Prediction Using Ridge and Lasso Regression",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    print("VoyageML Server Started — OSRM & OpenStreetMap Routing Engine Active.")

@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    """Prevents browsers from serving stale cached static frontend files."""
    response = await call_next(request)
    if (
        request.url.path.startswith("/static/")
        or request.url.path.startswith("/css/")
        or request.url.path.startswith("/js/")
        or request.url.path == "/"
    ):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

frontend_dir = BASE_DIR / "frontend"
if frontend_dir.exists():
    app.mount("/css", StaticFiles(directory=str(frontend_dir / "css")), name="css")
    app.mount("/js", StaticFiles(directory=str(frontend_dir / "js")), name="js")
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

# Include backend router & auth router
app.include_router(router)
app.include_router(auth_router)

@app.get("/")
def read_root():
    index_file = frontend_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"status": "ok", "message": "VoyageML Backend API is running."}

@app.get("/experiments")
@app.get("/ml-experiments")
def read_experiments():
    exp_file = frontend_dir / "experiments.html"
    if exp_file.exists():
        return FileResponse(exp_file)
    return {"status": "ok", "message": "ML Experiments page not found."}

@app.get("/health")
def health_check():
    """Phase 1 health check endpoint."""
    return {"status": "ok"}
