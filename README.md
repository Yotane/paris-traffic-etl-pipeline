# Paris Traffic Data Pipeline
**Data Engineering portfolio project demonstrating ETL pipeline design, API development, and data quality management.**

ETL pipeline for processing and analyzing Paris road traffic sensor data (2023) obtained from:
https://www.kaggle.com/datasets/chafikboulealam/local-merged-data

Dataset description from Kaggle:
This dataset contains more than 5,000,000 observations of road traffic conditions in Paris, France, collected during the year 2023. Each entry represents the state of traffic on a specific road segment at a given hourly timestamp. The data is ideal for classification, time-series analysis, and geospatial modeling tasks in intelligent transportation systems and urban mobility research.

Originally sourced as a large nested JSON file, this cleaned and structured version has been preprocessed for ease of use in machine learning workflows. It includes both numerical traffic metrics (e.g., flow and speed) and categorical labels (e.g., traffic state), along with rich geospatial metadata.

## Data Quality
However this dataset is very messy as it has a lot of missing data:
q (flow): 52.4% missing
k (speed): 51.6% missing
Geospatial & date fields: ~0.7% missing
Duplicates: Present — should be removed before modeling.
Class Imbalance: Present in etat_trafic — requires resampling or cost-sensitive learning.
Upon checking, I found that there around 40% missing both q and k and around 80% of sensors are marked invalid.
Most importantly, the dataset has a lot of decimal errors.(speeds like 0.43 km/h - should be 43 km/h)

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
| 0-1 km/h | 5,603 | 100% Fluide | Impossible - can't flow at 0.5 km/h |
| 1-10 km/h | 20,828 | 100% Fluide | Suspicious for all to be flowing |
| 10-100 km/h | 3,372 | Mixed states | Normal distribution |

**Best Example:**
```
Location: Quai_Hotel_de_Ville
Speed: 0.18778 km/h (walking is 5 km/h)
Flow: 406 cars/hour
State: Fluide (flowing)
406 cars/hour cannot flow at 0.19 km/h. After multiplying by 100 (→ 18.78 km/h), this matches typical Paris congestion patterns.
```
**Conclusion:** Systematic decimal error confirmed. Corrected 5,603 records by multiplying speeds < 1 km/h by 100, flagged with quality_score = 0.7 for transparency. These, together with other cleaning features were done with transform.py in the ETL.

### Data Cleaning
In the ETL, transform.py cleans and transforms raw traffic data with tiered quality assessment. It also drops data that are impossible outliers and are missing both flow and speed. It also assigns quality flags and prepares tables for loading.
Three files for ETL"
extract.py, transform.py, load.py. And pipeline.py runs them in order.

Furthermore, I researched on real Paris traffic data to further optimize the thresholds in the quality flag assessment in transform.py:
        Thresholds based on:
        - Paris average rush hour speed: 19 km/h
        - Typical Paris city speeds: 13-17 km/h
        - Urban arterial capacity: 1,100-1,900 veh/hr/lane
        - Maximum flow at 40-60 km/h (not at high speeds)

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

### Run ETL Pipeline

### Initial Dataset
The project includes January 1st, 2023 data (62,622 records) as the initial dataset. The full source file contains 2.2M+ records but is too large to include in the repository.
```bash
# Load included January 1st data
python pipeline.py --file Data/data_january1.json
```

### Load Additional Days
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
JSON Source (Kaggle) ──> Python ETL (pipeline.py) ──> MySQL Database
                                 │                        │
                           Data Cleaning            FastAPI (API Layer)
                                 │
                                 └──────────────────> Swagger UI / Docs
```
## Project Results

**Note:** Statistics reflect January 1-2, 2023 data (two days loaded to verify incremental loading functionality).

### Dataset Statistics
- **Raw input:** Jan 1: 62,622 records + Jan 2: 71,568 records = 134,190 records
- **Total loaded:** 79,919 traffic readings across 2 days
- **Processing time:** ~7.6 seconds per day
- **Data quality:**
  - Retained: ~80,000 readings (63.3%)
  - Dropped: ~46,000 rows (36.7% - missing both flow and speed)
- **Unique road segments:** 1,784 (stable across dates)
- **Decimal errors corrected:** 13,182 speeds < 1 km/h (multiplied by 100)

### Quality Distribution

| Quality Flag | Count | Percentage | Quality Score |
|-------------|-------|------------|---------------|
| INVALID_SENSOR_HAS_DATA | 50,588 | 63.3% | 0.6 |
| CORRECTED_DECIMAL_ERROR | 13,182 | 16.5% | 0.7 |
| OK | 6,591 | 8.2% | 1.0 |
| INCONSISTENT_STOPPED_WITH_FLOW | 6,104 | 7.6% | 0.4 |
| MISSING_FLOW | 2,498 | 3.1% | 0.8 |
| MISSING_SPEED | 679 | 0.8% | 0.8 |
| INCONSISTENT_EXTREME_FLOW_SPEED | 252 | 0.3% | 0.3 |
| INCONSISTENT_SPEED_STATE | 25 | 0.0% | 0.5 |

**Key Insight:** Only 8.2% of readings are "OK" quality, highlighting the real-world messiness of sensor data and the importance of transparent quality flagging rather than dropping questionable data.

### ETL Performance
- **Pipeline throughput:** ~8,200 records/second
- **Memory efficiency:** Generator-based chunking (5,000 records/chunk)
- **Duplicate handling:** Automatic via `INSERT IGNORE` and `UNIQUE KEY` constraints
- **Idempotent:** Safe to re-run without creating duplicates

### API Performance
- **Total endpoints:** 16 (9 CRUD + 6 Analytics + 1 Health)
- **Response format:** JSON
- **Documentation:** Auto-generated OpenAPI/Swagger UI
- **Concurrent requests:** Supported (FastAPI async)

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
* **Web Application:** Build a frontend web application to transform the API's anayltics into charts and other diagrams.
* **Real-time Integration:** Connect to the [Paris Open Data API](https://opendata.paris.fr/) for live traffic updates instead of static 2023 data.

## Technical Stack
* Language: Python 3.13
* API Framework: FastAPI
* Database: MySQL 8.0 (Relational storage & indexing)
* Data Processing: Pandas (ETL) & NumPy (Analytics)
* Validation: Pydantic (Data schemas & type safety)
* Version Control: Git & GitHub (Feature-branch workflow)
* Documentation: Swagger UI / OpenAPI (Interactive API testing interface)
* Server: Uvicorn (ASGI implementation)

## License
This project is for educational purposes. Dataset sourced from [Kaggle](https://www.kaggle.com/datasets/chafikboulealam/local-merged-data) under their terms of use.

## Author
Matt Raymond Ayento
Nagoya University
G30, 3rd year Automotive Engineering (Electrical, Electronics, Information Engineering)