import json

with open("restaurants.json") as f:
    data = json.load(f)

def normalize(c):
    return c.strip().lower()

# Sort alphabetically by cuisine, then by name
sorted_data = sorted(
    data,
    key=lambda r: (
        normalize(r["Cuisine"]),
        r["Name"].lower()
    )
)

with open("restaurants_sorted.json", "w") as f:
    json.dump(sorted_data, f, indent=2)

print("Sorted alphabetically by cuisine.")
