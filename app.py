import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date
import secrets
import smtplib
from email.mime.text import MIMEText
from twilio.rest import Client

# --- GOOGLE SHEETS SETUP ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
client = gspread.authorize(creds)
sheet = client.open("Event_Feedback") 
companies_sheet = sheet.worksheet("companies")
bookings_sheet = sheet.worksheet("bookings")

# --- SESSION STATE ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# --- HELPERS ---
def send_approval_email(to_email, link, company_name):
    subject = f"Your {company_name} account is approved"
    body = f"Hi {company_name},\n\nYour account is approved. Click here to set your password:\n{link}"
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = st.secrets["EMAIL_SENDER"]
    msg['To'] = to_email
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(st.secrets["EMAIL_SENDER"], st.secrets["EMAIL_PASSWORD"])
        server.sendmail(st.secrets["EMAIL_SENDER"], to_email, msg.as_string())

# --- PAGES ---

def register_page():
    st.title("Register Your Hiring Company")
    with st.form("register_form"):
        name = st.text_input("Company Name")
        email = st.text_input("Company Login Email")
        admin_email = st.text_input("Email to receive bookings")
        admin_wa = st.text_input("WhatsApp to receive bookings e.g. whatsapp:+2547...")
        submitted = st.form_submit_button("Submit Application")
        if submitted:
            company_id = name.lower().replace(" ", "_")
            new_row = [company_id, name, email, "", "", "pending", "FALSE", admin_email, admin_wa]
            companies_sheet.append_row(new_row)
            st.success("Application submitted! We'll review and email you within 24hrs.")

def set_password_page(token):
    st.title("Set Your Password")
    all_companies = companies_sheet.get_all_records()
    company = next((c for c in all_companies if c['temp_token'] == token), None)
    if not company: st.error("Invalid link"); return
    
    p1 = st.text_input("New Password", type="password")
    if st.button("Activate Account"):
        row = all_companies.index(company) + 2
        companies_sheet.update_cell(row, 4, p1) # password
        companies_sheet.update_cell(row, 5, "") # clear token
        companies_sheet.update_cell(row, 6, "active") # status
        st.success("Account Activated! Go to Company Login tab.")

def login_page():
    st.title("Company Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        comp = next((c for c in companies_sheet.get_all_records() if c['login_email'] == email), None)
        if comp and comp['password'] == password and comp['status'] == "active":
            st.session_state.logged_in = True
            st.session_state.company_id = comp['company_id']
            st.session_state.is_admin = comp['is_admin'] == "TRUE"
            st.rerun()
        else: st.error("Wrong credentials or account not active")

def admin_dashboard():
    st.title("Admin Dashboard")
    st.subheader("Pending Applications")
    pending = [c for c in companies_sheet.get_all_records() if c['status'] == "pending"]
    
    for comp in pending:
        with st.container(border=True):
            st.write(f"**{comp['company_name']}** - {comp['login_email']}")
            if st.button(f"Approve {comp['company_name']}", key=comp['company_id']):
                token = secrets.token_urlsafe(16)
                row = companies_sheet.get_all_records().index(comp) + 2
                companies_sheet.update_cell(row, 5, token) # temp_token
                companies_sheet.update_cell(row, 6, "approved") # status
                link = f"{st.secrets['APP_URL']}?set_password={token}"
                send_approval_email(comp['login_email'], link, comp['company_name'])
                st.success(f"Approved! Invite sent to {comp['login_email']}")
                st.rerun()

    st.divider()
    st.subheader("All Bookings")
    st.dataframe(bookings_sheet.get_all_records())

def company_dashboard(company_id):
    st.title(f"Dashboard")
    my_bookings = [b for b in bookings_sheet.get_all_records() if b['company_id'] == company_id]
    st.dataframe(my_bookings)
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

def customer_booking_page():
    st.title("Book a Service")
    if not active_companies:
    st.warning("No companies registered yet. Please register a company first.")
    st.stop()
    active_companies = [c for c in companies_sheet.get_all_records() if c['status'] == "active"]
    selected_name = st.selectbox("Select Company", [c['company_name'] for c in active_companies])
    selected_company = next(c for c in active_companies if c['company_name'] == selected_name)
    
    with st.form("booking_form"):
        name = st.text_input("Your Name")
        phone = st.text_input("Your Phone")
        email = st.text_input("Your Email")
        event_date = st.date_input("Event Date")
        event_loc = st.text_input("Event Location")
        items = st.text_area("Items to Hire")
        if st.form_submit_button("Send Booking Request"):
            new_row = [selected_company['company_id'], str(date.today()), name, phone, email, str(event_date), event_loc, "", items, "", "Pending"]
            bookings_sheet.append_row(new_row)
            st.success("Booking sent!")

# --- ROUTER ---
query_params = st.query_params
if "set_password" in query_params:
    set_password_page(query_params["set_password"])
elif st.session_state.get('logged_in'):
    if st.session_state.get('is_admin'):
        admin_dashboard()
    else:
        company_dashboard(st.session_state.company_id)
else:
    tab1, tab2, tab3 = st.tabs(["Book Service", "Company Register", "Company Login"])
    with tab1: customer_booking_page()
    with tab2: register_page()
    with tab3: login_page()

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
st.title("Event Services Portal")

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

def notify_company_all(name, customer_email, event, phone):
    """Sends Email + WhatsApp + SMS. Returns success count"""
    success = 0
    
    # 1. EMAIL
    try:
        subject = f"New Booking: {name}"
        body = f"""New Booking Received!
        Name: {name}
        Email: {customer_email}
        Phone: {phone}
        Details:
        {event_details}
Submitted At: {datetime.now().strftime('%Y-%m-%d %H:%M')}

View Dashboard: {st.secrets.get('APP_URL', 'your-app-url')}
"""
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
        st.toast(f"Company notified via {success}/3 channels", icon="🚀")
    
    return success
# INVENTORY LIST
inventory = {
    "Audio Equipment": ["Microphones", "Speakers", "Amplifiers", "Mixers"],
    "Visual Equipment": ["LED Screens", "Projector Screens", "LCD/Plasma Displays", "Backdrop Screens", "Interactive Touch Screens", "Mobile Screens"],
    "Furniture & Setup": ["Chairs", "Tables", "Tents", "Podiums", "Stages"],
    "Decoration Materials": ["Drapes", "Flowers", "Balloons", "Banners", "Branding Props"],
    "Catering Materials": ["Cutlery", "Crockery", "Serving Stations", "Food Storage Units"],
    "Stationery & Print": ["Invitations", "Programs", "Signage", "Name Tags"],
    "Transport Vehicles": ["Vans", "Trucks", "Cars"],
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
    event_date = st.date_input("Event Service Date", date.today(), key="b_date")
    customer_email = st.text_input("Your Email", key="b_email")
    event_location = st.text_input("Event Location/Venue", "e.g. Kisumu, Milimani", key="b_eloc")
    dispatch_location = st.text_input("Where should we dispatch/deliver to?", "e.g. Tom Mboya Hall", key="b_dloc")
    company = st.text_input("Preferred Company", "According to the service offered", key="b_comp")

    st.subheader("What do you want to hire?")
    selected_categories = st.multiselect("Select Categories", list(inventory.keys()), key="b_cat")
    items_to_hire = []
    if selected_categories:
        for cat in selected_categories:
            items = st.multiselect(f"{cat}", inventory[cat], key="b_"+cat)
            items_to_hire.extend(items)
    
    notes = st.text_area("Additional Notes / Quantity needed")


if 'booking_sent' not in st.session_state:
    st.session_state.booking_sent = False

if st.button("Send Booking Request", key="b_submit", disabled=st.session_state.booking_sent):
    
    st.session_state.booking_sent = True # LOCK IT
    
    # 1. SAVE TO SHEET
    new_row = [
        str(date.today()), name, phone, customer_email, str(event_date), 
        event_location, dispatch_location, company, ", ".join(items_to_hire), notes
    ]
    booking_sheet.append_row(new_row)

    # 2. BUILD MESSAGE
    event_details = f"""Date: {event_date}
Location: {event_location}
Dispatch: {dispatch_location}
Company: {company}
Items Booked: {', '.join(items_to_hire)}
Notes: {notes}"""
    
    # 3. SEND ONLY ONCE
    notify_company_all(name, customer_email, event_details, phone)

    st.success("✅ Booking request sent! We will call you soon")
    st.balloons()
    
    st.session_state.booking_sent = False # UNLOCK for next booking
    st.rerun() # Refresh the form
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
    
    st.subheader("Refer a Friend ")
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
        st.success("Thank you! Your feedback has been saved.")
