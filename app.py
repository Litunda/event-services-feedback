import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import date
import json
st.title("🎉 Event Services Portal")

# 1. CONNECT TO GOOGLE SHEETS
def connect_to_gsheet():
    try:
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=scope
        )
        client = gspread.authorize(creds)

        sh = client.open("Event Feedback")  # CHANGE THIS TO YOUR EXACT SHEET NAME
        booking_sheet = sh.worksheet("Bookings")
        feedback_sheet = sh.worksheet("Feedback")
        return booking_sheet, feedback_sheet
        
    except Exception as e:
        st.error(f"Google Connection Failed: {e}")
        st.stop() # stops the app so we see the error

booking_sheet, feedback_sheet = connect_to_gsheet()

# INVENTORY LIST
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

tab1, tab2 = st.tabs(["1. Make a Booking", "2. Submit Feedback"])

# ============= TAB 1: BOOKING =============
with tab1:
    st.header("Book Equipment & Services")
    name = st.text_input("Your Name", key="b_name")
    phone = st.text_input("Your Phone Number", key="b_phone")
    event_date = st.date_input("Event Date", date.today(), key="b_date")
    event_location = st.text_input("📍 Event Location/Venue", "e.g. Kisumu, Milimani", key="b_eloc")
    dispatch_location = st.text_input("🚚 Where should we dispatch/deliver to?", "e.g. Tom Mboya Hall", key="b_dloc")
    company = st.text_input("Preferred Company", "Litunda Events", key="b_comp")

    st.subheader("What do you want to hire?")
    selected_categories = st.multiselect("Select Categories", list(inventory.keys()), key="b_cat")
    items_to_hire = []
    if selected_categories:
        for cat in selected_categories:
            items = st.multiselect(f"{cat}", inventory[cat], key="b_"+cat)
            items_to_hire.extend(items)
    
    notes = st.text_area("Additional Notes / Quantity needed")

    if st.button("Send Booking Request"):
        new_row = [
            str(date.today()), name, phone, str(event_date), event_location, dispatch_location, company,
            ", ".join(items_to_hire), notes
        ]
        booking_sheet.append_row(new_row)
        st.success("✅ Booking request sent! We will call you with a quote within 2 hours.")
        st.balloons()

# ============= TAB 2: FEEDBACK =============
with tab2:
    st.header("Rate Your Past Event")
    f_name = st.text_input("Your Name", key="f_name")
    f_phone = st.text_input("Your Phone Number", key="f_phone")
    f_event_date = st.date_input("Date of your Event", key="f_date")
    
    st.subheader("What did you hire from us?")
    f_selected_categories = st.multiselect("Select Categories", list(inventory.keys()), key="f_cat")
    items_used = []
    if f_selected_categories:
        for cat in f_selected_categories:
            items = st.multiselect(f"{cat}", inventory[cat], key="f_"+cat)
            items_used.extend(items)
    
    ratings = {}
    if items_used:
        st.subheader("Rate the items you received")
        for item in items_used:
            ratings[item] = st.slider(f"Rate {item}", 1, 5, 3, key="rate_"+item)
    
    staff = st.slider("How was our staff?", 1, 5, 5)
    delivery = st.slider("How was delivery & setup?", 1, 5, 5)
    comments = st.text_area("Any comments or suggestions?")
    
    st.subheader("Refer a Friend 🤝")
    refer = st.radio("Would you refer us?", ["Yes", "No", "Maybe"])
    ref_name, ref_phone = "", ""
    if refer == "Yes":
        ref_name = st.text_input("Friend's Name")
        ref_phone = st.text_input("Friend's Phone Number")

    if st.button("Submit Feedback"):
        new_row = [
            str(date.today()), f_name, f_phone, str(f_event_date),
            ", ".join(items_used), str(ratings), staff, delivery, comments,
            refer, ref_name, ref_phone
        ]
        feedback_sheet.append_row(new_row)
        st.success("✅ Thank you! Your feedback has been saved.")
