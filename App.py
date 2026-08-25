import streamlit as st
import pandas as pd
import os
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import gspread
from google.oauth2.service_account import Credentials
import time as t  # Aliased explicitly to avoid naming collisions

st.set_page_config(page_title="Welcome to the Bulimba Roadies Monthly Challenge", page_icon="🚴‍♂️", layout="wide")

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

@st.cache_data(ttl=600)  # Caches the result for 10 minutes to avoid hitting Google Sheet limits
    
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
    """Fetches segment configuration history from the 'Segment' worksheet using raw values."""
    expected_columns = ["Name", "Segment URL", "Date"]
    try:
        sheet = init_connection().worksheet("Segment")
        rows = sheet.get_all_values()
        
        # If there's only a header row or nothing at all
        if not rows or len(rows) <= 1:
            return pd.DataFrame(columns=expected_columns)
            
        # First row is headers, remaining rows are data
        header = rows[0]
        data = rows[1:]
        df = pd.DataFrame(data, columns=header)
        
        # Ensure all expected columns exist
        for col in expected_columns:
            if col not in df.columns:
                df[col] = ""
                
        # Filter out completely blank rows
        df = df.dropna(how="all")
        if df.empty:
            return pd.DataFrame(columns=expected_columns)
            
        return df
    except Exception as e:
        st.error(f"Error loading segment history: {e}")
        return pd.DataFrame(columns=expected_columns)

@st.cache_data(ttl=600)
app_token = os.getenv("STRAVA_ACCESS_TOKEN") # Or use your existing token generator function

def get_strava_segment_info(segment_url):
    """Fetches the segment name from the Strava API using its URL."""
    try:
        segment_id = segment_url.strip("/").split("/")[-1]
        headers = {'Authorization': f'Bearer {get_strava_access_token()}'}
        response = requests.get(f"https://www.strava.com/api/v3/segments/{segment_id}", headers=headers)
        
        if response.status_code == 200:
            return response.json().get('name', "Active Segment")
    except Exception:
        pass
    return "Active Segment"

def save_segment_submission(admin_name, url):
    """Appends submitter name, segment URL, and timestamp to the 'Segment' worksheet."""
    try:
        brisbane_tz = ZoneInfo("Australia/Brisbane")
        now_brisbane = datetime.now(brisbane_tz).strftime("%Y-%m-%d %H:%M:%S")
        
        sheet = init_connection().worksheet("Segment")
        sheet.append_row([admin_name, url, now_brisbane])
        
        # Give Google Sheets a brief moment to commit the append operation 
        # using the aliased time module to prevent collision.
        t.sleep(1)
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
    <h1 style="margin: 0; padding: 0; text-align: center; flex-grow: 1; line-height: 1.1;">Bulimba Roadies</h1>
    <span style="font-size: 2.5rem; visibility: hidden;">🚴‍♀️ 🚴‍♂️</span>
</div>
<div style="display: flex; justify-content: space-between; align-items: center; width: 100%; margin-top: -10px;">
    <span style="font-size: 2.5rem; visibility: hidden;">🚴‍♂️ 🚴‍♀️</span>
    <h1 style="margin: 0; padding: 0; text-align: center; flex-grow: 1; line-height: 1.1;">Monthly Challenge</h1>
    <span style="font-size: 2.5rem;">🚴‍♂️ 🚴‍♀️</span>
</div>
""", unsafe_allow_html=True)

segment_name = get_strava_segment_info(SEGMENT_URL)

st.markdown(
    f"<div style='text-align: left; margin-top: 25px; margin-bottom: 20px; font-size: 0.9rem;'>"
    f"The active challenge segment is: <a href='{SEGMENT_URL}' target='_blank'>{segment_name}</a>"
    f"</div>", 
    unsafe_allow_html=True
)

# --- TABS ---
tab_inst, tab_entry, tab_seed, tab_res, tab_faq, tab_admin = st.tabs(
    ["Instructions", "Data Entry", "Seeding", "Results", "FAQ", "Admin"]
)

with tab_inst:
    st.info("Disclaimer: This application is a casual social experiment. Participation is entirely voluntary, and no one involved in the creation, hosting, or management of this app is legally or financially accountable for any outcomes, incidents, or errors. All submitted data remains available in the public domain. If you are concerned about privacy please use a different name. Stay safe and have fun!")

    st.markdown("""
    We have a love hate relationship with Strava. We all love the platform and how it presents our data. Unfortunately getting data out is more challenging. This app should minimise the effort for all parties.    
    
    1. Admin will set the "The active challenge segment".
    2. Participants just ride the segment and then complete the data entry form. 
    3. This app will calculate handicaps, seeding and the results.
    4. The app will also format the weekly Facebook posts.
    5. Please submit any questions via the FAQ. Complaints should be sent to the Mayor of Bulimba!
    """)
    
    with st.expander("ℹ️ How is my handicap calculated?"):
        st.markdown("""
        ### 🚴‍♂️ How Dynamic Handicapping Works
        Our club handicap system is fully dynamic, meaning it adapts automatically based on who turns up to ride and what the group collectively expects the pace gap to be.
        
        Instead of rigid, hard-coded start times, every handicap is calculated through four simple steps:
        
        1. **Delta Estimate (Community Powered):** To submit actual times for each challenge, everyone also provides a personal estimate of the Delta (the time gap in seconds between the fastest and slowest rider). We take the average of all submissions to create our official Group Estimated Delta.
           
        2. **Seeding:** Using your submitted FTP, participants are sorted from lowest to highest. Your FTP isn't the competition; it is used to allocate your handicap relative to all participants. However, the FTP that you submit will be visible to all participants.
           
        3. **Inclusive Handicap:** Everyone receives a calculated handicap designed to level the playing field. The person with the highest FTP receives the maximum handicap penalty (the full Group Estimated Delta). Every other rider receives a scaled handicap based on their position in the field.  
           The person with the lowest FTP still receives a handicap (Group Estimated Delta divided by the total participant count), ensuring no one sits at zero and the exact same formula applies equally to all members.
           
        4. **Results:** Your official adjusted time is calculated by adding your calculated handicap to your actual segment time:

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
        time_input = st.number_input("Your actual completion time for the segment (in seconds).", 60, 3600, value=st.session_state.form_time)
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
                    "Segment Time (s)": time_input, 
                    "Delta_Estimate": delta_est, 
                    "Segment": SEGMENT_URL,
                    "Date": now_brisbane
                }])
                
                df_all = load_data()
                df_all = pd.concat([df_all[~((df_all["Name"] == active_name) & (df_all["Segment"] == SEGMENT_URL))], new_entry], ignore_index=True)
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
                segment_filtered["Sort_Date"] = parsed_dates.fillna(pd.Timestamp.min)
                segment_filtered = segment_filtered.sort_values(by="Sort_Date", ascending=False)
                segment_filtered["Date"] = parsed_dates.dt.strftime("%Y-%m-%d %H:%M:%S").fillna(segment_filtered["Date"].astype(str))
            
            deduplicated_df = segment_filtered.drop_duplicates(subset=["Name"], keep="first")
            seed_df = deduplicated_df.sort_values(by="FTP (W)", ascending=True)[["Name", "FTP (W)", "Date"]]
            st.dataframe(seed_df, use_container_width=True, hide_index=True)
        else:
            st.info("No entries found for the currently active segment.")
    else:
        st.info("No data available.")

with tab_res:
    st.header("Challenge Results")
    df = load_data()
    
    if not df.empty and "Segment" in df.columns:
        segment_filtered = df[df["Segment"] == SEGMENT_URL].copy()
        
        if not segment_filtered.empty:
            if "Date" in segment_filtered.columns:
                parsed_dates = pd.to_datetime(segment_filtered["Date"], errors="coerce")
                segment_filtered["Sort_Date"] = parsed_dates.fillna(pd.Timestamp.min)
                segment_filtered = segment_filtered.sort_values(by="Sort_Date", ascending=False)
            
            deduplicated_df = segment_filtered.drop_duplicates(subset=["Name"], keep="first")
            active = deduplicated_df[(deduplicated_df["Segment Time (s)"] > 0) & (deduplicated_df["Delta_Estimate"] > 0)].copy()
            
            if not active.empty:
                avg_delta = active["Delta_Estimate"].mean()
                st.markdown(f"**Current average delta for this segment:** {int(avg_delta)} seconds.")
                
                active = active.sort_values(by=["FTP (W)", "Segment Time (s)"], ascending=[True, False]).reset_index(drop=True)
                count = len(active)
                
                base_slice = avg_delta / count
                handicaps = []
                for i in range(count):
                    if count > 1:
                        h = base_slice + (avg_delta - base_slice) * (i / (count - 1))
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
                st.info("No valid segment times or delta estimates found for this segment yet.")
        else:
            st.info("No challenge results recorded for the currently active segment.")
    else:
        st.info("No data available.")

with tab_faq:
    st.header("Frequently Asked Questions")
    faq_df = load_faq_data()
    
    if not faq_df.empty:
        for _, row in faq_df.iterrows():
            if str(row["Question"]).strip():
                with st.expander(str(row["Question"])): 
                    st.write(str(row["Answer"]))
    else:
        st.info("No FAQs available yet.")
        
    st.markdown("---")
    q = st.text_input("Submit a question:")
    
    if st.button("Submit Question"):
        if not q.strip():
            st.error("Question cannot be empty.")
        elif is_inappropriate(q):
            st.error("Keep it constructive.")
        elif not faq_df.empty and q in faq_df["Question"].values:
            st.warning("This question has already been submitted.")
        else:
            new_q = pd.DataFrame([{"Question": q, "Answer": "Response pending"}])
            faq_df = pd.concat([faq_df, new_q], ignore_index=True)
            save_faq_data(faq_df)
            st.success("Question submitted! It will appear here once reviewed.")
            st.rerun()

with tab_admin:
    if st.checkbox("Show Admin Segment Controls"):
        st.header("Admin Configuration & Submitter Tracking")
        
        with st.form("segment_config_form"):
            admin_names_list = get_existing_names()
            
            admin_col1, admin_col2 = st.columns(2)
            with admin_col1:
                selected_admin_existing = st.selectbox("Select Existing Admin Name", options=["-- Select --"] + admin_names_list)
            with admin_col2:
                typed_admin_new = st.text_input("Or Type New Admin Name", help="Type your name if you are a new admin.")
            
            new_url = st.text_input("Active Strava Segment URL", value=SEGMENT_URL)
            
            submitted = st.form_submit_button("Update Segment & Log Submitter")
            
            if submitted:
                # Safely evaluate inputs with explicit cleaning
                cleaned_typed = typed_admin_new.strip() if typed_admin_new else ""
                cleaned_selected = selected_admin_existing.strip() if selected_admin_existing and selected_admin_existing != "-- Select --" else ""
                
                admin_name = cleaned_typed if cleaned_typed else cleaned_selected

                if not admin_name:
                    st.error("Please select an existing admin name or type a new name.")
                elif not new_url.strip():
                    st.error("Please enter a valid Segment URL.")
                else:
                    if save_segment_submission(admin_name, new_url):
                        st.success(f"Segment updated and logged successfully by {admin_name}!")
                        st.rerun()
        
        # Load segment data here so it re-queries fresh data AFTER any app reruns
        segment_df = get_segment_data()
        
        st.subheader("Segment Configuration History")
        if not segment_df.empty:
            st.dataframe(segment_df.sort_values(by="Date", ascending=False).head(10), use_container_width=True, hide_index=True)
        else:
            st.write("No segment history available.")
