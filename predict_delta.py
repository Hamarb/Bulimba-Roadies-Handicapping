import os
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def run_delta_prediction():
    # 1. Authenticate and connect to Google Sheets using environment variables (stored in GitHub Secrets)
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
    
    spreadsheet = client.open_by_url(spreadsheet_url)
    
    # 2. Load historical entries to see past actual deltas
    entries_sheet = spreadsheet.worksheet("Entries")
    entries_data = entries_sheet.get_all_records()
    df_entries = pd.DataFrame(entries_data)
    
    # 3. Load segment history specs
    segment_sheet = spreadsheet.worksheet("Segment")
    segment_data = segment_sheet.get_all_records()
    df_segments = pd.DataFrame(segment_data)
    
    # Example logic: Calculate a smart suggested delta based on past averages or segment length
    # (You can refine this formula as your historical dataset grows)
    default_delta = 300  # fallback default seconds
    if not df_entries.empty and "Delta_Estimate" in df_entries.columns:
        default_delta = int(df_entries["Delta_Estimate"].mean())
        
    print(f"Calculated smart recommended delta: {default_delta} seconds")
    
    # 4. Optional: Write this prediction back to a designated cell or configuration tab in your sheet
    # e.g., spreadsheet.worksheet("Config").update("B1", default_delta)

if __name__ == "__main__":
    run_delta_prediction()
