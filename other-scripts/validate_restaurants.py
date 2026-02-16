import json
from collections import Counter

with open("restaurants_sorted.json") as f:
    data = json.load(f)

print("Total restaurants:", len(data))

# Check cuisines
cuisine_counts = Counter(r["Cuisine"] for r in data)

print("\nCuisine breakdown:")
for cuisine, count in cuisine_counts.items():
    print(f"{cuisine}: {count}")

#  Check minimum cuisines
print("\nNumber of cuisines:", len(cuisine_counts))

#Check duplicates
business_ids = [r["BusinessID"] for r in data]
unique_ids = set(business_ids)

if len(business_ids) == len(unique_ids):
    print("\nNo duplicates found ✅")
else:
    print("\nDuplicates detected ❌")
    print("Duplicate count:", len(business_ids) - len(unique_ids))
