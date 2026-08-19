import streamlit as st
import pandas as pd
import os
from datetime import datetime

st.set_page_config(page_title="Welcome to the Bulimba Roadies Monthly Challenge", page_icon="🚴‍♂️", layout="wide")

# --- FILE CONFIG ---
DATA_FILE = "manual_entries.csv"
FAQ_FILE = "faq_data.csv"
CONFIG_FILE = "config.csv"

def get_segment_url():
    if os.path.exists(CONFIG_FILE):
        try: return pd.read_csv(CONFIG_FILE).iloc[0]["URL"]
        except: pass
    return "https://www.strava.com/segments/22270858"

def save_segment_url(url):
    pd.DataFrame({"URL": [url]}).to_csv(CONFIG_FILE, index=False)

def is_inappropriate(text):
    bad_words = ["rude", "badword1", "badword2"] 
    return any(word in text.lower() for word in bad_words)

def load_data(file, cols):
    if os.path.exists(file):
        try:
            df = pd.read_csv(file)
            for col in cols:
                if col not in df.columns:
                    df[col] = 0 if col not in ["Name", "Date"] else ""
            return df
        except Exception:
            return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

def format_time(sec):
    m, s = int(sec // 60), int(sec % 60)
    return f"0:{m:02d}:{s:02d}"

SEGMENT_URL = get_segment_url()
st.title("🚴‍♂️ Bulimba Roadies - Monthly Challenge")

# --- TABS ---
tab_inst, tab_entry, tab_seed, tab_res, tab_faq, tab_admin = st.tabs(
    ["Instructions", "Data Entry", "Seeding", "Results", "FAQ", "Admin"]
)

with tab_inst:
    st.info("Disclaimer: This application is a casual social experiment. Participation is entirely voluntary, and no one involved in the creation, hosting, or management of this app is legally or financially accountable for any outcomes, incidents, or errors. AI-generated elements and handicap calculations may include mistakes—use your best judgment and ride safely!")
    st.markdown(f"**The active challenge segment is:** [{SEGMENT_URL}]({SEGMENT_URL})")
    st.markdown("All submitted data is stored for 45 days. Data deletion is automated via a backend workflow.")

with tab_entry:
    st.header("Data Entry")
    st.markdown(f"**Active Challenge Segment:** [{SEGMENT_URL}]({SEGMENT_URL})")
    with st.form("entry_form", clear_on_submit=True):
        name = st.text_input("Firstname Lastname")
        ftp = st.number_input("Current FTP (Watts). The amount of power you can sustain for 20 minutes.", 0, 500, 100, help="This is used to create the seeding or order of participants. The data that you enter will be visible to other participants.")
        time = st.number_input("Your actual completion time for the segment (in seconds). This should come from Strava.", 60, 3600, 400)
        delta_est = st.number_input("Your Estimated Delta (in seconds) between first and last place.", 10, 1200, 300, help="What do you think is the gap between the fastest and slowest rider?")
        
        if st.form_submit_button("Submit Entry"):
            if not name or is_inappropriate(name): st.error("Please enter a valid, constructive name.")
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
    if not df.empty and "FTP (W)" in df.columns:
        seed_df = df.sort_values(by="FTP (W)", ascending=False)[["Name", "FTP (W)", "Date"]]
        st.dataframe(seed_df, use_container_width=True, hide_index=True)
    else:
        st.info("No data available.")

with tab_res:
    st.header("Challenge Results")
    df = load_data(DATA_FILE, ["Name", "Segment Time (s)", "Delta_Estimate"])
    active = df[(df["Segment Time (s)"] > 0) & (df["Delta_Estimate"] > 0)].copy()
    
    if not active.empty:
        delta = active["Delta_Estimate"].mean()
        active = active.sort_values(by="Segment Time (s)").reset_index(drop=True)
        count = len(active)
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
            summary += f"\nCheck out the active challenge segment details here: {SEGMENT_URL}"
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
        if is_inappropriate(q): st.error("Keep it constructive.")
        else: st.success("Question submitted for review.")

with tab_admin:
    st.header("Admin Configuration")
    
    # Initialize session state for the message
    if 'url_updated' not in st.session_state:
        st.session_state.url_updated = False

    new_url = st.text_input("Active Challenge Segment URL - Type the full Strava URL and click the button below to apply changes.", value=SEGMENT_URL)
    
    if st.button("Update Segment URL"):
        save_segment_url(new_url)
        st.session_state.url_updated = True # Set the flag
        st.rerun()

    # Show the message if the flag is True
    if st.session_state.url_updated:
        st.success("Segment URL updated across the app!")
        st.session_state.url_updated = False # Reset flag so it doesn't show again on next refresh

    st.markdown("---")
    if st.checkbox("Show Admin Reset Controls"):
        st.warning("This will delete all current challenge data.")
        if st.button("🚨 PERMANENTLY RESET DATA"):
            if os.path.exists(DATA_FILE): os.remove(DATA_FILE)
            st.rerun()
