
from sqlalchemy import URL, create_engine, text

from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD


def get_engine():
    database_url = URL.create(
        drivername="postgresql+psycopg",
        username=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
    )

    return create_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_recycle=1800,
    )


def create_tables(engine):
    with engine.begin() as conn:
        conn.execute(
            text("""
                CREATE TABLE IF NOT EXISTS weather_readings (
                    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                    district VARCHAR(100) NOT NULL,
                    city VARCHAR(100) NOT NULL,
                    timestamp TIMESTAMPTZ NOT NULL,
                    temp_c DOUBLE PRECISION NOT NULL,
                    humidity SMALLINT NOT NULL,
                    wind_kph DOUBLE PRECISION,
                    weather_condition VARCHAR(100),
                    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    CONSTRAINT uq_weather_city_timestamp
                        UNIQUE (city, timestamp),
                    CONSTRAINT ck_weather_humidity
                        CHECK (humidity BETWEEN 0 AND 100),
                    CONSTRAINT ck_weather_temperature
                        CHECK (temp_c BETWEEN -60 AND 60),
                    CONSTRAINT ck_weather_wind
                        CHECK (wind_kph IS NULL OR wind_kph >= 0)
                )
            """)
        )

        # Supports an existing table created by the earlier version.
        conn.execute(text("""
            ALTER TABLE weather_readings
            ADD COLUMN IF NOT EXISTS district VARCHAR(100)
        """))
