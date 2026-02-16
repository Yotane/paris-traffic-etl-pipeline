import mysql.connector
import pandas as pd
from config import DB_CONFIG
from typing import Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_to_mysql(transformed_data: Dict[str, pd.DataFrame]):
    """
    Load transformed data into MySQL database.
    
    Args:
        transformed_data: Dictionary with 'segments' and 'readings' DataFrames
    """
    logger.info("Loading data to MySQL")
    
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        segments_df = transformed_data['segments']
        
        insert_segment_query = """
        INSERT IGNORE INTO road_segments 
        (segment_id, street_name, latitude, longitude, 
         upstream_node_id, upstream_node_name,
         downstream_node_id, downstream_node_name,
         sensor_install_date, sensor_end_date, geometry_json)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        segment_data = [tuple(row) for row in segments_df.values]
        cursor.executemany(insert_segment_query, segment_data)
        logger.info(f"Inserted {cursor.rowcount} segments")
        
        readings_df = transformed_data['readings']
        
        insert_reading_query = """
        INSERT INTO traffic_readings
        (segment_id, timestamp, traffic_flow, avg_speed,
         traffic_state, sensor_status, is_flow_imputed, is_speed_corrected, 
         data_quality_flag, quality_score)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        reading_data = [tuple(row) for row in readings_df.values]
        cursor.executemany(insert_reading_query, reading_data)
        logger.info(f"Inserted {cursor.rowcount} readings")
        
        conn.commit()
        logger.info("Data loaded successfully")
        
    except mysql.connector.Error as err:
        logger.error(f"MySQL Error: {err}")
        conn.rollback()
        raise
        
    finally:
        cursor.close()
        conn.close()