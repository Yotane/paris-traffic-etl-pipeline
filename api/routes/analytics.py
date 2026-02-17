from fastapi import APIRouter, Query
from typing import List, Optional
import numpy as np
import logging
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from api.database import execute_query
from api.models import (
    PeakHourResponse,
    BusiestSegmentResponse,
    SpeedStatsResponse,
    QualityReportResponse,
    CongestionHotspotResponse
)

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/peak-hours", response_model=List[PeakHourResponse])
def get_peak_hours(
    segment_id: Optional[str] = Query(default=None),
    min_quality_score: float = Query(default=0.0, ge=0.0, le=1.0)
):
    """
    Get traffic flow and speed by hour of day.
    Useful for identifying peak congestion periods.
    """
    if segment_id:
        query = """
        SELECT
            HOUR(timestamp) as hour,
            ROUND(AVG(traffic_flow), 2) as avg_flow,
            ROUND(AVG(avg_speed), 2) as avg_speed,
            COUNT(*) as reading_count
        FROM traffic_readings
        WHERE segment_id = %s
        AND quality_score >= %s
        GROUP BY HOUR(timestamp)
        ORDER BY hour
        """
        results = execute_query(query, (segment_id, min_quality_score))
    else:
        query = """
        SELECT
            HOUR(timestamp) as hour,
            ROUND(AVG(traffic_flow), 2) as avg_flow,
            ROUND(AVG(avg_speed), 2) as avg_speed,
            COUNT(*) as reading_count
        FROM traffic_readings
        WHERE quality_score >= %s
        GROUP BY HOUR(timestamp)
        ORDER BY hour
        """
        results = execute_query(query, (min_quality_score,))

    logger.info(f"GET /analytics/peak-hours returned {len(results)} hours")
    return results

@router.get("/busiest-segments", response_model=List[BusiestSegmentResponse])
def get_busiest_segments(
    limit: int = Query(default=10, ge=1, le=100),
    min_quality_score: float = Query(default=0.0, ge=0.0, le=1.0)
):
    """
    Get road segments ranked by average traffic flow.
    """
    query = """
    SELECT
        r.segment_id,
        s.street_name,
        ROUND(AVG(r.traffic_flow), 2) as avg_flow,
        ROUND(AVG(r.avg_speed), 2) as avg_speed,
        COUNT(*) as reading_count
    FROM traffic_readings r
    JOIN road_segments s ON r.segment_id = s.segment_id
    WHERE r.traffic_flow IS NOT NULL
    AND r.quality_score >= %s
    GROUP BY r.segment_id, s.street_name
    ORDER BY avg_flow DESC
    LIMIT %s
    """
    results = execute_query(query, (min_quality_score, limit))
    logger.info(f"GET /analytics/busiest-segments returned {len(results)} segments")
    return results

@router.get("/speed-stats", response_model=SpeedStatsResponse)
def get_speed_stats(
    segment_id: Optional[str] = Query(default=None),
    min_quality_score: float = Query(default=0.0, ge=0.0, le=1.0)
):
    """
    Calculate speed statistics using NumPy.
    Returns mean, median, std deviation, and percentiles.
    """
    if segment_id:
        query = """
        SELECT avg_speed FROM traffic_readings
        WHERE avg_speed IS NOT NULL
        AND segment_id = %s
        AND quality_score >= %s
        """
        results = execute_query(query, (segment_id, min_quality_score))
    else:
        query = """
        SELECT avg_speed FROM traffic_readings
        WHERE avg_speed IS NOT NULL
        AND quality_score >= %s
        """
        results = execute_query(query, (min_quality_score,))

    if not results:
        return SpeedStatsResponse(
            segment_id=segment_id,
            mean_speed=0, median_speed=0, std_dev=0,
            percentile_25=0, percentile_75=0,
            min_speed=0, max_speed=0, sample_size=0
        )

    speeds = np.array([row['avg_speed'] for row in results], dtype=float)

    logger.info(f"GET /analytics/speed-stats calculated stats for {len(speeds)} readings")

    return SpeedStatsResponse(
        segment_id=segment_id,
        mean_speed=round(float(np.mean(speeds)), 2),
        median_speed=round(float(np.median(speeds)), 2),
        std_dev=round(float(np.std(speeds)), 2),
        percentile_25=round(float(np.percentile(speeds, 25)), 2),
        percentile_75=round(float(np.percentile(speeds, 75)), 2),
        min_speed=round(float(np.min(speeds)), 2),
        max_speed=round(float(np.max(speeds)), 2),
        sample_size=len(speeds)
    )

@router.get("/quality-report", response_model=List[QualityReportResponse])
def get_quality_report():
    """
    Get a breakdown of data quality across all readings.
    Shows distribution of quality flags and average scores.
    """
    query = """
    SELECT
        data_quality_flag,
        COUNT(*) as count,
        ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM traffic_readings), 2) as percentage,
        ROUND(AVG(quality_score), 2) as avg_quality_score
    FROM traffic_readings
    GROUP BY data_quality_flag
    ORDER BY count DESC
    """
    results = execute_query(query)
    logger.info(f"GET /analytics/quality-report returned {len(results)} flags")
    return results

@router.get("/congestion-hotspots", response_model=List[CongestionHotspotResponse])
def get_congestion_hotspots(
    limit: int = Query(default=10, ge=1, le=100)
):
    """
    Get road segments with most blocked or saturated traffic states.
    """
    query = """
    SELECT
        r.segment_id,
        s.street_name,
        SUM(CASE WHEN r.traffic_state = 'Bloqué' THEN 1 ELSE 0 END) as blocked_count,
        SUM(CASE WHEN r.traffic_state = 'Saturé' THEN 1 ELSE 0 END) as saturated_count,
        SUM(CASE WHEN r.traffic_state IN ('Bloqué', 'Saturé') THEN 1 ELSE 0 END) as total_incidents
    FROM traffic_readings r
    JOIN road_segments s ON r.segment_id = s.segment_id
    GROUP BY r.segment_id, s.street_name
    HAVING total_incidents > 0
    ORDER BY total_incidents DESC
    LIMIT %s
    """
    results = execute_query(query, (limit,))
    logger.info(f"GET /analytics/congestion-hotspots returned {len(results)} segments")
    return results

@router.get("/traffic-by-hour", response_model=List[PeakHourResponse])
def get_traffic_by_hour(
    segment_id: str = Query(..., description="Road segment ID (required)")
):
    """
    Get hourly traffic breakdown for a specific road segment.
    """
    check_query = "SELECT segment_id FROM road_segments WHERE segment_id = %s"
    existing = execute_query(check_query, (segment_id,))

    if not existing:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Segment {segment_id} not found")

    query = """
    SELECT
        HOUR(timestamp) as hour,
        ROUND(AVG(traffic_flow), 2) as avg_flow,
        ROUND(AVG(avg_speed), 2) as avg_speed,
        COUNT(*) as reading_count
    FROM traffic_readings
    WHERE segment_id = %s
    GROUP BY HOUR(timestamp)
    ORDER BY hour
    """
    results = execute_query(query, (segment_id,))
    logger.info(f"GET /analytics/traffic-by-hour for segment {segment_id}")
    return results