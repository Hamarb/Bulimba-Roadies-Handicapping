# --- SIDEBAR: SUBMISSION FORM ---
st.sidebar.header("🚴‍♂️ Submit Your Time")
with st.sidebar.form("submission_form"):
    name = st.text_input("Name")
    ftp = st.number_input("FTP (Watts)", min_value=0, max_value=500, value=250)
    time = st.number_input("Segment Time (seconds)", min_value=60, max_value=3600, value=400)
    
    # NEW: Mandatory Delta Estimate field
    delta_estimate = st.number_input("Your Estimated Delta (seconds)", min_value=10, max_value=1200, value=300, help="What do you think the difference is between the fastest and slowest rider today?")
    
    submitted = st.form_submit_button("Submit / Update Record")

    if submitted:
        if not name:
            st.error("Please enter your name!")
        else:
            df = load_data()
            # If your CSV doesn't have the estimate column yet, add it
            if "Delta_Estimate" not in df.columns:
                df["Delta_Estimate"] = 0
                
            if name in df["Name"].values:
                df.loc[df["Name"] == name, ["FTP (W)", "Segment Time (s)", "Delta_Estimate"]] = [ftp, time, delta_estimate]
            else:
                new_row = pd.DataFrame([{"Name": name, "FTP (W)": ftp, "Segment Time (s)": time, "Delta_Estimate": delta_estimate}])
                df = pd.concat([df, new_row], ignore_index=True)
            
            df.to_csv(DATA_FILE, index=False)
            st.success(f"Updated record for {name}!")
Updated compute_handicaps in App.py:
Python
def compute_handicaps(df):
    # Use the average of all user-submitted estimates
    delta = df["Delta_Estimate"].mean()
    
    # Sort from fastest to slowest
    df = df.sort_values(by="Segment Time (s)").reset_index(drop=True)
    count = len(df)
    
    # Calculate handicaps using the community delta
    handicaps = [round(delta * (1 - (i / (count - 1)))) if count > 1 else 0 for i in range(count)]
    
    df["Handicap_Sec"] = handicaps
    df["Adjusted_Sec"] = df["Segment Time (s)"] + df["Handicap_Sec"]
    
    df = df.sort_values(by="Adjusted_Sec").reset_index(drop=True)
    df["Place"] = df.index + 1
    return df
