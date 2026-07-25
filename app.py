import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import date
import json
import smtplib
from email.mine.text import MIMEText
# --- LOAD SECRETS ---
EMAIL_SENDER = st.secrets["EMAIL_SENDER"]
EMAIL_PASSWORD = st.secrets["EMAIL_PASSWORD"] 
ADMIN_EMAIL = st.secrets["ADMIN_EMAIL"]

ULTRA_INSTANCE = st.secrets["ULTRA_INSTANCE"]
ULTRA_TOKEN = st.secrets["ULTRA_TOKEN"]
COMPANY_WHATSAPP = st.secrets["COMPANY_WHATSAPP"]

AT_USERNAME = st.secrets["AT_USERNAME"]
AT_API_KEY = st.secrets["AT_API_KEY"]
COMPANY_PHONE = st.secrets["COMPANY_PHONE"] # "+2547XXXXXXXX"

# Initialize Africa's Talking
africastalking.initialize(AT_USERNAME, AT_API_KEY)
sms = africastalking.SMS
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

        sh = client.open("Event_Feedback")  # CHANGE THIS TO YOUR EXACT SHEET NAME
        booking_sheet = sh.worksheet("Bookings")
        feedback_sheet = sh.worksheet("Feedback")
        return booking_sheet, feedback_sheet
        
    except Exception as e:
        st.error(f"Google Connection Failed: {e}")
        st.stop() # stops the app so we see the error

booking_sheet, feedback_sheet = connect_to_gsheet()

booking_sheet, feedback_sheet = connect_to_gsheet()

def notify_company_all(name, customer_email, event, phone=""):
    """Sends Email + WhatsApp + SMS. Returns success count"""
    success = 0
    
    # 1. EMAIL
    try:
        subject = f"🔔 New Booking: {event}"
        body = f"""New Booking Received!

Name: {name}
Email: {customer_email} 
Phone: {phone}
Event: {event}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}

View Dashboard: {st.secrets.get('APP_URL', 'your-app-url')}"""
        
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = EMAIL_SENDER
        msg['To'] = ADMIN_EMAIL
        
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, ADMIN_EMAIL, msg.as_string())
        success += 1
    except Exception as e:
        st.error(f"Email failed: {e}")

    # 2. WHATSAPP
    try:
        url = f"https://api.ultramsg.com/{ULTRA_INSTANCE}/messages/chat"
        payload = {
            "token": ULTRA_TOKEN,
            "to": COMPANY_WHATSAPP,
            "body": f"🔔 *NEW BOOKING ALERT*\n\n👤 {name}\n📧 {customer_email}\n📅 {event}\n📞 {phone}"
        }
        requests.post(url, data=payload, timeout=5)
        success += 1
    except Exception as e:
        st.error(f"WhatsApp failed: {e}")

    # 3. SMS
    try:
        message = f"NEW BOOKING: {name} for {event}. Phone: {phone}. Check dashboard."
        recipients = [COMPANY_PHONE]
        response = sms.send(message, recipients)
        if response['SMSMessageData']['Recipients'][0]['status'] == 'Success':
            success += 1
    except Exception as e:
        st.error(f"SMS failed: {e}")
    
    if success > 0:
        st.toast(f"✅ Company notified via {success}/3 channels", icon="🚀")
    
    return success
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
      if st.button("Send Booking Request"):
    new_row = [
        str(date.today()), name, phone, str(event_date),
        ", ".join(items_to_hire), notes
    ]
    booking_sheet.append_row(new_row)  # LINE 150 - SAVES TO SHEETS
    
    # ⬇️⬇️⬇️ ADD THIS LINE HERE ⬇️⬇️⬇️
    notify_company_all(name, f"customer@email.com", str(event_date), phone)
    
    st.success("✅ Booking request sent! We will call you soon")  # LINE 151
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
