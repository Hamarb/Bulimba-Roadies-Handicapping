import os
import requests
import pandas as pd
from datetime import datetime

# --- CREDENTIALS ---
CLIENT_ID = os.environ.get('STRAVA_CLIENT_ID')
CLIENT_SECRET = os.environ.get('STRAVA_CLIENT_SECRET')
REFRESH_TOKEN = os.environ.get('STRAVA_REFRESH_TOKEN')

def get_fresh_token():
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'refresh_token',
        'refresh_token': REFRESH_TOKEN
    }
    response = requests.post('https://www.strava.com/api/v3/oauth/token', data=data)
    if response.status_code == 200:
        return response.json()['access_token']
    return None

def fetch_from_strava(club_id, segment_id):
    """Helper to perform the actual API call."""
    access_token = get_fresh_token()
    if not access_token: return []
    
    headers = {'Authorization': f'Bearer {access_token}'}
    url = f"https://www.strava.com/api/v3/clubs/{club_id}/activities?per_page=200"
    response = requests.get(url, headers=headers)
    
    print(f"DEBUG: Strava API Response Code: {response.status_code}")
    if response.status_code != 200:
        print(f"DEBUG: API Error Details: {response.text}")
        return []

    activities = response.json()
    print(f"DEBUG: Fetched {len(activities)} activities from Strava.")
    
    club_efforts = []
    for activity in activities:
        # DIAGNOSTIC: Print what we are scanning
        print(f"DEBUG: Scanning activity: '{activity.get('name')}' by {activity.get('athlete', {}).get('firstname')}")
        
        activity_id = activity.get('id')
        if not activity_id: continue
            
        detail_url = f"https://www.strava.com/api/v3/activities/{activity_id}?include_all_efforts=true"
        detail_resp = requests.get(detail_url, headers=headers)
        
        if detail_resp.status_code == 200:
            for effort in detail_resp.json().get('segment_efforts', []):
                # Ensure we compare ID as strings
                if str(effort.get('segment', {}).get('id')) == str(segment_id):
                    club_efforts.append({
                        "Name": f"{activity['athlete']['firstname']} {activity['athlete'].get('lastname', '')}".strip(),
                        "actual_time_sec": effort['elapsed_time']
                    })
                    print(f"DEBUG: Found segment match for {activity['athlete']['firstname']}")
                    break 
    return club_efforts

def fetch_club_segment_efforts(club_id, segment_id):
    # 1. Try API Fetch
    efforts = fetch_from_strava(club_id, segment_id)
    
    # 2. Hybrid Merge: If API data is sparse (e.g., < 5 riders), add manual entries
    if os.path.exists('manual_entries.csv'):
        manual_df = pd.read_csv('manual_entries.csv')
        manual_data = manual_df.to_dict('records')
        
        # Merge, preferring API data if available
        names_in_efforts = [e['Name'] for e in efforts]
        for entry in manual_data:
            if entry['Name'] not in names_in_efforts:
                efforts.append(entry)
    
    return efforts

def process_club_handicaps(club_id, segment_id):
    efforts = fetch_club_segment_efforts(club_id, segment_id)
    
    if not efforts:
        print("No data found, skipping processing.")
        return

    df = pd.DataFrame(efforts)
    # Deduplicate: Keep fastest time for each rider
    df = df.sort_values('actual_time_sec').drop_duplicates('Name').reset_index(drop=True)
    
    fastest = df['actual_time_sec'].min()
    slowest = df['actual_time_sec'].max()
    delta = slowest - fastest
    count = len(df)
    
    # Dynamic Handicap Allocation
    handicaps = [round(delta * (i / (count - 1))) if count > 1 else 0.0 for i in range(count)]
    df['Handicap_Sec'] = handicaps
    df['Adjusted_Sec'] = df['actual_time_sec'] + df['Handicap_Sec']
    
    df.to_csv("bulimba_roadies_latest.csv", index=False)
    print(f"Successfully processed {count} riders.")

if __name__ == "__main__":
    process_club_handicaps("2304788", "22270858")
