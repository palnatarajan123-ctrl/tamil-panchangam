from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.base_chart import router as base_chart_router
from app.api.prediction import router as prediction_router

app = FastAPI(
    title="Tamil Panchangam Astrology Engine",
    description="Drik Ganita based Tamil astrology with Lahiri ayanamsa",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(base_chart_router, prefix="/base-chart", tags=["Base Chart"])
app.include_router(prediction_router, prefix="/prediction", tags=["Prediction"])

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "Tamil Panchangam Engine",
        "ayanamsa": "Lahiri",
        "calculation_method": "Drik Ganita"
    }
