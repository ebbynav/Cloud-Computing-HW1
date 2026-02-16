# Cloud-Computing-HW1

## Setup

Create and activate a virtual environment, then install dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

On Windows (PowerShell):

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## API key

Set your Yelp API key as an environment variable before running the scraper:

```bash
export YELP_API_KEY="your_api_key_here"
```

On Windows (PowerShell):

```powershell
$env:YELP_API_KEY="your_api_key_here"
```

## Scripts

- `other-scripts/yelp_scraper.py` queries the Yelp API for restaurants by cuisine/zip code and writes results to `restaurants.json`.
- `other-scripts/validate_restaurants.py` checks the dataset size, cuisine counts, and duplicate Business IDs.
- `other-scripts/sort_restaurants.py` sorts `restaurants.json` by a fixed cuisine order and writes `restaurants_sorted.json`.

## Usage

```bash
python other-scripts/yelp_scraper.py
python other-scripts/validate_restaurants.py
python other-scripts/sort_restaurants.py
```
