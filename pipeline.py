from extract import extract_traffic_data
from transform import transform_traffic_data
from load import load_to_mysql
import logging
import argparse
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_pipeline(input_file: str, chunk_size: int = 5000):
    """
    Run complete ETL pipeline on any extracted JSON file.
    
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
            logger.info(f"Progress: {total_processed} records")
        
        elapsed = datetime.now() - start_time
        logger.info("Pipeline complete")
        logger.info(f"Total: {total_processed} records, Time: {elapsed}")
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        raise

def run_date_range(start_date: str, end_date: str, chunk_size: int = 5000):
    """
    Extract and load data for a range of dates.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        chunk_size: Records per chunk
    """
    from extractor_by_date import run_extraction
    
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    current = start
    
    logger.info(f"Running pipeline for date range: {start_date} to {end_date}")
    
    while current <= end:
        date_str = current.strftime("%Y-%m-%d")
        logger.info(f"Processing date: {date_str}")
        
        # Extract
        output_file = run_extraction(date_str)
        
        if output_file:
            # Load
            run_pipeline(output_file, chunk_size)
        
        current += timedelta(days=1)
    
    logger.info("Date range pipeline complete")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run Paris Traffic ETL Pipeline')
    parser.add_argument(
        '--file',
        type=str,
        default='Data/data_january1.json',
        help='Path to input JSON file'
    )
    parser.add_argument(
        '--date',
        type=str,
        default=None,
        help='Extract and load a single date (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--start-date',
        type=str,
        default=None,
        help='Start of date range (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--end-date',
        type=str,
        default=None,
        help='End of date range (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--chunk-size',
        type=int,
        default=5000,
        help='Records per chunk (default: 5000)'
    )
    
    args = parser.parse_args()
    
    if args.start_date and args.end_date:
        # Load entire date range
        run_date_range(args.start_date, args.end_date, args.chunk_size)
    elif args.date:
        # Extract and load single date
        from extractor_by_date import run_extraction
        output_file = run_extraction(args.date)
        if output_file:
            run_pipeline(output_file, args.chunk_size)
    else:
        # Load already extracted file
        run_pipeline(args.file, args.chunk_size)