import mysql.connector
import pandas as pd
import numpy as np
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
                         readings DataFrame includes new 'correction_confidence' column
    """
    logger.info("Loading data to MySQL")
    
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        
        # Load road_segments dimension table
        
        segments_df = transformed_data['segments']
        
        # Replace NaN with None for MySQL compatibility (NULL values)
        segments_df = segments_df.replace({np.nan: None})
        
        # INSERT IGNORE: Skip duplicates based on UNIQUE KEY (segment_id)
        # Column order must match the VALUES placeholders exactly
        insert_segment_query = """
        INSERT IGNORE INTO road_segments 
        (segment_id, street_name, latitude, longitude, 
         upstream_node_id, upstream_node_name,
         downstream_node_id, downstream_node_name,
         sensor_install_date, sensor_end_date, geometry_json)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        # Convert DataFrame rows to list of tuples for executemany
        segment_data = [tuple(row) for row in segments_df.values]
        cursor.executemany(insert_segment_query, segment_data)
        logger.info(f"Inserted {cursor.rowcount} segments")
        
        
        # Load traffic_readings fact table
        # UPDATED: Added correction_confidence column (11 columns total)
        
        readings_df = transformed_data['readings']
        
        # Replace NaN with None for MySQL compatibility
        readings_df = readings_df.replace({np.nan: None})
        
        # INSERT query with 11 columns to match transform.py output order:
        # segment_id, timestamp, traffic_flow, avg_speed, traffic_state, 
        # sensor_status, is_flow_imputed, is_speed_corrected, 
        # correction_confidence, data_quality_flag, quality_score
        insert_reading_query = """
        INSERT INTO traffic_readings
        (segment_id, timestamp, traffic_flow, avg_speed,
         traffic_state, sensor_status, is_flow_imputed, is_speed_corrected,
         correction_confidence, data_quality_flag, quality_score)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE 
            traffic_flow = VALUES(traffic_flow),
            avg_speed = VALUES(avg_speed),
            traffic_state = VALUES(traffic_state),
            sensor_status = VALUES(sensor_status),
            is_flow_imputed = VALUES(is_flow_imputed),
            is_speed_corrected = VALUES(is_speed_corrected),
            correction_confidence = VALUES(correction_confidence),
            data_quality_flag = VALUES(data_quality_flag),
            quality_score = VALUES(quality_score),
            created_at = CURRENT_TIMESTAMP
        """
        
        # Convert DataFrame rows to list of tuples for executemany
        # Order must exactly match the 11 %s placeholders above
        reading_data = [tuple(row) for row in readings_df.values]
        cursor.executemany(insert_reading_query, reading_data)
        logger.info(f"Inserted {cursor.rowcount} readings")
        
        # Commit all changes to database
        conn.commit()
        logger.info("Data loaded successfully")
        
    except mysql.connector.Error as err:
        # Log error and rollback to maintain data integrity
        logger.error(f"MySQL Error: {err}")
        conn.rollback()
        raise
        
    finally:
        # Always close cursor and connection to free resources
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
        logger.info("MySQL connection closed")