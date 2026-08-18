import streamlit as st
import pandas as pd
from datetime import datetime

import os

# Instead of hardcoding keys:
CLIENT_ID = os.environ.get('STRAVA_CLIENT_ID')
CLIENT_SECRET = os.environ.get('STRAVA_CLIENT_SECRET')
ACCESS_TOKEN = os.environ.get('STRAVA_ACCESS_TOKEN')

st.set_page_config(page_title="Bulimba Roadies Handicapping", page_icon="🚴‍♂️", layout="wide")

st.title("🚴‍♂️ Bulimba Roadies - Dynamic Handicapping Portal")
st.markdown("Manage club segments, update your FTP (set to 0 to opt out/hide), and generate weekly handicap summaries.")

# --- SESSION STATE SETUP ---
if 'riders_df' not in st.session_state:
    st.session_state.riders_df = pd.DataFrame([
        {"Name": "Lee Brentz", "FTP (W)": 280, "Segment Time (s)": 331},
        {"Name": "Renee Ryan", "FTP (W)": 240, "Segment Time (s)": 341},
        {"Name": "Shona Matigian", "FTP (W)": 220, "Segment Time (s)": 353},
        {"Name": "Angus Donaldson", "FTP (W)": 290, "Segment Time (s)": 357},
        {"Name": "Frederik Joergensen", "FTP (W)": 310, "Segment Time (s)": 401},
        {"Name": "Dennis Foley", "FTP (W)": 230, "Segment Time (s)": 404},
        {"Name": "Michael Aspinall", "FTP (W)": 260, "Segment Time (s)": 406},
        {"Name": "Simon Teed", "FTP (W)": 250, "Segment Time (s)": 415},
        {"Name": "D G", "FTP (W)": 220, "Segment Time (s)": 417},
        {"Name": "Adam Khan", "FTP (W)": 210, "Segment Time (s)": 424},
        {"Name": "Mark Routledge", "FTP (W)": 240, "Segment Time (s)": 444},
        {"Name": "Farhan Juhari", "FTP (W)": 200, "Segment Time (s)": 501},
        {"Name": "Ben Matigian", "FTP (W)": 190, "Segment Time (s)": 509},
    ])

# --- ADMIN CONTROLS: Segment Search & Period ---
st.sidebar.header("⚙️ Event & Segment Controls")
selected_segment = st.sidebar.selectbox(
    "Select Strava Segment", 
    ["Hawthorne Crit Track", "Bulimba River Loop", "Oxford St Climb", "Memorial Park Sprint"]
)
selected_month_year = st.sidebar.text_input("Period (MM/YYYY)", value=datetime.now().strftime("%m/%Y"))

st.sidebar.markdown("---")

# --- PRIVACY & FTP OPT-OUT ---
st.sidebar.header("🚴‍♂️ Update Your FTP")
rider_to_update = st.sidebar.selectbox("Select Your Name", st.session_state.riders_df["Name"].tolist())
new_ftp = st.sidebar.number_input("Your FTP (Watts) [Set to 0 to opt out]", min_value=0, max_value=500, value=250)

if st.sidebar.button("Update FTP"):
    idx = st.session_state.riders_df[st.session_state.riders_df["Name"] == rider_to_update].index[0]
    st.session_state.riders_df.loc[idx, "FTP (W)"] = new_ftp
    st.success(f"Updated FTP for {rider_to_update} to {new_ftp}W!")

# Filter out riders who set FTP to 0 (Privacy requirement)
active_riders = st.session_state.riders_df[st.session_state.riders_df["FTP (W)"] > 0].copy()

# --- DYNAMIC HANDICAP CALCULATION ENGINE ---
def compute_handicaps(df):
    # Sort fastest to slowest
    df = df.sort_values(by="Segment Time (s)").reset_index(drop=True)
    
    fastest = df["Segment Time (s)"].min()
    slowest = df["Segment Time (s)"].max()
    delta = slowest - fastest
    count = len(df)
    
    handicaps = []
    for i, row in df.iterrows():
        if count > 1:
            h = delta * (i / (count - 1))
        else:
            h = 0.0
        handicaps.append(round(h))
        
    df["Handicap_Sec"] = handicaps
    df["Adjusted_Sec"] = df["Segment Time (s)"] + df["Handicap_Sec"]
    
    # Sort final podium by adjusted time
    final_df = df.sort_values(by="Adjusted_Sec").reset_index(drop=True)
    final_df["Place"] = final_df.index + 1
    return final_df

def format_time(sec):
    m = int(sec // 60)
    s = int(sec % 60)
    return f"0:{m:02d}:{s:02d}"

processed_df = compute_handicaps(active_riders)

# Prepare display table
display_table = pd.DataFrame({
    "Name": processed_df["Name"],
    "Actual Time": processed_df["Segment Time (s)"].apply(format_time),
    "Handicap": processed_df["Handicap_Sec"].apply(format_time),
    "Adjusted Time": processed_df["Adjusted_Sec"].apply(format_time),
    "Place": processed_df["Place"]
})

st.subheader(f"🏁 Live Seeding & Handicap Preview: {selected_segment} ({selected_month_year})")
st.dataframe(display_table, use_container_width=True)

# --- GENERATE WEEKLY SUMMARY FOR FACEBOOK ---
st.markdown("---")
if st.button("📋 Generate Facebook Monthly Challenge Summary"):
    summary_markdown = f"""### 🏆 Monthly Challenge

**Segment:** {selected_segment}  
**Period:** {selected_month_year}  

| Name | Actual Time | Handicap | Adjusted Time | Place |
| :--- | :--- | :--- | :--- | :---: |
"""
    for _, row in display_table.iterrows():
        summary_markdown += f"| {row['Name']} | {row['Actual Time']} | {row['Handicap']} | {row['Adjusted Time']} | {row['Place']} |\n"
        
    summary_markdown += "\nCheck the full live portal view here: [Bulimba Roadies Streamlit App]"
    
    st.markdown(summary_markdown)
    st.code(summary_markdown, language="markdown")

# --- MONTHLY CSV OVERWRITE / ARCHIVE LOGIC ---
st.markdown("---")
st.subheader("📂 Monthly CSV Management (Admin)")
today = datetime.now()

if today.day == 1:
    st.warning("⚠️ Today is the 1st of the month. Previous month's CSV has been archived/overwritten and live page data reset.")

if st.button("Download Previous Month CSV"):
    csv_data = display_table.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download CSV",
        data=csv_data,
        file_name=f"bulimba_roadies_{selected_month_year.replace('/', '_')}.csv",
        mime="text/csv",
    )
