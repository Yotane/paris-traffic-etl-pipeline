from extract import extract_traffic_data
from transform import transform_traffic_data
from load import load_to_mysql
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_pipeline(input_file: str, chunk_size: int = 5000):
    """
    Run complete ETL pipeline.
    
    Args:
        input_file: Path to extracted JSON file
        chunk_size: Records per chunk
    """
    start_time = datetime.now()
    
    logger.info("Starting ETL pipeline")
    logger.info(f"Input: {input_file}, Chunk size: {chunk_size}")
    
    total_processed = 0
    
    try:
        for chunk in extract_traffic_data(input_file, chunk_size=chunk_size):
            transformed = transform_traffic_data(chunk)
            load_to_mysql(transformed)
            
            total_processed += len(chunk)
            logger.info(f"Progress: {total_processed} records processed")
        
        elapsed = datetime.now() - start_time
        
        logger.info("Pipeline complete")
        logger.info(f"Total: {total_processed} records, Time: {elapsed}")
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        raise

if __name__ == '__main__':
    run_pipeline('../data_january1.json')