import os
import requests
import pandas as pd
from datetime import datetime

# --- CREDENTIALS ---
CLIENT_ID = os.environ.get('STRAVA_CLIENT_ID')
CLIENT_SECRET = os.environ.get('STRAVA_CLIENT_SECRET')
REFRESH_TOKEN = os.environ.get('STRAVA_REFRESH_TOKEN')

def get_fresh_token():
    print(f"DEBUG: Checking Env Vars - Client ID: {bool(CLIENT_ID)}, Refresh Token: {bool(REFRESH_TOKEN)}")
    
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
        print(f"DEBUG: Token refresh failed. Status: {response.status_code}, Response: {response.text}")
        return None

def fetch_club_segment_efforts(club_id, segment_id):
    access_token = get_fresh_token()
    if not access_token:
        return []
        
    headers = {'Authorization': f'Bearer {access_token}'}
    
    # Query the segment leaderboard directly for the club
    url = f"https://www.strava.com/api/v3/segments/{segment_id}/leaderboard?club_id={club_id}&per_page=50"
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Error fetching segment leaderboard: {response.status_code}, {response.text}")
        return []

    data = response.json()
    club_efforts = []

    # Strava returns leaderboard entries in 'entries'
    for entry in data.get('entries', []):
        club_efforts.append({
            "Name": f"{entry.get('athlete_name', 'Unknown')}",
            "actual_time_sec": entry.get('elapsed_time')
        })
        
    return club_efforts
    
def process_club_handicaps(club_id, segment_id):
    efforts = fetch_club_segment_efforts(club_id, segment_id)
    if not efforts:
        print("Using baseline dataset for calculation...")
        data = [{"Name": "Lee Brentz", "actual_time_sec": 331}, {"Name": "Renee Ryan", "actual_time_sec": 341}]
        df = pd.DataFrame(data)
    else:
        df = pd.DataFrame(efforts)

    df = df.sort_values(by='actual_time_sec').reset_index(drop=True)
    fastest = df['actual_time_sec'].min()
    slowest = df['actual_time_sec'].max()
    delta = slowest - fastest
    count = len(df)
    
    handicaps = [round(delta * (i / (count - 1))) if count > 1 else 0.0 for i in range(count)]
    df['Handicap_Sec'] = handicaps
    df['Adjusted_Sec'] = df['actual_time_sec'] + df['Handicap_Sec']
    
    df.to_csv("bulimba_roadies_latest.csv", index=False)
    print(f"Successfully processed {count} riders.")

if __name__ == "__main__":
    process_club_handicaps("224169", "41151160")
