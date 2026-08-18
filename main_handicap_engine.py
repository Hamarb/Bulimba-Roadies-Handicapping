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

def fetch_segment_efforts(segment_id):
    access_token = get_fresh_token()
    if not access_token:
        return []
        
    headers = {'Authorization': f'Bearer {access_token}'}
    url = f'https://www.strava.com/api/v3/segments/{segment_id}/all_efforts'
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching from Strava: {response.status_code}")
        return []

# ... (Keep the rest of your process_club_handicaps logic as is)
