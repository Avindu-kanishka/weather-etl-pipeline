from sqlalchemy import create_engine, text
from config import DB_PATH

def get_engine():
    return create_engine(f"sqlite:///{DB_PATH}")

def create_tables(engine):
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS weather_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                temp_c REAL,
                humidity INTEGER,
                wind_kph REAL,
                condition TEXT,
                fetched_at TEXT NOT NULL,
                UNIQUE(city, timestamp)
            )
        """))
        conn.commit()