import streamlit as st
from datetime import date

st.title("🎉 Event Services Feedback")
st.write("Help us serve you better!")

# 1. BASIC INFO
name = st.text_input("Your Name")
phone = st.text_input("Your Phone Number")
event_date = st.date_input("Event Date", date.today())
place = st.text_input("📍 Location/Place of Event", "e.g. Kisumu, Milimani")
company = st.text_input("Which company served you?", "Litunda Events")

# 2. PREDICT WHAT THEY ORDERED BASED ON PACKAGE
st.subheader("1. What type of event/package was this?")
package = st.selectbox(
    "Select your package",
    ["Wedding Full Package", "Birthday Package", "Corporate Event", 
     "Tents Only", "Catering Only", "Custom/Mixed"]
)

# PREDICTION LOGIC
package_items = {
    "Wedding Full Package": ["Tents", "Chairs & Tables", "Decoration", "Catering", "Sound System", "Lighting"],
    "Birthday Package": ["Tents", "Chairs & Tables", "Decoration", "Sound System"],
    "Corporate Event": ["Tents", "Chairs & Tables", "Sound System", "Lighting"],
    "Tents Only": ["Tents", "Chairs & Tables"],
    "Catering Only": ["Catering"],
    "Custom/Mixed": []
}

predicted_items = package_items[package]

# If Custom, let them pick manually
if package == "Custom/Mixed":
    ordered_items = st.multiselect("Select services you ordered", 
        ["Tents", "Chairs & Tables", "Decoration", "Catering", "Sound System", "A-Frames", "MC/DJ", "Lighting"])
else:
    st.success(f"We predicted you ordered: {', '.join(predicted_items)}")
    ordered_items = predicted_items
    edit = st.checkbox("Add/Remove items?")
    if edit:
        ordered_items = st.multiselect("Edit your services", 
            ["Tents", "Chairs & Tables", "Decoration", "Catering", "Sound System", "A-Frames", "MC/DJ", "Lighting"],
            default=predicted_items)

# 3. RATE ONLY PREDICTED ITEMS
if ordered_items:
    st.subheader("2. Rate the services you received")
    ratings = {}
    for service in ordered_items:
        ratings[service] = st.slider(f"Rate our {service}", 1, 5, 3)
    
    staff = st.slider("How was our staff?", 1, 5, 5)
    comments = st.text_area("Any comments or suggestions?")
    
    # 4. REFERRAL SECTION - THIS IS THE MONEY MAKER
    st.subheader("3. Refer a Friend 🤝")
    refer = st.radio("Would you refer us to a friend?", ["Yes", "No", "Maybe"])
    
    referral_name = ""
    referral_phone = ""
    if refer == "Yes":
        st.write("Thank you! Please give us your friend's contact")
        referral_name = st.text_input("Friend's Name")
        referral_phone = st.text_input("Friend's Phone Number")
        st.info("We will contact them with a special discount from you")
    
    if st.button("Submit Feedback"):
        st.success("Thank you! Your feedback has been submitted.")
        st.balloons()
        st.write("### Summary:")
        st.write(f"**Location:** {place}")
        st.write(f"**Services Rated:** {ratings}")
        if refer == "Yes":
            st.write(f"**Referral:** {referral_name} - {referral_phone}")
else:
    st.info("👆 Please select a package first")

        
