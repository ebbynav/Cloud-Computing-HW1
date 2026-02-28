import boto3
import requests
from requests.auth import HTTPBasicAuth

# --- CONFIG ---
OPENSEARCH_ENDPOINT = "https://search-restaurants-2vq6eg5ul5na5el2khpyuihjri.aos.us-east-1.on.aws"
MASTER_USER = "CloudComputing"
MASTER_PASS = "CloudComputing@123"
INDEX = "restaurants"
DYNAMODB_TABLE = "yelp-restaurants"
REGION = "us-east-1"

auth = HTTPBasicAuth(MASTER_USER, MASTER_PASS)
headers = {"Content-Type": "application/json"}

# Create index first
create_index_url = f"{OPENSEARCH_ENDPOINT}/{INDEX}"
r = requests.put(create_index_url, auth=auth, headers=headers)
print("Create index:", r.status_code, r.text)

# Scan DynamoDB
dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(DYNAMODB_TABLE)

response = table.scan()
items = response["Items"]
while "LastEvaluatedKey" in response:
    response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
    items.extend(response["Items"])

print(f"Total items to index: {len(items)}")

# Push to OpenSearch
success = 0
for item in items:
    doc = {
        "RestaurantID": item["id"],
        "Cuisine": item["cuisine"],
        "City": item["city"]
    }
    url = f"{OPENSEARCH_ENDPOINT}/{INDEX}/_doc/{item['id']}"
    r = requests.put(url, json=doc, auth=auth, headers=headers)
    if r.status_code in [200, 201]:
        success += 1
    else:
        print(f"Failed: {item['id']} - {r.text}")

print(f"Done. {success}/{len(items)} indexed successfully.")