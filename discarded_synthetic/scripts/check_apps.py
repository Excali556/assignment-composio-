import csv
import json
import os
import re

# Load canonical apps
with open("apps.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    apps = list(reader)

print(f"Loaded {len(apps)} apps from apps.csv.")

# The 25 human audit sample indices
sample_ids = {1, 5, 10, 11, 15, 20, 21, 27, 28, 31, 36, 39, 41, 49, 53, 56, 58, 61, 67, 71, 73, 81, 90, 96, 98}
print(f"Audit sample size: {len(sample_ids)} apps across 10 categories.")
