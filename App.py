import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Welcome to the Bulimba Roadies Monthly Challenge", page_icon="🚴‍♂️", layout="wide")

# --- FILE CONFIG & CONNECTIONS ---
FAQ_FILE = "faq_data.csv"

# Establish Google Sheets connection
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    """Loads the main challenge data directly from Google Sheets ('Entries' tab)."""
    expected_columns = ["Name", "FTP (W)", "Segment Time (s)", "Delta_Estimate", "Segment", "Date"]
    try:
        df = conn.read(worksheet="Entries", ttl=0)
        df = df.dropna(how="all")
        for col in expected_columns:
            if col not in df.columns:
                df[col] = 0 if col not in ["Name", "Segment", "Date"] else ""
        return df
    except Exception:
        return pd.DataFrame(columns=expected_columns)

def save_data(df):
    """Saves the main challenge dataframe back to Google Sheets ('Entries' tab)."""
    conn.update(worksheet="Entries", data=df)

def get_segment_data():
    """Fetches segment history from the 'Segment' tab of the Google Sheet."""
    expected_columns = ["Firstname Lastname", "Segment URL", "Date"]
    try:
        df = conn.read(worksheet="Segment", ttl=0)
        df = df.dropna(how="all")
        for col in expected_columns:
            if col not in df.columns:
                df[col] = ""
        return df
    except Exception:
        return pd.DataFrame(columns=expected_columns)

def save_segment_submission(admin_name, url):
    """Appends submitter name, segment URL, and timestamp to the 'Segment' tab."""
    try:
        brisbane_tz = ZoneInfo("Australia/Brisbane")
        now_brisbane = datetime.now(brisbane_tz).strftime("%Y-%m-%d %H:%M:%S")
        
        df = get_segment_data()
        new_row = pd.DataFrame([{
            "Firstname Lastname": admin_name,
            "Segment URL": url,
            "Date": now_brisbane
        }])
        df = pd.concat([df, new_row], ignore_index=True)
        conn.update(worksheet="Segment", data=df)
        return True
    except Exception as e:
        st.error(f"Failed to save segment submission: {e}")
        return False

def get_segment_url():
    """Retrieves the latest active segment URL from Google Sheets."""
    segment_df = get_segment_data()
    if not segment_df.empty and "Segment URL" in segment_df.columns:
        valid_urls = segment_df["Segment URL"].dropna()
        if not valid_urls.empty:
            return str(valid_urls.iloc[-1])
    return "https://www.strava.com/segments/22270858"

def is_inappropriate(text):
    bad_words = ["rude", "badword1", "badword2"] 
    return any(word in text.lower() for word in bad_words)

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
    with st.expander("ℹ️ How is my handicap calculated?"):
        st.markdown("""
        Your handicap is dynamically calculated using a community-voted **Delta** (the estimated gap between the fastest and slowest rider). 
        
        * **Fastest riders** receive a larger handicap penalty.
        * **Slowest riders** receive a fair baseline slice of the handicap.
        * **Your Adjusted Time** = Your Actual Time + Your Handicap. 
        
        Everyone is measured on the exact same mathematical model!
        """)
    st.markdown(f"**The active challenge segment is:** [{SEGMENT_URL}]({SEGMENT_URL})")
    st.markdown("All submitted participant data is securely stored via Google Sheets.")

with tab_entry:
    st.header("Data Entry")
    st.markdown(f"**Active Challenge Segment:** [{SEGMENT_URL}]({SEGMENT_URL})")
    with st.form("entry_form", clear_on_submit=True):
        name = st.text_input("Firstname Lastname")
        ftp = st.number_input("Current FTP (Watts). The amount of power you can sustain for 20 minutes.", 0, 500, 100, help="This is used to create the seeding or order of participants. The data that you enter will be visible to other participants.")
        time = st.number_input("Your actual completion time for the segment (in seconds). This should come from Strava.", 60, 3600, 400)
        delta_est = st.number_input("Your Estimated Delta (in seconds) between first and last place.", 10, 1200, 300, help="What do you think is the gap between the fastest and slowest rider?")
        
        if st.form_submit_button("Submit Entry"):
            if not name.strip(): 
                st.error("Name is required!")
            else:
                df = load_data()
                brisbane_tz = ZoneInfo("Australia/Brisbane")
                today_str = datetime.now(brisbane_tz).strftime("%Y-%m-%d")
                
                new_entry = pd.DataFrame([{
                    "Name": name, 
                    "FTP (W)": ftp, 
                    "Segment Time (s)": time, 
                    "Delta_Estimate": delta_est, 
                    "Segment": SEGMENT_URL,
                    "Date": today_str
                }])
                
                # Merge and Save back to Google Sheets
                df = pd.concat([df[df["Name"] != name], new_entry], ignore_index=True)
                save_data(df)
                
                st.success("Entry saved to Google Sheets!")
                st.rerun()

with tab_seed:
    st.header("Seeding Order")
    df = load_data()
    if not df.empty and "FTP (W)" in df.columns:
        seed_df = df.sort_values(by="FTP (W)", ascending=True)[["Name", "FTP (W)", "Date", "Segment"]]
        st.dataframe(seed_df, use_container_width=True, hide_index=True)
    else:
        st.info("No data available.")

with tab_res:
    st.header("Challenge Results")
    df = load_data()
    active = df[(df["Segment Time (s)"] > 0) & (df["Delta_Estimate"] > 0)].copy()
    
    if not active.empty:
        avg_delta = active["Delta_Estimate"].mean()
        
        st.markdown(f"**Current average delta based on the inputs provided by all participants:** {int(avg_delta)} seconds! This number gets divided by the number of participants and then multiplied by your relative position in the seeding table.")
        
        active = active.sort_values(by="Segment Time (s)").reset_index(drop=True)
        count = len(active)
        
        # Handicap Logic
        base_slice = avg_delta / count
        handicaps = []
        for i in range(count):
            if count > 1:
                h = (avg_delta - base_slice) * (1 - (i / (count - 1))) + base_slice
            else:
                h = 0.0
            handicaps.append(round(h))
            
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
            summary = f"### 🏆 Monthly Challenge Summary\n**Period:** {datetime.now().strftime('%m/%Y')}\n**Current Average Delta:** {int(avg_delta)} seconds\n\n| Place | Name | Actual Time | Handicap | Adjusted Time |\n| :--- | :--- | :--- | :--- | :--- |\n"
            for _, row in display.iterrows():
                summary += f"| {row['Place']} | {row['Name']} | {row['Actual Time']} | {row['Handicap']} | {row['Adjusted Time']} |\n"
            summary += f"\nCheck out the active challenge segment details here: {SEGMENT_URL}"
            st.code(summary, language="markdown")
    else:
        st.info("No data available.")

with tab_faq:
    st.header("Frequently Asked Questions")
    
    faq_df = load_data() # Falls back gracefully if columns differ, or read your FAQ CSV
    if os.path.exists(FAQ_FILE):
        faq_df = pd.read_csv(FAQ_FILE)
    else:
        faq_df = pd.DataFrame(columns=["Question", "Answer"])
        
    for _, row in faq_df.iterrows():
        with st.expander(str(row["Question"])): 
            st.write(str(row["Answer"]))
            
    st.markdown("---")
    q = st.text_input("Submit a question:")
    
    if st.button("Submit Question"):
        if not q.strip():
            st.error("Question cannot be empty.")
        elif is_inappropriate(q):
            st.error("Keep it constructive.")
        elif q in faq_df["Question"].values:
            st.warning("This question has already been submitted.")
        else:
            new_q = pd.DataFrame([{"Question": q, "Answer": "Response pending"}])
            faq_df = pd.concat([faq_df, new_q], ignore_index=True)
            faq_df.to_csv(FAQ_FILE, index=False)
            st.success("Question submitted! It will appear here once reviewed.")
            st.rerun()

with tab_admin:
    if st.checkbox("Show Admin Segment & Reset Controls"):
        st.header("Admin Configuration & Submitter Tracking")
        
        # Pull latest URL history from Google Sheets 'Segment' tab
        segment_df = get_segment_data()
        
        with st.form("segment_config_form"):
            admin_name = st.text_input("Your Name (Firstname Lastname)")
            new_url = st.text_input("Active Strava Segment URL", value=SEGMENT_URL)
            
            submitted = st.form_submit_button("Update Segment & Log Submitter")
            
            if submitted:
                if not admin_name.strip():
                    st.error("Please enter your First and Last Name.")
                elif not new_url.strip():
                    st.error("Please enter a valid Segment URL.")
                else:
                    if save_segment_submission(admin_name, new_url):
                        st.success(f"Segment updated and logged successfully by {admin_name}!")
                        st.rerun()
        
        # --- SEGMENT URL HISTORY TABLE ---
        st.subheader("Segment Configuration History")
        if not segment_df.empty:
            st.dataframe(segment_df.sort_values(by="Date", ascending=False).head(10), use_container_width=True, hide_index=True)
        else:
            st.write("No segment history available.")
        
        if os.path.exists(FAQ_FILE):
            with open(FAQ_FILE, "rb") as f:
                st.download_button("Download current FAQ", f, "faq_data.csv")
            
        st.markdown("---")
        st.subheader("⚠️ Danger Zone")
        
        confirm_reset = st.checkbox("I understand this will clear local cache/configs.")
        if confirm_reset:
            if st.button("🚨 PERMANENTLY RESET LOCAL CONFIG"):
                if os.path.exists(FAQ_FILE):
                    os.remove(FAQ_FILE)
                st.success("Local cache cleared.")
                st.rerun()
        else:
            st.button("🚨 PERMANENTLY RESET LOCAL CONFIG", disabled=True)
