import os
import requests
import pandas as pd
from datetime import datetime

# Credentials
CLIENT_ID = os.environ.get('STRAVA_CLIENT_ID')
CLIENT_SECRET = os.environ.get('STRAVA_CLIENT_SECRET')
REFRESH_TOKEN = os.environ.get('STRAVA_REFRESH_TOKEN')

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
    headers = {'Authorization': f'Bearer {access_token}'}
    
    # 1. Get recent club activities
    url = f'https://www.strava.com/api/v3/clubs/{club_id}/activities'
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Error fetching club activities: {response.status_code}")
        return []

    activities = response.json()
    club_efforts = []

    # 2. Filter activities for the specific segment
    for activity in activities:
        # Note: You may need to fetch detailed activity data to see segments
        # This is a simplified check
        if activity.get('segment_effort_id') == segment_id: # or similar logic
            club_efforts.append({
                "Name": activity['athlete']['firstname'],
                "actual_time_sec": activity['elapsed_time']
            })
    return club_efforts


# ... (Keep the rest of your process_club_handicaps logic as is)
