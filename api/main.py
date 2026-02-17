from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.routes import segments, readings, analytics

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Paris Traffic API",
    description="REST API for Paris road traffic sensor data (January 2023)",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(segments.router, prefix="/segments", tags=["Segments"])
app.include_router(readings.router, prefix="/readings", tags=["Readings"])
app.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])

@app.get("/health")
def health_check():
    """Check if the API is running"""
    return {
        "status": "ok",
    }

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)