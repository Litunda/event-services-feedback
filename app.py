import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date
import secrets
import smtplib
from email.mime.text import MIMEText

# --- 1. CONNECT TO GOOGLE SHEETS ONCE ---
@st.cache_resource
def connect_to_gsheet():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        sh = client.open("Event_Feedback")  # YOUR SHEET NAME
        companies_sheet = sh.worksheet("companies")
        bookings_sheet = sh.worksheet("bookings_sheet") # MUST MATCH YOUR TAB NAME
        return companies_sheet, bookings_sheet
    except Exception as e:
        st.error(f"Google Connection Failed: {e}")
        st.stop()

companies_sheet, bookings_sheet = connect_to_gsheet()

# --- 2. SESSION STATE ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.is_admin = False

# --- 3. HELPERS ---
def send_approval_email(to_email, link, company_name):
    try:
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
    except Exception as e:
        st.error(f"Email failed: {e}")

# --- 4. PAGES ---
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
            new_row = [company_id, name, email, "", "", "Pending", "FALSE", admin_email, admin_wa]
            companies_sheet.append_row(new_row)
            st.success("Application submitted! We'll review and email you within 24hrs.")

def admin_dashboard():
    st.title("🔑 Admin Dashboard")
    st.subheader("Pending Applications")
    pending = [c for c in companies_sheet.get_all_records() if str(c.get('Status','')).strip().lower() == 'pending']
    
    for comp in pending:
        with st.container(border=True):
            st.write(f"**{comp['CompanyName']}** - {comp['LoginEmail']}")
            if st.button(f"Approve {comp['CompanyName']}", key=comp['CompanyID']):
                token = secrets.token_urlsafe(16)
                row = companies_sheet.get_all_records().index(comp) + 2
                companies_sheet.update_cell(row, 5, token) # temp_token
                companies_sheet.update_cell(row, 6, "Approved") # status
                link = f"{st.secrets['APP_URL']}?set_password={token}"
                send_approval_email(comp['LoginEmail'], link, comp['CompanyName'])
                st.success(f"Approved! Invite sent")
                st.rerun()

    st.divider()
    st.subheader("All Bookings + Feedback")
    try:
        bookings = bookings_sheet.get_all_records()
        if bookings:
            st.dataframe(bookings)
            for i, b in enumerate(bookings):
                with st.expander(f"{b.get('ClientName')} - {b.get('Service')}"):
                    new_fb = st.text_area("Edit Feedback", b.get('Feedback',''), key=f"fb{i}")
                    if st.button("Save Feedback", key=f"btn{i}"):
                        bookings_sheet.update_cell(i+2, 8, new_fb) # Col 8 = Feedback
                        st.success("Updated!")
                        st.rerun()
        else:
            st.info("No bookings yet.")
    except Exception as e:
        st.error(f"Bookings Error: {e}")

def company_dashboard(company_id):
    st.title(f"Company Dashboard")
    my_bookings = [b for b in bookings_sheet.get_all_records() if b['CompanyID'] == company_id]
    st.dataframe(my_bookings)
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

def customer_booking_page():
    st.title("Book a Service")
    all_companies = companies_sheet.get_all_records()
    active_companies = [c for c in all_companies if c.get('Status', '').lower() == 'active']

    if not active_companies:
        st.warning("No companies registered yet.")
        return

    selected_name = st.selectbox("Select Company", [c['CompanyName'] for c in active_companies])
    selected_company = next(c for c in active_companies if c['CompanyName'] == selected_name)

    with st.form("booking_form"):
        name = st.text_input("Your Name")
        event_date = st.date_input("Event Date")
        venue = st.text_input("Venue")
        service = st.selectbox("Item to Book", ["DJ", "Decor", "Catering", "MC", "Photography", "Sound"])
        feedback = st.text_area("Additional Notes")
        submitted = st.form_submit_button("Send Booking Request")
        
        if submitted:
            new_row = [
                str(datetime.now()),
                selected_company['CompanyName'],
                name, 
                str(event_date),
                venue,
                service,
                "Pending",
                feedback
            ]
            bookings_sheet.append_row(new_row)
            st.success(f"Booking request sent to {selected_company['CompanyName']}!")

def login_page():
    st.title("Company Login")
    if st.button("🔑 Login as Admin"):
        st.session_state.logged_in = True
        st.session_state.is_admin = True
        st.rerun()
    st.divider()
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

# --- 5. ROUTER ---
query_params = st.query_params
if st.session_state.get('logged_in'):
    if st.session_state.get('is_admin'):
        admin_dashboard()
    else:
        company_dashboard(st.session_state.company_id)
else:
    tab1, tab2, tab3 = st.tabs(["Book Service", "Company Register", "Company Login"])
    with tab1: customer_booking_page()
    with tab2: register_page()
    with tab3: login_page()
