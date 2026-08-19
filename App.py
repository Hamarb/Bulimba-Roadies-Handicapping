import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

st.set_page_config(page_title="Welcome to the Bulimba Roadies Monthly Challenge", page_icon="🚴‍♂️", layout="wide")

# --- FILE CONFIG ---
DATA_FILE = "manual_entries.csv"
FAQ_FILE = "faq_data.csv"
CONFIG_FILE = "config.csv"
HISTORY_FILE = "url_history.csv"

def enforce_retention(file):
    # Only try to process if file exists and has content
    if os.path.exists(file) and os.path.getsize(file) > 0:
        try:
            # Try to read the file
            df = pd.read_csv(file)
            
            # Check if there is actual data (not just an empty file or headers only)
            if not df.empty and 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
                # Drop rows where Date conversion failed (bad data)
                df = df.dropna(subset=['Date'])
                
                cutoff = datetime.now() - timedelta(days=45)
                df_cleaned = df[df['Date'] >= cutoff]
                
                # Only save if we actually removed something
                if len(df_cleaned) < len(df):
                    df_cleaned.to_csv(file, index=False)
        except Exception:
            # If the file is unreadable (e.g. corrupted), delete it to start fresh
            if os.path.exists(file):
                os.remove(file)

enforce_retention(DATA_FILE)

def get_segment_url():
    if os.path.exists(CONFIG_FILE):
        try: return pd.read_csv(CONFIG_FILE).iloc[0]["URL"]
        except: pass
    return "https://www.strava.com/segments/22270858"

def save_segment_url(url):
    pd.DataFrame({"URL": [url]}).to_csv(CONFIG_FILE, index=False)

def log_url_history(url):
    # Set to Brisbane time
    brisbane_tz = ZoneInfo("Australia/Brisbane")
    now_brisbane = datetime.now(brisbane_tz).strftime("%Y-%m-%d %H:%M:%S")
    
    df = pd.DataFrame({"Date": [now_brisbane], "URL": [url]})
    
    if os.path.exists(HISTORY_FILE):
        history = pd.read_csv(HISTORY_FILE)
        history = pd.concat([history, df], ignore_index=True)
    else:
        history = df
        
    # Keep only the last 10 entries
    history.tail(10).to_csv(HISTORY_FILE, index=False)
    
def is_inappropriate(text):
    bad_words = ["rude", "badword1", "badword2"] 
    return any(word in text.lower() for word in bad_words)

def load_data(file, cols):
    # Ensure we are looking at the current path
    if os.path.exists(file):
        try:
            # Re-read the file every single time the function is called
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
            if not name: 
                st.error("Name is required!")
            else:
                # Load current state
                df = load_data(DATA_FILE, ["Name", "FTP (W)", "Segment Time (s)", "Delta_Estimate", "Date"])
                # Create new entry
                new_entry = pd.DataFrame([{"Name": name, "FTP (W)": ftp, "Segment Time (s)": time, 
                                           "Delta_Estimate": delta_est, "Date": datetime.now().strftime("%Y-%m-%d")}])
                # Merge and Save
                df = pd.concat([df[df["Name"] != name], new_entry], ignore_index=True)
                df.to_csv(DATA_FILE, index=False)
                
                st.success("Entry saved!")
                st.rerun() # This forces the entire app to reload and hit load_data() again
                
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
        # Calculate the current average delta from all participants
        avg_delta = active["Delta_Estimate"].mean()
        
        # Display the Delta metric at the top of the tab
        st.markdown(f"**Current average delta based on the inputs provided by all participants:** {int(avg_delta)} seconds! This number gets divided by the number of participants and then multiplier by your relative position in the seeding table.")
        
        active = active.sort_values(by="Segment Time (s)").reset_index(drop=True)
        count = len(active)
        
        # Handicap Logic using the calculated avg_delta
        handicaps = [round(avg_delta * (1 - (i / (count - 1)))) if count > 1 else 0 for i in range(count)]
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
            # Include the avg_delta in the summary header
            summary = f"### 🏆 Monthly Challenge Summary\n**Period:** {datetime.now().strftime('%m/%Y')}\n**Current Average Delta:** {int(avg_delta)} seconds\n\n| Place | Name | Actual Time | Handicap | Adjusted Time |\n| :--- | :--- | :--- | :--- | :--- |\n"
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
    
    if 'url_updated' not in st.session_state:
        st.session_state.url_updated = False

    new_url = st.text_input("Active Challenge Segment URL - Type the full Strava URL and click the button below to apply changes.", value=SEGMENT_URL)
    
    if st.button("Update Segment URL"):
        save_segment_url(new_url)
        log_url_history(new_url)  # Log to history
        st.session_state.url_updated = True
        st.rerun()

    if st.session_state.url_updated:
        st.success("Segment URL updated across the app!")
        st.session_state.url_updated = False

    # --- URL HISTORY TABLE ---
    st.subheader("Recent URL History")
    if os.path.exists(HISTORY_FILE):
        history_df = pd.read_csv(HISTORY_FILE).sort_values(by="Date", ascending=False)
        st.dataframe(history_df.head(10), use_container_width=True, hide_index=True)
    else:
        st.write("No history available.")

    st.markdown("---")
    if st.checkbox("Show Admin Reset Controls"):
        st.warning("This will delete all current challenge data.")
        if st.button("🚨 PERMANENTLY RESET DATA"):
            if os.path.exists(DATA_FILE): os.remove(DATA_FILE)
            if os.path.exists(HISTORY_FILE): os.remove(HISTORY_FILE)
            st.rerun()
