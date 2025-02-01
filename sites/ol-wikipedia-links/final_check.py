# This is a python file

import json
import requests
import csv  # Import the csv module

example_redirect = {
    "key": "/authors/OL11412678A",
    "type": {"key": "/type/redirect"},
    "location": "/authors/OL1354006A",
}
example_url = "https://openlibrary.org/authors/OL11412678A.json"

# Load data from alldata.json once
with open("./alldata.json", "r") as file:
    data_arr = json.load(file)

# Read existing OLIDs from types.csv into a set
existing_olids = set()
try:
    with open("./types.csv", "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None)  # Skip header
        existing_olids = {row[0] for row in reader}  # Store OLIDs in a set
except FileNotFoundError:
    pass  # If the file doesn't exist, we start with an empty set

# Open types.csv in append mode to store results incrementally
with open("./types.csv", "a", newline="") as output_file:  # Change to append mode
    csv_writer = csv.writer(output_file)  # Create a CSV writer
    # Only write the header row if the file is empty
    if output_file.tell() == 0:
        csv_writer.writerow(["OLID", "type", "location"])  # Write the header row

    for item in data_arr:
        olid = item["OLID"]  # Keep OLID as a string
        if olid in existing_olids:
            continue  # Skip already processed items

        url = f"https://openlibrary.org/authors/{olid}.json"
        response = requests.get(url)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        json_data = response.json()

        # Handle missing keys gracefully
        r = {
            "OLID": olid,
            "type": json_data.get("type"),
            "location": json_data.get("location"),
        }
        print(r)

        csv_writer.writerow([r["OLID"], r["type"], r["location"]])
