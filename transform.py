import pandas as pd
from typing import Dict, List, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def transform_traffic_data(raw_chunk: List[Dict]) -> Dict[str, pd.DataFrame]:
    """
    Clean and transform raw traffic data with tiered quality assessment.
    
    Args:
        raw_chunk: List of raw traffic records
        
    Returns:
        Dictionary containing 'segments' and 'readings' DataFrames
    """
    logger.info(f"Transforming {len(raw_chunk)} records")
    
    df = pd.DataFrame(raw_chunk)
    
    # Step 1: Fix decimal errors in speed
    df['k_original'] = df['k'].copy()
    df['is_speed_corrected'] = False
    
    decimal_mask = (df['k'] > 0) & (df['k'] < 1)
    df.loc[decimal_mask, 'k'] = df.loc[decimal_mask, 'k'] * 100
    df.loc[decimal_mask, 'is_speed_corrected'] = True
    
    logger.info(f"Fixed {decimal_mask.sum()} decimal errors in speed")
    
    # Step 2: Drop rows missing both flow and speed
    both_null = (df['q'].isna()) & (df['k'].isna())
    df_clean = df[~both_null].copy()
    logger.info(f"Dropped {both_null.sum()} rows with no data")
    
    # Step 3: Remove impossible outliers
    outliers = (df_clean['k'] > 200) | (df_clean['q'] < 0)
    df_clean = df_clean[~outliers]
    logger.info(f"Removed {outliers.sum()} impossible outliers")
    
    # Step 4: Extract GPS coordinates
    df_clean['latitude'] = df_clean['geo_point_2d'].apply(
        lambda x: x['lat'] if pd.notna(x) and isinstance(x, dict) else None
    )
    df_clean['longitude'] = df_clean['geo_point_2d'].apply(
        lambda x: x['lon'] if pd.notna(x) and isinstance(x, dict) else None
    )
    
    # Step 5: Assign quality flags and scores
    def assign_quality_flag(row) -> Tuple[str, float]:
        """
        Assign quality flag and score (0.0-1.0) based on data quality.
        
        Thresholds based on:
        - Paris average rush hour speed: 19 km/h
        - Typical Paris city speeds: 13-17 km/h
        - Urban arterial capacity: 1,100-1,900 veh/hr/lane
        - Maximum flow at 40-60 km/h (not at high speeds)
        
        Returns:
            Tuple of (flag_name, quality_score)
        """
        
        # Tier 1: Corrected decimal errors
        if row.get('is_speed_corrected', False):
            return 'CORRECTED_DECIMAL_ERROR', 0.7
        
        # Tier 2: Check for genuine inconsistencies
        if pd.notna(row['k']) and pd.notna(row['q']):
            
            # High speed + blocked state (physically impossible)
            # Traffic can't be flowing at 60+ km/h if it's "blocked"
            if row['k'] > 60 and row['etat_trafic'] in ['Bloqué', 'Saturé']:
                return 'INCONSISTENT_SPEED_STATE', 0.5
            
            # Extremely high flow with unrealistically low speed
            # If flow > 2000 veh/hr (above lane capacity) but speed < 5 km/h
            # This suggests either sensor malfunction or remaining decimal error
            if row['q'] > 2000 and row['k'] < 5:
                return 'INCONSISTENT_EXTREME_FLOW_SPEED', 0.3
            
            # Very high flow at moderate-low speed (this is NORMAL for Paris!)
            # Paris rush hour: 500-1500 veh/hr at 10-25 km/h is typical
            # DON'T flag this as inconsistent anymore
            
            # Zero or near-zero speed with high flow (cars can't flow if stopped)
            if row['q'] > 100 and row['k'] < 2:
                return 'INCONSISTENT_STOPPED_WITH_FLOW', 0.4
        
        # Tier 3: Sensor quality issues
        if row['etat_barre'] == 'Invalide':
            if pd.notna(row['q']) or pd.notna(row['k']):
                return 'INVALID_SENSOR_HAS_DATA', 0.6
            else:
                return 'INVALID_SENSOR_NO_DATA', 0.1
        
        # Tier 4: Missing single metric
        if pd.isna(row['q']) and pd.notna(row['k']):
            return 'MISSING_FLOW', 0.8
        if pd.isna(row['k']) and pd.notna(row['q']):
            return 'MISSING_SPEED', 0.8
        
        # Tier 5: Good quality
        return 'OK', 1.0
    
    df_clean[['data_quality_flag', 'quality_score']] = df_clean.apply(
        assign_quality_flag, axis=1, result_type='expand'
    )
    
    # Log quality distribution
    quality_dist = df_clean['data_quality_flag'].value_counts()
    logger.info(f"Quality distribution:")
    for flag, count in quality_dist.items():
        logger.info(f"  {flag}: {count} ({count/len(df_clean)*100:.1f}%)")
    
    # Step 6: Prepare road_segments table
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
    
    # Step 7: Prepare traffic_readings table
    readings_df = df_clean[['iu_ac', 't_1h', 'q', 'k', 'etat_trafic', 
                            'etat_barre', 'is_speed_corrected',
                            'data_quality_flag', 'quality_score']].copy()

    readings_df.columns = ['segment_id', 'timestamp', 'traffic_flow', 'avg_speed',
                        'traffic_state', 'sensor_status', 'is_speed_corrected',
                        'data_quality_flag', 'quality_score']

    readings_df['timestamp'] = pd.to_datetime(readings_df['timestamp'])
    readings_df['is_flow_imputed'] = False


    readings_df = readings_df[[
        'segment_id', 'timestamp', 'traffic_flow', 'avg_speed',
        'traffic_state', 'sensor_status', 'is_flow_imputed', 'is_speed_corrected',
        'data_quality_flag', 'quality_score'
    ]]
    
    readings_df['timestamp'] = pd.to_datetime(readings_df['timestamp'])
    readings_df['is_flow_imputed'] = False
    
    logger.info(f"Created {len(segments_df)} segments, {len(readings_df)} readings")
    
    return {
        'segments': segments_df,
        'readings': readings_df
    }

if __name__ == '__main__':
    import json
    
    with open('data_january1.json', 'r') as f:
        sample = json.load(f)[:1000]
    
    result = transform_traffic_data(sample)
    print(f"Segments: {len(result['segments'])}")
    print(f"Readings: {len(result['readings'])}")
    print(f"\nQuality distribution:")
    print(result['readings']['data_quality_flag'].value_counts())