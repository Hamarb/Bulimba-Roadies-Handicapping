import streamlit as st
import pandas as pd

st.set_page_config(page_title="Bulimba Roadies Handicapping", page_icon="🚴‍♂️", layout="wide")

st.title("🚴‍♂️ Bulimba Roadies - Dynamic Handicapping Portal")
st.markdown("Review the active participant seeding order and update your FTP to refine handicaps.")

# Initialize mock participant data (can be linked to your Strava / Excel backend)
if 'riders_df' not in st.session_state:
    st.session_state.riders_df = pd.DataFrame([
        {"Name": "Lee Brentz", "FTP (W)": 280, "Segment Time (s)": 331},
        {"Name": "Renee Ryan", "FTP (W)": 240, "Segment Time (s)": 341},
        {"Name": "Shona Matigian", "FTP (W)": 220, "Segment Time (s)": 353},
        {"Name": "Angus Donaldson", "FTP (W)": 290, "Segment Time (s)": 357},
        {"Name": "Frederik Joergensen", "FTP (W)": 310, "Segment Time (s)": 401},
        {"Name": "Mark Routledge", "FTP (W)": 250, "Segment Time (s)": 444},
    ])

# Sidebar for Rider FTP Updates
st.sidebar.header("⚙️ Update Your Stats")
rider_to_update = st.sidebar.selectbox("Select Your Name", st.session_state.riders_df["Name"].tolist())
new_ftp = st.sidebar.number_input("Your FTP (Watts)", min_value=100, max_value=500, value=250)

if st.sidebar.button("Update FTP"):
    idx = st.session_state.riders_df[st.session_state.riders_df["Name"] == rider_to_update].index[0]
    st.session_state.riders_df.loc[idx, "FTP (W)"] = new_ftp
    st.success(f"Successfully updated FTP for {rider_to_update} to {new_ftp}W!")

# Sort riders from fastest to slowest based on segment time / performance
sorted_riders = st.session_state.riders_df.sort_values(by="Segment Time (s)", ascending=True).reset_index(drop=True)
sorted_riders["Seed Rank"] = sorted_riders.index + 1

# Reorder columns for display
sorted_riders = sorted_riders[["Seed Rank", "Name", "FTP (W)", "Segment Time (s)"]]

st.subheader("🏁 Current Seeding Order")
st.dataframe(sorted_riders, use_container_width=True)

if st.button("🚀 Generate Weekly Handicap Sheet"):
    st.success("Handicap sheet calculated based on current participant count and delta! Ready for Strava & Flourish export.")
