# 🚴‍♂️ Bulimba Roadies Monthly Challenge & Dynamic Handicapping App

Welcome to the official repository for the **Bulimba Roadies Monthly Challenge**! This is a Streamlit-powered web application designed to automate club segment challenges, dynamic handicap calculations, rider seeding, and Facebook summary generation with minimal friction.

---

## ✨ Key Features

* **Dynamic Handicapping System:** Automatically calculates weekly handicaps based on who shows up, participant FTPs, and a community-voted estimated Delta.
* **Strava Integration:** Dynamically fetches live segment details (Name, URL, and route metrics) directly via the Strava API.
* **Participant Data History:** Allows returning riders to pre-load their previous stats instantly while keeping historical records cleanly archived.
* **Admin Segment Controls:** Lets admins update the active monthly challenge segment, logging a full configuration audit trail.
* **Facebook Post Generator:** Instantly formats the final weekly results table and summary into clean markdown ready for social media.

---

## 📊 How the Dynamic Handicap Works

1. **Delta Estimate:** Participants submit a personal estimate of the time gap (Delta) between the fastest and slowest rider. The app averages these to establish the official Group Estimated Delta.
2. **Seeding:** Riders are sorted from lowest to highest based on their submitted 20-minute FTP (Watts).
3. **Inclusive Handicap:** Handicaps scale smoothly across the field. The highest FTP receives the maximum handicap penalty, while every other rider receives a proportional head start, ensuring an inclusive and level playing field.
4. **Adjusted Time:** 
   $$\text{Adjusted Time} = \text{Actual Segment Time} + \text{Handicap}$$
   The fastest adjusted time takes the win!

---

## 🛠️ Repository Structure

```text
Bulimba-Roadies-Handicapping/
│
├── App.py                # Main Streamlit application user interface & logic
├── requirements.txt      # Project Python dependencies
└── README.md             # Project documentation
