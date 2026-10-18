
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

# Representative weather observation locations for all 25 districts.
CITIES = [
    {"name": "Colombo", "district": "Colombo", "lat": 6.9271, "lon": 79.8612},
    {"name": "Gampaha", "district": "Gampaha", "lat": 7.0840, "lon": 80.0098},
    {"name": "Kalutara", "district": "Kalutara", "lat": 6.5854, "lon": 79.9607},
    {"name": "Kandy", "district": "Kandy", "lat": 7.2906, "lon": 80.6337},
    {"name": "Matale", "district": "Matale", "lat": 7.4675, "lon": 80.6234},
    {"name": "Nuwara Eliya", "district": "Nuwara Eliya", "lat": 6.9497, "lon": 80.7891},
    {"name": "Galle", "district": "Galle", "lat": 6.0535, "lon": 80.2210},
    {"name": "Matara", "district": "Matara", "lat": 5.9549, "lon": 80.5540},
    {"name": "Hambantota", "district": "Hambantota", "lat": 6.1429, "lon": 81.1212},
    {"name": "Jaffna", "district": "Jaffna", "lat": 9.6615, "lon": 80.0255},
    {"name": "Kilinochchi", "district": "Kilinochchi", "lat": 9.3803, "lon": 80.3770},
    {"name": "Mannar", "district": "Mannar", "lat": 8.9810, "lon": 79.9044},
    {"name": "Vavuniya", "district": "Vavuniya", "lat": 8.7514, "lon": 80.4971},
    {"name": "Mullaitivu", "district": "Mullaitivu", "lat": 9.2671, "lon": 80.8142},
    {"name": "Batticaloa", "district": "Batticaloa", "lat": 7.7102, "lon": 81.6924},
    {"name": "Ampara", "district": "Ampara", "lat": 7.2912, "lon": 81.6724},
    {"name": "Trincomalee", "district": "Trincomalee", "lat": 8.5874, "lon": 81.2152},
    {"name": "Kurunegala", "district": "Kurunegala", "lat": 7.4863, "lon": 80.3623},
    {"name": "Puttalam", "district": "Puttalam", "lat": 8.0362, "lon": 79.8283},
    {"name": "Anuradhapura", "district": "Anuradhapura", "lat": 8.3114, "lon": 80.4037},
    {"name": "Polonnaruwa", "district": "Polonnaruwa", "lat": 7.9403, "lon": 81.0188},
    {"name": "Badulla", "district": "Badulla", "lat": 6.9895, "lon": 81.0550},
    {"name": "Monaragala", "district": "Monaragala", "lat": 6.8728, "lon": 81.3507},
    {"name": "Ratnapura", "district": "Ratnapura", "lat": 6.6828, "lon": 80.3992},
    {"name": "Kegalle", "district": "Kegalle", "lat": 7.2513, "lon": 80.3464},
]

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "weather_db")
DB_USER = os.getenv("DB_USER", "weather_app")
DB_PASSWORD = os.getenv("DB_PASSWORD")

if not DB_PASSWORD:
    raise RuntimeError(
        "DB_PASSWORD is missing. Check the DB_PASSWORD entry in your .env file."
    )
