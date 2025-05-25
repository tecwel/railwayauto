import os
import json
import requests
import csv
import time
from datetime import datetime
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from oauth2client.service_account import ServiceAccountCredentials

# Load Google Drive credentials from Railway environment variable
creds_json = os.getenv("GDRIVE_CREDENTIALS")
if creds_json:
    creds_path = "/tmp/credentials.json"
    with open(creds_path, "w") as f:
        f.write(creds_json)

    scope = ["https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
    drive = GoogleDrive(creds)  # ✅ Directly use service account credentials
else:
    print("❌ Google Drive credentials not found!")


# Constants
URL = "https://imgametransit.com/api/webapi/GetNoaverageEmerdList"
HEADERS = {"Content-Type": "application/json"}
CSV_FILE = "data.csv"
CSV_HEADERS = ["Period", "Number", "Premium"]
MAX_ENTRIES = 8000  # data rows only (excluding header)

def fetch_data():
    payload = {
        "pageSize": 10,
        "pageNo": 1,
        "typeId": 1,
        "language": 0,
        "random": "4f7eb2c47c0641c2be6b62053f2f3f53",
        "signature": "E3D7840D7D96C459DD2074174CD5A9A5",
        "timestamp": int(datetime.now().timestamp())
    }
    response = requests.post(URL, headers=HEADERS, json=payload)
    if response.status_code == 200:
        data = response.json()
        return data["data"]["list"] if "data" in data and "list" in data["data"] else None
    return None

def get_existing_periods():
    if not os.path.exists(CSV_FILE):
        return set()
    with open(CSV_FILE, "r") as file:
        return {line.split(",")[0] for line in file.readlines()[1:]}

def write_to_csv(items):
    existing_periods = get_existing_periods()
    new_data = []

    for item in items:
        period = item["issueNumber"]
        number = item["number"]
        premium = item["premium"]
        if period not in existing_periods:
            new_data.append([period, number, premium])
            print(f"✅ New period added: {period}")
        else:
            print(f"⚠️ Duplicate period skipped: {period}")

    if not new_data:
        return

    # Read existing data (excluding header)
    existing_data = []
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, "r") as file:
            lines = file.readlines()
            existing_data = [line.strip().split(",") for line in lines[1:]]

    # Prepend new data on top of existing
    combined_data = new_data + existing_data

    # Trim to MAX_ENTRIES if needed
    if len(combined_data) > MAX_ENTRIES:
        print("🧹 Trimming CSV to latest 8000 rows.")
        combined_data = combined_data[:MAX_ENTRIES]

    # Write to file (header + combined)
    with open(CSV_FILE, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(CSV_HEADERS)
        writer.writerows(combined_data)

    upload_to_drive()

def upload_to_drive():
    file_list = drive.ListFile({'q': f"title='{CSV_FILE}' and trashed=false"}).GetList()
    if file_list:
        file_id = file_list[0]['id']
        file = drive.CreateFile({'id': file_id})
    else:
        file = drive.CreateFile({'title': CSV_FILE})
    file.SetContentFile(CSV_FILE)
    file.Upload()
    print(f"📤 Uploaded {CSV_FILE} to Google Drive!")

def main_loop():
    while True:
        print(f"\n⏰ Running fetch at {datetime.now()}")
        try:
            data = fetch_data()
            if data:
                write_to_csv(data)
            else:
                print("⚠️ No new data found.")
        except Exception as e:
            print(f"❌ Error occurred: {e}")
        time.sleep(9 * 60)

if __name__ == "__main__":
    main_loop()
