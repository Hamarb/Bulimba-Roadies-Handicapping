import streamlit as st
import pandas as pd
import os
from datetime import datetime

st.set_page_config(page_title="Bulimba Roadies Handicapping", page_icon="🚴‍♂️", layout="wide")

# --- FILE CONFIG ---
DATA_FILE = "manual_entries.csv"

def load_data():
    """Robustly loads or initializes the data file with required columns."""
    expected_columns = ["Name", "FTP (W)", "Segment Time (s)", "Delta_Estimate"]
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_csv(DATA_FILE)
            # Ensure all columns exist
            for col in expected_columns:
                if col not in df.columns:
                    df[col] = 0
            return df
        except Exception:
            return pd.DataFrame(columns=expected_columns)
    return pd.DataFrame(columns=expected_columns)

def format_time(sec):
    """Formats seconds into 0:mm:ss string."""
    m = int(sec // 60)
    s = int(sec % 60)
    return f"0:{m:02d}:{s:02d}"

st.title("🚴‍♂️ Bulimba Roadies - Dynamic Handicapping Portal")
st.markdown("Submit your time and a group delta estimate to generate the weekly handicap.")

# --- SIDEBAR: SUBMISSION & ADMIN ---
st.sidebar.header("🚴‍♂️ Submit / Update Your Time")
with st.sidebar.form("submission_form", clear_on_submit=True):
    name = st.text_input("Name")
    ftp = st.number_input("FTP (Watts)", min_value=0, max_value=500, value=250)
    time = st.number_input("Segment Time (seconds)", min_value=60, max_value=3600, value=400)
    delta_est = st.number_input("Your Estimated Delta (seconds)", min_value=10, max_value=1200, value=300, 
                                help="What do you think is the gap between the fastest and slowest rider today?")
    
    submitted = st.form_submit_button("Submit / Update Record")

    if submitted:
        if not name:
            st.error("Name is required!")
        else:
            df = load_data()
            if name in df["Name"].values:
                df.loc[df["Name"] == name, ["FTP (W)", "Segment Time (s)", "Delta_Estimate"]] = [ftp, time, delta_est]
            else:
                new_row = pd.DataFrame([{"Name": name, "FTP (W)": ftp, "Segment Time (s)": time, "Delta_Estimate": delta_est}])
                df = pd.concat([df, new_row], ignore_index=True)
            df.to_csv(DATA_FILE, index=False)
            st.success(f"Updated record for {name}!")

if st.sidebar.button("⚠️ Admin: Reset for New Month"):
    if os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)
        st.rerun()

# --- HANDICAP CALCULATION ENGINE ---
df = load_data()
active_riders = df[(df["FTP (W)"] > 0) & (df["Segment Time (s)"] > 0)].copy()

def compute_handicaps(df):
    # Use community-voted delta
    delta = df["Delta_Estimate"].mean()
    df = df.sort_values(by="Segment Time (s)").reset_index(drop=True)
    count = len(df)
    
    # Fastest gets penalty (delta), slowest gets 0 penalty
    handicaps = [round(delta * (1 - (i / (count - 1)))) if count > 1 else 0 for i in range(count)]
    df["Handicap_Sec"] = handicaps
    df["Adjusted_Sec"] = df["Segment Time (s)"] + df["Handicap_Sec"]
    
    df = df.sort_values(by="Adjusted_Sec").reset_index(drop=True)
    df["Place"] = df.index + 1
    return df, delta

if not active_riders.empty:
    processed_df, group_delta = compute_handicaps(active_riders)
    
    # Metrics display
    col1, col2, col3 = st.columns(3)
    col1.metric("Participants", len(active_riders))
    col2.metric("Group Estimated Delta", f"{int(group_delta)}s")
    col3.metric("Fastest Actual", format_time(active_riders["Segment Time (s)"].min()))

    # Display table
    display_table = pd.DataFrame({
        "Place": processed_df["Place"],
        "Name": processed_df["Name"],
        "Actual Time": processed_df["Segment Time (s)"].apply(format_time),
        "Handicap": processed_df["Handicap_Sec"].apply(format_time),
        "Adjusted Time": processed_df["Adjusted_Sec"].apply(format_time),
    })
    st.dataframe(display_table, use_container_width=True, hide_index=True)

    # --- FACEBOOK SUMMARY ---
    st.markdown("---")
    if st.button("📋 Generate Facebook Monthly Challenge Summary"):
        summary_markdown = f"### 🏆 Monthly Challenge Summary\n**Period:** {datetime.now().strftime('%m/%Y')}\n\n| Place | Name | Actual Time | Handicap | Adjusted Time |\n| :--- | :--- | :--- | :--- | :--- |\n"
        for _, row in display_table.iterrows():
            summary_markdown += f"| {row['Place']} | {row['Name']} | {row['Actual Time']} | {row['Handicap']} | {row['Adjusted Time']} |\n"
        
        st.markdown(summary_markdown)
        st.info("👆 Copy the following text block for your Facebook post:")
        st.code(summary_markdown, language="markdown")
else:
    st.info("No times submitted yet. Be the first to enter your data!")
