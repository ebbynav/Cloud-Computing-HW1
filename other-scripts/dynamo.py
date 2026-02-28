
import requests
import boto3
import json
import time
from decimal import Decimal

# ========================
# CONFIG
# ========================

API_KEY = "gBq6dq1rE0biLXLMQEc0P_HM24ZtR_1FHQF1OS7FK_ncYchoogQ2EdBo6oXYflPzc76XTEekodO9arHxcxf2alwXZOBNns1gOGR6ExCvrUB50tXvbcpHcVvaH0WeaXYx"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}"
}

DYNAMODB_TABLE = "yelp-restaurants"

cities = [
    "New York",
    "Manhattan",
    "Brooklyn",
    "Queens",
    "Chicago",
    "Los Angeles",
    "San Francisco",
    "Boston",
    "Seattle",
    "Austin",
    "Miami"
]

cuisines = [
    "Italian",
    "Chinese",
    "Indian",
    "Mexican",
    "Japanese",
]

# ========================
# AWS DynamoDB
# ========================

dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
table = dynamodb.Table(DYNAMODB_TABLE)


# ========================
# Helpers
# ========================

def to_decimal(value):
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


# ========================
# Yelp Fetch
# ========================

def fetch_restaurants(city, cuisine, offset=0, limit=50):

    url = "https://api.yelp.com/v3/businesses/search"

    params = {
        "term": cuisine,
        "location": city,
        "limit": limit,
        "offset": offset
    }

    response = requests.get(url, headers=HEADERS, params=params)

    if response.status_code != 200:
        print(f"Error (offset={offset}):", response.text)
        return []

    return response.json().get("businesses", [])


# ========================
# Store in DynamoDB
# ========================

def store_restaurant(business, cuisine):

    location = business.get("location", {})
    coordinates = business.get("coordinates", {})

    item = {
        # REQUIRED FIELDS
        "id": business.get("id"),  # Partition Key

        "name": business.get("name"),
        "address": " ".join(location.get("display_address", [])),
        "city": location.get("city"),
        "zip_code": location.get("zip_code"),

        "latitude": to_decimal(coordinates.get("latitude")),
        "longitude": to_decimal(coordinates.get("longitude")),

        "review_count": business.get("review_count", 0),

        "rating": to_decimal(business.get("rating")),

        "cuisine": cuisine
    }

    # Skip if ID missing
    if not item["id"]:
        return

    table.put_item(Item=item)


# ========================
# MAIN
# ========================

TARGET_PER_CUISINE = 1000
MAX_OFFSET = 240       # Yelp API max offset
LIMIT = 50             # Yelp API max per request

all_data = []
seen_ids = set()       # Global dedup across all queries
cuisine_counts = {c: 0 for c in cuisines}

for cuisine in cuisines:
    for city in cities:
        if cuisine_counts[cuisine] >= TARGET_PER_CUISINE:
            break

        offset = 0
        while offset <= MAX_OFFSET and cuisine_counts[cuisine] < TARGET_PER_CUISINE:

            print(f"Fetching {cuisine} in {city} (offset={offset}, total so far={cuisine_counts[cuisine]})")

            businesses = fetch_restaurants(city, cuisine, offset=offset, limit=LIMIT)

            if not businesses:
                break  # No more results for this city

            new_count = 0
            for b in businesses:
                bid = b.get("id")
                if bid and bid not in seen_ids:
                    seen_ids.add(bid)
                    all_data.append(b)
                    store_restaurant(b, cuisine)
                    cuisine_counts[cuisine] += 1
                    new_count += 1

            if new_count == 0 or len(businesses) < LIMIT:
                break  # No new unique results or last page

            offset += LIMIT
            time.sleep(0.5)  # Avoid Yelp rate limit

        time.sleep(0.5)

    print(f"✅ {cuisine}: {cuisine_counts[cuisine]} unique restaurants stored")

print(f"\n✅ Done. Total unique entries: {len(all_data)}")
print("Per cuisine:", {c: cuisine_counts[c] for c in cuisines})

# Backup locally
with open("restaurants.json", "w") as f:
    json.dump(all_data, f, indent=2)

print("Backup saved to restaurants.json")