import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Welcome to the Bulimba Roadies Monthly Challenge", page_icon="🚴‍♂️", layout="wide")

# --- CUSTOM CSS FOR BOLD, HIGH-CONTRAST TABS ---
st.markdown("""
<style>
    /* Target the overall tab container wrapper */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #e9ecef;
        padding: 8px;
        border-radius: 12px;
    }

    /* Style for individual inactive tabs */
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: #ffffff;
        border-radius: 8px;
        color: #212529 !important;
        font-size: 1.1rem;
        font-weight: 700;
        padding: 0px 24px;
        border: 2px solid #ced4da;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        transition: all 0.2s ease;
    }

    /* Hover effect */
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #f8f9fa;
        border-color: #adb5bd;
        color: #000000 !important;
    }

    /* Style for the active selected tab (High Visibility Pop) */
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, #ff4b4b 0%, #d90429 100%) !important;
        color: white !important;
        border: 2px solid #b7091c !important;
        box-shadow: 0 4px 12px rgba(217, 4, 41, 0.4) !important;
    }

    /* Force text inside the active tab to be crisp white */
    .stTabs [data-baseweb="tab"][aria-selected="true"] div p {
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# --- GOOGLE SHEETS SETUP VIA GSPREAD ---
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def init_connection():
    """Initializes gspread client using Streamlit Secrets."""
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(creds)
    spreadsheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    return client.open_by_url(spreadsheet_url)

def load_data():
    """Loads the main challenge data from the 'Entries' worksheet."""
    expected_columns = ["Name", "FTP (W)", "Segment Time (s)", "Delta_Estimate", "Segment", "Date"]
    try:
        sheet = init_connection().worksheet("Entries")
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        if df.empty:
            return pd.DataFrame(columns=expected_columns)
        for col in expected_columns:
            if col not in df.columns:
                df[col] = 0 if col not in ["Name", "Segment", "Date"] else ""
        return df
    except Exception:
        return pd.DataFrame(columns=expected_columns)

def get_existing_names():
    """Fetches a sorted list of unique participant names from the 'Entries' sheet."""
    try:
        df = load_data()
        if not df.empty and "Name" in df.columns:
            names = df["Name"].dropna().astype(str).str.strip().unique()
            valid_names = [n for n in names if n]
            return sorted(valid_names)
    except Exception:
        pass
    return []
    
def save_data(df):
    """Saves the dataframe back to the 'Entries' worksheet."""
    try:
        sheet = init_connection().worksheet("Entries")
        sheet.clear()
        sheet.update([df.columns.values.tolist()] + df.values.tolist())
    except Exception as e:
        st.error(f"Failed to save data: {e}")

def get_segment_data():
    """Fetches segment configuration history from the 'Segment' worksheet."""
    expected_columns = ["Name", "Segment URL", "Date"]
    try:
        sheet = init_connection().worksheet("Segment")
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        if df.empty:
            return pd.DataFrame(columns=expected_columns)
        for col in expected_columns:
            if col not in df.columns:
                df[col] = ""
        return df
    except Exception:
        return pd.DataFrame(columns=expected_columns)

def save_segment_submission(admin_name, url):
    """Appends submitter name, segment URL, and timestamp to the 'Segment' worksheet."""
    try:
        brisbane_tz = ZoneInfo("Australia/Brisbane")
        now_brisbane = datetime.now(brisbane_tz).strftime("%Y-%m-%d %H:%M:%S")
        
        sheet = init_connection().worksheet("Segment")
        sheet.append_row([admin_name, url, now_brisbane])
        return True
    except Exception as e:
        st.error(f"Failed to save segment submission: {e}")
        return False

def get_segment_url():
    """Retrieves the latest active segment URL from the Google Sheet."""
    segment_df = get_segment_data()
    if not segment_df.empty and "Segment URL" in segment_df.columns:
        valid_urls = segment_df["Segment URL"].dropna()
        if not valid_urls.empty:
            return str(valid_urls.iloc[-1])
    return "https://www.strava.com/segments/22270858"

def load_faq_data():
    """Loads FAQ data from the 'FAQ' worksheet."""
    expected_columns = ["Question", "Answer"]
    try:
        sheet = init_connection().worksheet("FAQ")
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        if df.empty:
            return pd.DataFrame(columns=expected_columns)
        for col in expected_columns:
            if col not in df.columns:
                df[col] = ""
        return df
    except Exception:
        return pd.DataFrame(columns=expected_columns)

def save_faq_data(df):
    """Saves the FAQ dataframe back to the 'FAQ' worksheet."""
    try:
        sheet = init_connection().worksheet("FAQ")
        sheet.clear()
        sheet.update([df.columns.values.tolist()] + df.values.tolist())
    except Exception as e:
        st.error(f"Failed to save FAQ data: {e}")

def is_inappropriate(text):
    bad_words = ["rude", "badword1", "badword2"] 
    return any(word in text.lower() for word in bad_words)

def format_time(sec):
    m, s = int(sec // 60), int(sec % 60)
    return f"0:{m:02d}:{s:02d}"

SEGMENT_URL = get_segment_url()

# --- CUSTOM HEADER LAYOUT ---
st.markdown("""
<div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
    <span style="font-size: 2.5rem;">🚴‍♀️ 🚴‍♂️</span>
    <h1 style="margin: 0; text-align: center; flex-grow: 1;">Bulimba Roadies</h1>
    <span style="font-size: 2.5rem; visibility: hidden;">🚴‍♀️ 🚴‍♂️</span>
</div>
<div style="display: flex; justify-content: space-between; align-items: center; width: 100%; margin-top: 2px;">
    <span style="font-size: 2.5rem; visibility: hidden;">🚴‍♂️ 🚴‍♀️</span>
    <h1 style="margin: 0; text-align: center; flex-grow: 1;">Monthly Challenge</h1>
    <span style="font-size: 2.5rem;">🚴‍♂️ 🚴‍♀️</span>
</div>
""", unsafe_allow_html=True)

st.markdown(f"<div style='text-align: left; margin-top: 15px;'><b>The active challenge segment is:</b> <a href='{SEGMENT_URL}'>{SEGMENT_URL}</a></div>", unsafe_allow_html=True)

# --- TABS ---
tab_inst, tab_entry, tab_seed, tab_res, tab_faq, tab_admin = st.tabs(
    ["Instructions", "Data Entry", "Seeding", "Results", "FAQ", "Admin"]
)

with tab_inst:
    st.info("Disclaimer: This application is a casual social experiment. Participation is entirely voluntary, and no one involved in the creation, hosting, or management of this app is legally or financially accountable for any outcomes, incidents, or errors. All submitted data remains available in the public domain. If you are concerned about privacy please use a different name. Stay safe and have fun!")
    
    with st.expander("ℹ️ How is my handicap calculated?"):
        st.markdown("""
        ### 🚴‍♂️ How Dynamic Handicapping Works
        Our club handicap system is fully dynamic, meaning it adapts automatically based on who turns up to ride and what the group collectively expects the pace gap to be.
        
        Instead of rigid, hard-coded start times, every handicap is calculated through four simple steps:
        
        1. **Delta Estimate (Community Powered)** To submit actual times for each challenge, everyone also provides a personal estimate of the Delta (the time gap in seconds between the fastest and slowest rider). We take the average of all submissions to create our official Group Estimated Delta.
           
        2. **Seeding** Using your submitted FTP, participants are sorted from lowest to highest. Your FTP isn't the competition; it is used to allocate your handicap relative to all participants. However, the FTP that you submit will be visible to all participants.
           
        3. **Inclusive Handicap** Everyone receives a calculated handicap designed to level the playing field. The person with the highest FTP receives the maximum handicap penalty (the full Group Estimated Delta). Every other rider receives a scaled handicap based on their position in the field.  
           The person with the lowest FTP still receives a handicap (Group Estimated Delta divided by the total participant count), ensuring no one sits at zero and the exact same formula applies equally to all members.
           
        4. **Results** Your official adjusted time is calculated by adding your calculated handicap to your actual segment time:

            *Adjusted Time = Actual Time + Handicap*

            The rider with the fastest adjusted time takes the win!

        ---

        ### 📊 Quick Comparison: Standard vs. Dynamic

        | Feature | Traditional Handicapping | Bulimba Roadies Dynamic System |
        | :--- | :--- | :--- |
        | **The Baseline** | Fixed historical times | Changes weekly based on who shows up |
        | **The Gap (Delta)** | Set by an admin | Voted on collectively by the participants |
        | **The Slowest Rider** | Gets zero head start (Scratch) | Gets an inclusive baseline handicap slice |
        | **Fairness** | Rigid and prone to outdated metrics | Self-correcting and community-driven |
        """)

with tab_entry:
    st.header("Data Entry")
        
    df_all = load_data()
    existing_names = get_existing_names()
    
    st.markdown("### Rider Details")
    
    if "selected_rider" not in st.session_state:
        st.session_state.selected_rider = "-- Select --"
    if "typed_rider" not in st.session_state:
        st.session_state.typed_rider = ""
    if "form_ftp" not in st.session_state:
        st.session_state.form_ftp = 100
    if "form_time" not in st.session_state:
        st.session_state.form_time = 400
    if "form_delta" not in st.session_state:
        st.session_state.form_delta = 300
    if "loaded_from_history" not in st.session_state:
        st.session_state.loaded_from_history = False

    def update_from_dropdown():
        rider = st.session_state.sel_rider_box
        if rider != "-- Select --":
            st.session_state.selected_rider = rider
            st.session_state.typed_rider = ""
            user_records = df_all[df_all["Name"] == rider]
            if not user_records.empty:
                if "Date" in user_records.columns:
                    user_records["Date"] = pd.to_datetime(user_records["Date"], errors="coerce")
                    user_records = user_records.sort_values(by="Date", ascending=False)
                latest = user_records.iloc[0]
                st.session_state.form_ftp = int(latest.get("FTP (W)", 100))
                st.session_state.form_time = int(latest.get("Segment Time (s)", 400))
                st.session_state.form_delta = int(latest.get("Delta_Estimate", 300))
                st.session_state.loaded_from_history = True
            else:
                st.session_state.loaded_from_history = False
        else:
            st.session_state.loaded_from_history = False

    col1, col2 = st.columns(2)
    with col1:
        st.selectbox("Select Existing Rider", options=["-- Select --"] + existing_names, key="sel_rider_box", on_change=update_from_dropdown)
    with col2:
        typed_new_name = st.text_input("Or Type New Name Here", key="typed_rider_box", help="Type your name if you are a new participant.")

    if st.session_state.loaded_from_history and st.session_state.sel_rider_box != "-- Select --":
        st.success(f"ℹ️ Form pre-loaded with the most recent submission data for **{st.session_state.sel_rider_box}**.")

    active_name = typed_new_name.strip() if typed_new_name.strip() else (st.session_state.sel_rider_box if st.session_state.sel_rider_box != "-- Select --" else "")

    with st.form("entry_form"):
        ftp = st.number_input("Current FTP (Watts)", 0, 500, value=st.session_state.form_ftp, help="Sustained 20-minute power output.")
        time = st.number_input("Your actual completion time for the segment (in seconds).", 60, 3600, value=st.session_state.form_time)
        delta_est = st.number_input("Your Estimated Delta (in seconds) between first and last place.", 10, 1200, value=st.session_state.form_delta)
        
        submitted = st.form_submit_button("Submit Entry")
        
        if submitted:
            if not active_name: 
                st.error("Please select an existing rider or type a new name!")
            else:
                brisbane_tz = ZoneInfo("Australia/Brisbane")
                now_brisbane = datetime.now(brisbane_tz).strftime("%Y-%m-%d %H:%M:%S")
                
                new_entry = pd.DataFrame([{
                    "Name": active_name, 
                    "FTP (W)": ftp, 
                    "Segment Time (s)": time, 
                    "Delta_Estimate": delta_est, 
                    "Segment": SEGMENT_URL,
                    "Date": now_brisbane
                }])
                
                df_all = load_data()
                df_all = pd.concat([df_all[df_all["Name"] != active_name], new_entry], ignore_index=True)
                save_data(df_all)
                
                st.session_state.loaded_from_history = False
                st.success(f"Entry saved for {active_name}!")
                st.rerun()

    st.markdown("---")
    with st.expander("🗑️ Need to delete your entry?"):
        with st.form("delete_form"):
            existing_names_for_del = get_existing_names()
            target_name = st.selectbox("Select your name to delete", options=["-- Select --"] + existing_names_for_del)
            confirm_delete = st.checkbox("I confirm I want to permanently remove all my records.")
            
            if st.form_submit_button("Delete All My Records"):
                if target_name == "-- Select --":
                    st.error("Please select your name.")
                elif not confirm_delete:
                    st.error("Please check the confirmation box.")
                else:
                    df = load_data()
                    if target_name in df["Name"].values:
                        df = df[df["Name"] != target_name]
                        save_data(df)
                        st.success(f"Successfully removed all records for {target_name}.")
                        st.rerun()
                    else:
                        st.warning(f"No entry found for '{target_name}'.")

with tab_seed:
    header_col1, header_col2 = st.columns([3, 1])
    with header_col1:
        st.header("Seeding Order")
    with header_col2:
        st.caption(f"Active Segment Focus")
        
    df = load_data()
    if not df.empty and "Segment" in df.columns:
        segment_filtered = df[df["Segment"] == SEGMENT_URL].copy()
        
        if not segment_filtered.empty:
            if "Date" in segment_filtered.columns:
                parsed_dates = pd.to_datetime(segment_filtered["Date"], errors="coerce")
                segment_filtered["Sort_Date"] = parsed
