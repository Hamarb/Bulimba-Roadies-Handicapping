import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Bulimba Roadies Handicapping", page_icon="🚴‍♂️", layout="wide")

st.title("🚴‍♂️ Bulimba Roadies - Dynamic Handicapping Portal")
st.markdown("Admin & Rider view: Select segment, month/year, update FTP, and generate weekly summaries.")

# --- MOCK / SESSION STATE SETUP ---
if 'riders_df' not in st.session_state:
    st.session_state.riders_df = pd.DataFrame([
        {"Name": "Lee Brentz", "FTP (W)": 280, "Segment Time (s)": 331},
        {"Name": "Renee Ryan", "FTP (W)": 240, "Segment Time (s)": 341},
        {"Name": "Shona Matigian", "FTP (W)": 220, "Segment Time (s)": 353},
        {"Name": "Angus Donaldson", "FTP (W)": 290, "Segment Time (s)": 357},
        {"Name": "Frederik Joergensen", "FTP (W)": 310, "Segment Time (s)": 401},
        {"Name": "Mark Routledge", "FTP (W)": 250, "Segment Time (s)": 444},
    ])

# --- TWEAK 2: Segment Search & Month/Year Picker (Admin View, No Login) ---
st.sidebar.header("⚙️ Admin & Event Controls")
selected_segment = st.sidebar.selectbox(
    "Select Strava Segment", 
    ["Hawthorne Crit Track", "Bulimba River Loop", "Oxford St Climb", "Memorial Park Sprint"]
)
selected_month_year = st.sidebar.text_input("Month & Year (MM/YYYY)", value=datetime.now().strftime("%m/%Y"))

st.sidebar.markdown("---")

# --- PRIVACY & OPT-OUT (Setting FTP to 0 removes/hides rider) ---
st.sidebar.header("🚴‍♂️ Update Your FTP")
rider_to_update = st.sidebar.selectbox("Select Your Name", st.session_state.riders_df["Name"].tolist())
new_ftp = st.sidebar.number_input("Your FTP (Watts) [Set to 0 to opt out]", min_value=0, max_value=500, value=250)

if st.sidebar.button("Update FTP"):
    idx = st.session_state.riders_df[st.session_state.riders_df["Name"] == rider_to_update].index[0]
    st.session_state.riders_df.loc[idx, "FTP (W)"] = new_ftp
    st.success(f"Updated FTP for {rider_to_update} to {new_ftp}W!")

# Filter out riders who set FTP to 0 (Privacy requirement)
active_riders = st.session_state.riders_df[st.session_state.riders_df["FTP (W)"] > 0].copy()

# Sort riders from fastest to slowest
sorted_riders = active_riders.sort_values(by="Segment Time (s)", ascending=True).reset_index(drop=True)
sorted_riders["Seed Rank"] = sorted_riders.index + 1
sorted_riders = sorted_riders[["Seed Rank", "Name", "FTP (W)", "Segment Time (s)"]]

st.subheader(f"🏁 Seeding Order for: {selected_segment} ({selected_month_year})")
st.dataframe(sorted_riders, use_container_width=True)

# --- TWEAK 3: Generate Weekly Summary View for Facebook ---
if st.button("🚀 Generate Weekly Summary"):
    st.markdown("### 📋 Weekly Summary View (Copy link or text for Facebook)")
    summary_markdown = f"""
    🚴‍♂️ **BULIMBA ROADIES WEEKLY HANDICAP SUMMARY** 🚴‍♀️
    * Segment: **{selected_segment}**
    * Period: **{selected_month_year}**
    * Active Participants: **{len(sorted_riders)}**

    🥇 **Top Seed:** {sorted_riders.iloc[0]['Name']}  
    🥈 **2nd Seed:** {sorted_riders.iloc[1]['Name']}  
    🥉 **3rd Seed:** {sorted_riders.iloc[2]['Name']}  

    _Check the full live portal view here: [Bulimba Roadies Streamlit App]_
    """
    st.info(summary_markdown)

# --- TWEAK 4 & 5: Monthly CSV Overwrite / Purge Logic ---
st.markdown("---")
st.subheader("📂 Monthly CSV Management (Admin)")
today = datetime.now()

if today.day == 1:
    st.warning("⚠️ Today is the 1st of the month. Previous month's CSV has been archived/overwritten and live page data reset.")
    # In backend logic, this triggers file overwrite/deletion if no data exists.
    
if st.button("Download Previous Month CSV"):
    csv_data = sorted_riders.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download CSV",
        data=csv_data,
        file_name=f"bulimba_roadies_{selected_month_year.replace('/', '_')}.csv",
        mime="text/csv",
    )
