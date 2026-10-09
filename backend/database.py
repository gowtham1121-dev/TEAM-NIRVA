
import sqlite3
from pathlib import Path

# Project directories
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "results"
DB_PATH = RESULTS_DIR / "inspections.db"


def initialize_database():
    """Create the results directory and inspection table."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS inspections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                anomaly_score REAL NOT NULL,
                decision TEXT NOT NULL,
                heatmap_path TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        connection.commit()


def save_inspection(filename, score, decision, heatmap_path=None):
    """Save one inspection result and return its database ID."""
    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.execute(
            """
            INSERT INTO inspections
                (filename, anomaly_score, decision, heatmap_path)
            VALUES (?, ?, ?, ?)
            """,
            (filename, float(score), decision, heatmap_path)
        )

        connection.commit()
        return cursor.lastrowid


def get_inspections(limit=100):
    """Return the most recent inspection records."""
    limit = max(1, min(int(limit), 1000))

    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row

        rows = connection.execute(
            """
            SELECT id, filename, anomaly_score, decision,
                   heatmap_path, created_at
            FROM inspections
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()

        return [dict(row) for row in rows]
