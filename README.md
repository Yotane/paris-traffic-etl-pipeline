# Paris Traffic Data Pipeline

ETL pipeline for processing and analyzing Paris road traffic sensor data (2023).

## Project Structure
- `SQL/schema.sql`: Database schema
- `extract.py`: Read JSON data in chunks
- `transform.py`: Clean and validate data
- `load.py`: Insert into MySQL
- `pipeline.py`: Orchestrate full ETL process

## Setup
1. Install MySQL
2. Create database: `CREATE DATABASE paris_traffic;`
3. Run schema: `mysql paris_traffic < SQL/schema.sql`
4. Copy `config.example.py` to `config.py` and set password
5. Install dependencies: `pip install pandas mysql-connector-python`

## Run
```bash
python pipeline.py
```

## Data Quality
- 53% of data has missing metrics
- Systematic decimal error in speed corrected
- Quality scoring system (0.0-1.0) flags data issues

## Author
Matt Raymond Ayento
Nagoya University
G30, 3rd year Automotive Engineering (Electrical, Electronics, Information Engineering)