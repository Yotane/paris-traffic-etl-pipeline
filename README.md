# Paris Traffic Data Pipeline
**Data Engineering portfolio project demonstrating ETL pipeline design, API development, and data quality management. Made for educational purposes such as data engineering and API practice.**

ETL pipeline for processing and analyzing Paris road traffic sensor data (2023) obtained from:
https://www.kaggle.com/datasets/chafikboulealam/local-merged-data

Dataset description from Kaggle:
This dataset contains more than 5,000,000 observations of road traffic conditions in Paris, France, collected during the year 2023. Each entry represents the state of traffic on a specific road segment at a given hourly timestamp. The data is ideal for classification, time-series analysis, and geospatial modeling tasks in intelligent transportation systems and urban mobility research.

### Data Schema Overview
| Field | Type | Description |
|-------|------|-------------|
| Segment ID | String | Unique identifier for the road segment (arc) |
| Street name | String | Human-readable street name (e.g., "Bd_de_Belleville") |
| Timestamp | Timestamp | Hourly observation time in ISO 8601 format (`2023-01-01T03:00:00+00:00`) |
| Traffic flow (`q`) | Float | Number of vehicles counted during the hour (frequently null due to sensor maintenance) |
| Occupancy rate (`k`) | Float | Percentage of the hour (0-100) during which the sensor loop is occupied by vehicles. **Not speed.** Frequently null due to sensor maintenance. Stored as `occupancy_rate`. |
| Traffic state | String | Derived from `k` by the source: Free-flowing (k < 15%), Pre-saturated (15-30%), Saturated (30-50%), Blocked (≥ 50%), or Unknown (k missing) |
| Upstream / downstream node IDs | String | Node IDs at each end of the segment, for network topology analysis |
| Sensor status | String | Open, Closed, or Invalid (used for data quality filtering) |
| Centroid | Object | Centroid coordinates `{lon, lat}` for mapping and spatial joins |
| Geometry | GeoJSON | `LineString` geometry defining the precise road segment path for geospatial visualization |

The source data and the code use the original French field names and values. See the [Language Note](#language-note) at the end for the mapping.

**Note on `k`:** The Kaggle description (and earlier versions of this README) treat `k` as average speed in km/h. The original source, the Paris Open Data [permanent road counting dataset](https://opendata.paris.fr/explore/dataset/comptages-routiers-permanents/information/), defines it differently. Its notice describes `q` as "flow (number of vehicles counted during the hour)" and `k` as "occupancy rate (percentage of time during the hour that the measuring station is occupied by vehicles)". It also derives the traffic state from `k` using the thresholds above. Occupancy is a proxy for traffic density, not speed.

Originally sourced as a large nested JSON file, this cleaned and structured version has been preprocessed for ease of use in machine learning workflows. It includes both numerical traffic metrics (e.g., flow and speed) and categorical labels (e.g., traffic state), along with rich geospatial metadata.

## Data Quality
However this dataset is very messy as it has a lot of missing data:
q (flow): 52.4% missing
k (occupancy): 51.6% missing
Geospatial and date fields: 0.7% missing
Duplicates: Present and should be removed before modeling.
Class Imbalance: Present in the traffic state and requires resampling or cost-sensitive learning.
Upon checking, I found that there around 40.0% missing both q and k and around 80.0% of sensors are marked invalid.

### Retracted Hypothesis: "Decimal Errors" in k
An earlier version of this pipeline treated `k` as speed in km/h, following the Kaggle description. Under that reading the data looked broken:

- The mean "speed" was 4.88 km/h.
- All 5,603 records with k < 1 were marked Free-flowing.
- Records such as Quai_Hotel_de_Ville (k = 0.18778, q = 406 veh/h, Free-flowing) seemed to show 406 cars/hour moving at walking pace.

I concluded these were decimal placement errors. The ETL multiplied k by 100 when several "signals" agreed: k < 1, flow > 100, state Free-flowing, and sensor Open. It then validated the results with a fundamental-diagram check (flow = density × speed).

**This hypothesis was wrong, and the correction has been removed.** `k` is occupancy, the percentage of the hour the sensor loop is occupied, and the source derives the traffic state from it. Free-flowing means k < 15%, so a low k paired with Free-flowing is exactly what the definition predicts. A mean of 4.88% is a normal occupancy for mostly free-flowing traffic. The fundamental-diagram check did not apply as written, because occupancy is a proxy for density, not speed. The ×100 "correction" therefore changed 114 correct values in the Jan 1-2 data.

**Evidence** ([occupancy_analysis.py](occupancy_analysis.py)): the official thresholds reproduce the reported traffic state for every record that has a `k` value. Unknown appears exactly when `k` is missing.

| Reported traffic state | State derived from k (Jan 1) | Count | Match |
|------------------------|------------------------------|-------|-------|
| Free-flowing | k < 15% | 28,388 | 100% |
| Pre-saturated | 15% ≤ k < 30% | 1,125 | 100% |
| Saturated | 30% ≤ k < 50% | 263 | 100% |
| Blocked | k ≥ 50% | 119 | 100% |
| Unknown | k missing | 32,727 | 100% |

Jan 2 shows the same result: 34,120 of 34,120 records with `k` match. The maximum `k` across both days is 98.9, consistent with a 0-100% scale.

**What changed:**
- `k` is loaded unchanged into `occupancy_rate` (previously `avg_speed`).
- The `is_speed_corrected` and `correction_confidence` columns were dropped.
- The flags built on the speed reading were removed: `CORRECTED_DECIMAL_ERROR_*`, `INCONSISTENT_STOPPED_WITH_FLOW` (q > 100 with k < 2, which is normal at 2% occupancy), `INCONSISTENT_EXTREME_FLOW_SPEED`, and `INCONSISTENT_SPEED_STATE`.
- The outlier rule "k > 200 km/h" became "k outside 0-100%".
- A new check, `INCONSISTENT_OCCUPANCY_STATE`, flags any record whose traffic state disagrees with the state derived from `k`.

**Lesson:** check the original data publisher's documentation, not only a secondary description, before "correcting" values that look implausible.

### Data Cleaning
In the ETL, transform.py cleans and transforms raw traffic data with tiered quality assessment:
1. Drop rows missing both flow and occupancy (no usable signal)
2. Remove physically impossible values (occupancy outside 0-100%, negative flow)
3. Extract structured GPS coordinates from nested GeoJSON
4. Assign tiered quality flags, including a consistency check of the traffic state against the official occupancy thresholds
5. Split normalized output into dimension (segments) and fact (readings) tables

Three files for ETL: extract.py, transform.py, load.py. pipeline.py orchestrates execution.

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

**Upgrading an existing database** (created before the `k` = occupancy fix):
```sql
SOURCE SQL/migrations/001_k_is_occupancy.sql;
```
Then re-run `pipeline.py` for every date already loaded. The upsert overwrites the old ×100 "corrected" values and the speed-based quality flags.

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
  - Retained: 63.3% of raw records (after dropping rows missing both flow and occupancy)
  - Dropped: 36.7% (missing core metrics or physically impossible values)
- **Unique road segments:** 1,779 (stable across dates, confirms dimension table integrity)
- **Traffic state consistency:** 100% of readings with `k` match the state derived from the official occupancy thresholds (0 `INCONSISTENT_OCCUPANCY_STATE`)

### Quality Distribution (Jan 1-2 Combined)

Each reading gets the flag of the first rule it matches, checked in the order shown in the "Check Order" column. Rows are sorted by increasing quality score.

| Score | Flag | Rule | Check Order | Jan 1-2 |
|-------|------|------|-------------|---------|
| 0.1 | `INVALID_SENSOR_NO_DATA` | Sensor is Invalid and sent neither `q` nor `k` | 2 | 0 (already dropped in cleaning step 1) |
| 0.5 | `INCONSISTENT_OCCUPANCY_STATE` | `k` exists, but the reported traffic state is not the state the official thresholds give for that `k` | 1 | 0 |
| 0.6 | `INVALID_SENSOR_HAS_DATA` | Sensor is Invalid but still sent `q` or `k` | 2 | 68,998 (86.33%) |
| 0.8 | `MISSING_FLOW` | `q` missing, `k` present | 3 | 2,663 (3.33%) |
| 0.8 | `MISSING_OCCUPANCY` | `k` missing, `q` present | 3 | 679 (0.85%) |
| 1.0 | `OK` | None of the above | 4 | 7,579 (9.48%) |

**Total readings:** 79,919 (sum of all counts)

These counts come from running the current transform.py over the Jan 1-2 files with the pipeline's chunking and the `(segment_id, timestamp)` upsert. Running the previous transform.py the same way reproduces the previously published database results exactly. Those results included 9,769 `INCONSISTENT_STOPPED_WITH_FLOW` and 114 `CORRECTED_DECIMAL_ERROR_*` readings, which were artifacts of the speed misreading described above.

**Key Insight:** Only 9.48% of readings are "OK" quality, highlighting the real-world messiness of sensor data. The 86.33% flagged as `INVALID_SENSOR_HAS_DATA` reflects that most Paris traffic sensors were marked invalid in January 2023 but still reported data, which is a common issue in municipal IoT deployments.

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
GET /analytics/occupancy-stats        NumPy occupancy statistics
GET /analytics/quality-report         Data quality breakdown
GET /analytics/congestion-hotspots    Blocked/saturated segments
```
**Example Request:**
```bash
curl "http://localhost:8000/analytics/occupancy-stats?min_quality_score=0.8"
```

**Expected Response (January 1 and 2 data; values are occupancy in %):**
```json
{"segment_id":null,"mean_occupancy":9.13,"median_occupancy":7.15,"std_dev":8.47,"percentile_25":3.4,"percentile_75":11.8,"min_occupancy":0.0,"max_occupancy":71.6,"sample_size":10242}
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

## Language Note
The source data (Paris Open Data, redistributed on Kaggle) is in French. The code keeps the original French field names and category values: raw records in `transform.py`, the `ENUM` values in `SQL/schema.sql`, and the values the API returns (e.g., `traffic_state = 'Fluide'`). Database column names are in English. This README uses English equivalents throughout; the mapping is below.

**Fields**

| README (English) | Source field (French) | Database column |
|------------------|-----------------------|-----------------|
| Segment ID | `iu_ac` | `segment_id` |
| Street name | `libelle` | `street_name` |
| Timestamp | `t_1h` | `timestamp` |
| Traffic flow | `q` (*débit*) | `traffic_flow` |
| Occupancy rate | `k` (*taux d'occupation*) | `occupancy_rate` |
| Traffic state | `etat_trafic` | `traffic_state` |
| Sensor status | `etat_barre` | `sensor_status` |
| Upstream node ID / name | `iu_nd_amont` / `libelle_nd_amont` | `upstream_node_id` / `upstream_node_name` |
| Downstream node ID / name | `iu_nd_aval` / `libelle_nd_aval` | `downstream_node_id` / `downstream_node_name` |
| Sensor install / end date | `date_debut` / `date_fin` | `sensor_install_date` / `sensor_end_date` |
| Centroid | `geo_point_2d` | `latitude`, `longitude` |
| Geometry | `geo_shape` | `geometry_json` |

**Values**

| README (English) | Source and code value (French) |
|------------------|--------------------------------|
| Free-flowing | `Fluide` |
| Pre-saturated | `Pré-saturé` |
| Saturated | `Saturé` |
| Blocked | `Bloqué` |
| Unknown | `Inconnu` |
| Open | `Ouvert` |
| Closed | `Barré` |
| Invalid | `Invalide` |

**Original definitions** from the Paris Open Data notice, translated in the [Note on `k`](#data-schema-overview) above:
- `q`: "Débit (nombre de véhicules comptés pendant l'heure)"
- `k`: "Taux d'occupation (en pourcentage de temps d'occupation de la station de mesure par des véhicules sur l'heure)"
