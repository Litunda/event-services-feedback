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
      f"Hi {company_name},\n\nYour account has been approved by the Super Admin. Click here to set your password and activate your account:\n{link}"
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
    body = f"""Hello,\n\nYou have received a new booking request through the platform.\n\nClient Name: {name}\nEmail: {customer_email}\nPhone: {phone}\n\nDetails:\n{event_details}\n\nLog in to your dashboard to review and approve this booking."""
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
          "body": f"NEW BOOKING REQUEST\n\n Client: {name}\n Phone: {phone}\n Email: {customer_email}\n\nCheck your dashboard to approve details.",
      }
      requests.post(url, data=payload, timeout=5)
    except Exception as e:
      st.error(f"WhatsApp notification failed: {e}")


# --- PAGES ---
def register_page():
  st.title("Register Your Hiring Company")
  st.info("Register your company. Accounts require Super Admin approval before you can access the platform.")
  
  with st.form("register_form"):
    name = st.text_input("Company Name")
    login_email = st.text_input("Company Login Email") 
    password = st.text_input("Choose Password (temporary placeholder)", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")
    admin_email = st.text_input("Email to receive booking notifications")
    admin_wa = st.text_input("WhatsApp to receive bookings (e.g., +2547...)")
    submitted = st.form_submit_button("Register Company")
    
    if submitted:
      if not name or not login_email or not password:
        st.warning("Please fill out Company Name, Login Email, and Password.")
      elif password != confirm_password:
        st.error("Passwords do not match. Please check and try again.")
      elif len(password) < 6:
        st.warning("Password must be at least 6 characters long for security.")
      else:
        company_id = name.lower().replace(" ", "_")
        
        existing_companies = companies_sheet.get_all_records()
        email_exists = any(
            str(c.get('login_email', '')).strip().lower() == login_email.strip().lower() 
            for c in existing_companies
        )
        
        if email_exists:
          st.error("An account with this login email already exists.")
        else:
          new_row = [company_id, name, login_email, password, "", "pending", "FALSE", admin_email, admin_wa]
          companies_sheet.append_row(new_row)
          st.success("Registration successful! Your account is pending Super Admin review and approval.")

def set_password_page(token):
  st.title("Activate & Set Your Password")
  all_companies = companies_sheet.get_all_records()
  company = next((c for c in all_companies if str(c.get('temp_token', '')) == token), None)
  
  if not company:
    st.error("Invalid or expired activation link.")
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
      st.success("Account Activated! You can now go to the Portal Login tab.")


def login_page():
  st.title("Portal Login")
  st.info("Enter your credentials below to access your account.")

  email = st.text_input("Email")
  password = st.text_input("Password", type="password")

  if st.button("Login"):
    # 1. CHECK IF SUPER ADMIN
    admin_email = st.secrets.get("ADMIN_EMAIL", "admin@admin.com")
    admin_pass = st.secrets.get("ADMIN_PASSWORD", "admin123")

    if email.strip().lower() == admin_email.strip().lower() and password.strip() == admin_pass:
      st.session_state.logged_in = True
      st.session_state.company_name = "Admin"
      st.session_state.company_id = "admin"
      st.session_state.is_admin = True
      st.success("Logged in as Super Admin Successfully!")
      st.rerun()
    else:
      # 2. CHECK IF COMPANY PARTNER
      all_companies = companies_sheet.get_all_records()
      matched_company = None
      for c in all_companies:
        sheet_email = str(c.get('login_email', '')).strip().lower()
        sheet_pass = str(c.get('password') or c.get('Password', '')).strip()
        
        if sheet_email == email.strip().lower() and sheet_pass == password.strip():
          matched_company = c
          break

      if matched_company:
        status = str(matched_company.get('Status') or matched_company.get('status') or '').strip().lower()
        if status != "active":
          st.warning("Your account is pending Super Admin review. Please wait for approval.")
        else:
          st.session_state.logged_in = True
          st.session_state.company_name = matched_company.get('company_name') or matched_company.get('CompanyName')
          st.session_state.company_id = matched_company.get('company_id') or matched_company.get('Company_ID')
          st.session_state.is_admin = False
          st.success(f"Welcome back, {st.session_state.company_name}!")
          st.rerun()
      else:
        st.error("Invalid email or password.")


def admin_dashboard():
  st.title("Super Admin Dashboard")
  st.subheader("Company Account Approvals")
  st.info("Approve companies that want to utilize the platform. You do not approve bookings.")
  
  all_companies = companies_sheet.get_all_records()
  pending = [c for c in all_companies if str(c.get('Status', '')).strip().lower() == 'pending']

  if not pending:
    st.info("No pending company applications awaiting approval.")

  for comp in pending:
    with st.container(border=True):
      st.write(f"**{comp.get('company_name')}** - {comp.get('login_email')}")
      if st.button(f"Approve Company & Send Activation Link", key=comp.get('company_id')):
        token = secrets.token_urlsafe(16)
        row_idx = all_companies.index(comp) + 2
        companies_sheet.update_cell(row_idx, 5, token)  # temp_token
          
        app_url = st.secrets.get('APP_URL', 'https://share.streamlit.io')
        link = f"{app_url}?set_password={token}"
          
        send_approval_email(comp.get('login_email'), link, comp.get('company_name'))
        st.success(f"Company approved! Activation email sent to {comp.get('login_email')}")
        st.rerun()

  st.divider()
  st.subheader("Platform Bookings Overview (Read-Only)")
  st.info("As Super Admin, you can view all bookings across the platform for overview purposes. Companies handle their own booking approvals.")
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
  st.subheader("Review and Approve Assigned Bookings")
  
  try:
    all_bookings = bookings_sheet.get_all_records()
    my_bookings = [b for b in all_bookings if str(b.get('company_id')) == str(company_id)]
    
    if my_bookings:
      for idx, booking in enumerate(my_bookings):
        with st.container(border=True):
          st.write(f"**Client Name:** {booking.get('name')}")
          st.write(f"**Phone:** {booking.get('phone')} | **Email:** {booking.get('customer_email')}")
          st.write(f"**Event Date:** {booking.get('event_date')} | **Location:** {booking.get('event_location')}")
          st.write(f"**Items Hired:** {booking.get('items_to_hire')}")
          st.write(f"**Current Status:** `{booking.get('status', 'Pending')}`")

          new_status = st.selectbox(
              "Update / Approve Booking Status", 
              ["Pending", "Confirmed / Approved", "Completed", "Cancelled"], 
              index=0, 
              key=f"status_{company_id}_{idx}"
          )
          
          if st.button("Save Status Update", key=f"save_{company_id}_{idx}"):
            row_idx = all_bookings.index(booking) + 2
            bookings_sheet.update_cell(row_idx, 12, new_status)  # column 12 is status
            st.success("Booking status updated successfully!")
            st.rerun()
    else:
      st.info("No booking requests assigned to your company yet.")
  except Exception as e:
    st.error(f"Error loading bookings: {e}")

  st.divider()
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

  try:
    has_email_sender = bool(st.secrets.get("EMAIL_SENDER"))
  except Exception:
    has_email_sender = False

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

      if has_email_sender:
        notify_company(
            selected_company_obj.get('admin_email'),
            selected_company_obj.get('admin_wa'),
            name,
            customer_email,
            event_details,
            phone
        )
      else:
        st.warning("Booking saved to sheet, but email notification skipped because `EMAIL_SENDER` is not configured in Streamlit secrets yet.")

      st.success("Booking request sent successfully to the company!")
      st.balloons()
      st.session_state.booking_sent = False

def customer_dashboard_page():
  st.title("My Customer Portal")
  st.info("Enter your phone number or email to track your bookings and view your history.")

  lookup_val = st.text_input("Enter your Phone Number or Email").strip().lower()

  if lookup_val:
    try:
      all_bookings = bookings_sheet.get_all_records()
      customer_bookings = [
          b for b in all_bookings 
          if lookup_val in str(b.get('phone', '')).lower() or lookup_val in str(b.get('customer_email', '')).lower()
      ]

      st.subheader("Your Booking Requests")
      if customer_bookings:
        st.dataframe(customer_bookings)
      else:
        st.info("No bookings found matching that phone number or email.")
    except Exception as e:
      st.error(f"Error loading bookings: {e}")

    try:
      all_feedback = feedback_sheet.get_all_records()
      customer_feedback = [
          f for f in all_feedback 
          if lookup_val in str(f.get('f_phone', '')).lower() or lookup_val in str(f.get('f_name', '')).lower()
      ]

      if customer_feedback:
        st.subheader("Your Past Feedback Submissions")
        st.dataframe(customer_feedback)
    except Exception as e:
      pass


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
  if st.session_state.get('is_admin'):
    admin_dashboard()
  else:
    company_dashboard(st.session_state.company_id, st.session_state.company_name)
else:
  tab1, tab2, tab3, tab4, tab5 = st.tabs([
      "Make a Booking", 
      "Track My Bookings", 
      "Submit Feedback", 
      "Register Company", 
      "Portal Login"
  ])
  with tab1:
    customer_booking_page()
  with tab2:
    customer_dashboard_page()
  with tab3:
    feedback_page()
  with tab4:
    register_page()
  with tab5:
    login_page()
