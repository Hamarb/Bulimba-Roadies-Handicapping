import streamlit as st
import pandas as pd
import os
from datetime import datetime

st.set_page_config(page_title="Bulimba Roadies Challenge", page_icon="🚴‍♂️", layout="wide")

# --- FILE CONFIG ---
DATA_FILE = "manual_entries.csv"
FAQ_FILE = "faq_data.csv"
SEGMENT_URL = "https://www.strava.com/segments/22270858"

def load_data(file, cols):
    if os.path.exists(file):
        try:
            df = pd.read_csv(file)
            # Ensure every required column exists; if not, add it as 0/empty
            for col in cols:
                if col not in df.columns:
                    df[col] = 0 if col != "Name" and col != "Date" else ""
            return df
        except: 
            pass
    return pd.DataFrame(columns=cols)

def format_time(sec):
    m, s = int(sec // 60), int(sec % 60)
    return f"0:{m:02d}:{s:02d}"

st.title("🚴‍♂️ Bulimba Roadies - Handicapped Monthly Challenge")

# --- TABS ---
tab_inst, tab_entry, tab_seed, tab_res, tab_faq, tab_admin = st.tabs(
    ["Instructions", "Data Entry", "Seeding", "Results", "FAQ", "Admin"]
)

with tab_inst:
    st.header("Welcome to the Bulimba Roadies Monthly Challenge!")
    st.info("Disclaimer: This application is a casual social experiment. Participation is entirely voluntary, and no one involved in the creation, hosting, or management of this app is legally or financially accountable for any outcomes, incidents, or errors. AI-generated elements and handicap calculations may include mistakes—use your best judgment and ride safely!")
    st.markdown(f"**The active Challenge segment is:** [{SEGMENT_URL}]({SEGMENT_URL})")
    st.markdown("All submitted data is stored for 45 days. Data deletion is automated via a backend workflow.")

with tab_entry:
    st.header("Data Entry")
    st.markdown(f"**Active Challenge Segment:** [{SEGMENT_URL}]({SEGMENT_URL})")
    with st.form("entry_form", clear_on_submit=True):
        name = st.text_input("Name")
        ftp = st.number_input("Current FTP (Watts). The amount of power can you maintain for 20 minutes.", 0, 500, 100)
        time = st.number_input("Your actual time to complete the segment from Strava (in seconds)", 60, 3600, 400)
        delta_est = st.number_input("Your Estimated Delta (in seconds) between first and last place.", 10, 1200, 300, help="What do you think is the gap between the fastest and slowest rider today?")
        
        if st.form_submit_button("Submit Entry"):
            if not name: st.error("Name is required!")
            else:
                df = load_data(DATA_FILE, ["Name", "FTP (W)", "Segment Time (s)", "Delta_Estimate", "Date"])
                new_entry = pd.DataFrame([{"Name": name, "FTP (W)": ftp, "Segment Time (s)": time, 
                                           "Delta_Estimate": delta_est, "Date": datetime.now().strftime("%Y-%m-%d")}])
                df = pd.concat([df[df["Name"] != name], new_entry], ignore_index=True)
                df.to_csv(DATA_FILE, index=False)
                st.success("Entry saved!")
                st.rerun()

with tab_seed:
    st.header("Seeding Order")
    df = load_data(DATA_FILE, ["Name", "FTP (W)", "Date"])
    if not df.empty:
        seed_df = df.sort_values(by="FTP (W)", ascending=False)[["Name", "FTP (W)", "Date"]]
        st.dataframe(seed_df, use_container_width=True, hide_index=True)

with tab_res:
    st.header("Challenge Results")
    df = load_data(DATA_FILE, ["Name", "Segment Time (s)", "Delta_Estimate"])
    active = df[(df["Segment Time (s)"] > 0) & (df["Delta_Estimate"] > 0)].copy()
    
    if not active.empty:
        delta = active["Delta_Estimate"].mean()
        active = active.sort_values(by="Segment Time (s)").reset_index(drop=True)
        count = len(active)
        
        # Handicap Logic
        handicaps = [round(delta * (1 - (i / (count - 1)))) if count > 1 else 0 for i in range(count)]
        active["Handicap_Sec"] = handicaps
        active["Adjusted_Sec"] = active["Segment Time (s)"] + active["Handicap_Sec"]
        active = active.sort_values(by="Adjusted_Sec").reset_index(drop=True)
        active["Place"] = active.index + 1
        
        display = active.copy()
        display["Actual Time"] = display["Segment Time (s)"].apply(format_time)
        display["Handicap"] = display["Handicap_Sec"].apply(format_time)
        display["Adjusted Time"] = display["Adjusted_Sec"].apply(format_time)
        st.dataframe(display[["Place", "Name", "Actual Time", "Handicap", "Adjusted Time"]], use_container_width=True, hide_index=True)

        if st.button("📋 Generate Facebook Summary"):
            summary = f"### 🏆 Monthly Challenge Summary\n**Period:** {datetime.now().strftime('%m/%Y')}\n\n| Place | Name | Actual Time | Handicap | Adjusted Time |\n| :--- | :--- | :--- | :--- | :--- |\n"
            for _, row in display.iterrows():
                summary += f"| {row['Place']} | {row['Name']} | {row['Actual Time']} | {row['Handicap']} | {row['Adjusted Time']} |\n"
            summary += f"\nCheck out the Challenge segment details here: {SEGMENT_URL}"
            st.code(summary, language="markdown")
    else:
        st.info("No data available.")

with tab_faq:
    st.header("Frequently Asked Questions")
    faq_df = load_data(FAQ_FILE, ["Question", "Answer"])
    for _, row in faq_df.iterrows():
        with st.expander(row["Question"]): st.write(row["Answer"])
    
    q = st.text_input("Submit a question:")
    if st.button("Submit Question"):
        if any(bad in q.lower() for bad in ["rude", "name"]): st.error("Keep it constructive and avoid personal names.")
        else: st.success("Question submitted for review.")

with tab_admin:
    st.header("Admin Configuration")
    st.markdown("All data is stored for 45 days. Data deletion is automated via a backend workflow.")
    st.text_input("Active Challenge Segment URL", value=SEGMENT_URL, disabled=True)
