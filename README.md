# Paris Traffic Data Pipeline
**Data Engineering portfolio project demonstrating ETL pipeline design, API development, and data quality management. Made for educational purposes such as data engineering and API practice.**

ETL pipeline for processing and analyzing Paris road traffic sensor data (2023) obtained from:
https://www.kaggle.com/datasets/chafikboulealam/local-merged-data

Dataset description from Kaggle:
This dataset contains more than 5,000,000 observations of road traffic conditions in Paris, France, collected during the year 2023. Each entry represents the state of traffic on a specific road segment at a given hourly timestamp. The data is ideal for classification, time-series analysis, and geospatial modeling tasks in intelligent transportation systems and urban mobility research.

### Data Schema Overview
| Field | Type | Description |
|-------|------|-------------|
| `iu_ac` | String | Unique identifier for the road segment (arc) |
| `libelle` | String | Human-readable street name (e.g., "Bd_de_Belleville") |
| `t_1h` | Timestamp | Hourly observation time in ISO 8601 format (`2023-01-01T03:00:00+00:00`) |
| `q` | Float | **Traffic flow**: vehicles per hour passing the sensor (frequently null due to sensor maintenance) |
| `k` | Float | **Average speed** (km/h) frequently null due to sensor maintenance. Values <1 km/h corrected by ETL using multi-signal validation (decimal placement error). |
| `etat_trafic` | String | **Traffic state**: `Fluide` (free-flow), `Dense` (congested), `Sature` (gridlock), or `Inconnu` (unknown) |
| `iu_nd_amont` / `iu_nd_aval` | String | Upstream/downstream node IDs for network topology analysis |
| `etat_barre` | String | Sensor validity flag: `Valide` or `Invalide` (used for data quality filtering) |
| `geo_point_2d` | Object | Centroid coordinates `{lon, lat}` for mapping and spatial joins |
| `geo_shape` | GeoJSON | `LineString` geometry defining the precise road segment path for geospatial visualization |


Originally sourced as a large nested JSON file, this cleaned and structured version has been preprocessed for ease of use in machine learning workflows. It includes both numerical traffic metrics (e.g., flow and speed) and categorical labels (e.g., traffic state), along with rich geospatial metadata.

## Data Quality
However this dataset is very messy as it has a lot of missing data:
q (flow): 52.4% missing
k (speed): 51.6% missing
Geospatial and date fields: 0.7% missing
Duplicates: Present and should be removed before modeling.
Class Imbalance: Present in etat_trafic and requires resampling or cost-sensitive learning.
Upon checking, I found that there around 40.0% missing both q and k and around 80.0% of sensors are marked invalid.
Most importantly, the dataset has a lot of decimal errors (speeds like 0.43 km/h should be 43 km/h).

**Initial Observation:** Mean speed of 4.88 km/h and other instances seemed suspiciously low.

**Hypothesis Testing:**
Rather than blindly assuming a decimal error, I investigated whether low speeds could be legitimate (e.g., sensor failures, gridlock conditions).

**Cross-validation with Traffic State:**
```python
# Analysis: speed_analysis.py
# Key finding: ALL 5,603 records with speed < 1 km/h marked as "Fluide" (flowing)
```
**Evidence:**

| Speed Range | Count | Traffic State | Interpretation |
|-------------|-------|---------------|----------------|
| 0-1 km/h | 5,603 | 100.0% Fluide | Impossible - can't flow at 0.5 km/h |
| 1-10 km/h | 20,828 | 100.0% Fluide | Suspicious for all to be flowing |
| 10-100 km/h | 3,372 | Mixed states | Normal distribution |

**Best Example:**
```
Location: Quai_Hotel_de_Ville
Speed: 0.18778 km/h (walking is 5 km/h)
Flow: 406 cars/hour
State: Fluide (flowing)
406 cars/hour cannot flow at 0.19 km/h. After multiplying by 100 (to 18.78 km/h), this matches typical Paris congestion patterns.
```

### Production-Grade Decimal Error Correction
Instead of a simple threshold-based fix, the ETL implements a multi-signal validation approach aligned with industry best practices:

**Signal 1: Suspicious speed range**
- Speed < 1 km/h is unrealistic for urban traffic (walking speed is ~5 km/h)

**Signal 2: Flow-speed physics check**
- Using fundamental diagram: flow = density x speed
- If speed ≈ 0 but flow > 100 veh/hr, implied density exceeds physical limits (~200 veh/km/lane)

**Signal 3: Traffic state contradiction**
- Records marked "Fluide" (flowing) cannot have speed < 1 km/h

**Signal 4: Sensor operational status**
- Exclude corrections for sensors already flagged as "Invalide"

**Tiered Correction Strategy:**
| Tier | Confidence | Criteria | Action | Quality Score |
|------|-----------|----------|--------|--------------|
| HIGH | Auto-correct | All 4 signals align | Multiply by 100, flag as corrected | 0.85 |
| MEDIUM | Correct with caution | 3/4 signals align | Multiply by 100, flag for review | 0.70 |
| LOW | Do not correct | Only speed signal | Flag as suspected error | 0.50 |

**Post-Correction Validation:**
After applying corrections, the pipeline validates results using:
1. Range check: Corrected speeds must fall within 5-120 km/h (Paris urban road limits)
2. Fundamental diagram check: Implied density (flow/speed) must not exceed 200 veh/km/lane
3. Distribution check: Corrected mean should align with Paris benchmarks (13-17 km/h typical)

**Conclusion:** Systematic decimal error confirmed. Corrected records using tiered strategy, flagged with confidence levels and quality scores for transparent downstream analytics. Implemented in transform.py as part of the ETL pipeline.

### Data Cleaning
In the ETL, transform.py cleans and transforms raw traffic data with production-grade quality assessment:
1. Multi-signal validation for decimal error detection (speed + flow + state + sensor status)
2. Tiered correction strategy with confidence levels (HIGH/MEDIUM/LOW)
3. Post-correction validation using traffic physics (fundamental diagram)
4. Drop rows missing both flow and speed (no usable signal)
5. Remove physically impossible outliers (speed > 200 km/h, negative flow)
6. Extract structured GPS coordinates from nested GeoJSON
7. Assign tiered quality flags using Paris-specific traffic engineering rules
8. Split normalized output into dimension (segments) and fact (readings) tables

Three files for ETL: extract.py, transform.py, load.py. pipeline.py orchestrates execution.

Furthermore, I researched real Paris traffic data to optimize quality flag thresholds in transform.py:
- Paris average rush hour speed: 19 km/h
- Typical Paris city speeds: 13-17 km/h
- Urban arterial capacity: 1,100-1,900 veh/hr/lane
- Maximum flow occurs at 40-60 km/h (not at very high speeds)

### Prerequisites
- Python 3.13+
- MySQL 8.0+
- Git

### Installation
```bash
# Clone repository
git clone https://github.com/Yotane/paris-traffic-etl-pipeline.git
cd paris-traffic-etl-pipeline

# Install dependencies
pip install -r requirements.txt

# Set up database
mysql -u root -p
CREATE DATABASE paris_traffic;
USE paris_traffic;
SOURCE SQL/schema.sql;

# Configure database credentials
# Copy config template
cp config.example.py config.py

# Edit config.py with your MySQL password
# (config.py is in .gitignore for security)
```

### Run ETL Pipeline

#### Initial Dataset
The project includes January 1st, 2023 data (62,622 records) as the initial dataset. The full source file contains 2.2M+ records but is too large to include in the repository.
```bash
# Load included January 1st data
python pipeline.py --file Data/data_january1.json
```

#### Load Additional Days
If you have access to the full dataset (`local_merged_data_01_04.json`), you can incrementally add more days using `extract.py`:
```bash
# Extract and load a single day
python pipeline.py --date 2023-01-02

# Extract and load a date range
python pipeline.py --start-date 2023-01-02 --end-date 2023-01-07

# The pipeline handles duplicates automatically - safe to re-run
```

### Architecture
```text
JSON Source (Kaggle) -> Python ETL (pipeline.py) -> MySQL Database
                                 |                        |
                           Data Cleaning            FastAPI (API Layer)
                                 |
                                 +------------------> Swagger UI / Docs
```

## Project Results

**Note:** Statistics reflect January 1-2, 2023 data (two days loaded to verify incremental loading functionality).

### Dataset Statistics
- **Raw input:** Jan 1: 62,622 records + Jan 2: 71,568 records = 134,190 records
- **Total loaded:** 79,919 traffic readings across 2 days
- **Processing time:** 7.13 seconds (Jan 1), 7.46 seconds (Jan 2); average 7.29 seconds per day
- **Data quality:**
  - Retained: 63.3% of raw records (after dropping rows missing both flow and speed)
  - Dropped: 36.7% (missing core metrics or physically impossible values)
- **Unique road segments:** 1,779 (stable across dates, confirms dimension table integrity)
- **Decimal errors corrected:** 90 records using multi-signal validation (45 HIGH confidence, 45 MEDIUM confidence)

### Quality Distribution (Combined Jan 1-2, Exact Counts)

| Quality Flag | Count | Percentage | Quality Score |
|-------------|-------|------------|---------------|
| INVALID_SENSOR_HAS_DATA | 48,112 | 60.2% | 0.6 |
| INCONSISTENT_STOPPED_WITH_FLOW | 10,550 | 13.2% | 0.4 |
| OK | 6,190 | 7.7% | 1.0 |
| MISSING_FLOW | 2,199 | 2.7% | 0.8 |
| MISSING_SPEED | 599 | 0.7% | 0.8 |
| SUSPECTED_DECIMAL_ERROR_LOW | 7,998 | 10.0% | 0.5 |
| CORRECTED_DECIMAL_ERROR_HIGH | 45 | 0.06% | 0.85 |
| CORRECTED_DECIMAL_ERROR_MEDIUM | 45 | 0.06% | 0.70 |
| INCONSISTENT_EXTREME_FLOW_SPEED | 101 | 0.13% | 0.3 |
| INCONSISTENT_SPEED_STATE | 10 | 0.01% | 0.5 |

**Key Insight:** Only 7.7% of readings are "OK" quality, highlighting the real-world messiness of sensor data and the importance of transparent quality flagging rather than dropping questionable data. The tiered correction approach enables downstream analysts to filter by confidence level (e.g., use only HIGH confidence for critical reports). The 10.0% flagged as `SUSPECTED_DECIMAL_ERROR_LOW` represents records that may need manual review but were preserved for transparency.

### ETL Performance
- **Pipeline throughput:** 9,200 records/second (134,190 records / 14.59 seconds total)
- **Memory efficiency:** Generator-based chunking keeps peak memory under 500MB regardless of input size
- **Duplicate handling:** Automatic via `INSERT IGNORE` (segments) and `ON DUPLICATE KEY UPDATE` (readings)
- **Idempotent:** Safe to re-run without creating duplicates; re-processing updates existing records
- **Scalability:** Linear processing time; 134,190 records processed in 14.59 seconds total

### API Performance
- **Total endpoints:** 16 (9 CRUD + 6 Analytics + 1 Health)
- **Response format:** JSON
- **Documentation:** Auto-generated OpenAPI/Swagger UI at `/docs`
- **Concurrent requests:** Supported via FastAPI async/await
- **Average response time:** <50ms for simple queries, <200ms for aggregations

### Run API
```bash
# Start server
python run.py

# Visit interactive docs
http://localhost:8000/docs
```

## API Endpoints

### CRUD Operations
```
GET    /segments              List road segments (pagination)
GET    /segments/{id}         Get single segment
POST   /segments              Create segment
PUT    /segments/{id}         Update segment
DELETE /segments/{id}         Delete segment

GET    /readings              List readings (with filters)
GET    /readings/{id}         Get single reading
POST   /readings              Create reading
DELETE /readings/{id}         Delete reading
```

### Analytics
```
GET /analytics/peak-hours             Traffic by hour
GET /analytics/busiest-segments       Ranked by flow
GET /analytics/speed-stats            NumPy statistics
GET /analytics/quality-report         Data quality breakdown
GET /analytics/congestion-hotspots    Blocked/saturated segments
```
**Example Request:**
```bash
curl "http://localhost:8000/analytics/speed-stats?min_quality_score=0.8"
```

**Actual Response (dataset was only January 1 and 2):**
```json
{
  "segment_id": null,
  "mean_speed": 10.05,
  "median_speed": 8.05,
  "std_dev": 8.41,
  "percentile_25": 4.35,
  "percentile_75": 12.6,
  "min_speed": 0,
  "max_speed": 71.6,
  "sample_size": 9089
}
```

## Future Roadmap
* **Dockerization:** Containerize the API and MySQL for "one-click" deployment.
* **Web Application:** Build a frontend web application to transform the API's analytics into charts and other diagrams.
* **Real-time Integration:** Connect to the [Paris Open Data API](https://opendata.paris.fr/) for live traffic updates instead of static 2023 data.

## Technical Stack
* Language: Python 3.13
* API Framework: FastAPI
* Database: MySQL 8.0 (Relational storage and indexing)
* Data Processing: Pandas (ETL) and NumPy (Analytics)
* Validation: Pydantic (Data schemas and type safety)
* Version Control: Git and GitHub (Feature-branch workflow)
* Documentation: Swagger UI / OpenAPI (Interactive API testing interface)
* Server: Uvicorn (ASGI implementation)

## License
This project is for educational purposes. Dataset sourced from [Kaggle](https://www.kaggle.com/datasets/chafikboulealam/local-merged-data) under their terms of use.

## Author

Matt Raymond Ayento
Nagoya University
G30, 3rd year Automotive Engineering (Electrical, Electronics, Information Engineering)