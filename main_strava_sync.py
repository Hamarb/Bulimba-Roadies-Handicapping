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
            # Assuming columns are Name, Segment URL, Date; let's check headers or grab the last row's URL column
            header = rows[0]
            if "Segment URL" in header:
                url_idx = header.index("Segment URL")
                # Look at the last row added
                last_row = rows[-1]
                if len(last_row) > url_idx and last_row[url_idx].startswith("http"):
                    return last_row[url_idx]
    except Exception:
        pass
    # Fallback default if sheet check fails
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
        target_segment_id = int(active_segment_url.strip("/").split("/")[-1])
    except Exception:
        print(f"Invalid segment URL format: {active_segment_url}")
        return

    # 3. Fetch club activities list
    club_id = os.getenv("STRAVA_CLUB_ID")
    url = f"https://www.strava.com/api/v3/clubs/{club_id}/activities"
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    activities = response.json()
    
    rows_to_insert = []
    
    # 4. Check each club activity's detailed segment efforts
    for act in activities:
        activity_id = act.get('id')
        athlete_name = f"{act.get('athlete', {}).get('firstname', '')} {act.get('athlete', {}).get('lastname', '')}".strip()
        
        detail_url = f"https://www.strava.com/api/v3/activities/{activity_id}"
        detail_params = {'include_all_efforts': 'true'}
        
        detail_response = requests.get(detail_url, headers=headers, params=detail_params)
        if detail_response.status_code != 200:
            continue
            
        activity_detail = detail_response.json()
        efforts = activity_detail.get('segment_efforts', [])
        
        for effort in efforts:
            seg = effort.get('segment', {})
            # ADD THIS PRINT LINE TO DEBUG:
            print(f"DEBUG: Found activity by {athlete_name} with segment '{seg.get('name')}' (ID: {seg.get('id')})")
            if seg.get('id') == target_segment_id:
                elapsed_time = effort.get('elapsed_time', 0) # Exact segment time in seconds
                start_date = effort.get('start_date_local', act.get('start_date', ''))
                
                rows_to_insert.append([
                    athlete_name, 
                    0,             # FTP placeholder
                    elapsed_time,  # Precise segment time (s)
                    0,             # Delta Estimate placeholder
                    segment_name,  # Correct segment name
                    start_date
                ])
                break # Move to next activity once the matching segment is found
    
    # 5. Push data to Google Sheets "Strava" worksheet
    sheet = client.open_by_url(spreadsheet_url).worksheet("Strava")
    sheet.batch_clear(["A2:F100"])
    
    if rows_to_insert:
        sheet.append_rows(rows_to_insert)
        print(f"Successfully pushed {len(rows_to_insert)} segment effort rows for '{segment_name}'.")
    else:
        print("No club members found with efforts matching this segment in recent activities.")
    pull_and_push_strava_data()
