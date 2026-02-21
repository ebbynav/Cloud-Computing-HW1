import boto3
import json
from decimal import Decimal
from datetime import datetime, timezone

def convert_numbers(obj):
    if isinstance(obj, list):
        return [convert_numbers(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: convert_numbers(v) for k, v in obj.items()}
    elif isinstance(obj, float):
        return Decimal(str(obj))
    return obj

dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
table = dynamodb.Table("yelp-restaurants")

with open("restaurants.json") as f:
    data = json.load(f)

total = len(data)
print(f"Uploading {total} restaurants...")

count = 0

with table.batch_writer(overwrite_by_pkeys=["BusinessID"]) as batch:
    for item in data:
        item["insertedAtTimestamp"] = datetime.now(timezone.utc).isoformat()
        item = convert_numbers(item)
        batch.put_item(Item=item)

        count += 1
        if count % 200 == 0:
            print(f"{count}/{total} uploaded...")

print("Upload finished.")