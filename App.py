import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import gspread
from google.oauth2.service_account import Credentials

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

# --- SPLIT HEADER WITH FEMALE & MALE CYCLISTS ---
st.markdown("<h1 style='text-align: center;'>🚴‍♀️ 🚴‍♂️ Bulimba Roadies</h1>", unsafe_allow_html=True)
st.markdown("<h2 style='text-align: center;'>Monthly Challenge</h2>", unsafe_allow_html=True)
st.markdown(f"**The active challenge segment is:** [{SEGMENT_URL}]({SEGMENT_URL})")

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
        
    existing_names = get_existing_names()
    
    with st.form("entry_form", clear_on_submit=True):
        st.markdown("### Rider Details")
        
        col1, col2 = st.columns(2)
        with col1:
            selected_existing = st.selectbox("Select Existing Rider", options=["-- Select --"] + existing_names)
        with col2:
            typed_new_name = st.text_input("Or Type New Name Here", help="Type your name if you are a new participant.")
        
        ftp = st.number_input("Current FTP (Watts)", 0, 500, 100, help="Sustained 20-minute power output.")
        time = st.number_input("Your actual completion time for the segment (in seconds).", 60, 3600, 400)
        delta_est = st.number_input("Your Estimated Delta (in seconds) between first and last place.", 10, 1200, 300)
        
        if st.form_submit_button("Submit Entry"):
            if typed_new_name.strip():
                clean_name = typed_new_name.strip()
            elif selected_existing != "-- Select --":
                clean_name = selected_existing.strip()
            else:
                clean_name = ""
                
            if not clean_name: 
                st.error("Please select an existing rider or type a new name!")
            else:
                df = load_data()
                brisbane_tz = ZoneInfo("Australia/Brisbane")
                now_brisbane = datetime.now(brisbane_tz).strftime("%Y-%m-%d %H:%M:%S")
                
                new_entry = pd.DataFrame([{
                    "Name": clean_name, 
                    "FTP (W)": ftp, 
                    "Segment Time (s)": time, 
                    "Delta_Estimate": delta_est, 
                    "Segment": SEGMENT_URL,
                    "Date": now_brisbane
                }])
                
                df = pd.concat([df[df["Name"] != clean_name], new_entry], ignore_index=True)
                save_data(df)
                
                st.success(f"Entry saved for {clean_name}!")
                st.rerun()

    st.markdown("---")
    with st.expander("🗑️ Need to delete your entry?"):
        with st.form("delete_form"):
            existing_names_for_del = get_existing_names()
            target_name = st.selectbox("Select your name to delete", options=["-- Select --"] + existing_names_for_del)
            confirm_delete = st.checkbox("I confirm I want to permanently remove my entry.")
            
            if st.form_submit_button("Delete My Record"):
                if target_name == "-- Select --":
                    st.error("Please select your name.")
                elif not confirm_delete:
                    st.error("Please check the confirmation box.")
                else:
                    df = load_data()
                    if target_name in df["Name"].values:
                        df = df[df["Name"] != target_name]
                        save_data(df)
                        st.success(f"Successfully deleted records for {target_name}.")
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
                segment_filtered["Date"] = pd.to_datetime(segment_filtered["Date"], errors="coerce")
                segment_filtered = segment_filtered.sort_values(by="Date", ascending=False)
            
            deduplicated_df = segment_filtered.drop_duplicates(subset=["Name"], keep="first")
            seed_df = deduplicated_df.sort_values(by="FTP (W)", ascending=True)[["Name", "FTP (W)", "Date"]]
            
            # Format date timestamp nicely for display
            seed_df["Date"] = seed_df["Date"].dt.strftime("%Y-%m-%d %H:%M:%S")
            
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
                segment_filtered["Date"] = pd.to_datetime(segment_filtered["Date"], errors="coerce")
                segment_filtered = segment_filtered.sort_values(by="Date", ascending=False)
            
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
        segment_df = get_segment_data()
        
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
                if typed_admin_new.strip():
                    admin_name = typed_admin_new.strip()
                elif selected_admin_existing != "-- Select --":
                    admin_name = selected_admin_existing.strip()
                else:
                    admin_name = ""

                if not admin_name:
                    st.error("Please select an existing admin name or type a new name.")
                elif not new_url.strip():
                    st.error("Please enter a valid Segment URL.")
                else:
                    if save_segment_submission(admin_name, new_url):
                        st.success(f"Segment updated and logged successfully by {admin_name}!")
                        st.rerun()
        
        st.subheader("Segment Configuration History")
        if not segment_df.empty:
            st.dataframe(segment_df.sort_values(by="Date", ascending=False).head(10), use_container_width=True, hide_index=True)
        else:
            st.write("No segment history available.")
