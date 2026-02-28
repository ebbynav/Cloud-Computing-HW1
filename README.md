# Cloud Computing HW1

Restaurant recommendation system built with AWS services and a simple web frontend.

- Abhinav Sivakumar as21153@nyu.edu, Carlin Joseph cj2803@nyu.edu

## Project Structure

- `front-end/`: Static chat UI and generated API Gateway SDK
- `lambda-functions/LF0.py`: API-facing Lambda that forwards user messages to Amazon Lex V2
- `lambda-functions/LF1.py`: Lex Lambda hook for slot validation and SQS message publishing
- `lambda-functions/LF2.py`: Worker Lambda that reads SQS, queries OpenSearch/DynamoDB, and emails results via SES
- `other-scripts/dynamo.py`: Loads restaurant data from Yelp API into DynamoDB
- `other-scripts/load_opensearch.py`: Indexes DynamoDB restaurant records into OpenSearch
- `requirements.txt`: Python dependencies

## Prerequisites

- Python 3.10+
- AWS account with Lex V2, Lambda, SQS, DynamoDB, OpenSearch, and SES configured

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Data Loading Scripts

```powershell
python .\other-scripts\dynamo.py
python .\other-scripts\load_opensearch.py
```

## Lambda Configuration Notes

Set Lambda environment variables as needed:

- `LF0.py`: `LEX_BOT_ID`, `LEX_BOT_ALIAS_ID`, `LEX_LOCALE_ID`
- `LF1.py`: `SQS_QUEUE_URL`

Also verify queue URLs, sender email, and service endpoints used in code before deployment.
