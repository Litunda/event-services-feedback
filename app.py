from datetime import date, datetime
import secrets
import smtplib
from email.mime.text import MIMEText
from google.oauth2.service_account import Credentials
import gspread
import streamlit as st

# --- GOOGLE SHEETS SETUP ---
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"], scopes=scope
)
client = gspread.authorize(creds)
sheet = client.open("Event_Feedback")
companies_sheet = sheet.worksheet("companies")
bookings_sheet = sheet.worksheet("bookings_sheet")
feedback_sheet = sheet.worksheet("Feedback")

# --- SESSION STATE ---
if "logged_in" not in st.session_state:
  st.session_state.logged_in = False
if "booking_sent" not in st.session_state:
  st.session_state.booking_sent = False


# --- HELPERS ---
def send_approval_email(to_email, link, company_name):
  subject = f"Your {company_name} account is approved"
  body = (
      f"Hi {company_name},\n\nYour account is approved. Click here to set your"
      f" password:\n{link}"
  )
  msg = MIMEText(body)
  msg["Subject"] = subject
  msg["From"] = st.secrets["EMAIL_SENDER"]
  msg["To"] = to_email
  with smtplib.SMTP("smtp.gmail.com", 587) as server:
    server.starttls()
    server.login(st.secrets["EMAIL_SENDER"], st.secrets["EMAIL_PASSWORD"])
    server.sendmail(st.secrets["EMAIL_SENDER"], to_email, msg.as_string())


def notify_company(company_email, company_wa, name, customer_email, event_details, phone):
  """Sends Email and WhatsApp notification to the specific hired company."""
  # 1. EMAIL
  try:
    subject = f"New Booking Request: {name}"
    body = f"""Hello,\n\nYou have received a new booking request through the platform.\n\nClient Name: {name}\nEmail: {customer_email}\nPhone: {phone}\n\nDetails:\n{event_details}\n\nLog in to your dashboard to manage this booking."""
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = st.secrets["EMAIL_SENDER"]
    msg["To"] = company_email

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
      server.starttls()
      server.login(st.secrets["EMAIL_SENDER"], st.secrets["EMAIL_PASSWORD"])
      server.sendmail(st.secrets["EMAIL_SENDER"], company_email, msg.as_string())
  except Exception as e:
    st.error(f"Email failed: {e}")

  # 2. WHATSAPP (If WhatsApp number provided)
  if company_wa:
    try:
      import requests

      url = f"https://api.ultramsg.com/{st.secrets['ULTRA_INSTANCE']}/messages/chat"
      payload = {
          "token": st.secrets["ULTRA_TOKEN"],
          "to": company_wa,
          "body": f"🔔 NEW BOOKING REQUEST\n\n👤 Client: {name}\n📞 Phone: {phone}\n📧 Email: {customer_email}\n\nCheck your dashboard for details.",
      }
      requests.post(url, data=payload, timeout=5)
    except Exception as e:
      st.error(f"WhatsApp notification failed: {e}")


# --- PAGES ---
def register_page():
  st.title("Register Your Hiring Company")
  st.info("Create your company account and set your secure password immediately.")
  
  with st.form("register_form"):
    name = st.text_input("Company Name")
    email = st.text_input("Company Login Email")
    password = st.text_input("Choose Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")
    admin_email = st.text_input("Email to receive booking notifications")
    admin_wa = st.text_input("WhatsApp to receive bookings (e.g., +2547...)")
    submitted = st.form_submit_button("Register & Activate Account")
    if submitted:
       if not name or not email or not password:
            st.warning("Please fill out Company Name, Login Email, and Password.")
       elif password != confirm_password:
            st.error("Passwords do not match. Please check and try again.")
       elif len(password) < 6:
            st.warning("Password must be at least 6 characters long for security.")
    else:
            company_id = name.lower().replace(" ", "_")
# Checks if company ID or email already exists to prevent duplicates
existing_companies = companies_sheet.get_all_records()
email_exists = any(str(c.get('login_email', '')).strip().lower() == email.strip().lower() for c in existing_companies)
 if email_exists:
    st.error("An account with this login email already exists.")
 else:
# Automatically saves as 'active' with the secure password provided
new_row = [company_id, name, email, password, "", "active", "FALSE", admin_email, admin_wa]
companies_sheet.append_row(new_row)
          st.success("Registration successful! You can now go to the 'Company Login' tab and sign in securely.")
def set_password_page(token):
  st.title("Set Your Password")
  all_companies = companies_sheet.get_all_records()
  company = next((c for c in all_companies if str(c.get('temp_token', '')) == token), None)
  
  if not company:
    st.error("Invalid or expired link.")
    return

  p1 = st.text_input("New Password", type="password")
  if st.button("Activate Account"):
    if len(p1) < 6:
      st.warning("Password must be at least 6 characters long.")
    else:
      row_idx = all_companies.index(company) + 2
      companies_sheet.update_cell(row_idx, 4, p1)  # password column
      companies_sheet.update_cell(row_idx, 5, "")  # clear temp_token
      companies_sheet.update_cell(row_idx, 6, "active")  # status column
      st.success("Account Activated! You can now go to the Company Login tab.")


def login_page():
  st.title("Company Portal Login")

  # ADMIN BYPASS
  if st.button("🔑 Login as Super Admin"):
    st.session_state.logged_in = True
    st.session_state.company_name = "Admin"
    st.session_state.company_id = "admin"
    st.session_state.is_admin = True
    st.success("Logged in as Admin")
    st.rerun()

  st.divider()
  st.subheader("Company Partner Login")

  email = st.text_input("Login Email")
  password = st.text_input("Password", type="password")

  if st.button("Login"):
    all_companies = companies_sheet.get_all_records()
 # --- DEBUG HELPER (Remove after fixing) ---
    with st.expander("🔍 Click here to view sheet debugging data"):
      st.write("Fetched Companies from Sheet:", all_companies)
    # ------------------------------------------

    matched_company = next(
        (c for c in all_companies if str(c.get('login_email', '')).strip().lower() == email.strip().lower() and str(c.get('password', '')) == password),
        None
    )
    if matched_company:
      if str(matched_company.get('Status')).lower() != "active":
        st.warning("Your account is pending review or inactive.")
      else:
        st.session_state.logged_in = True
        st.session_state.company_name = matched_company.get('company_name')
        st.session_state.company_id = matched_company.get('company_id')
        st.session_state.is_admin = False
        st.success(f"Welcome back, {matched_company.get('company_name')}!")
        st.rerun()
    else:
      st.error("Invalid email or password.")


def admin_dashboard():
  st.title("Super Admin Dashboard")
  st.subheader("Pending Company Applications")
  
  all_companies = companies_sheet.get_all_records()
  pending = [c for c in all_companies if str(c.get('Status', '')).strip().lower() == 'pending']

  if not pending:
    st.info("No pending applications.")

  for comp in pending:
    with st.container(border=True):
      st.write(f"*{comp.get('company_name')}* - {comp.get('login_email')}")
      if st.button(f"Approve {comp.get('company_name')}", key=comp.get('company_id')):
        token = secrets.token_urlsafe(16)
        row_idx = all_companies.index(comp) + 2
        companies_sheet.update_cell(row_idx, 5, token)  # temp_token
        companies_sheet.update_cell(row_idx, 6, "active")  # status update
          
        app_url = st.secrets.get('APP_URL', 'https://share.streamlit.io')
        link = f"{app_url}?set_password={token}"
          
        send_approval_email(comp.get('login_email'), link, comp.get('company_name'))
        st.success(f"Approved! Invite sent to {comp.get('login_email')}")
        st.rerun()

  st.divider()
  st.subheader("All Platform Bookings")
  try:
    bookings = bookings_sheet.get_all_records()
    if bookings:
      st.dataframe(bookings)
    else:
      st.info("No bookings registered on the platform yet.")
  except Exception as e:
    st.error(f"Bookings Sheet Error: {e}")
    
  if st.button("Logout Admin"):
    st.session_state.logged_in = False
    st.rerun()


def company_dashboard(company_id, company_name):
  st.title(f"{company_name} Dashboard")
  
  st.subheader("Assigned Bookings")
  try:
    all_bookings = bookings_sheet.get_all_records()
    my_bookings = [b for b in all_bookings if str(b.get('company_id')) == str(company_id)]
    
    if my_bookings:
      st.dataframe(my_bookings)
    else:
      st.info("No booking requests assigned to your company yet.")
  except Exception as e:
    st.error(f"Error loading bookings: {e}")

  if st.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()


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


def customer_booking_page():
  st.title("Book Equipment & Services")
  st.info("No account required! Simply select a company, fill out your event details, and submit.")
  
  all_companies = companies_sheet.get_all_records()
  active_companies = [c for c in all_companies if str(c.get('Status', '')).lower() == 'active']

  if not active_companies:
    st.warning("No active hiring companies are available right now. Please check back later.")
    return

  company_options = {c['company_name']: c for c in active_companies}
  selected_company_name = st.selectbox("Select Preferred Hiring Company", list(company_options.keys()))
  selected_company_obj = company_options[selected_company_name]

  name = st.text_input("Your Name", key="b_name")
  phone = st.text_input("Your Phone Number", key="b_phone")
  event_date = st.date_input("Event Service Date", date.today(), key="b_date")
  customer_email = st.text_input("Your Email", key="b_email")
  event_location = st.text_input("Event Location/Venue", "e.g. Kisumu, Milimani", key="b_eloc")
  dispatch_location = st.text_input("Where should we dispatch/deliver to?", "e.g. Tom Mboya Hall", key="b_dloc")

  st.subheader("What do you want to hire?")
  selected_categories = st.multiselect("Select Categories", list(inventory.keys()), key="b_cat")
  items_to_hire = []
  if selected_categories:
    for cat in selected_categories:
      items = st.multiselect(f"{cat}", inventory[cat], key="b_" + cat)
      items_to_hire.extend(items)

  notes = st.text_area("Additional Notes / Quantity needed")

  if st.button("Send Booking Request", key="b_submit", disabled=st.session_state.booking_sent):
    if not name or not phone:
      st.warning("Please provide your name and phone number.")
    else:
      st.session_state.booking_sent = True

      new_row = [
          selected_company_obj['company_id'],
          str(date.today()),
          name,
          phone,
          customer_email,
          str(event_date),
          event_location,
          dispatch_location,
          selected_company_name,
          ", ".join(items_to_hire),
          notes,
          "Pending"
      ]
      bookings_sheet.append_row(new_row)

      event_details = f"""Date: {event_date}
Location: {event_location}
Dispatch: {dispatch_location}
Items Booked: {', '.join(items_to_hire)}
Notes: {notes}"""

      notify_company(
          selected_company_obj.get('admin_email'),
          selected_company_obj.get('admin_wa'),
          name,
          customer_email,
          event_details,
          phone
      )

      st.success("✅ Booking request sent successfully to the company!")
      st.balloons()
      st.session_state.booking_sent = False


def feedback_page():
  st.title("Rate Your Past Event")
  f_name = st.text_input("Your Name", key="f_name")
  f_phone = st.text_input("Your Phone Number", key="f_phone")
  f_event_date = st.date_input("Date of your Event", key="f_date")

  st.subheader("What did you hire?")
  f_selected_categories = st.multiselect("Select Categories", list(inventory.keys()), key="f_cat")
  items_used = []
  if f_selected_categories:
    for cat in f_selected_categories:
      items = st.multiselect(f"{cat}", inventory[cat], key="f_" + cat)
      items_used.extend(items)

  ratings = {}
  if items_used:
    st.subheader("Rate the items you received")
    for item in items_used:
      ratings[item] = st.slider(f"Rate {item}", 1, 5, 3, key="rate_" + item)

  staff = st.slider("How was our staff?", 1, 5, 5)
  delivery = st.slider("How was delivery & setup?", 1, 5, 5)
  comments = st.text_area("Any comments or suggestions?")

  if st.button("Submit Feedback"):
    new_row = [
        str(date.today()),
        f_name,
        f_phone,
        str(f_event_date),
        ", ".join(items_used),
        str(ratings),
        staff,
        delivery,
        comments
    ]
    feedback_sheet.append_row(new_row)
    st.success("Thank you! Your feedback has been saved.")


# --- ROUTER ---
query_params = st.query_params

if "set_password" in query_params:
  set_password_page(query_params["set_password"])
elif st.session_state.get('logged_in'):
  # Show Dashboard if logged in as Admin or Company Partner
  if st.session_state.get('is_admin'):
    admin_dashboard()
  else:
    company_dashboard(st.session_state.company_id, st.session_state.company_name)
else:
  # Public tabs for customers and new company partners wanting to join/login
  tab1, tab2, tab3, tab4 = st.tabs(["Make a Booking", "Submit Feedback", "Register Company", "Company Login"])
  with tab1:
    customer_booking_page()
  with tab2:
    feedback_page()
  with tab3:
    register_page()
  with tab4:
    login_page()
