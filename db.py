"""
db.py — MySQL/phpMyAdmin database integration
==============================================
Tables maintained:
    classifications — one row per stable detection event
    sensor_readings — periodic sensor samples (~every 3 s)
    captured_photos — image bytes (LONGBLOB) linked to classifications

Writes are queued and persisted by a background worker so camera/sensor loops
are never blocked by database I/O.

Environment variables (.env)
----------------------------
DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
SNAPSHOT_DIR (optional; defaults to ./snapshots)
"""

import os
import queue
import threading
import traceback
from pathlib import Path

from dotenv import load_dotenv

try:
    import mysql.connector
except Exception:
    mysql = None
else:
    mysql = mysql.connector

# ─── Load credentials from .env ──────────────────────────────────────────────
load_dotenv()

DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
DB_PORT = int(os.getenv('DB_PORT', '3306'))
DB_USER = os.getenv('DB_USER', '')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_NAME = os.getenv('DB_NAME', '')
SNAPSHOT_DIR = Path(os.getenv('SNAPSHOT_DIR', Path(__file__).resolve().parent / 'snapshots'))

# ─── Client initialisation ───────────────────────────────────────────────────
_conn = None
_db_ready = False


def _connect_mysql():
    return mysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        autocommit=False,
    )


def _column_exists(table: str, column: str) -> bool:
    cursor = _conn.cursor()
    try:
        cursor.execute(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s AND column_name = %s
            LIMIT 1
            """,
            (DB_NAME, table, column),
        )
        return cursor.fetchone() is not None
    finally:
        cursor.close()


def _ensure_column(table: str, column: str, definition: str):
    if _column_exists(table, column):
        return
    cursor = _conn.cursor()
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        _conn.commit()
    finally:
        cursor.close()


def _migrate_existing_schema():
    """Patch older table layouts so current inserts won't fail."""
    classification_columns = {
        'created_at': "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
        'label': "ENUM('not_pollinated','pollinated','pollinating') NOT NULL DEFAULT 'not_pollinated'",
        'confidence': "DECIMAL(6,4) NOT NULL DEFAULT 0",
        'prob_not_pollinated': "DECIMAL(6,4) NULL",
        'prob_pollinated': "DECIMAL(6,4) NULL",
        'prob_pollinating': "DECIMAL(6,4) NULL",
        'snapshot_filename': "VARCHAR(255) NULL",
        'temperature': "DECIMAL(5,2) NULL",
        'humidity': "DECIMAL(5,2) NULL",
        'light': "DECIMAL(10,2) NULL",
    }
    sensor_columns = {
        'created_at': "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
        'temperature': "DECIMAL(5,2) NULL",
        'humidity': "DECIMAL(5,2) NULL",
        'light': "DECIMAL(10,2) NULL",
        'error': "VARCHAR(255) NULL",
    }

    for column_name, definition in classification_columns.items():
        _ensure_column('classifications', column_name, definition)

    for column_name, definition in sensor_columns.items():
        _ensure_column('sensor_readings', column_name, definition)


def _create_tables_if_missing():
    ddl = [
        """
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
        """,
        """
        CREATE TABLE IF NOT EXISTS sensor_readings (
            id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            temperature DECIMAL(5,2) NULL,
            humidity DECIMAL(5,2) NULL,
            light DECIMAL(10,2) NULL,
            error VARCHAR(255) NULL,
            INDEX idx_sensor_created_at (created_at)
        ) ENGINE=InnoDB;
        """,
        """
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
        """,
    ]
    cursor = _conn.cursor()
    try:
        for statement in ddl:
            cursor.execute(statement)
        _conn.commit()
    finally:
        cursor.close()
    _migrate_existing_schema()


def _ensure_connection() -> bool:
    global _conn
    if _conn is None:
        _conn = _connect_mysql()
        return True
    if not _conn.is_connected():
        _conn.reconnect(attempts=2, delay=0)
    return True

def init_db() -> bool:
    """Initialise MySQL connection. Returns True if successful."""
    global _conn, _db_ready
    if mysql is None:
        print('  [db] ✗  mysql-connector-python not installed — DB disabled.')
        return False

    if not DB_USER or not DB_NAME or 'your-user' in DB_USER or 'your-db' in DB_NAME:
        print('  [db] ⚠  MySQL credentials not set in .env — DB disabled.')
        return False
    try:
        _conn = _connect_mysql()
        _create_tables_if_missing()
        _db_ready = True
        print(f'  [db] ✓  Connected to MySQL: {DB_HOST}:{DB_PORT}/{DB_NAME}')
        return True
    except Exception as e:
        print(f'  [db] ✗  MySQL init failed: {e}')
        return False

# ─── Background write queue ──────────────────────────────────────────────────
_write_queue: queue.Queue = queue.Queue(maxsize=500)


def _worker():
    """Background thread: drain queue and write rows to MySQL."""
    while True:
        action, payload = _write_queue.get()
        if not _db_ready:
            _write_queue.task_done()
            continue
        try:
            _ensure_connection()
            if action == 'classification':
                _insert_classification(payload)
            elif action == 'sensor':
                _insert_sensor(payload)
        except Exception:
            traceback.print_exc()
        finally:
            _write_queue.task_done()


_worker_thread = threading.Thread(target=_worker, daemon=True, name='db-worker')
_worker_thread.start()


def _enqueue(table: str, row: dict):
    """Add a row to the write queue (non-blocking, drops if queue is full)."""
    if not _db_ready:
        return
    try:
        _write_queue.put_nowait((table, row))
    except queue.Full:
        print('  [db] ⚠  Write queue full — row dropped.')


def _snapshot_to_blob(filename: str):
    if not filename:
        return None, None

    file_path = SNAPSHOT_DIR / filename
    if not file_path.exists() or not file_path.is_file():
        return None, None

    with file_path.open('rb') as image_file:
        data = image_file.read()
    return data, len(data)


def _mime_type_from_filename(filename: str) -> str:
    lower_name = (filename or '').lower()
    if lower_name.endswith('.png'):
        return 'image/png'
    if lower_name.endswith('.webp'):
        return 'image/webp'
    return 'image/jpeg'


def _insert_classification(row: dict):
    cursor = _conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO classifications (
                label, confidence,
                prob_not_pollinated, prob_pollinated, prob_pollinating,
                snapshot_filename, temperature, humidity, light
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                row['label'],
                row['confidence'],
                row['prob_not_pollinated'],
                row['prob_pollinated'],
                row['prob_pollinating'],
                row['snapshot_filename'],
                row['temperature'],
                row['humidity'],
                row['light'],
            ),
        )
        classification_id = cursor.lastrowid

        photo_data, file_size = _snapshot_to_blob(row.get('snapshot_filename'))
        if photo_data is not None:
            cursor.execute(
                """
                INSERT INTO captured_photos (
                    classification_id, filename, mime_type, file_size, photo_data
                ) VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    classification_id,
                    row.get('snapshot_filename'),
                    _mime_type_from_filename(row.get('snapshot_filename', '')),
                    file_size,
                    photo_data,
                ),
            )

        _conn.commit()
    except Exception:
        _conn.rollback()
        raise
    finally:
        cursor.close()


def _insert_sensor(row: dict):
    cursor = _conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO sensor_readings (temperature, humidity, light, error)
            VALUES (%s, %s, %s, %s)
            """,
            (row['temperature'], row['humidity'], row['light'], row['error']),
        )
        _conn.commit()
    except Exception:
        _conn.rollback()
        raise
    finally:
        cursor.close()


# ─── Public helpers ──────────────────────────────────────────────────────────

def log_classification(label: str, confidence: float, probs: dict,
                       snapshot_filename: str, sensor: dict):
    """
    Insert one row into `classifications`.
    Call this every time a stable detection fires (in camera_loop).
    """
    row = {
        'label':               label,
        'confidence':          round(confidence, 4),
        'prob_not_pollinated': round(probs.get('not_pollinated', 0.0), 4),
        'prob_pollinated':     round(probs.get('pollinated',     0.0), 4),
        'prob_pollinating':    round(probs.get('pollinating',    0.0), 4),
        'snapshot_filename':   snapshot_filename,
        'temperature':         sensor.get('temperature'),
        'humidity':            sensor.get('humidity'),
        'light':               sensor.get('light'),
    }
    _enqueue('classification', row)


def log_sensor(temperature, humidity, light, error=None):
    """
    Insert one row into `sensor_readings`.
    Call this from sensor_loop on every successful read.
    """
    row = {
        'temperature': temperature,
        'humidity':    humidity,
        'light':       light,
        'error':       error,
    }
    _enqueue('sensor', row)


def get_health() -> dict:
    """Return database health information for API monitoring."""
    configured = bool(DB_USER and DB_NAME)
    status = {
        'ok': False,
        'ready': bool(_db_ready),
        'configured': configured,
        'driver_available': mysql is not None,
        'host': DB_HOST,
        'port': DB_PORT,
        'database': DB_NAME,
        'user': DB_USER,
        'queue_size': _write_queue.qsize(),
        'error': '',
    }

    if mysql is None:
        status['error'] = 'mysql-connector-python not installed'
        return status

    if not configured:
        status['error'] = 'DB_USER/DB_NAME missing in .env'
        return status

    if not _db_ready:
        status['error'] = 'Database not initialised'
        return status

    try:
        _ensure_connection()
        cursor = _conn.cursor()
        try:
            cursor.execute('SELECT 1')
            cursor.fetchone()
        finally:
            cursor.close()
        status['ok'] = True
        status['error'] = ''
    except Exception as e:
        status['ok'] = False
        status['error'] = str(e)

    return status
