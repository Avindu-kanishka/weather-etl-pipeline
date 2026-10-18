
import logging
import time
from pathlib import Path
from datetime import datetime, timezone

from config import CITIES
from pipeline import extract_weather, transform_weather, load_to_db


# --------------------------------------------------
# LOGGING CONFIGURATION
# --------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "weather_etl.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
    force=True,
)

logger = logging.getLogger("weather_etl")


def main():
    started_at = datetime.now(timezone.utc)
    start_time = time.perf_counter()

    records = []
    failed = []

    logger.info("=" * 60)
    logger.info("ETL RUN STARTED")
    logger.info("Start time (UTC): %s", started_at.isoformat())
    logger.info("Districts configured: %s", len(CITIES))

    for location in CITIES:
        district = location["district"]

        try:
            raw = extract_weather.fn(location)
            record = transform_weather.fn(raw)

            records.append(record)

            logger.info(
                "SUCCESS | district=%s | temperature=%s C",
                district,
                record.get("temp_c"),
            )

        except Exception:
            failed.append(district)
            logger.exception("FAILED | district=%s", district)

    processed = 0
    database_failed = False

    if records:
        try:
            processed = load_to_db.fn(records)
            logger.info(
                "DATABASE LOAD COMPLETED | records_submitted=%s",
                len(records),
            )
        except Exception:
            database_failed = True
            logger.exception("DATABASE LOAD FAILED")

    finished_at = datetime.now(timezone.utc)
    duration = time.perf_counter() - start_time

    logger.info("ETL RUN FINISHED")
    logger.info("Finish time (UTC): %s", finished_at.isoformat())
    logger.info("Duration: %.2f seconds", duration)
    logger.info("Successful districts: %s/%s", len(records), len(CITIES))
    logger.info("Failed districts: %s", failed)
    logger.info("Database load failed: %s", database_failed)
    logger.info("Records submitted to database: %s", len(records))
    logger.info("Database task return value: %s", processed)

    if failed or database_failed:
        logger.warning("ETL RUN COMPLETED WITH ERRORS")
    else:
        logger.info("ETL RUN COMPLETED WITHOUT ERRORS")

    logger.info("Log file: %s", LOG_FILE)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
