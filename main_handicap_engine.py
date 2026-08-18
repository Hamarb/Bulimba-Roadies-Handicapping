import os
import requests
import pandas as pd
from datetime import datetime

# Fetch Strava credentials securely from GitHub Actions environment variables
CLIENT_ID = os.environ.get('STRAVA_CLIENT_ID')
CLIENT_SECRET = os.environ.get('STRAVA_CLIENT_SECRET')
ACCESS_TOKEN = os.environ.get('STRAVA_ACCESS_TOKEN')

def fetch_segment_efforts(segment_id):
    headers = {'Authorization': f'Bearer {ACCESS_TOKEN}'}
    url = f'https://www.strava.com/api/v3/segments/{segment_id}/all_efforts'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching from Strava API: {response.status_code}")
        return []

def process_club_handicaps():
    # Replace with your specific Bulimba Roadies Strava Segment ID
    segment_id = "12345678" 
    efforts = fetch_segment_efforts(segment_id)
    
    # Fallback / parsing logic if connecting live or using local baseline
    if not efforts:
        print("Using baseline dataset for calculation...")
        data = [
            {"Name": "Lee Brentz", "actual_time_sec": 331},
            {"Name": "Renee Ryan", "actual_time_sec": 341},
            {"Name": "Shona Matigian", "actual_time_sec": 353},
            {"Name": "Angus Donaldson", "actual_time_sec": 357},
            {"Name": "Frederik Joergensen", "actual_time_sec": 401},
            {"Name": "Dennis Foley", "actual_time_sec": 404},
            {"Name": "Michael Aspinall", "actual_time_sec": 406}
        ]
        df = pd.DataFrame(data)
    else:
        parsed = []
        for effort in efforts:
            parsed.append({
                "Name": f"{effort.get('athlete', {}).get('firstname', 'Unknown')} {effort.get('athlete', {}).get('lastname', '')}".strip(),
                "actual_time_sec": effort.get("elapsed_time")
            })
        df = pd.DataFrame(parsed).drop_duplicates(subset=['Name'])

    # 1. Sort riders strongest/fastest to weakest/slowest
    df = df.sort_values(by='actual_time_sec').reset_index(drop=True)
    
    fastest = df['actual_time_sec'].min()
    slowest = df['actual_time_sec'].max()
    delta = slowest - fastest
    count = len(df)
    
    # 2. Dynamic Handicap Allocation based on participant count
    handicaps = []
    for i, row in df.iterrows():
        if count > 1:
            h = delta * (i / (count - 1))
        else:
            h = 0.0
        handicaps.append(round(h))
        
    df['Handicap_Sec'] = handicaps
    df['Adjusted_Sec'] = df['actual_time_sec'] + df['Handicap_Sec']
    
    # Sort final podium by adjusted finish time
    final_df = df.sort_values(by='Adjusted_Sec').reset_index(drop=True)
    final_df['Place'] = final_df.index + 1
    
    # Helper for formatting seconds to mm:ss
    def format_time(sec):
        m = int(sec // 60)
        s = int(sec % 60)
        return f"0:{m:02d}:{s:02d}"

    final_df['Actual Time'] = final_df['actual_time_sec'].apply(format_time)
    final_df['Handicap'] = final_df['Handicap_Sec'].apply(format_time)
    final_df['Adjusted Time'] = final_df['Adjusted_Sec'].apply(format_time)

    output_table = final_df[['Name', 'Actual Time', 'Handicap', 'Adjusted Time', 'Place']]

    # 3. Monthly CSV Management (Overwrite / Purge on the 1st of the month)
    today = datetime.now()
    if today.day == 1:
        csv_filename = "bulimba_roadies_previous_month.csv"
    else:
        csv_filename = "bulimba_roadies_latest.csv"
        
    output_table.to_csv(csv_filename, index=False)
    print(f"Successfully processed {count} riders and saved to {csv_filename}!")

if __name__ == "__main__":
    process_club_handicaps()
