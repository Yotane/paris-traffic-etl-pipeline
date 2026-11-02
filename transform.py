import pandas as pd
from typing import Dict, List, Tuple, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Official Paris Open Data definitions (comptages routiers permanents):
#   q = débit: vehicles counted during the hour
#   k = taux d'occupation: % of the hour the sensor loop is occupied by vehicles
# etat_trafic is derived from k using these thresholds (lower bound inclusive)
OCCUPANCY_STATE_THRESHOLDS = [
    (50, 'Bloqué'),
    (30, 'Saturé'),
    (15, 'Pré-saturé'),
    (0, 'Fluide'),
]

def expected_traffic_state(k: float) -> Optional[str]:
    """Return the etat_trafic implied by occupancy k (%) under the official thresholds."""
    if pd.isna(k):
        return None
    for lower_bound, state in OCCUPANCY_STATE_THRESHOLDS:
        if k >= lower_bound:
            return state
    return None

def transform_traffic_data(raw_chunk: List[Dict]) -> Dict[str, pd.DataFrame]:
    """
    Clean and transform raw traffic data with tiered quality assessment.

    k is occupancy (%), not speed. An earlier version treated k as speed and
    multiplied values < 1 by 100 as a suspected "decimal error"; that hypothesis
    was retracted (see README) and k is now passed through unchanged.

    Args:
        raw_chunk: List of raw traffic records from Paris open data API

    Returns:
        Dict[str, pd.DataFrame]: {'segments': metadata_df, 'readings': timeseries_df}
    """
    logger.info(f"Transforming {len(raw_chunk)} records")

    df = pd.DataFrame(raw_chunk)


    # STEP 1: Drop rows missing both flow and occupancy (no usable signal)

    both_null = (df['q'].isna()) & (df['k'].isna())
    df_clean = df[~both_null].copy()
    logger.info(f"Dropped {both_null.sum()} rows with no traffic data")


    # STEP 2: Remove physically impossible outliers

    # Occupancy is a percentage of the hour (0-100); negative flow is sensor error
    outliers = (df_clean['k'] < 0) | (df_clean['k'] > 100) | (df_clean['q'] < 0)
    df_clean = df_clean[~outliers]
    logger.info(f"Removed {outliers.sum()} physically impossible outliers")


    # STEP 3: Extract GPS coordinates from nested geo_point_2d field

    df_clean['latitude'] = df_clean['geo_point_2d'].apply(
        lambda x: x['lat'] if pd.notna(x) and isinstance(x, dict) else None
    )
    df_clean['longitude'] = df_clean['geo_point_2d'].apply(
        lambda x: x['lon'] if pd.notna(x) and isinstance(x, dict) else None
    )


    # STEP 4: Tiered quality assessment

    def assign_quality_flag(row) -> Tuple[str, float]:
        """
        Assign quality flag and score (0.0-1.0) based on data quality.

        Quality tiers (highest to lowest confidence):
        Tier 1: Reported state contradicts occupancy -> 0.5
        Tier 2: Sensor status issues -> 0.1-0.6
        Tier 3: Partial missingness -> 0.8
        Tier 4: Fully valid data -> 1.0
        """

        # Tier 1: etat_trafic should match the state implied by k
        expected_state = expected_traffic_state(row['k'])
        if expected_state is not None and row['etat_trafic'] != expected_state:
            return 'INCONSISTENT_OCCUPANCY_STATE', 0.5

        # Tier 2: Sensor quality issues
        if row['etat_barre'] == 'Invalide':
            if pd.notna(row['q']) or pd.notna(row['k']):
                return 'INVALID_SENSOR_HAS_DATA', 0.6
            else:
                return 'INVALID_SENSOR_NO_DATA', 0.1

        # Tier 3: Missing single metric
        if pd.isna(row['q']) and pd.notna(row['k']):
            return 'MISSING_FLOW', 0.8
        if pd.isna(row['k']) and pd.notna(row['q']):
            return 'MISSING_OCCUPANCY', 0.8

        # Tier 4: Good quality
        return 'OK', 1.0

    df_clean[['data_quality_flag', 'quality_score']] = df_clean.apply(
        assign_quality_flag, axis=1, result_type='expand'
    )

    # Log quality distribution
    quality_dist = df_clean['data_quality_flag'].value_counts()
    logger.info(f"Quality distribution:")
    for flag, count in quality_dist.items():
        logger.info(f"  {flag}: {count} ({count/len(df_clean)*100:.1f}%)")


    # STEP 5: Prepare road_segments dimension table

    segments_df = df_clean[['iu_ac', 'libelle', 'latitude', 'longitude',
                             'iu_nd_amont', 'libelle_nd_amont',
                             'iu_nd_aval', 'libelle_nd_aval',
                             'date_debut', 'date_fin', 'geo_shape']].copy()

    segments_df['geo_shape'] = segments_df['geo_shape'].apply(
        lambda x: str(x) if pd.notna(x) else None
    )

    segments_df = segments_df.drop_duplicates(subset=['iu_ac'])
    segments_df.columns = ['segment_id', 'street_name', 'latitude', 'longitude',
                           'upstream_node_id', 'upstream_node_name',
                           'downstream_node_id', 'downstream_node_name',
                           'sensor_install_date', 'sensor_end_date', 'geometry_json']


    # STEP 6: Prepare traffic_readings fact table

    readings_df = df_clean[['iu_ac', 't_1h', 'q', 'k', 'etat_trafic',
                            'etat_barre', 'data_quality_flag', 'quality_score']].copy()

    readings_df.columns = ['segment_id', 'timestamp', 'traffic_flow', 'occupancy_rate',
                        'traffic_state', 'sensor_status', 'data_quality_flag', 'quality_score']

    readings_df['timestamp'] = pd.to_datetime(readings_df['timestamp'])
    readings_df['is_flow_imputed'] = False

    readings_df = readings_df[[
        'segment_id', 'timestamp', 'traffic_flow', 'occupancy_rate',
        'traffic_state', 'sensor_status', 'is_flow_imputed',
        'data_quality_flag', 'quality_score'
    ]]

    logger.info(f"Created {len(segments_df)} segments, {len(readings_df)} readings")

    return {
        'segments': segments_df,
        'readings': readings_df
    }

if __name__ == '__main__':
    import json

    with open('Data/data_january1.json', 'r', encoding='utf-8') as f:
        sample = json.load(f)[:1000]

    result = transform_traffic_data(sample)
    print(f"Segments: {len(result['segments'])}")
    print(f"Readings: {len(result['readings'])}")
    print(f"\nQuality distribution:")
    print(result['readings']['data_quality_flag'].value_counts())
