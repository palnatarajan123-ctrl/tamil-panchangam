from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid

router = APIRouter()

class BirthDetails(BaseModel):
    name: str
    date_of_birth: str
    time_of_birth: str
    place_of_birth: str
    latitude: float
    longitude: float
    timezone: str

class BaseChartResponse(BaseModel):
    id: str
    name: str
    date_of_birth: str
    time_of_birth: str
    place_of_birth: str
    latitude: float
    longitude: float
    timezone: str
    status: str
    message: str
    created_at: str

base_charts_storage = {}

@router.post("/create", response_model=BaseChartResponse)
def create_base_chart(details: BirthDetails):
    """
    This endpoint will:
    - Compute immutable birth chart data
    - Store sidereal Moon, Nakshatra, Pada, D1/D9, Dashas
    - Return a base_chart_id

    Astrology logic NOT implemented yet.
    """
    chart_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()
    
    chart_data = {
        "id": chart_id,
        "name": details.name,
        "date_of_birth": details.date_of_birth,
        "time_of_birth": details.time_of_birth,
        "place_of_birth": details.place_of_birth,
        "latitude": details.latitude,
        "longitude": details.longitude,
        "timezone": details.timezone,
        "status": "stub",
        "message": "Base chart created. Astrology calculations pending implementation.",
        "created_at": created_at
    }
    
    base_charts_storage[chart_id] = chart_data
    
    return chart_data

@router.get("/list")
def list_base_charts():
    """
    List all stored base charts
    """
    return list(base_charts_storage.values())

@router.get("/{chart_id}")
def get_base_chart(chart_id: str):
    """
    Get a specific base chart by ID
    """
    if chart_id not in base_charts_storage:
        raise HTTPException(status_code=404, detail="Chart not found")
    return base_charts_storage[chart_id]
