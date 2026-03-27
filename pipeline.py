import requests
from datetime import datetime, timezone, timedelta
from prefect import flow, task
from sqlalchemy import text
from database import get_engine, create_tables
from config import CITIES

WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    61: "Light rain",
    63: "Moderate rain",
    80: "Rain showers",
    95: "Thunderstorm",
}

@task(retries=3, retry_delay_seconds=10)
def extract_weather(city: dict) -> dict:
    print(f"Fetching weather for {city['name']}...")

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": city["lat"],
        "longitude": city["lon"],
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
        "wind_speed_unit": "kmh",
    }

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()

    current = response.json()["current"]
    current["city"] = city["name"]
    return current

@task
def transform_weather(raw: dict) -> dict:
    temp = raw.get("temperature_2m")
    humidity = raw.get("relative_humidity_2m")
    wind = raw.get("wind_speed_10m")
    code = raw.get("weather_code", 0)

    if temp is None or not (-60 <= temp <= 60):
        raise ValueError(f"Invalid temperature: {temp}")

    if humidity is None or not (0 <= humidity <= 100):
        raise ValueError(f"Invalid humidity: {humidity}")

    return {
        "city": raw["city"],
        "timestamp": raw["time"],
        "temp_c": round(temp, 1),
        "humidity": int(humidity),
        "wind_kph": round(wind, 1) if wind is not None else None,
        "condition": WEATHER_CODES.get(code, f"Code {code}"),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }

@task
def load_to_db(records: list[dict]):
    print("Loading records into database...")

    engine = get_engine()
    create_tables(engine)

    inserted = 0
    skipped = 0

    with engine.connect() as conn:
        for record in records:
            try:
                conn.execute(text("""
                    INSERT INTO weather_readings
                    (city, timestamp, temp_c, humidity, wind_kph, condition, fetched_at)
                    VALUES
                    (:city, :timestamp, :temp_c, :humidity, :wind_kph, :condition, :fetched_at)
                """), record)
                inserted += 1
            except Exception:
                skipped += 1

        conn.commit()

    print(f"Inserted: {inserted}, Skipped duplicates: {skipped}")

@flow(name="weather-etl-pipeline", log_prints=True)
def weather_pipeline():
    raw_data = [extract_weather(city) for city in CITIES]
    transformed_data = [transform_weather(item) for item in raw_data]
    load_to_db(transformed_data)

if __name__ == "__main__":
    weather_pipeline.serve(
        name="hourly-weather",
        interval=timedelta(hours=1)
    )