from fastapi import FastAPI
from src.api.routes import candidate_sites, health, analytics, future_forecast, forecasts, advanced_forecast

app = FastAPI(
    title="India Groundwater Intelligence API",
    description="Read-only Data Access Layer for M1-M12 analytical artifacts.",
    version="1.0.0"
)

import threading

@app.on_event("startup")
def startup_event():
    def _warmup():
        try:
            advanced_forecast.warmup_advanced_forecast_models()
        except Exception:
            pass
        try:
            from src.api.dal import GroundwaterDAL
            dal = GroundwaterDAL()
            dal._ensure_mh_tele_cache()
            dal._ensure_mh_alerts_cache()
            dal._ensure_mh_condition_cache()
            forecasts._load_chain_context()
        except Exception:
            pass

    threading.Thread(target=_warmup, daemon=True).start()

app.include_router(health.router)
app.include_router(candidate_sites.router)
app.include_router(analytics.router)
app.include_router(future_forecast.router)
app.include_router(forecasts.router)
app.include_router(advanced_forecast.router)

from fastapi.responses import RedirectResponse

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
