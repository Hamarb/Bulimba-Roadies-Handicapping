import os
import requests
import pandas as pd
import gspread
import requests
from google.oauth2.service_account import Credentials

# --- 1. CONFIGURATION & AUTHENTICATION ---
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_strava_access_token():
    """Refreshes and returns a valid Strava API access token."""
    payload = {
        'client_id': os.getenv("STRAVA_CLIENT_ID"),
        'client_secret': os.getenv("STRAVA_CLIENT_SECRET"),
        'refresh_token': os.getenv("STRAVA_REFRESH_TOKEN"),
        'grant_type': "refresh_token"
    }
    response = requests.post("https://www.strava.com/oauth/token", data=payload)
    response.raise_for_status()
    return response.json()['access_token']

def init_google_sheets():
    """Initializes the gspread client and returns the 'Strava' worksheet."""
    creds_dict = {
        "type": os.getenv("GCP_TYPE"),
        "project_id": os.getenv("GCP_PROJECT_ID"),
        "private_key_id": os.getenv("GCP_PRIVATE_KEY_ID"),
        "private_key": os.getenv("GCP_PRIVATE_KEY", "").replace("\\n", "\n"),
        "client_email": os.getenv("GCP_CLIENT_EMAIL"),
        "client_id": os.getenv("GCP_CLIENT_ID_GCP"),
        "auth_uri": "https://accounts.google.com/oauth/v2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": os.getenv("GCP_CERT_URL")
    }
    
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(creds)
    
    # Open spreadsheet and select the 'Strava' worksheet tab
    spreadsheet_url = os.getenv("GSHEETS_SPREADSHEET_URL")
    sheet = client.open_by_url(spreadsheet_url).worksheet("Strava")
    return sheet

# --- 2. MAIN SYNC LOGIC ---
def get_strava_segment_name(segment_url, access_token):
    """Extracts segment ID from URL and fetches the segment name from the Strava API."""
    try:
        # Extract the numeric segment ID from the end of the URL
        segment_id = segment_url.strip("/").split("/")[-1]
        
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(f"https://www.strava.com/api/v3/segments/{segment_id}", headers=headers)
        
        if response.status_code == 200:
            return response.json().get('name', segment_url)
    except Exception:
        pass
    
    return segment_url  # Fallback to URL if it fails

def pull_and_push_strava_data():
    access_token = get_strava_access_token()
    headers = {'Authorization': f'Bearer {access_token}'}
    
    # Fetch club activities from Strava API
    club_id = os.getenv("STRAVA_CLUB_ID")
    url = f"https://www.strava.com/api/v3/clubs/{club_id}/activities"
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    activities = response.json()
    
    # Parse data into rows matching your schema structure
    rows_to_insert = []
    for act in activities:
        athlete_name = f"{act.get('athlete', {}).get('firstname', '')} {act.get('athlete', {}).get('lastname', '')}".strip()
        moving_time = act.get('moving_time', 0)
        start_date = act.get('start_date', '')
        
        rows_to_insert.append([
            athlete_name, 
            0,             # FTP placeholder
            moving_time,   # Segment Time (s)
            0,             # Delta Estimate placeholder
            "Strava API Sync", 
            start_date
        ])
    
    # Push data to Google Sheets "Strava" worksheet
    sheet = init_google_sheets()
    
    # Clear existing data rows (keeping header row 1) before writing fresh data
    sheet.batch_clear(["A2:F100"])
    
    if rows_to_insert:
        sheet.append_rows(rows_to_insert)
        print(f"Successfully pushed {len(rows_to_insert)} rows to the 'Strava' Google Sheets tab.")
    else:
        print("No new activities found to sync.")

if __name__ == "__main__":
    pull_and_push_strava_data()
