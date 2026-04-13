import pandas as pd
from typing import Dict, List, Tuple, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def transform_traffic_data(raw_chunk: List[Dict]) -> Dict[str, pd.DataFrame]:
    """
    Clean and transform raw traffic data with tiered quality assessment.
    
    Implements production-grade data quality pipeline:
    1. Multi-signal validation for decimal error detection (speed + flow + state)
    2. Tiered correction strategy with confidence levels
    3. Post-correction validation using traffic physics (fundamental diagram)
    4. Transparent audit trail for all transformations
    
    Args:
        raw_chunk: List of raw traffic records from Paris open data API
        
    Returns:
        Dict[str, pd.DataFrame]: {'segments': metadata_df, 'readings': timeseries_df}
    """
    logger.info(f"Transforming {len(raw_chunk)} records")
    
    df = pd.DataFrame(raw_chunk)
    

    # STEP 1: Multi-signal validation for decimal placement errors in speed

    # Preserve original values for audit trail
    df['k_original'] = df['k'].copy()
    df['is_speed_corrected'] = False
    df['correction_confidence'] = None
    
    # Signal 1: Suspiciously low speed (< 1 km/h is unrealistic for urban traffic)
    low_speed = (df['k'] > 0) & (df['k'] < 1)
    
    # Signal 2: High flow with low speed is physically impossible
    # flow = density × speed; if speed≈0 but flow>100, implied density is impossible
    impossible_combo = low_speed & (df['q'] > 100)
    
    # Signal 3: Traffic state contradiction (can't be "Fluide" at 0.5 km/h)
    state_contradiction = low_speed & (df['etat_trafic'] == 'Fluide')
    
    # Signal 4: Sensor is operational (exclude known-bad sensors)
    sensor_ok = df['etat_barre'] == 'Ouvert'
    
    # Tier 1: HIGH confidence - auto-correct (all 4 signals align)
    high_confidence = impossible_combo & state_contradiction & sensor_ok
    
    # Tier 2: MEDIUM confidence - correct but flag heavily (3/4 signals)
    medium_confidence = low_speed & (
        ((df['q'] > 50) & (df['q'] <= 100)) |  # Moderate flow
        (df['etat_trafic'].isin(['Pré-saturé', 'Saturé']))  # Congested state
    ) & sensor_ok
    
    # Tier 3: LOW confidence - don't correct, just flag (only speed signal)
    low_confidence = low_speed & ~high_confidence & ~medium_confidence
    
    logger.info(f"Decimal error detection: HIGH={high_confidence.sum()}, MEDIUM={medium_confidence.sum()}, LOW={low_confidence.sum()}")
    
    # Apply corrections by tier
    # Tier 1: Auto-correct with high confidence
    df.loc[high_confidence, 'k'] = df.loc[high_confidence, 'k'] * 100
    df.loc[high_confidence, 'is_speed_corrected'] = True
    df.loc[high_confidence, 'correction_confidence'] = 'HIGH'
    
    # Tier 2: Correct but flag for downstream caution
    df.loc[medium_confidence, 'k'] = df.loc[medium_confidence, 'k'] * 100
    df.loc[medium_confidence, 'is_speed_corrected'] = True
    df.loc[medium_confidence, 'correction_confidence'] = 'MEDIUM'
    
    # Tier 3: Don't correct; flag as suspected error for manual review
    df.loc[low_confidence, 'is_speed_corrected'] = False
    df.loc[low_confidence, 'correction_confidence'] = 'LOW_SUSPECTED'
    

    # STEP 2: Post-correction validation using traffic physics

    corrected_mask = df['is_speed_corrected']
    if corrected_mask.any():
        corrected_speeds = df.loc[corrected_mask, 'k']
        
        # Validation 1: Realistic range check (Paris urban roads: 5-120 km/h)
        too_low = (corrected_speeds < 5).sum()
        too_high = (corrected_speeds > 120).sum()
        
        # Validation 2: Fundamental diagram check (flow = density × speed)
        # If speed is corrected but flow is still low, implied density may be impossible
        corrected_flows = df.loc[corrected_mask, 'q']
        valid_flow = corrected_flows.notna() & (corrected_flows > 0)
        if valid_flow.any():
            implied_density = corrected_flows[valid_flow] / corrected_speeds[valid_flow]
            impossible_density = (implied_density > 200).sum()  # Max ~200 veh/km/lane
        else:
            impossible_density = 0
        
        # Validation 3: Distribution check vs Paris benchmarks
        corrected_mean = corrected_speeds.mean()
        paris_typical_min, paris_typical_max = 13, 17  # From traffic engineering research
        
        logger.info(f"Post-correction validation:")
        logger.info(f"  Corrected {corrected_mask.sum()} records")
        logger.info(f"  Range: {corrected_speeds.min():.1f} - {corrected_speeds.max():.1f} km/h")
        logger.info(f"  Mean: {corrected_mean:.1f} km/h (Paris typical: {paris_typical_min}-{paris_typical_max})")
        logger.info(f"  Issues: {too_low} too low, {too_high} too high, {impossible_density} impossible density")
        
        # Log warnings for manual review
        if too_low > 0 or too_high > 0 or impossible_density > 0:
            logger.warning(f"  ⚠ {too_low + too_high + impossible_density} corrections need manual review")
    
    logger.info(f"Fixed {high_confidence.sum() + medium_confidence.sum()} decimal errors in speed")
    

    # STEP 3: Drop rows missing both flow and speed (no usable signal)

    both_null = (df['q'].isna()) & (df['k'].isna())
    df_clean = df[~both_null].copy()
    logger.info(f"Dropped {both_null.sum()} rows with no traffic data")
    

    # STEP 4: Remove physically impossible outliers

    # Speed > 200 km/h impossible on Paris roads; negative flow is sensor error
    outliers = (df_clean['k'] > 200) | (df_clean['q'] < 0)
    df_clean = df_clean[~outliers]
    logger.info(f"Removed {outliers.sum()} physically impossible outliers")
    

    # STEP 5: Extract GPS coordinates from nested geo_point_2d field

    df_clean['latitude'] = df_clean['geo_point_2d'].apply(
        lambda x: x['lat'] if pd.notna(x) and isinstance(x, dict) else None
    )
    df_clean['longitude'] = df_clean['geo_point_2d'].apply(
        lambda x: x['lon'] if pd.notna(x) and isinstance(x, dict) else None
    )
    

    # STEP 6: Tiered quality assessment with Paris-specific traffic rules

    def assign_quality_flag(row) -> Tuple[str, float]:
        """
        Assign quality flag and score (0.0-1.0) based on data quality.
        
        Quality tiers (highest to lowest confidence):
        Tier 1: High-confidence corrected values -> 0.85
        Tier 2: Medium-confidence corrected values -> 0.7
        Tier 3: Logical inconsistencies -> 0.3-0.5
        Tier 4: Sensor status issues -> 0.1-0.6
        Tier 5: Partial missingness -> 0.8
        Tier 6: Fully valid data -> 1.0
        Domain thresholds based on Paris traffic engineering research:
        - Average rush hour speed: 19 km/h
        - Typical city speeds: 13-17 km/h
        - Urban arterial capacity: 1,100-1,900 veh/hr/lane
        - Maximum flow occurs at 40-60 km/h (not at very high speeds)
        """
        
        # Tier 1-2: Corrected values (confidence-based scoring)
        if row.get('is_speed_corrected', False):
            confidence = row.get('correction_confidence', 'LOW')
            if confidence == 'HIGH':
                return 'CORRECTED_DECIMAL_ERROR_HIGH', 0.85
            elif confidence == 'MEDIUM':
                return 'CORRECTED_DECIMAL_ERROR_MEDIUM', 0.7
            else:  # LOW_SUSPECTED
                return 'SUSPECTED_DECIMAL_ERROR_LOW', 0.5
        
        # Tier 3: Check for logical inconsistencies
        if pd.notna(row['k']) and pd.notna(row['q']):
            
            # High speed + blocked state (physically impossible)
            if row['k'] > 60 and row['etat_trafic'] in ['Bloqué', 'Saturé']:
                return 'INCONSISTENT_SPEED_STATE', 0.5
            
            # Extremely high flow with unrealistically low speed
            if row['q'] > 2000 and row['k'] < 5:
                return 'INCONSISTENT_EXTREME_FLOW_SPEED', 0.3
            
            # Zero/near-zero speed with high flow (cars can't flow if stopped)
            if row['q'] > 100 and row['k'] < 2:
                return 'INCONSISTENT_STOPPED_WITH_FLOW', 0.4
        
        # Tier 4: Sensor quality issues
        if row['etat_barre'] == 'Invalide':
            if pd.notna(row['q']) or pd.notna(row['k']):
                return 'INVALID_SENSOR_HAS_DATA', 0.6
            else:
                return 'INVALID_SENSOR_NO_DATA', 0.1
        
        # Tier 5: Missing single metric
        if pd.isna(row['q']) and pd.notna(row['k']):
            return 'MISSING_FLOW', 0.8
        if pd.isna(row['k']) and pd.notna(row['q']):
            return 'MISSING_SPEED', 0.8
        
        # Tier 6: Good quality
        return 'OK', 1.0
    
    df_clean[['data_quality_flag', 'quality_score']] = df_clean.apply(
        assign_quality_flag, axis=1, result_type='expand'
    )
    
    # Log quality distribution
    quality_dist = df_clean['data_quality_flag'].value_counts()
    logger.info(f"Quality distribution:")
    for flag, count in quality_dist.items():
        logger.info(f"  {flag}: {count} ({count/len(df_clean)*100:.1f}%)")
    

    # STEP 7: Prepare road_segments dimension table

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
    

    # STEP 8: Prepare traffic_readings fact table

    readings_df = df_clean[['iu_ac', 't_1h', 'q', 'k', 'etat_trafic', 
                            'etat_barre', 'is_speed_corrected', 'correction_confidence',
                            'data_quality_flag', 'quality_score']].copy()

    readings_df.columns = ['segment_id', 'timestamp', 'traffic_flow', 'avg_speed',
                        'traffic_state', 'sensor_status', 'is_speed_corrected', 
                        'correction_confidence', 'data_quality_flag', 'quality_score']

    readings_df['timestamp'] = pd.to_datetime(readings_df['timestamp'])
    readings_df['is_flow_imputed'] = False

    readings_df = readings_df[[
        'segment_id', 'timestamp', 'traffic_flow', 'avg_speed',
        'traffic_state', 'sensor_status', 'is_flow_imputed', 'is_speed_corrected',
        'correction_confidence', 'data_quality_flag', 'quality_score'
    ]]
    
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