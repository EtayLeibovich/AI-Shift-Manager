import streamlit as st
import pandas as pd
from datetime import datetime, timedelta  # הוספנו את timedelta כדי לטפל באזורי זמן
import os
import google.generativeai as genai

# ==========================================
# 1. הגדרות ועיצוב (UI/UX)
# ==========================================
st.set_page_config(page_title="AI Operational Manager", page_icon="🚀", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; font-weight: bold; height: 50px; }
    .status-card { background-color: #f8f9fa; border-radius: 10px; padding: 20px; border: 1px solid #dee2e6; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. ניהול משאבים וניקוי נתונים
# ==========================================
FILE_PATH = "attendance.csv"

def load_data():
    if not os.path.exists(FILE_PATH):
        return pd.DataFrame(columns=["שם עובד", "כניסה", "יציאה", "סהכ שעות"])
    with open(FILE_PATH, 'r', encoding='utf-8') as file:
        df = pd.read_csv(file)
    return df

def save_data(df):
    """שמירה בטוחה עם ולידציה למניעת מינוסים ושורות ריקות"""
    # 1. ניקוי שורות ריקות (NaT/None) שגורמות לקריסת הגרפים
    df = df.dropna(subset=['שם עובד', 'כניסה'])
    df = df[df['שם עובד'].astype(str).str.strip() != '']
    
    # 2. הגנה מפני שעות שליליות - אם סה"כ שעות קטן מ-0, נהפוך אותו ל-0
    if 'סהכ שעות' in df.columns:
        df['סהכ שעות'] = df['סהכ שעות'].apply(lambda x: x if (pd.notnull(x) and x >= 0) else 0)
    
    # 3. שמירה פיזית לקובץ (Resource Management)
    with open(FILE_PATH, 'w', encoding='utf-8', newline='') as file:
        df.to_csv(file, index=False)

# ==========================================
# 3. הגדרות AI
# ==========================================
API_KEY = st.secrets.get("GEMINI_API_KEY", "") 
if API_KEY:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-pro')

# ==========================================
# 4. ממשק המערכת
# ==========================================
st.title("AI Operational Shift Manager 🚀")

menu = st.sidebar.radio("ניווט", ["⏱️ החתמת שעון", "📊 פאנל ניהול ו-BI"])

if menu == "⏱️ החתמת שעון":
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.subheader("כניסה/יציאה מהירה")
        worker_name_raw = st.text_input("שם עובד:", placeholder="הקלד שם מלא")
        
        if worker_name_raw:
            worker_name = worker_name_raw.strip() # ניקוי רווחים למניעת כפילויות
            df = load_data()
            
            # בדיקה האם העובד כבר במשמרת (יציאה ריקה)
            active_shift = df[(df["שם עובד"].astype(str).str.strip() == worker_name) & (df["יציאה"].isna())]
            
            # ---> התיקון הקריטי: חישוב שעה מדויק לישראל, גם כשהשרת בענן! <---
            now = (datetime.utcnow() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")
            
            if active_shift.empty:
                if st.button("🟢 כניסה למשמרת", type="primary"):
                    new_row = pd.DataFrame([{"שם עובד": worker_name, "כניסה": now, "יציאה": None, "סהכ שעות": None}])
                    df = pd.concat([df, new_row], ignore_index=True)
                    save_data(df)
                    st.success(f"משמרת החלה ב-{now}")
                    st.rerun()
            else:
                st.warning(f"הנך במשמרת מאז {active_shift.iloc[0]['כניסה']}. לא ניתן להיכנס שוב.")
                if st.button("🔴 יציאה ממשמרת"):
                    idx = active_shift.index[-1]
                    df.at[idx, "יציאה"] = now
                    t1 = datetime.strptime(df.at[idx, "כניסה"], "%Y-%m-%d %H:%M")
                    t2 = datetime.strptime(now, "%Y-%m-%d %H:%M")
                    hours = round((t2 - t1).total_seconds() / 3600, 2)
                    df.at[idx, "סהכ שעות"] = hours
                    save_data(df)
                    st.balloons()
                    st.success(f"משמרת הסתיימה. סה\"כ: {hours} שעות")
                    st.rerun()

elif menu == "📊 פאנל ניהול ו-BI":
    pwd = st.sidebar.text_input("סיסמה:", type="password")
    if pwd == "1234":
        df = load_data()
        
        if not df.empty:
            df['תאריך'] = pd.to_datetime(df['כניסה'], errors='coerce').dt.date

        # --- מדדים מהירים ---
        st.subheader("מדדי פעילות (Real-time)")
        active_workers_df = df[df["יציאה"].isna()] if not df.empty else pd.DataFrame()
        active_count = len(active_workers_df)
        total_hours = df["סהכ שעות"].sum() if not df.empty else 0
        
        c1, c2, c3 = st.columns(3)
        c1.metric("עובדים כעת", active_count)
        c2.metric("סה\"כ שעות שנרשמו", f"{total_hours:.1f}")
        c3.metric("משמרות חריגות (>9ש')", len(df[df["סהכ שעות"] > 9]) if not df.empty else 0)

        # --- הפיצ'ר החדש: כפתורי שחרור מהיר למנהל ---
        st.markdown("---")
        st.subheader("⚡ עובדים פעילים (סגירת משמרת בלחיצת כפתור)")
        if active_count > 0:
            st.write("לחץ על כפתור ה'הוצאה' ליד שם העובד כדי לסגור לו משמרת עם השעה הנוכחית.")
            for idx, row in active_workers_df.iterrows():
                col_name, col_btn = st.columns([3, 1])
                with col_name:
                    st.markdown(f"**{row['שם עובד']}** (נכנס ב: {row['כניסה']})")
                with col_btn:
                    if st.button(f"🔴 הוצא עכשיו", key=f"btn_{idx}"):
                        # ---> התיקון הקריטי גם בכפתור המנהל! <---
                        now_str = (datetime.utcnow() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")
                        df.at[idx, "יציאה"] = now_str
                        t1 = datetime.strptime(df.at[idx, "כניסה"], "%Y-%m-%d %H:%M")
                        t2 = datetime.strptime(now_str, "%Y-%m-%d %H:%M")
                        df.at[idx, "סהכ שעות"] = round((t2 - t1).total_seconds() / 3600, 2)
                        save_data(df)
                        st.success(f"המשמרת נסגרה בהצלחה!")
                        st.rerun()
        else:
            st.info("אין עובדים במשמרת כרגע.")

        # --- סידור וסינון לפי ימים ---
        st.markdown("---")
        st.subheader("📅 סיכום יומי וגרף עומסים")
        if not df.empty and not df['תאריך'].dropna().empty:
            available_days = sorted(df['תאריך'].dropna().unique(), reverse=True)
            selected_day = st.selectbox("בחר יום לצפייה:", available_days)
            daily_df = df[df['תאריך'] == selected_day]
            st.dataframe(daily_df[['שם עובד', 'כניסה', 'יציאה', 'סהכ שעות']], use_container_width=True)
            
            st.write("**מגמת עומס שעות שבועית:**")
            hours_per_day = df.groupby('תאריך')['סהכ שעות'].sum().reset_index()
            st.line_chart(data=hours_per_day, x='תאריך', y='סהכ שעות')

        # --- עריכה וניהול משאבים (הטבלה נעולה לזמנים!) ---
        st.markdown("---")
        st.subheader("📝 מחיקת שורות וייצוא (ללא עריכת זמנים)")
        st.warning("כדי למנוע טעויות, לא ניתן להקליד שעות ידנית. למחיקת כפילויות: סמן את השורה משמאל ולחץ על פח האשפה (Delete).")
        
        edited = st.data_editor(
            df, 
            num_rows="dynamic", 
            use_container_width=True,
            disabled=["כניסה", "יציאה", "סהכ שעות", "תאריך"] # חוסם לחלוטין הקלדה ידנית של שעות!
        )
        if st.button("💾 שמור מחיקות / שינויי שמות"):
            save_data(edited)
            st.success("הנתונים נשמרו בהצלחה.")
            st.rerun()
            
        csv_data = edited.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 הורד דוח לרואה חשבון", csv_data, "shifts.csv", "text/csv")

        # --- עוזר AI ---
        with st.expander("🤖 עוזר ניהול AI"):
            q = st.text_input("שאל על נתוני העבודה (למשל: מי עבד הכי הרבה השבוע?)")
            if q and API_KEY:
                with st.spinner("מנתח..."):
                    try:
                        res = model.generate_content(f"נתוני משמרות:\n{edited.to_string()}\nשאלה: {q}")
                        st.info(res.text)
                    except Exception as e:
                        st.error(f"השגיאה האמיתית מגוגל: {e}")