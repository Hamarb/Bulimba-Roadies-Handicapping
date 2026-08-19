import streamlit as st
import pandas as pd
import os
from datetime import datetime

st.set_page_config(page_title="Bulimba Roadies Handicapping", page_icon="🚴‍♂️", layout="wide")

# --- FILE CONFIG ---
DATA_FILE = "manual_entries.csv"

def load_data():
    expected_columns = ["Name", "FTP (W)", "Segment Time (s)"]
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_csv(DATA_FILE)
            # Check if columns are missing
            if not all(col in df.columns for col in expected_columns):
                return pd.DataFrame(columns=expected_columns)
            return df
        except Exception:
            return pd.DataFrame(columns=expected_columns)
    return pd.DataFrame(columns=expected_columns)

def format_time(sec):
    m = int(sec // 60)
    s = int(sec % 60)
    return f"0:{m:02d}:{s:02d}"

st.title("🚴‍♂️ Bulimba Roadies - Dynamic Handicapping Portal")
st.markdown("Manage club segments, update your FTP (set to 0 to opt out), and generate monthly handicap summaries.")

# --- SIDEBAR: SUBMISSION & ADMIN ---
st.sidebar.header("🚴‍♂️ Submit / Update Your Time")
with st.sidebar.form("submission_form"):
    name = st.text_input("Name")
    ftp = st.number_input("FTP (Watts)", min_value=0, max_value=500, value=250)
    time = st.number_input("Segment Time (seconds)", min_value=60, max_value=3600, value=400)
    submitted = st.form_submit_button("Submit / Update Record")

    if submitted:
        df = load_data()
        if name in df["Name"].values:
            df.loc[df["Name"] == name, ["FTP (W)", "Segment Time (s)"]] = [ftp, time]
        else:
            new_row = pd.DataFrame([{"Name": name, "FTP (W)": ftp, "Segment Time (s)": time}])
            df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(DATA_FILE, index=False)
        st.success(f"Updated record for {name}!")

if st.sidebar.button("⚠️ Admin: Reset for New Month"):
    if os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)
        st.rerun()

# --- HANDICAP CALCULATION ENGINE ---
df = load_data()
active_riders = df[df["FTP (W)"] > 0].copy()

def compute_handicaps(df):
    df = df.sort_values(by="Segment Time (s)").reset_index(drop=True)
    fastest = df["Segment Time (s)"].min()
    slowest = df["Segment Time (s)"].max()
    delta = slowest - fastest
    count = len(df)
    
    handicaps = [round(delta * (i / (count - 1))) if count > 1 else 0 for i in range(count)]
    df["Handicap_Sec"] = handicaps
    df["Adjusted_Sec"] = df["Segment Time (s)"] + df["Handicap_Sec"]
    df = df.sort_values(by="Adjusted_Sec").reset_index(drop=True)
    df["Place"] = df.index + 1
    return df

if not active_riders.empty:
    processed_df = compute_handicaps(active_riders)
    
    # Prepare display table
    display_table = pd.DataFrame({
        "Place": processed_df["Place"],
        "Name": processed_df["Name"],
        "Actual Time": processed_df["Segment Time (s)"].apply(format_time),
        "Handicap": processed_df["Handicap_Sec"].apply(format_time),
        "Adjusted Time": processed_df["Adjusted_Sec"].apply(format_time),
    })

    st.subheader(f"🏁 Live Seeding & Handicap Preview ({datetime.now().strftime('%m/%Y')})")
    st.dataframe(display_table, use_container_width=True, hide_index=True)

    # --- FACEBOOK SUMMARY GENERATOR ---
    st.markdown("---")
    if st.button("📋 Generate Facebook Monthly Challenge Summary"):
        summary_markdown = f"""### 🏆 Monthly Challenge Summary
**Period:** {datetime.now().strftime('%m/%Y')}

| Place | Name | Actual Time | Handicap | Adjusted Time |
| :--- | :--- | :--- | :--- | :--- |
"""
        for _, row in display_table.iterrows():
            summary_markdown += f"| {row['Place']} | {row['Name']} | {row['Actual Time']} | {row['Handicap']} | {row['Adjusted Time']} |\n"
        
        st.markdown(summary_markdown)
        st.code(summary_markdown, language="markdown")
else:
    st.info("No times submitted yet. Be the first to enter your data!")
