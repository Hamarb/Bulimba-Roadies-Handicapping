import os
import requests
import pandas as pd
from datetime import datetime

# --- CREDENTIALS ---
CLIENT_ID = os.environ.get('STRAVA_CLIENT_ID')
CLIENT_SECRET = os.environ.get('STRAVA_CLIENT_SECRET')
REFRESH_TOKEN = os.environ.get('STRAVA_REFRESH_TOKEN')

# --- FUNCTIONS ---

def get_fresh_token():
    """Refreshes the access token automatically."""
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'refresh_token',
        'refresh_token': REFRESH_TOKEN
    }
    response = requests.post('https://www.strava.com/api/v3/oauth/token', data=data)
    if response.status_code == 200:
        return response.json()['access_token']
    else:
        print(f"Token refresh failed: {response.status_code}")
        return None

def fetch_club_segment_efforts(club_id, segment_id):
    access_token = get_fresh_token()
    if not access_token:
        return []
        
    headers = {'Authorization': f'Bearer {access_token}'}
    
    # 1. Get recent club activities
    url = f'https://www.strava.com/api/v3/clubs/{club_id}/activities'
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Error fetching club activities: {response.status_code}")
        return []

    activities = response.json()
    club_efforts = []

    # 2. Iterate through activity summaries to get detailed IDs
    for activity in activities:
        activity_id = activity['id']
        
        # 3. Fetch detailed activity to see segment efforts
        detail_url = f'https://www.strava.com/api/v3/activities/{activity_id}?include_all_efforts=true'
        detail_resp = requests.get(detail_url, headers=headers)
        
        if detail_resp.status_code == 200:
            activity_details = detail_resp.json()
            
            # 4. Look through segment_efforts for our target segment_id
            for effort in activity_details.get('segment_efforts', []):
                # We compare as strings to ensure matching
                if str(effort['segment']['id']) == str(segment_id):
                    club_efforts.append({
                        "Name": f"{activity['athlete']['firstname']} {activity['athlete'].get('lastname', '')}".strip(),
                        "actual_time_sec": effort['elapsed_time']
                    })
                    break # Found the effort for this rider, move to next activity
    
    return club_efforts

def process_club_handicaps(club_id, segment_id):
    efforts = fetch_club_segment_efforts(club_id, segment_id)
    
    # Fallback to baseline if no efforts found
    if not efforts:
        print("Using baseline dataset for calculation...")
        data = [
            {"Name": "Lee Brentz", "actual_time_sec": 331},
            {"Name": "Renee Ryan", "actual_time_sec": 341},
            {"Name": "Shona Matigian", "actual_time_sec": 353}
        ]
        df = pd.DataFrame(data)
    else:
        df = pd.DataFrame(efforts)

    # 1. Sort riders strongest/fastest to weakest/slowest
    df = df.sort_values(by='actual_time_sec').reset_index(drop=True)
    
    fastest = df['actual_time_sec'].min()
    slowest = df['actual_time_sec'].max()
    delta = slowest - fastest
    count = len(df)
    
    # 2. Dynamic Handicap Allocation
    handicaps = []
    for i, row in df.iterrows():
        h = delta * (i / (count - 1)) if count > 1 else 0.0
        handicaps.append(round(h))
        
    df['Handicap_Sec'] = handicaps
    df['Adjusted_Sec'] = df['actual_time_sec'] + df['Handicap_Sec']
    
    # 3. Save Output
    df.to_csv("bulimba_roadies_latest.csv", index=False)
    print(f"Successfully processed {count} riders and saved to bulimba_roadies_latest.csv!")

# --- EXECUTION ---
if __name__ == "__main__":
    MY_CLUB_ID = "224169"    
    MY_SEGMENT_ID = "41151160"
    process_club_handicaps(MY_CLUB_ID, MY_SEGMENT_ID)
