# Paris Traffic Data Pipeline

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
cp config.py
# Edit config.py with your MySQL password

### Run ETL Pipeline
```bash
# Load January 1st (included already)
python pipeline.py --file Data/data_january1.json

# Load additional days (requires full dataset)
python pipeline.py --date 2023-01-02
python pipeline.py --start-date 2023-01-02 --end-date 2023-01-07
```
### Architecture
```text
JSON Source (Kaggle) ──> Python ETL (pipeline.py) ──> MySQL Database
                                 │                        │
                           Data Cleaning            FastAPI (API Layer)
                        (Decimal Correction)              │
                                 └──────────────────> Swagger UI / Docs
```

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

## Author
Matt Raymond Ayento
Nagoya University
G30, 3rd year Automotive Engineering (Electrical, Electronics, Information Engineering)