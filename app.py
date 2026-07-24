import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import date
import pandas as pd

st.title("🎉 Event Services Feedback")
st.write("Help us serve you better!")

# 1. CONNECT TO GOOGLE SHEETS
def connect_to_gsheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open("Event_Feedback").sheet1
    return sheet

# 2. BASIC INFO
name = st.text_input("Your Name")
phone = st.text_input("Your Phone Number")
event_date = st.date_input("Event Date", date.today())
place = st.text_input("📍 Location/Place of Event", "e.g. Kisumu, Milimani")
company = st.text_input("Which company served you?", "Litunda Events")

# 3. FULL INVENTORY CATEGORIES
st.subheader("1. What did you hire from us?")
inventory = {
    "Audio Equipment": ["Microphones", "Speakers", "Amplifiers", "Mixers"],
    "Visual Equipment": ["LED Screens", "Projector Screens", "LCD/Plasma Displays", "Backdrop Screens", "Interactive Touch Screens", "Mobile Screens"],
    "Furniture & Setup": ["Chairs", "Tables", "Tents", "Podiums", "Stages"],
    "Decoration Materials": ["Drapes", "Flowers", "Balloons", "Banners", "Branding Props"],
    "Catering Materials": ["Cutlery", "Crockery", "Serving Stations", "Food Storage Units"],
    "Stationery & Print": ["Invitations", "Programs", "Signage", "Name Tags"],
    "Transport Vehicles": ["Vans", "Trucks", "Buses"],
    "Safety Gear": ["Fire Extinguishers", "First Aid Kits", "Barriers", "Uniforms"],
    "Power Supply": ["Generators", "Extension Cables", "Backup Batteries"],
    "Technology Tools": ["Laptops", "Event Management Software", "Livestream Kits"]
}

selected_categories = st.multiselect("Select Categories you used", list(inventory.keys()))

ordered_items = []
if selected_categories:
    st.write("### Select specific items:")
    for cat in selected_categories:
        items = st.multiselect(f"{cat}", inventory[cat], key=cat)
        ordered_items.extend(items)

# 4. RATE + SAVE
if ordered_items:
    st.subheader("2. Rate the items you received")
    ratings = {}
    for item in ordered_items:
        ratings[item] = st.slider(f"Rate {item}", 1, 5, 3, key=item)

    staff = st.slider("How was our staff?", 1, 5, 5)
    delivery = st.slider("How was delivery & setup?", 1, 5, 5)
    comments = st.text_area("Any comments or suggestions?")

    # 5. REFERRAL SECTION
    st.subheader("3. Refer a Friend 🤝")
    refer = st.radio("Would you refer us to a friend?", ["Yes", "No", "Maybe"])
    referral_name = ""
    referral_phone = ""
    if refer == "Yes":
        referral_name = st.text_input("Friend's Name")
        referral_phone = st.text_input("Friend's Phone Number")

    if st.button("Submit Feedback"):
        try:
            sheet = connect_to_gsheet()
            new_row = [
                str(date.today()), name, phone, str(event_date), place, company,
                ", ".join(ordered_items), str(ratings), staff, delivery, comments,
                refer, referral_name, referral_phone
            ]
            sheet.append_row(new_row)
            st.success("✅ Thank you! Your feedback has been saved.")
            st.balloons()
        except Exception as e:
            st.error(f"Error saving: {e}")
else:
    st.info("👆 Please select at least 1 category first")

        
