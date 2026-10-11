from fastapi import FastAPI
from src.api.routes import candidate_sites, health, analytics, future_forecast

app = FastAPI(
    title="India Groundwater Intelligence API",
    description="Read-only Data Access Layer for M1-M12 analytical artifacts.",
    version="1.0.0"
)

app.include_router(health.router)
app.include_router(candidate_sites.router)
app.include_router(analytics.router)
app.include_router(future_forecast.router)
from fastapi.responses import RedirectResponse

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
