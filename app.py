from datetime import date, datetime
import secrets
import smtplib
from email.mime.text import MIMEText
from google.oauth2.service_account import Credentials
import gspread
import streamlit as str_lit

# --- GOOGLE SHEETS SETUP ---
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
creds = Credentials.from_service_account_info(
    str_lit.secrets["gcp_service_account"], scopes=scope
)
client = gspread.authorize(creds)
sheet = client.open("Event_Feedback")
companies_sheet = sheet.worksheet("companies")
bookings_sheet = sheet.worksheet("bookings_sheet")
feedback_sheet = sheet.worksheet("Feedback")

# --- SESSION STATE ---
if "logged_in" not in str_lit.session_state:
  str_lit.session_state.logged_in = False
if "booking_sent" not in str_lit.session_state:
  str_lit.session_state.booking_sent = False


# --- HELPERS ---
def send_approval_email(to_email, link, company_name):
  subject = f"Your {company_name} account is approved"
  body = (
      f"Hi {company_name},\n\nYour account is approved. Click here to set your"
      f" password:\n{link}"
  )
  msg = MIMEText(body)
  msg["Subject"] = subject
  msg["From"] = str_lit.secrets["EMAIL_SENDER"]
  msg["To"] = to_email
  with smtplib.SMTP("smtp.gmail.com", 587) as server:
    server.starttls()
    server.login(
        str_lit.secrets["EMAIL_SENDER"], str_lit.secrets["EMAIL_PASSWORD"]
    )
    server.sendmail(str_lit.secrets["EMAIL_SENDER"], to_email, msg.as_string())


def notify_company_all(name, customer_email, event_details, phone):
  """Sends Email + WhatsApp notifications."""
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

    View Dashboard: {str_lit.secrets.get('APP_URL', 'your-app-url')}
    """
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = str_lit.secrets["EMAIL_SENDER"]
    msg["To"] = str_lit.secrets["ADMIN_EMAIL"]

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
      server.starttls()
      server.login(
          str_lit.secrets["EMAIL_SENDER"], str_lit.secrets["EMAIL_PASSWORD"]
      )
      server.sendmail(
          str_lit.secrets["EMAIL_SENDER"], str_lit.secrets["ADMIN_EMAIL"], msg.as_string()
      )
    success += 1
  except Exception as e:
    str_lit.error(f"Email failed: {e}")

  # 2. WHATSAPP
  try:
    import requests

    url = (
        f"https://api.ultramsg.com/{str_lit.secrets['ULTRA_INSTANCE']}/messages/chat"
    )
    payload = {
        "token": str_lit.secrets["ULTRA_TOKEN"],
        "to": str_lit.secrets["COMPANY_WHATSAPP"],
        "body": (
            f"🔔 NEW BOOKING ALERT\n\n👤 {name}\n📧 {customer_email}\n📅"
            f" {event_details}\n📞 {phone}"
        ),
    }
    requests.post(url, data=payload, timeout=5)
    success += 1
  except Exception as e:
    str_lit.error(f"WhatsApp failed: {e}")

  if success > 0:
    str_lit.toast(f"Company notified via {success} channels", icon="🚀")

  return success


# --- PAGES ---
def register_page():
  str_lit.title("Register Your Hiring Company")
  with str_lit.form("register_form"):
    name = str_lit.text_input("Company Name")
    email = str_lit.text_input("Company Login Email")
    admin_email = str_lit.text_input("Email to receive bookings")
    admin_wa = str_lit.text_input("WhatsApp to receive bookings e.g. whatsapp:+2547...")
    submitted = str_lit.form_submit_button("Submit Application")
    if submitted:
      company_id = name.lower().replace(" ", "_")
      new_row = [
          company_id,
          name,
          email,
          "",
          "",
          "pending",
          "FALSE",
          admin_email,
          admin_wa,
      ]
      companies_sheet.append_row(new_row)
      str_lit.success("Application submitted! We'll review and email you within 24hrs.")


def set_password_page(token):
  str_lit.title("Set Your Password")
  all_companies = companies_sheet.get_all_records()
  company = next((c for c in all_companies if c["temp_token"] == token), None)
  if not company:
    str_lit.error("Invalid link")
    return

  p1 = str_lit.text_input("New Password", type="password")
  if str_lit.button("Activate Account"):
    row = all_companies.index(company) + 2
    companies_sheet.update_cell(row, 4, p1)  # password
    companies_sheet.update_cell(row, 5, "")  # clear token
    companies_sheet.update_cell(row, 6, "active")  # status
    str_lit.success("Account Activated! Go to Company Login tab.")


def login_page():
  str_lit.title("Company Login")

  # ADMIN BYPASS
  if str_lit.button("🔑 Login as Admin"):
    str_lit.session_state.logged_in = True
    str_lit.session_state.company_name = "Admin"
    str_lit.session_state.is_admin = True
    str_lit.success("Logged in as Admin")
    str_lit.rerun()

  str_lit.divider()
  str_lit.subheader("Company Login")

  email = str_lit.text_input("Email")
  password = str_lit.text_input("Password", type="password")


def admin_dashboard():
  str_lit.title("Admin Dashboard")
  str_lit.subheader("Pending Applications")
  pending = [
      c
      for c in companies_sheet.get_all_records()
      if str(c.get("Status", "")).strip().lower() == "pending"
  ]

  for comp in pending:
    with str_lit.container(border=True):
      str_lit.write(f"*{comp['company_name']}* - {comp['login_email']}")
      if str_lit.button(f"Approve {comp['company_name']}", key=comp["company_id"]):
        token = secrets.token_urlsafe(16)
        row = companies_sheet.get_all_records().index(comp) + 2
        companies_sheet.update_cell(row, 5, token)  # temp_token
        companies_sheet.update_cell(row, 6, "approved")  # status
        link = f"{str_lit.secrets['APP_URL']}?set_password={token}"
        send_approval_email(comp["login_email"], link, comp["company_name"])
        str_lit.success(f"Approved! Invite sent to {comp['login_email']}")
        str_lit.rerun()

  str_lit.divider()
  str_lit.subheader("All Bookings")

  try:
    bookings = bookings_sheet.get_all_records()
    if bookings:
      str_lit.dataframe(bookings)
    else:
      str_lit.info("No bookings yet.")
  except Exception as e:
    str_lit.error(f"Bookings Sheet Error: {e}")


def company_dashboard(company_id):
  str_lit.title("Dashboard")
  my_bookings = [
      b for b in bookings_sheet.get_all_records() if b["company_id"] == company_id
  ]
  str_lit.dataframe(my_bookings)
  if str_lit.button("Logout"):
    str_lit.session_state.logged_in = False
    str_lit.rerun()


# INVENTORY LIST
inventory = {
    "Audio Equipment": ["Microphones", "Speakers", "Amplifiers", "Mixers"],
    "Visual Equipment": [
        "LED Screens",
        "Projector Screens",
        "LCD/Plasma Displays",
        "Backdrop Screens",
        "Interactive Touch Screens",
        "Mobile Screens",
    ],
    "Furniture & Setup": ["Chairs", "Tables", "Tents", "Podiums", "Stages"],
    "Decoration Materials": [
        "Drapes",
        "Flowers",
        "Balloons",
        "Banners",
        "Branding Props",
    ],
    "Catering Materials": [
        "Cutlery",
        "Crockery",
        "Serving Stations",
        "Food Storage Units",
    ],
    "Stationery & Print": ["Invitations", "Programs", "Signage", "Name Tags"],
    "Transport Vehicles": ["Vans", "Trucks", "Cars"],
    "Safety Gear": [
        "Fire Extinguishers",
        "First Aid Kits",
        "Barriers",
        "Uniforms",
    ],
    "Power Supply": ["Generators", "Extension Cables", "Backup Batteries"],
    "Technology Tools": [
        "Laptops",
        "Event Management Software",
        "Livestream Kits",
    ],
}


def customer_booking_page():
  str_lit.title("Book Equipment & Services")
  name = str_lit.text_input("Your Name", key="b_name")
  phone = str_lit.text_input("Your Phone Number", key="b_phone")
  event_date = str_lit.date_input("Event Service Date", date.today(), key="b_date")
  customer_email = str_lit.text_input("Your Email", key="b_email")
  event_location = str_lit.text_input(
      "Event Location/Venue", "e.g. Kisumu, Milimani", key="b_eloc"
  )
  dispatch_location = str_lit.text_input(
      "Where should we dispatch/deliver to?", "e.g. Tom Mboya Hall", key="b_dloc"
  )
  company = str_lit.text_input(
      "Preferred Company", "According to the service offered", key="b_comp"
  )

  str_lit.subheader("What do you want to hire?")
  selected_categories = str_lit.multiselect(
      "Select Categories", list(inventory.keys()), key="b_cat"
  )
  items_to_hire = []
  if selected_categories:
    for cat in selected_categories:
      items = str_lit.multiselect(f"{cat}", inventory[cat], key="b_" + cat)
      items_to_hire.extend(items)

  notes = str_lit.text_area("Additional Notes / Quantity needed")

  if str_lit.button(
      "Send Booking Request",
      key="b_submit",
      disabled=str_lit.session_state.booking_sent,
  ):
    str_lit.session_state.booking_sent = True

    new_row = [
        str(date.today()),
        name,
        phone,
        customer_email,
        str(event_date),
        event_location,
        dispatch_location,
        company,
        ", ".join(items_to_hire),
        notes,
    ]
    bookings_sheet.append_row(new_row)

    event_details = f"""Date: {event_date}
Location: {event_location}
Dispatch: {dispatch_location}
Company: {company}
Items Booked: {', '.join(items_to_hire)}
Notes: {notes}"""

    notify_company_all(name, customer_email, event_details, phone)

    str_lit.success("✅ Booking request sent! We will call you soon")
    str_lit.balloons()
    str_lit.session_state.booking_sent = False
    str_lit.rerun()


def feedback_page():
  str_lit.title("Rate Your Past Event")
  f_name = str_lit.text_input("Your Name", key="f_name")
  f_phone = str_lit.text_input("Your Phone Number", key="f_phone")
  f_event_date = str_lit.date_input("Date of your Event", key="f_date")

  str_lit.subheader("What did you hire from us?")
  f_selected_categories = str_lit.multiselect(
      "Select Categories", list(inventory.keys()), key="f_cat"
  )
  items_used = []
  if f_selected_categories:
    for cat in f_selected_categories:
      items = str_lit.multiselect(f"{cat}", inventory[cat], key="f_" + cat)
      items_used.extend(items)

  ratings = {}
  if items_used:
    str_lit.subheader("Rate the items you received")
    for item in items_used:
      ratings[item] = str_lit.slider(f"Rate {item}", 1, 5, 3, key="rate_" + item)

  staff = str_lit.slider("How was our staff?", 1, 5, 5)
  delivery = str_lit.slider("How was delivery & setup?", 1, 5, 5)
  comments = str_lit.text_area("Any comments or suggestions?")

  str_lit.subheader("Refer a Friend ")
  refer = str_lit.radio("Would you refer us?", ["Yes", "No", "Maybe"])
  ref_name, ref_phone = "", ""
  if refer == "Yes":
    ref_name = str_lit.text_input("Friend's Name")
    ref_phone = str_lit.text_input("Friend's Phone Number")

  if str_lit.button("Submit Feedback"):
    new_row = [
        str(date.today()),
        f_name,
        f_phone,
        str(f_event_date),
        ", ".join(items_used),
        str(ratings),
        staff,
        delivery,
        comments,
        refer,
        ref_name,
        ref_phone,
    ]
    feedback_sheet.append_row(new_row)
    str_lit.success("Thank you! Your feedback has been saved.")


# --- ROUTER ---
query_params = str_lit.query_params
if "set_password" in query_params:
  set_password_page(query_params["set_password"])
elif str_lit.session_state.get("logged_in"):
  if str_lit.session_state.get("is_admin"):
    admin_dashboard()
  else:
    company_dashboard(str_lit.session_state.company_id)
else:
  tab1, tab2, tab3, tab4 = str_lit.tabs(
      ["Make a Booking", "Submit Feedback", "Company Register", "Company Login"]
  )
  with tab1:
    customer_booking_page()
  with tab2:
    feedback_page()
  with tab3:
    register_page()
  with tab4:
    login_page()
