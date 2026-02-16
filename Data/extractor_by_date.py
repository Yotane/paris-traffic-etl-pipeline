import ijson
import json
from decimal import Decimal
import os

# --- CONFIGURATION ---
INPUT_FILE = "local_merged_data_01_04.json"
TARGET_MONTH = "2023-01" 
OUTPUT_FILE = f"data_sample_{TARGET_MONTH}.json"
LIMIT = 62622  # Stop after this many matches

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

def run_extraction():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: Could not find {INPUT_FILE}")
        return

    print(f"Starting sample extraction (Limit: {LIMIT})...")
    count = 0
    total_processed = 0

    with open(INPUT_FILE, 'rb') as f:
        parser = ijson.items(f, 'item')
        
        with open(OUTPUT_FILE, 'w') as out_f:
            out_f.write('[') 
            first = True
            
            try:
                for record in parser:
                    total_processed += 1
                    timestamp = record.get('t_1h', '')
                    
                    if timestamp and timestamp.startswith(TARGET_MONTH):
                        # OPTIONAL: Remove the heavy geometry to make VS Code even happier
                        # record.pop('geo_shape', None) 
                        
                        if not first:
                            out_f.write(',')
                        
                        json.dump(record, out_f, default=decimal_default)
                        
                        first = False
                        count += 1
                        
                        if count % 1000 == 0:
                            print(f"Found {count} matches...")

                        # STOP HERE
                        if count >= LIMIT:
                            print(f"Reached limit of {LIMIT} matches. Stopping.")
                            break

            except Exception as e:
                print(f"\nAn error occurred: {e}")
                
            out_f.write(']') 

    print(f"\nFinished!")
    print(f"Total records saved to {OUTPUT_FILE}: {count}")

if __name__ == "__main__":
    run_extraction()