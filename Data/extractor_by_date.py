import ijson
import json
from decimal import Decimal
import os
import argparse

INPUT_FILE = "Data/local_merged_data_01_04.json"

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


def run_extraction(target_date: str, limit: int = None):
    #Extract records for a specific date from large JSON file.

    output_file = f"Data/data_{target_date}.json"
    
    if not os.path.exists(INPUT_FILE):
        print(f"Error: Could not find {INPUT_FILE}")
        return None

    print(f"Extracting data for date: {target_date}")
    if limit:
        print(f"Limit: {limit} records")
    
    count = 0
    total_processed = 0

    with open(INPUT_FILE, 'rb') as f:
        parser = ijson.items(f, 'item')
        
        with open(output_file, 'w') as out_f:
            out_f.write('[')
            first = True
            
            try:
                for record in parser:
                    total_processed += 1
                    timestamp = record.get('t_1h', '')
                    
                    if timestamp and timestamp.startswith(target_date):
                        if not first:
                            out_f.write(',')
                        
                        json.dump(record, out_f, default=decimal_default)
                        first = False
                        count += 1
                        
                        if count % 5000 == 0:
                            print(f"Found {count} matches...")
                        
                        if limit and count >= limit:
                            print(f"Reached limit of {limit}. Stopping.")
                            break
                            
            except Exception as e:
                print(f"Error: {e}")
                
            out_f.write(']')

    print(f"Saved {count} records to {output_file}")
    return output_file

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Extract Paris traffic data for a specific date')
    parser.add_argument(
        '--date',
        type=str,
        default='2023-01-01',
        help='Date to extract in YYYY-MM-DD format (default: 2023-01-01)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Max records to extract (default: all records for that date)'
    )
    
    args = parser.parse_args()
    run_extraction(args.date, args.limit)