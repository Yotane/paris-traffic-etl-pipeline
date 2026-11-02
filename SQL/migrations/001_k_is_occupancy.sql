-- k is occupancy (taux d'occupation, %), not average speed.
-- Renames the speed columns and drops the retracted decimal-correction columns.
-- After running this, re-run pipeline.py for every loaded date: ON DUPLICATE KEY UPDATE
-- overwrites the x100 "corrected" values and the old speed-based quality flags.
USE paris_traffic;

ALTER TABLE traffic_readings
    CHANGE COLUMN avg_speed occupancy_rate DECIMAL(5, 2),
    DROP COLUMN is_speed_corrected,
    DROP COLUMN correction_confidence;

ALTER TABLE hourly_stats
    CHANGE COLUMN avg_speed avg_occupancy DECIMAL(5, 2);
