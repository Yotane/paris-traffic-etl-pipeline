from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date

# Road Segment Models
class RoadSegmentBase(BaseModel):
    street_name: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    upstream_node_id: Optional[str] = None
    upstream_node_name: Optional[str] = None
    downstream_node_id: Optional[str] = None
    downstream_node_name: Optional[str] = None

class RoadSegmentCreate(RoadSegmentBase):
    segment_id: str

class RoadSegmentResponse(RoadSegmentBase):
    segment_id: str
    sensor_install_date: Optional[date] = None
    sensor_end_date: Optional[date] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Traffic Reading Models
class TrafficReadingBase(BaseModel):
    segment_id: str
    timestamp: datetime
    traffic_flow: Optional[int] = None
    avg_speed: Optional[float] = None
    traffic_state: str
    sensor_status: str

class TrafficReadingCreate(TrafficReadingBase):
    pass

class TrafficReadingResponse(TrafficReadingBase):
    reading_id: int
    is_flow_imputed: bool
    is_speed_corrected: bool
    data_quality_flag: Optional[str] = None
    quality_score: Optional[float] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Analytics Models
class PeakHourResponse(BaseModel):
    hour: int
    avg_flow: Optional[float] = None
    avg_speed: Optional[float] = None
    reading_count: int

class BusiestSegmentResponse(BaseModel):
    segment_id: str
    street_name: str
    avg_flow: Optional[float] = None
    avg_speed: Optional[float] = None
    reading_count: int

class SpeedStatsResponse(BaseModel):
    segment_id: Optional[str] = None
    mean_speed: float
    median_speed: float
    std_dev: float
    percentile_25: float
    percentile_75: float
    min_speed: float
    max_speed: float
    sample_size: int

class QualityReportResponse(BaseModel):
    data_quality_flag: str
    count: int
    percentage: float
    avg_quality_score: float

class CongestionHotspotResponse(BaseModel):
    segment_id: str
    street_name: str
    blocked_count: int
    saturated_count: int
    total_incidents: int

# Pagination Model
class PaginationParams(BaseModel):
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=100, ge=1, le=1000)