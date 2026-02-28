import json
import boto3
import random
import requests
from requests.auth import HTTPBasicAuth

OPENSEARCH_ENDPOINT = "https://search-restaurants-2vq6eg5ul5na5el2khpyuihjri.aos.us-east-1.on.aws"
MASTER_USER = "CloudComputing"
MASTER_PASS = "CloudComputing@123"
SQS_QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/255982107374/Q1"
REGION = "us-east-1"
DYNAMODB_TABLE = "yelp-restaurants"
SES_SENDER_EMAIL = "as21153@nyu.edu"

LOCATION_MAP = {
    "nyc":           ["New York", "Manhattan", "Brooklyn", "Queens"],
    "new york":      ["New York"],
    "manhattan":     ["Manhattan"],
    "brooklyn":      ["Brooklyn"],
    "queens":        ["Queens"],
    "chicago":       ["Chicago"],
    "los angeles":   ["Los Angeles"],
    "san francisco": ["San Francisco"],
    "boston":        ["Boston"],
    "seattle":       ["Seattle"],
    "austin":        ["Austin"],
    "miami":         ["Miami"]
}

dynamodb = boto3.resource("dynamodb", region_name=REGION)
sqs = boto3.client("sqs", region_name=REGION)
ses = boto3.client("ses", region_name=REGION)
auth = HTTPBasicAuth(MASTER_USER, MASTER_PASS)
headers = {"Content-Type": "application/json"}


def query_opensearch(cuisine, location):
    url = f"{OPENSEARCH_ENDPOINT}/restaurants/_search"
    cities = LOCATION_MAP.get(location, [location.title()])

    if len(cities) == 1:
        location_filter = {"term": {"City.keyword": cities[0]}}
    else:
        location_filter = {
            "bool": {
                "should": [{"term": {"City.keyword": city}} for city in cities],
                "minimum_should_match": 1
            }
        }

    query = {
        "query": {
            "bool": {
                "must": [
                    {"match": {"Cuisine": cuisine}},
                    location_filter
                ]
            }
        },
        "size": 50
    }

    r = requests.get(url, json=query, auth=auth, headers=headers)
    print("OpenSearch response:", r.status_code, r.text[:500])
    return r.json().get("hits", {}).get("hits", [])


def lambda_handler(event, context):
    response = sqs.receive_message(
        QueueUrl=SQS_QUEUE_URL,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=0
    )

    messages = response.get("Messages", [])
    if not messages:
        print("No messages in queue.")
        return {"statusCode": 200, "body": "No messages"}

    message = messages[0]
    receipt_handle = message["ReceiptHandle"]
    body = json.loads(message["Body"])

    cuisine     = body["cuisine"]
    location    = body["location"]
    dining_date = body["diningDate"]
    dining_time = body["diningTime"]
    num_people  = body["numPeople"]
    email       = body["email"]

    hits = query_opensearch(cuisine, location)

    if not hits:
        sqs.delete_message(QueueUrl=SQS_QUEUE_URL, ReceiptHandle=receipt_handle)
        return {"statusCode": 200, "body": "No restaurants found"}

    selected = random.sample(hits, min(3, len(hits)))
    restaurant_ids = [h["_source"]["RestaurantID"] for h in selected]

    table = dynamodb.Table(DYNAMODB_TABLE)
    restaurant_details = []
    for rid in restaurant_ids:
        result = table.get_item(Key={"id": rid})
        item = result.get("Item")
        if item:
            restaurant_details.append(item)

    suggestions = ""
    for i, restaurant in enumerate(restaurant_details, 1):
        name    = restaurant.get("name", "Unknown")
        address = restaurant.get("address", "Unknown address")
        suggestions += f"{i}. {name}, located at {address}\n"

    location_display = "NYC" if location == "nyc" else location.title()

    email_body = (
        f"Hello! Here are my {cuisine} restaurant suggestions for "
        f"{num_people} people in {location_display} on {dining_date} at {dining_time}:\n\n"
        f"{suggestions}\nEnjoy your meal!"
    )

    ses.send_email(
        Source=SES_SENDER_EMAIL,
        Destination={"ToAddresses": [email]},
        Message={
            "Subject": {"Data": f"Your {cuisine} Restaurant Suggestions!"},
            "Body":    {"Text": {"Data": email_body}}
        }
    )

    sqs.delete_message(QueueUrl=SQS_QUEUE_URL, ReceiptHandle=receipt_handle)

    return {"statusCode": 200, "body": "Done"}