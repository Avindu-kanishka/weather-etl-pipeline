
import logging
from datetime import datetime, timedelta, timezone

import requests
from prefect import flow, task
from sqlalchemy import MetaData, Table
from sqlalchemy.dialects.postgresql import insert

from config import CITIES
from database import create_tables, get_engine

logger = logging.getLogger(__name__)

WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


@task(retries=3, retry_delay_seconds=10, log_prints=True)
def extract_weather(location: dict) -> dict:
    """Fetch the current weather for one Sri Lankan district representative location."""
    logger.info("Fetching weather for %s", location["district"])

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": location["lat"],
        "longitude": location["lon"],
        "current": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "wind_speed_10m,"
            "weather_code"
        ),
        "wind_speed_unit": "kmh",
        "timezone": "Asia/Colombo",
    }

    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()

    payload = response.json()
    current = payload.get("current")

    if not current:
        raise ValueError(
            f"Open-Meteo returned no current weather for {location['district']}"
        )

    return {
        "district": location["district"],
        "city": location["name"],
        "temperature_2m": current.get("temperature_2m"),
        "relative_humidity_2m": current.get("relative_humidity_2m"),
        "wind_speed_10m": current.get("wind_speed_10m"),
        "weather_code": current.get("weather_code"),
        "time": current.get("time"),
    }


@task(log_prints=True)
def transform_weather(raw: dict) -> dict:
    """Validate and normalize the API response before loading."""
    temperature = raw.get("temperature_2m")
    humidity = raw.get("relative_humidity_2m")
    wind_speed = raw.get("wind_speed_10m")
    weather_code = raw.get("weather_code")
    observed_time = raw.get("time")

    if temperature is None or not -60 <= temperature <= 60:
        raise ValueError(f"Invalid temperature: {temperature}")

    if humidity is None or not 0 <= humidity <= 100:
        raise ValueError(f"Invalid humidity: {humidity}")

    if wind_speed is not None and wind_speed < 0:
        raise ValueError(f"Invalid wind speed: {wind_speed}")

    if observed_time is None:
        raise ValueError("Missing observation timestamp")

    # Open-Meteo returns local time because Asia/Colombo was requested.
    # Sri Lanka's timezone is UTC+05:30.
    local_timestamp = datetime.fromisoformat(observed_time)

    if local_timestamp.tzinfo is None:
        local_timestamp = local_timestamp.replace(
            tzinfo=timezone(timedelta(hours=5, minutes=30))
        )

    return {
        "district": raw["district"],
        "city": raw["city"],
        "timestamp": local_timestamp,
        "temp_c": round(float(temperature), 1),
        "humidity": int(humidity),
        "wind_kph": (
            round(float(wind_speed), 1)
            if wind_speed is not None
            else None
        ),
        "weather_condition": WEATHER_CODES.get(
            weather_code,
            f"Unknown code {weather_code}",
        ),
        "fetched_at": datetime.now(timezone.utc),
    }


@task(retries=2, retry_delay_seconds=5, log_prints=True)
def load_to_db(records: list[dict]) -> int:
    """Insert weather records or update existing city/timestamp records."""
    if not records:
        logger.warning("No valid records to load")
        return 0

    engine = get_engine()

    try:
        create_tables(engine)

        with engine.begin() as connection:
            metadata = MetaData()
            weather_table = Table(
                "weather_readings",
                metadata,
                autoload_with=connection,
            )

            statement = insert(weather_table).values(records)

            statement = statement.on_conflict_do_update(
                constraint="uq_weather_city_timestamp",
                set_={
                    "district": statement.excluded.district,
                    "temp_c": statement.excluded.temp_c,
                    "humidity": statement.excluded.humidity,
                    "wind_kph": statement.excluded.wind_kph,
                    "weather_condition": statement.excluded.weather_condition,
                    "fetched_at": statement.excluded.fetched_at,
                },
            )

            result = connection.execute(statement)
            processed_count = result.rowcount or 0

        logger.info("Weather records processed: %s", processed_count)
        return processed_count

    finally:
        engine.dispose()


@flow(name="sri-lanka-weather-etl", log_prints=True)
def weather_pipeline():
    """Run extraction, transformation, and loading for all configured districts."""
    logger.info("Starting Sri Lanka weather ETL for %s locations", len(CITIES))

    transformed_records = []
    failed_districts = []

    for location in CITIES:
        try:
            raw = extract_weather(location)
            transformed = transform_weather(raw)
            transformed_records.append(transformed)
        except Exception:
            failed_districts.append(location["district"])
            logger.exception(
                "Weather processing failed for district: %s",
                location["district"],
            )

    if transformed_records:
        load_to_db(transformed_records)

    logger.info(
        "ETL completed: successful=%s, failed=%s",
        len(transformed_records),
        len(failed_districts),
    )

    if failed_districts:
        logger.warning("Failed districts: %s", ", ".join(failed_districts))


if __name__ == "__main__":
    # Start the hourly Prefect deployment.
    weather_pipeline.serve(
        name="sri-lanka-hourly-weather",
        interval=timedelta(hours=1),
    )
