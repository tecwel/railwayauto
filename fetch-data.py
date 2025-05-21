import requests
import csv
import os
from datetime import datetime

# API details
URL = "https://imgametransit.com/api/webapi/GetNoaverageEmerdList"
HEADERS = {
    "Content-Type": "application/json"
}

# CSV file setup
CSV_FILE = "data.csv"
CSV_HEADERS = ["Period", "Number", "Premium"]

# Function to fetch data (all rows)
def fetch_data():
    payload = {
        "pageSize": 10,
        "pageNo": 1,
        "typeId": 1,
        "language": 0,
        "random": "4f7eb2c47c0641c2be6b62053f2f3f53",  # May need dynamic generation
        "signature": "E3D7840D7D96C459DD2074174CD5A9A5",  # May need dynamic generation
        "timestamp": int(datetime.now().timestamp())  # Dynamic timestamp
    }

    response = requests.post(URL, headers=HEADERS, json=payload)
    
    if response.status_code == 200:
        data = response.json()
        if "data" in data and "list" in data["data"]:
            return data["data"]["list"]  # Return all rows in the "list" field
    
    return None

# Function to check if period already exists in CSV
def get_existing_periods():
    if not os.path.exists(CSV_FILE):
        return set()  # If file doesn't exist, return empty set

    with open(CSV_FILE, "r") as file:
        return {line.split(",")[0] for line in file.readlines()[1:]}  # Read existing periods

# Function to write data to CSV (prepend new rows)
def write_to_csv(items):
    existing_periods = get_existing_periods()
    new_data = []

    for item in items:
        period = item["issueNumber"]
        number = item["number"]
        premium = item["premium"]
        
        if period not in existing_periods:  # Only add if it's a new period
            new_data.append([period, number, premium])
            print(f"✅ New period added: {period}")
        else:
            print(f"⚠️ Duplicate period skipped: {period}")

    if new_data:
        # Read existing data
        existing_data = []
        if os.path.exists(CSV_FILE):
            with open(CSV_FILE, "r") as file:
                existing_data = file.readlines()
        
        # Write new data at the top
        with open(CSV_FILE, "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(CSV_HEADERS)  # Write header
            writer.writerows(new_data)  # Write new rows first
            if existing_data:
                file.writelines(existing_data[1:])  # Append old data (skip header)

# Main function to fetch data
def main():
    print("Fetching data...")
    data = fetch_data()
    if data:
        write_to_csv(data)
    else:
        print("No new data found.")

if __name__ == "__main__":
    main()
