# Import necessary modules
import csv
import requests

# Define the path to the CSV file
csv_file_path = "./types.csv"

# Open the CSV file and read its contents
with open(csv_file_path, mode="r", encoding="utf-8") as file:
    reader = csv.reader(file)

    # Iterate through each row in the CSV
    for row in reader:
        # Check if the type is 'redirect'
        if len(row) > 1 and "redirect" in row[1]:
            # print(row)
            url = f"https://openlibrary.org{row[2]}.json"
            response = requests.get(url)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            json_data = response.json()
            print(row[0], json_data.get("type"), json_data.get("wikipedia"))
