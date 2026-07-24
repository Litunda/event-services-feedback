import streamlit as st
from textblob import TextBlob
import pandas as pd
import sqlite3

# Database
conn = sqlite3.connect('event_services_feedback.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS feedback 
             (customer_name TEXT, event_date TEXT, 
              tents INTEGER, decor INTEGER, sound INTEGER, aframes INTEGER, catering INTEGER,
              comment_improve TEXT, comment_adjust TEXT, sentiment TEXT)''')
conn.commit()

st.title("Event Services Feedback")
st.write("Thank you for hiring us! Help us improve.")

# FORM
col1, col2 = st.columns(2)
with col1:
    customer_name = st.text_input("Customer Name")
with col2:
    event_date = st.date_input("Event Date")

st.subheader("Rate Our Services 1-5 stars")
col1, col2, col3 = st.columns(3)
with col1:
    tents = st.slider("Tents & Seating", 1, 5)
    sound = st.slider("Sound System", 1, 5)
with col2:
    decor = st.slider("Decoration", 1, 5)
    aframes = st.slider("A-Frames / Signage", 1, 5)
with col3:
    catering = st.slider("Outside Catering", 1, 5)

st.markdown("---")
st.subheader("Your Feedback")
comment_improve = st.text_area("1. What should we IMPROVE for next time?")
comment_adjust = st.text_area("2. What should we ADJUST or do differently?")

if st.button("Submit Feedback"):
    if customer_name and (comment_improve or comment_adjust):
        # Check sentiment from both comments
        all_comments = comment_improve + " " + comment_adjust
        blob = TextBlob(all_comments)
        sentiment_score = blob.sentiment.polarity
        
        if sentiment_score > 0.1: sentiment = "Positive"
        elif sentiment_score < -0.1: sentiment = "Negative"
        else: sentiment = "Neutral"
            
        c.execute("INSERT INTO feedback VALUES (?,?,?,?,?,?,?,?,?,?)", 
                  (customer_name, str(event_date), tents, decor, sound, aframes, catering,
                   comment_improve, comment_adjust, sentiment))
        conn.commit()
        st.success(f"Thank you {customer_name}! Feedback saved.")
    else:
        st.warning("Please fill Customer Name and at least 1 feedback comment")

st.markdown("---")
st.header("Management Dashboard")

df = pd.read_sql("SELECT * FROM feedback", conn)

if not df.empty:
    st.metric("Total Feedback", len(df))
    
    st.subheader("Average Service Ratings")
    avg_ratings = df[['tents','decor','sound','aframes','catering']].mean().round(2)
    st.bar_chart(avg_ratings)
    
    st.subheader("Sentiment")
    st.bar_chart(df['sentiment'].value_counts())
    
    st.subheader("Key Feedback to Act On")
    st.write("**IMPROVE:**")
    for cmt in df['comment_improve'].dropna().tolist()[:5]:
        st.write(f"- {cmt}")
    st.write("**ADJUST:**")
    for cmt in df['comment_adjust'].dropna().tolist()[:5]:
        st.write(f"- {cmt}")
        
    st.subheader("All Submissions")
    st.dataframe(df)
else:
    st.info("No feedback yet.")

conn.close()
        
