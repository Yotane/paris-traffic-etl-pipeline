import json
import sys
import pandas as pd

from transform import expected_traffic_state

# Verifies that k is occupancy (%), not speed: the official Paris thresholds on k
# (Fluide < 15 <= Pré-saturé < 30 <= Saturé < 50 <= Bloqué) should reproduce etat_trafic
file_path = sys.argv[1] if len(sys.argv) > 1 else 'Data/data_january1.json'

with open(file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

df = pd.DataFrame(data)

print("Occupancy (k) Distribution Analysis")
print("=" * 60)

print(f"\nk summary (should lie within 0-100 %):")
print(df['k'].describe())

# Records that the retracted hypothesis treated as decimal errors
very_low = df[(df['k'] > 0) & (df['k'] < 1)]
print(f"\nOccupancy between 0-1 %: {len(very_low)}")
print(f"Traffic states (expected: all Fluide, since k < 15):")
print(very_low['etat_trafic'].value_counts())

# Reported state vs state derived from k
df['expected_state'] = df['k'].apply(expected_traffic_state).fillna('k is null')
print("\n\nReported etat_trafic vs state derived from k:")
print(pd.crosstab(df['etat_trafic'], df['expected_state']))

has_k = df['k'].notna()
matches = (df.loc[has_k, 'etat_trafic'] == df.loc[has_k, 'expected_state']).sum()
print(f"\nMatch rate: {matches}/{has_k.sum()} ({matches / has_k.sum() * 100:.2f}%) of records with k")
