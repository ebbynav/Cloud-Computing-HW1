import requests
import time
import json
import os
import random
from datetime import datetime, timezone
from collections import defaultdict

API_KEY = os.getenv("YELP_API_KEY")

if not API_KEY:
    raise ValueError("YELP_API_KEY not found. Set environment variable.")

HEADERS = {
    "Authorization": f"Bearer {API_KEY}"
}

CUISINES = ["chinese", "mexican", "japanese", "indian", "italian"]

ZIP_CODES = [
    "10001","10002","10003","10004","10005",
    "10006","10007","10009","10010","10011",
    "10012","10013","10014","10016","10017",
    "10018","10019","10020","10021","10022",
    "10023","10024","10025","10026","10027",
    "10028","10029","10030","10031","10032",
    "10033","10034","10035","10036","10037",
    "10038","10039","10040"
]

LIMIT = 50
MAX_OFFSET = 200
TARGET_TOTAL = 5000
PER_CYCLE_TARGET = 200   # 200 per cuisine per loop

# Load existing data
if os.path.exists("restaurants.json"):
    with open("restaurants.json") as f:
        existing_data = json.load(f)
else:
    existing_data = []

all_restaurants = {r["BusinessID"]: r for r in existing_data}

print(f"Currently stored: {len(all_restaurants)}")

def cuisine_counts():
    counts = defaultdict(int)
    for r in all_restaurants.values():
        counts[r["Cuisine"]] += 1
    return counts

def collect_for_cuisine(cuisine):
    counts = cuisine_counts()
    starting_count = counts[cuisine]
    target = starting_count + PER_CYCLE_TARGET

    print(f"\nCollecting {PER_CYCLE_TARGET} for {cuisine}...")

    random.shuffle(ZIP_CODES)

    for zip_code in ZIP_CODES:
        if cuisine_counts()[cuisine] >= target:
            return

        for offset in range(0, MAX_OFFSET, 50):

            url = "https://api.yelp.com/v3/businesses/search"

            params = {
                "term": f"{cuisine} restaurants",
                "location": zip_code,
                "limit": LIMIT,
                "offset": offset
            }

            response = requests.get(url, headers=HEADERS, params=params)

            if response.status_code != 200:
                break

            businesses = response.json().get("businesses", [])
            if not businesses:
                break

            for b in businesses:
                business_id = b["id"]

                if business_id not in all_restaurants:
                    all_restaurants[business_id] = {
                        "BusinessID": business_id,
                        "Name": b["name"],
                        "Address": " ".join(b["location"]["display_address"]),
                        "Coordinates": b["coordinates"],
                        "NumberOfReviews": b["review_count"],
                        "Rating": b["rating"],
                        "ZipCode": b["location"].get("zip_code", ""),
                        "Cuisine": cuisine,
                        "insertedAtTimestamp": datetime.now(timezone.utc).isoformat()
                    }

                    if cuisine_counts()[cuisine] >= target:
                        return

            time.sleep(0.3)

# Round-robin loop
while len(all_restaurants) < TARGET_TOTAL:

    for cuisine in CUISINES:

        if len(all_restaurants) >= TARGET_TOTAL:
            break

        collect_for_cuisine(cuisine)

    print("\nCurrent totals:")
    for c, count in cuisine_counts().items():
        print(f"{c}: {count}")

print(f"\nReached target of {TARGET_TOTAL} restaurants!")

with open("restaurants.json", "w") as f:
    json.dump(list(all_restaurants.values()), f, indent=2)

print("Saved to restaurants.json")
