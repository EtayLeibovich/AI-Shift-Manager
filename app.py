import streamlit as st
import pandas as pd
from datetime import datetime
import os
import google.generativeai as genai

# ==========================================
# הגדרות מודל ה-AI (המפתח שלך כבר בפנים)
# ==========================================
API_KEY = "AIzaSyC2Cv6VDjsQllzu9MrW8LseSKPsmXXKlWs"

if API_KEY:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')

st.title("מערכת ניהול משמרות חכמה 🍔")

menu = st.sidebar.selectbox("תפריט מערכת", ["החתמת שעון (עובדים)", "צפייה בנתונים (מנהל)"])

# פונקציית עזר לבדיקת סטטוס אחרון של עובד
def get_last_status(worker_name):
    if not os.path.exists("attendance.csv"):
        return None
    with open("attendance.csv", "r", encoding="utf-8") as file:
        lines = file.readlines()
        # מחפשים מהסוף להתחלה את הפעולה האחרונה של העובד הספציפי
        for line in reversed(lines):
            parts = line.strip().split(',')
            if parts[0] == worker_name:
                return parts[2] # מחזיר "Clock-In" או "Clock-Out"
    return None

# ==========================================
# מסך החתמת שעון - עם הגנה מפני כפילויות
# ==========================================
if menu == "החתמת שעון (עובדים)":
    st.subheader("החתמת שעות עבודה")
    name = st.text_input("הכנס את שמך:").strip()
    
    if name:
        last_status = get_last_status(name)
        
        col1, col2 = st.columns(2)
        with col1:
            # כפתור כניסה יהיה פעיל רק אם העובד לא רשום או שהפעולה האחרונה הייתה יציאה
            if st.button("🟢 כניסה למשמרת"):
                if last_status == "Clock-In":
                    st.error(f"שגיאה: {name}, כבר ביצעת כניסה! עליך לבצע יציאה לפני כניסה חדשה.")
                else:
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    with open("attendance.csv", "a", encoding="utf-8") as file:
                        file.write(f"{name},{now},Clock-In\n")
                    st.success(f"כניסה נרשמה בהצלחה ב-{now}")
                    st.rerun() # מרענן את המסך כדי לעדכן את הכפתורים
                    
        with col2:
            # כפתור יציאה יהיה פעיל רק אם הפעולה האחרונה הייתה כניסה
            if st.button("🔴 יציאה ממשמרת"):
                if last_status == "Clock-In":
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    with open("attendance.csv", "a", encoding="utf-8") as file:
                        file.write(f"{name},{now},Clock-Out\n")
                    st.success(f"יציאה נרשמה בהצלחה ב-{now}")
                    st.rerun()
                else:
                    st.error(f"שגיאה: {name}, לא ניתן לבצע יציאה ללא רישום כניסה פעיל.")
    else:
        st.info("אנא הכנס שם כדי להמשיך.")

# ==========================================
# מסך מנהל (ללא שינוי בלוגיקה, רק תצוגה)
# ==========================================
elif menu == "צפייה בנתונים (מנהל)":
    st.subheader("טבלת משמרות וחישוב שעות")
    
    if os.path.exists("attendance.csv"):
        with open("attendance.csv", "r", encoding="utf-8") as file:
            df = pd.read_csv(file, names=["שם עובד", "תאריך ושעה", "פעולה"])
        
        df['תאריך ושעה'] = pd.to_datetime(df['תאריך ושעה'])
        
        shifts = []
        for worker_name, group in df.groupby("שם עובד"):
            in_time = None
            for _, row in group.iterrows():
                if row["פעולה"] == "Clock-In":
                    in_time = row["תאריך ושעה"]
                elif row["פעולה"] == "Clock-Out" and in_time is not None:
                    out_time = row["תאריך ושעה"]
                    duration = out_time - in_time
                    hours = duration.total_seconds() / 3600
                    shifts.append({
                        "שם עובד": worker_name, 
                        "כניסה": in_time.strftime("%Y-%m-%d %H:%M"), 
                        "יציאה": out_time.strftime("%Y-%m-%d %H:%M"), 
                        "סה\"כ שעות": round(hours, 2)
                    })
                    in_time = None
        
        if shifts:
            st.dataframe(pd.DataFrame(shifts), use_container_width=True)
            
        st.write("---")
        st.subheader("🤖 עוזר מנהל חכם (AI)")
        user_question = st.chat_input("שאל את המערכת על נתוני המשמרות...")
        
        if user_question:
            with st.chat_message("user"):
                st.write(user_question)
            
            with open("attendance.csv", "r", encoding="utf-8") as file:
                csv_data = file.read()
            
            prompt = f"להלן נתוני נוכחות: \n{csv_data}\n ענה על: {user_question}"
            
            with st.spinner("מנתח..."):
                try:
                    response = model.generate_content(prompt)
                    with st.chat_message("assistant"):
                        st.write(response.text)
                except Exception as e:
                    st.error(f"שגיאה: {e}")
    else:
        st.info("אין נתונים עדיין.")