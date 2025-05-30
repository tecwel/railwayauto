import os
import time
import json
import requests
import csv
from datetime import datetime
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from oauth2client.service_account import ServiceAccountCredentials

# ✅ Load Google Drive credentials from Railway environment variable
creds_json = os.getenv("GDRIVE_CREDENTIALS")
drive = None

def authenticate_drive():
    """Authenticate and return a Google Drive instance."""
    global drive
    if creds_json:
        try:
            creds_dict = json.loads(creds_json)  # ✅ Load credentials from env variable
            scope = ["https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            
            gauth = GoogleAuth()
            gauth.credentials = creds
            gauth.LocalWebserverAuth = False  # ✅ Prevent PyDrive2 from looking for client_secrets.json
            drive = GoogleDrive(gauth)
            print("✅ Google Drive authentication successful!")
        except json.JSONDecodeError:
            print("❌ Error: Google Drive credentials are not in valid JSON format.")
            drive = None
        except Exception as e:
            print(f"❌ Error loading Google Drive credentials: {e}")
            drive = None
    else:
        print("❌ Google Drive credentials not found!")
        drive = None

# ✅ Authenticate Google Drive at startup
authenticate_drive()

# ✅ API details
URL = "https://imgametransit.com/api/webapi/GetNoaverageEmerdList"
HEADERS = {"Content-Type": "application/json"}
CSV_FILE = "data.csv"
CSV_HEADERS = ["Period", "Number", "Premium", "Big/Small"]

# ✅ Fetch data
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
    try:
        response = requests.post(URL, headers=HEADERS, json=payload)
        if response.status_code == 200:
            data = response.json()
            return data["data"]["list"] if "data" in data and "list" in data["data"] else None
    except Exception as e:
        print(f"❌ Error fetching data: {e}")
    return None

# ✅ Read existing periods (prevent duplicates)
def get_existing_periods():
    if not os.path.exists(CSV_FILE):
        return set()
    with open(CSV_FILE, "r", newline="") as file:
        reader = csv.reader(file)
        next(reader, None)  # Skip headers
        return {row[0] for row in reader}

# ✅ Prepend new data to CSV
def write_to_csv(items):
    existing_periods = get_existing_periods()
    new_data = []

    for item in items:
        period = str(item["issueNumber"])  # Ensure period is a string
        number = str(item["number"])
        premium = str(item["premium"])

        # ✅ Assign "B" for numbers 5-9 and "S" for numbers 0-4
        big_small = "B" if int(number) >= 5 else "S"

        if period not in existing_periods:
            new_data.append([period, number, premium, big_small])
            print(f"✅ New period added: {period}")

    if new_data:
        # ✅ Read existing CSV data (without adding extra commas)
        existing_data = []
        if os.path.exists(CSV_FILE):
            with open(CSV_FILE, "r", newline="") as file:
                reader = csv.reader(file)
                existing_data = list(reader)

        # ✅ Write new data at the top without corrupting CSV structure
        with open(CSV_FILE, "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(CSV_HEADERS)  # Always keep header
            writer.writerows(new_data)  # Write new data first
            writer.writerows(existing_data[1:])  # Append old data (skip duplicate header)

        # ✅ Upload to Google Drive if new data is added
        upload_to_drive()

# ✅ Upload CSV to Google Drive
def upload_to_drive():
    global drive
    if drive is None:
        print("❌ Google Drive not authenticated. Re-authenticating...")
        authenticate_drive()  # ✅ Try to re-authenticate
        if drive is None:
            print("❌ Google Drive authentication failed. Skipping upload.")
            return

    try:
        # ✅ Re-authenticate every time to prevent session expiration
        creds_dict = json.loads(os.getenv("GDRIVE_CREDENTIALS"))
        scope = ["https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        gauth = GoogleAuth()
        gauth.credentials = creds
        gauth.LocalWebserverAuth = False
        drive = GoogleDrive(gauth)  # ✅ Refresh Drive connection

        file_list = drive.ListFile({'q': f"title='{CSV_FILE}' and trashed=false"}).GetList()
        if file_list:
            file_id = file_list[0]['id']
            file = drive.CreateFile({'id': file_id})
        else:
            file = drive.CreateFile({'title': CSV_FILE})

        file.SetContentFile(CSV_FILE)
        file.Upload()
        print(f"📤 Uploaded {CSV_FILE} to Google Drive! ✅")
    except Exception as e:
        print(f"❌ Error uploading to Google Drive: {e}")

# ✅ Main function
def main():
    print("🔄 Fetching data...")
    data = fetch_data()
    if data:
        write_to_csv(data)
    else:
        print("⚠️ No new data found.")

if __name__ == "__main__":
    while True:
        main()
        time.sleep(540)  # Fetch data every 10 minutes
