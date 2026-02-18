import json
import pandas as pd

with open('Data/data_january1.json', 'r') as f:
    data = json.load(f)

df = pd.DataFrame(data)

print("Speed Distribution Analysis")
print("=" * 60)

# Speeds < 1
very_low = df[(df['k'] > 0) & (df['k'] < 1)]
print(f"\nSpeeds between 0-1 km/h: {len(very_low)}")
print(f"Traffic states for these speeds:")
print(very_low['etat_trafic'].value_counts())
print(f"\nSensor status:")
print(very_low['etat_barre'].value_counts())

# Speeds 1-10
low_speed = df[(df['k'] >= 1) & (df['k'] < 10)]
print(f"\n\nSpeeds between 1-10 km/h: {len(low_speed)}")
print(f"Traffic states:")
print(low_speed['etat_trafic'].value_counts())

# Speeds 10-100
normal_speed = df[(df['k'] >= 10) & (df['k'] < 100)]
print(f"\n\nSpeeds between 10-100 km/h: {len(normal_speed)}")
print(f"Traffic states:")
print(normal_speed['etat_trafic'].value_counts())

# Check if there's a pattern
print("\n\nSample of speeds < 1:")
print(very_low[['libelle', 'k', 'etat_trafic', 'etat_barre', 'q']].head(20))

# Check: Are speeds < 1 marked as "Blocked"?
blocked_with_low_speed = very_low[very_low['etat_trafic'] == 'Bloqué']
print(f"\n\nBlocked traffic with speed < 1: {len(blocked_with_low_speed)}")

# Check: What about "Fluide" (flowing) with speed < 1? (This would be suspicious!)
fluide_with_low_speed = very_low[very_low['etat_trafic'] == 'Fluide']
print(f"Flowing traffic with speed < 1: {len(fluide_with_low_speed)}")
print("\nSample:")
print(fluide_with_low_speed[['libelle', 'k', 'etat_trafic', 'q']].head(10))