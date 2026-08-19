import streamlit as st
import pandas as pd
import os
from datetime import datetime

st.set_page_config(page_title="Bulimba Roadies Handicapping", page_icon="🚴‍♂️", layout="wide")

# --- FILE CONFIG ---
DATA_FILE = "manual_entries.csv"

def load_data():
    expected_columns = ["Name", "FTP (W)", "Segment Time (s)", "Delta_Estimate"]
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_csv(DATA_FILE)
            for col in expected_columns:
                if col not in df.columns: df[col] = 0
            return df
        except: return pd.DataFrame(columns=expected_columns)
    return pd.DataFrame(columns=expected_columns)

def format_time(sec):
    m, s = int(sec // 60), int(sec % 60)
    return f"0:{m:02d}:{s:02d}"

st.title("🚴‍♂️ Bulimba Roadies - Dynamic Handicapping Portal")

# --- MAIN LAYOUT ---
tab1, tab2 = st.tabs(["🏁 Current Race", "📋 Submit & Admin"])

with tab1:
    # --- HANDICAP CALCULATION ENGINE ---
    df = load_data()
    active_riders = df[(df["FTP (W)"] > 0) & (df["Segment Time (s)"] > 0)].copy()

    if not active_riders.empty:
        delta = active_riders["Delta_Estimate"].mean()
        active_riders = active_riders.sort_values(by="Segment Time (s)").reset_index(drop=True)
        count = len(active_riders)
        
        # Corrected Handicap logic
        handicaps = [round(delta * (1 - (i / (count - 1)))) if count > 1 else 0 for i in range(count)]
        active_riders["Handicap_Sec"] = handicaps
        active_riders["Adjusted_Sec"] = active_riders["Segment Time (s)"] + active_riders["Handicap_Sec"]
        active_riders = active_riders.sort_values(by="Adjusted_Sec").reset_index(drop=True)
        active_riders["Place"] = active_riders.index + 1

        # Metrics Row
        col1, col2, col3 = st.columns(3)
        col1.metric("Participants", len(active_riders))
        col2.metric("Group Delta", f"{int(delta)}s")
        col3.metric("Fastest Actual", format_time(active_riders["Segment Time (s)"].min()))

        # Display Table
        display_table = active_riders[["Place", "Name", "Segment Time (s)", "Handicap_Sec", "Adjusted_Sec"]]
        display_table.columns = ["Place", "Name", "Actual Time", "Handicap", "Adjusted Time"]
        # Apply formatting for display
        display_fmt = display_table.copy()
        display_fmt["Actual Time"] = display_fmt["Actual Time"].apply(format_time)
        display_fmt["Handicap"] = display_fmt["Handicap"].apply(format_time)
        display_fmt["Adjusted Time"] = display_fmt["Adjusted Time"].apply(format_time)
        st.dataframe(display_fmt, use_container_width=True, hide_index=True)

        # Facebook Summary
        if st.button("📋 Generate Facebook Summary"):
            st.info("👆 Copy this for your Facebook post:")
            summary = "### 🏆 Monthly Challenge Summary\n"
            summary += "| Place | Name | Actual Time | Handicap | Adjusted Time |\n| :--- | :--- | :--- | :--- | :--- |\n"
            for _, row in display_fmt.iterrows():
                summary += f"| {row['Place']} | {row['Name']} | {row['Actual Time']} | {row['Handicap']} | {row['Adjusted Time']} |\n"
            st.code(summary, language="markdown")
    else:
        st.info("No times submitted yet. Head to the 'Submit' tab to enter data!")

with tab2:
    # --- SUBMISSION EXPANDER ---
    with st.expander("🚴‍♂️ Submit / Update Your Time", expanded=True):
        with st.form("submission_form", clear_on_submit=True):
            name = st.text_input("Name")
            ftp = st.number_input("FTP (Watts)", 0, 500, 250)
            time = st.number_input("Segment Time (seconds)", 60, 3600, 400)
            delta_est = st.number_input("Estimated Delta (sec)", 10, 1200, 300)
            if st.form_submit_button("Submit / Update"):
                df = load_data()
                if name in df["Name"].values:
                    df.loc[df["Name"] == name, ["FTP (W)", "Segment Time (s)", "Delta_Estimate"]] = [ftp, time, delta_est]
                else:
                    new = pd.DataFrame([{"Name": name, "FTP (W)": ftp, "Segment Time (s)": time, "Delta_Estimate": delta_est}])
                    df = pd.concat([df, new], ignore_index=True)
                df.to_csv(DATA_FILE, index=False)
                st.success("Entry saved!")
                st.rerun()

    # --- LOCKED ADMIN ZONE ---
    st.markdown("---")
    st.subheader("⚠️ Admin Controls")
    if st.checkbox("I want to show Admin controls"):
        st.warning("This will delete all current race data.")
        if st.button("🚨 PERMANENTLY RESET FOR NEW MONTH"):
            if os.path.exists(DATA_FILE):
                os.remove(DATA_FILE)
                st.rerun()
