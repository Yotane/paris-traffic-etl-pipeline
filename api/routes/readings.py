from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import logging
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from api.database import execute_query, execute_write
from api.models import TrafficReadingResponse, TrafficReadingCreate

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/", response_model=List[TrafficReadingResponse])
def get_readings(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    segment_id: Optional[str] = Query(default=None),
    quality_flag: Optional[str] = Query(default=None),
    min_quality_score: Optional[float] = Query(default=None, ge=0.0, le=1.0)
):
    """
    Get traffic readings with optional filtering.
    
    - **segment_id**: Filter by road segment
    - **quality_flag**: Filter by data quality flag (e.g. OK, MISSING_FLOW)
    - **min_quality_score**: Filter by minimum quality score (0.0-1.0)
    """
    conditions = []
    params = []

    if segment_id:
        conditions.append("segment_id = %s")
        params.append(segment_id)
    if quality_flag:
        conditions.append("data_quality_flag = %s")
        params.append(quality_flag)
        
    if min_quality_score is not None:
        conditions.append("quality_score >= %s")
        params.append(min_quality_score)

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""


    query = f"""
    SELECT * FROM traffic_readings
    {where_clause}
    ORDER BY timestamp
    LIMIT %s OFFSET %s
    """

    params.extend([limit, skip])

    results = execute_query(query, tuple(params))
    logger.info(f"GET /readings returned {len(results)} records")
    return results

@router.get("/{reading_id}", response_model=TrafficReadingResponse)
def get_reading(reading_id: int):
    """Get a single traffic reading by ID"""
    query = "SELECT * FROM traffic_readings WHERE reading_id = %s"
    results = execute_query(query, (reading_id,))

    if not results:
        raise HTTPException(status_code=404, detail=f"Reading {reading_id} not found")

    logger.info(f"GET /readings/{reading_id} returned 1 record")
    return results[0]

@router.post("/", response_model=dict, status_code=201)
def create_reading(reading: TrafficReadingCreate):
    """Create a new traffic reading"""
    check_query = "SELECT segment_id FROM road_segments WHERE segment_id = %s"
    segment_exists = execute_query(check_query, (reading.segment_id,))

    if not segment_exists:
        raise HTTPException(
            status_code=404,
            detail=f"Segment {reading.segment_id} not found"
        )

    query = """
    INSERT INTO traffic_readings
    (segment_id, timestamp, traffic_flow, avg_speed, traffic_state, sensor_status)
    VALUES (%s, %s, %s, %s, %s, %s)
    """
    try:
        execute_write(query, (
            reading.segment_id,
            reading.timestamp,
            reading.traffic_flow,
            reading.avg_speed,
            reading.traffic_state,
            reading.sensor_status
        ))
        logger.info(f"POST /readings created reading for segment {reading.segment_id}")
        return {"message": "Reading created successfully"}
    except Exception as err:
        raise HTTPException(status_code=400, detail=str(err))

@router.delete("/{reading_id}", response_model=dict)
def delete_reading(reading_id: int):
    """Delete a traffic reading"""
    check_query = "SELECT reading_id FROM traffic_readings WHERE reading_id = %s"
    existing = execute_query(check_query, (reading_id,))

    if not existing:
        raise HTTPException(status_code=404, detail=f"Reading {reading_id} not found")

    query = "DELETE FROM traffic_readings WHERE reading_id = %s"
    execute_write(query, (reading_id,))
    logger.info(f"DELETE /readings/{reading_id} deleted")
    return {"message": f"Reading {reading_id} deleted successfully"}