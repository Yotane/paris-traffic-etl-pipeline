CREATE TABLE road_segments (
    segment_id VARCHAR(50) PRIMARY KEY,
    street_name VARCHAR(255) NOT NULL,
    latitude DECIMAL(10, 7),
    longitude DECIMAL(10, 7),
    upstream_node_id VARCHAR(50),
    upstream_node_name VARCHAR(255),
    downstream_node_id VARCHAR(50),
    downstream_node_name VARCHAR(255),
    sensor_install_date DATE,
    sensor_end_date DATE,
    geometry_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_street_name (street_name),
    INDEX idx_location (latitude, longitude)
);

CREATE TABLE traffic_readings (
    reading_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    segment_id VARCHAR(50) NOT NULL,
    timestamp DATETIME NOT NULL,
    traffic_flow INT,
    avg_speed DECIMAL(6, 2),
    traffic_state ENUM('Fluide', 'Pré-saturé', 'Saturé', 'Bloqué', 'Inconnu') NOT NULL,
    sensor_status ENUM('Ouvert', 'Barré', 'Invalide') NOT NULL,
    is_flow_imputed BOOLEAN DEFAULT FALSE,
    is_speed_corrected BOOLEAN DEFAULT FALSE,
    data_quality_flag VARCHAR(50),
    quality_score DECIMAL(3, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (segment_id) REFERENCES road_segments(segment_id) ON DELETE CASCADE,
    UNIQUE KEY unique_reading (segment_id, timestamp),
    INDEX idx_timestamp (timestamp),
    INDEX idx_traffic_state (traffic_state),
    INDEX idx_segment_time (segment_id, timestamp),
    INDEX idx_quality (data_quality_flag),
    INDEX idx_quality_score (quality_score)
);

CREATE TABLE data_quality_log (
    log_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    segment_id VARCHAR(50),
    timestamp DATETIME,
    issue_type VARCHAR(50),
    original_value VARCHAR(255),
    corrected_value VARCHAR(255),
    action_taken VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_segment (segment_id),
    INDEX idx_issue_type (issue_type)
);

CREATE TABLE hourly_stats (
    stat_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    segment_id VARCHAR(50),
    hour INT,
    date DATE,
    avg_flow DECIMAL(8, 2),
    avg_speed DECIMAL(6, 2),
    total_readings INT,
    missing_readings INT,
    data_quality_score DECIMAL(3, 2),
    
    FOREIGN KEY (segment_id) REFERENCES road_segments(segment_id) ON DELETE CASCADE,
    UNIQUE KEY unique_hour_stat (segment_id, date, hour),
    INDEX idx_date (date),
    INDEX idx_hour (hour)
);