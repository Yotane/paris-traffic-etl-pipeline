import ijson
import json
from decimal import Decimal

# --- CONFIGURATION ---
FILE_TO_READ = "data_january1.json"
ROW_NUMBER = 62622

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def inspect():
    print(f"Searching for row {ROW_NUMBER} in {FILE_TO_READ}...")
    
    with open(FILE_TO_READ, 'rb') as f:
        # We use enumerate to count as we go
        parser = ijson.items(f, 'item')
        
        for index, record in enumerate(parser, 1):
            if index == ROW_NUMBER:
                print(f"\n--- FOUND ROW {ROW_NUMBER} ---\n")
                # indent=4 makes it pretty and easy to read in the terminal
                print(json.dumps(record, indent=4, default=decimal_default))
                return
        
        print(f"Finished. The file only has {index} rows.")

if __name__ == "__main__":
    inspect()