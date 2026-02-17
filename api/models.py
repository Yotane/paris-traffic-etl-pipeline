from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

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
    sensor_install_date: Optional[str] = None
    sensor_end_date: Optional[str] = None
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

