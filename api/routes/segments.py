from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import logging
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from api.database import execute_query, execute_write
from api.models import RoadSegmentResponse, RoadSegmentCreate

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/", response_model=List[RoadSegmentResponse])
def get_segments(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    street_name: Optional[str] = Query(default=None)
):
    """
    Get all road segments with optional filtering and pagination.
    
    - **skip**: Number of records to skip
    - **limit**: Maximum records to return (max 1000)
    - **street_name**: Filter by street name (partial match)
    """
    if street_name:
        query = """
        SELECT * FROM road_segments
        WHERE street_name LIKE %s
        LIMIT %s OFFSET %s
        """
        results = execute_query(query, (f"%{street_name}%", limit, skip))
    else:
        query = """
        SELECT * FROM road_segments
        LIMIT %s OFFSET %s
        """
        results = execute_query(query, (limit, skip))

    logger.info(f"GET /segments returned {len(results)} records")
    return results

@router.get("/{segment_id}", response_model=RoadSegmentResponse)
def get_segment(segment_id: str):
    """Get a single road segment by ID"""
    query = "SELECT * FROM road_segments WHERE segment_id = %s"
    results = execute_query(query, (segment_id,))

    if not results:
        raise HTTPException(status_code=404, detail=f"Segment {segment_id} not found")

    logger.info(f"GET /segments/{segment_id} returned 1 record")
    return results[0]

@router.post("/", response_model=dict, status_code=201)
def create_segment(segment: RoadSegmentCreate):
    """Create a new road segment"""
    query = """
    INSERT INTO road_segments
    (segment_id, street_name, latitude, longitude,
     upstream_node_id, upstream_node_name,
     downstream_node_id, downstream_node_name)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    try:
        execute_write(query, (
            segment.segment_id,
            segment.street_name,
            segment.latitude,
            segment.longitude,
            segment.upstream_node_id,
            segment.upstream_node_name,
            segment.downstream_node_id,
            segment.downstream_node_name
        ))
        logger.info(f"POST /segments created segment {segment.segment_id}")
        return {"message": f"Segment {segment.segment_id} created successfully"}
    except Exception as err:
        raise HTTPException(status_code=400, detail=str(err))

@router.put("/{segment_id}", response_model=dict)
def update_segment(segment_id: str, segment: RoadSegmentCreate):
    """Update an existing road segment"""
    check_query = "SELECT segment_id FROM road_segments WHERE segment_id = %s"
    existing = execute_query(check_query, (segment_id,))

    if not existing:
        raise HTTPException(status_code=404, detail=f"Segment {segment_id} not found")

    query = """
    UPDATE road_segments
    SET street_name = %s, latitude = %s, longitude = %s
    WHERE segment_id = %s
    """
    execute_write(query, (
        segment.street_name,
        segment.latitude,
        segment.longitude,
        segment_id
    ))
    logger.info(f"PUT /segments/{segment_id} updated")
    return {"message": f"Segment {segment_id} updated successfully"}

@router.delete("/{segment_id}", response_model=dict)
def delete_segment(segment_id: str):
    """Delete a road segment and all its readings"""
    check_query = "SELECT segment_id FROM road_segments WHERE segment_id = %s"
    existing = execute_query(check_query, (segment_id,))

    if not existing:
        raise HTTPException(status_code=404, detail=f"Segment {segment_id} not found")

    query = "DELETE FROM road_segments WHERE segment_id = %s"
    execute_write(query, (segment_id,))
    logger.info(f"DELETE /segments/{segment_id} deleted")
    return {"message": f"Segment {segment_id} deleted successfully"}