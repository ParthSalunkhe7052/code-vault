"""
Populate Mock Map Data for CodeVault Mission Control

This script inserts fake validation logs with realistic worldwide coordinates
so developers can verify the Mission Control map is working without needing
real license validations.

Usage:
    python populate_mock_map.py

This will insert 20 sample validation logs spread across major cities.
"""

import asyncio
import secrets
import random
from datetime import timedelta

# Sample cities with coordinates
SAMPLE_LOCATIONS = [
    {"city": "New York", "country": "US", "lat": 40.7128, "lng": -74.0060},
    {"city": "Los Angeles", "country": "US", "lat": 34.0522, "lng": -118.2437},
    {"city": "London", "country": "GB", "lat": 51.5074, "lng": -0.1278},
    {"city": "Paris", "country": "FR", "lat": 48.8566, "lng": 2.3522},
    {"city": "Tokyo", "country": "JP", "lat": 35.6762, "lng": 139.6503},
    {"city": "Sydney", "country": "AU", "lat": -33.8688, "lng": 151.2093},
    {"city": "Berlin", "country": "DE", "lat": 52.5200, "lng": 13.4050},
    {"city": "Toronto", "country": "CA", "lat": 43.6532, "lng": -79.3832},
    {"city": "Singapore", "country": "SG", "lat": 1.3521, "lng": 103.8198},
    {"city": "Mumbai", "country": "IN", "lat": 19.0760, "lng": 72.8777},
    {"city": "Dubai", "country": "AE", "lat": 25.2048, "lng": 55.2708},
    {"city": "São Paulo", "country": "BR", "lat": -23.5505, "lng": -46.6333},
    {"city": "Seoul", "country": "KR", "lat": 37.5665, "lng": 126.9780},
    {"city": "Amsterdam", "country": "NL", "lat": 52.3676, "lng": 4.9041},
    {"city": "Stockholm", "country": "SE", "lat": 59.3293, "lng": 18.0686},
]


async def populate_mock_data():
    """Insert mock validation logs for map testing."""
    from database import get_db, release_db
    from utils import utc_now

    conn = await get_db()
    try:
        # Get a license to attach validations to
        license_row = await conn.fetchrow(
            "SELECT id, license_key FROM licenses LIMIT 1"
        )

        if not license_row:
            print("❌ No licenses found. Create a license first via the web dashboard.")
            return

        license_id = license_row["id"]
        license_key = license_row["license_key"]

        print(f"📍 Using license: {license_key[:16]}...")
        print(f"🌍 Inserting {len(SAMPLE_LOCATIONS)} mock validation logs...")

        now = utc_now()
        inserted = 0

        for location in SAMPLE_LOCATIONS:
            # Random timestamp within last 24 hours
            random_hours = random.randint(0, 23)
            random_minutes = random.randint(0, 59)
            created_at = now - timedelta(hours=random_hours, minutes=random_minutes)

            # Random HWID for each location
            hwid = secrets.token_hex(16)

            await conn.execute(
                """
                INSERT INTO validation_logs 
                (license_id, license_key, hwid, ip_address, result, response_time_ms,
                 city, country, latitude, longitude, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """,
                license_id,
                license_key,
                hwid,
                f"203.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}",
                "valid",
                random.randint(50, 200),
                location["city"],
                location["country"],
                location["lat"],
                location["lng"],
                created_at,
            )
            inserted += 1
            print(f"   ✓ {location['city']}, {location['country']}")

        print()
        print(f"✅ Successfully inserted {inserted} mock validation logs!")
        print("🗺️  Refresh your dashboard to see the Mission Control map in action.")

    finally:
        await release_db(conn)


if __name__ == "__main__":
    print()
    print("═" * 60)
    print("  CodeVault - Mock Map Data Generator")
    print("═" * 60)
    print()

    asyncio.run(populate_mock_data())
