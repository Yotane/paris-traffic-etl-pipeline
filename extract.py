import json
from typing import Generator, List, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_traffic_data(filepath: str, chunk_size: int = 1000) -> Generator[List[Dict], None, None]:
    """
    Read extracted JSON file in chunks for ETL processing.
    
    Args:
        filepath: Path to extracted JSON file
        chunk_size: Number of records per chunk
        
    Yields:
        List of dictionaries containing traffic records
    """
    logger.info(f"Reading data from: {filepath}")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        total_records = len(data)
        logger.info(f"Total records: {total_records}")
        
        for i in range(0, total_records, chunk_size):
            chunk = data[i:i + chunk_size]
            yield chunk
            logger.info(f"Extracted chunk: {i+1}-{min(i+chunk_size, total_records)} / {total_records}")
            
    except FileNotFoundError:
        logger.error(f"File not found: {filepath}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON: {e}")
        raise

if __name__ == '__main__':
    for chunk in extract_traffic_data('data_january1.json', chunk_size=5000):
        print(f"Chunk size: {len(chunk)}")