-- =============================================================================
-- Pollination Monitoring System — phpMyAdmin/MySQL Schema
-- =============================================================================

CREATE DATABASE IF NOT EXISTS capstone_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE capstone_db;

CREATE TABLE IF NOT EXISTS classifications (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    label ENUM('not_pollinated','pollinated','pollinating') NOT NULL,
    confidence DECIMAL(6,4) NOT NULL,
    prob_not_pollinated DECIMAL(6,4) NULL,
    prob_pollinated DECIMAL(6,4) NULL,
    prob_pollinating DECIMAL(6,4) NULL,
    snapshot_filename VARCHAR(255) NULL,
    temperature DECIMAL(5,2) NULL,
    humidity DECIMAL(5,2) NULL,
    light DECIMAL(10,2) NULL,
    INDEX idx_classifications_created_at (created_at),
    INDEX idx_classifications_label (label)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS sensor_readings (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    temperature DECIMAL(5,2) NULL,
    humidity DECIMAL(5,2) NULL,
    light DECIMAL(10,2) NULL,
    INDEX idx_sensor_created_at (created_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS captured_photos (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    classification_id BIGINT UNSIGNED NOT NULL,
    filename VARCHAR(255) NULL,
    mime_type VARCHAR(50) NOT NULL DEFAULT 'image/jpeg',
    file_size INT UNSIGNED NULL,
    photo_data LONGBLOB NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_photo_classification
        FOREIGN KEY (classification_id)
        REFERENCES classifications(id)
        ON DELETE CASCADE,

    INDEX idx_photo_classification_id (classification_id),
    INDEX idx_photo_created_at (created_at)
) ENGINE=InnoDB;
