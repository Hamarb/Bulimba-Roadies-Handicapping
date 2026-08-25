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
def get_active_segment_url_from_sheet(sheet_client, spreadsheet_url):
    """Pulls the latest active segment URL from the 'Segment' worksheet tab."""
    try:
        seg_sheet = sheet_client.open_by_url(spreadsheet_url).worksheet("Segment")
        rows = seg_sheet.get_all_values()
        if len(rows) > 1:
            header = rows[0]
            if "Segment URL" in header:
                url_idx = header.index("Segment URL")
                last_row = rows[-1]
                if len(last_row) > url_idx and last_row[url_idx].startswith("http"):
                    return last_row[url_idx]
    except Exception:
        pass
    return "https://www.strava.com/segments/22270858"
    
def get_strava_segment_name(segment_url, access_token):
    """Extracts segment ID from URL and fetches the segment name from the Strava API."""
    try:
        segment_id = segment_url.strip("/").split("/")[-1]
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(f"https://www.strava.com/api/v3/segments/{segment_id}", headers=headers)
        
        if response.status_code == 200:
            return response.json().get('name', segment_url)
    except Exception:
        pass
    return segment_url

def pull_and_push_strava_data():
    access_token = get_strava_access_token()
    headers = {'Authorization': f'Bearer {access_token}'}
    
    # 1. Initialize Google Sheet client to fetch the active segment URL dynamically
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
    spreadsheet_url = os.getenv("GSHEETS_SPREADSHEET_URL")
    
    # 2. Get the active segment URL, name, and ID
    active_segment_url = get_active_segment_url_from_sheet(client, spreadsheet_url)
    segment_name = get_strava_segment_name(active_segment_url, access_token)
    
    try:
        segment_id = active_segment_url.strip("/").split("/")[-1]
    except Exception:
        print(f"Invalid segment URL format: {active_segment_url}")
        return

    # 3. Query the Segment Leaderboard endpoint filtered to "This Month"
    leaderboard_url = f"https://www.strava.com/api/v3/segments/{segment_id}/leaderboard"
    params = {
        'date_range': 'this_month',
        'per_page': 50
    }
    
    response = requests.get(leaderboard_url, headers=headers, params=params)
    response.raise_for_status()
    leaderboard_data = response.json()
    
    entries = leaderboard_data.get('entries', [])
    rows_to_insert = []
    
    # 4. Parse the leaderboard entries
    for entry in entries:
        athlete_name = entry.get('athlete_name', '')
        elapsed_time = entry.get('elapsed_time', 0) # Precise segment time in seconds
        start_date = entry.get('start_date', '')
        
        rows_to_insert.append([
            athlete_name, 
            0,             # FTP placeholder
            elapsed_time,  # Precise segment time (s)
            0,             # Delta Estimate placeholder
            segment_name,  # Correct segment name
            start_date
        ])
    
    # 5. Push data to Google Sheets "Strava" worksheet
    sheet = client.open_by_url(spreadsheet_url).worksheet("Strava")
    sheet.batch_clear(["A2:F100"])
    
    if rows_to_insert:
        sheet.append_rows(rows_to_insert)
        print(f"Successfully pushed {len(rows_to_insert)} monthly leaderboard entries for '{segment_name}'.")
    else:
        print("No leaderboard entries found for this segment this month.")

if __name__ == "__main__":
    pull_and_push_strava_data()
