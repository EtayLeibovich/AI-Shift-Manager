import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
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
    .login-box { max-width: 400px; margin: 0 auto; padding: 30px; border: 1px solid #ddd; border-radius: 10px; background-color: #f9f9f9; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. ניהול משאבים (נוכחות + רשימת מורשים)
# הקפדה יתרה על הקצאות וסגירת קבצים עם with
# ==========================================
FILE_PATH = "attendance.csv"
WORKERS_PATH = "workers.csv"

def load_data():
    if not os.path.exists(FILE_PATH):
        return pd.DataFrame(columns=["שם עובד", "כניסה", "יציאה", "סהכ שעות"])
    with open(FILE_PATH, 'r', encoding='utf-8') as file:
        return pd.read_csv(file)

def save_data(df):
    df = df.dropna(subset=['שם עובד', 'כניסה'])
    df = df[df['שם עובד'].astype(str).str.strip() != '']
    if 'סהכ שעות' in df.columns:
        df['סהכ שעות'] = df['סהכ שעות'].apply(lambda x: x if (pd.notnull(x) and x >= 0) else 0)
    with open(FILE_PATH, 'w', encoding='utf-8', newline='') as file:
        df.to_csv(file, index=False)

def load_workers():
    if not os.path.exists(WORKERS_PATH):
        df = pd.DataFrame([{"שם עובד": "איתי"}, {"שם עובד": "אורלי"}])
        save_workers(df)
        return df
    with open(WORKERS_PATH, 'r', encoding='utf-8') as file:
        return pd.read_csv(file)

def save_workers(df):
    df = df.dropna(subset=['שם עובד'])
    df = df[df['שם עובד'].astype(str).str.strip() != '']
    with open(WORKERS_PATH, 'w', encoding='utf-8', newline='') as file:
        df.to_csv(file, index=False)

# ==========================================
# 3. אתחול משתני מערכת (Session State)
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.user_name = ""

# ==========================================
# 4. מסך התחברות (Login Gateway)
# ==========================================
if not st.session_state.logged_in:
    st.markdown("<div style='text-align: center; margin-bottom: 20px;'><h1>🔐 כניסה למערכת שעות</h1></div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        login_type = st.radio("בחר סוג התחברות:", ["עובד", "מנהל"], horizontal=True)
        
        if login_type == "עובד":
            emp_name = st.text_input("שם עובד / תעודת זהות:", placeholder="הקלד שם מדויק...")
            if st.button("🚪 היכנס כעובד", type="primary"):
                if emp_name.strip():
                    workers_df = load_workers()
                    allowed_workers = workers_df['שם עובד'].astype(str).str.strip().tolist()
                    
                    if emp_name.strip() in allowed_workers:
                        st.session_state.logged_in = True
                        st.session_state.role = "worker"
                        st.session_state.user_name = emp_name.strip()
                        st.rerun()
                    else:
                        st.error("❌ הגישה נדחתה: שמך אינו מופיע ברשימת העובדים המורשים. פנה למנהל.")
                else:
                    st.error("חובה להזין מזהה עובד!")
                    
        elif login_type == "מנהל":
            pwd = st.text_input("סיסמת מנהל:", type="password", placeholder="הקלד 1234...")
            if st.button("👑 היכנס כמנהל", type="primary"):
                if pwd == "1234":
                    st.session_state.logged_in = True
                    st.session_state.role = "manager"
                    st.session_state.user_name = "מנהל ראשי"
                    st.rerun()
                else:
                    st.error("סיסמה שגויה!")

# ==========================================
# 5. המערכת הפעילה (אחרי התחברות)
# ==========================================
else:
    st.sidebar.markdown(f"### 👋 שלום, {st.session_state.user_name}")
    if st.sidebar.button("🔴 התנתק"):
        st.session_state.logged_in = False
        st.session_state.role = None
        st.session_state.user_name = ""
        st.rerun()
        
    df = load_data()
    # זמן ישראל (UTC+2)
    ist_now = datetime.utcnow() + timedelta(hours=2)
    now_str = ist_now.strftime("%Y-%m-%d %H:%M")

    # ------------------------------------------
    # מבט עובד זוטר (Worker View)
    # ------------------------------------------
    if st.session_state.role == "worker":
        st.title("🕒 אזור אישי - החתמת שעון")
        st.info(f"מחובר כ: **{st.session_state.user_name}** | לא ניתן לצפות בנתוני עובדים אחרים.")
        
        worker_name = st.session_state.user_name
        active_shift = df[(df["שם עובד"].astype(str).str.strip() == worker_name) & (df["יציאה"].isna())]
        
        st.markdown("<br>", unsafe_allow_html=True)
        col_w1, col_w2, col_w3 = st.columns([1, 2, 1])
        with col_w2:
            if active_shift.empty:
                st.success("אתה מחוץ למשמרת. יום עבודה פורה!")
                if st.button("🟢 כניסה למשמרת עכשיו", type="primary"):
                    new_row = pd.DataFrame([{"שם עובד": worker_name, "כניסה": now_str, "יציאה": None, "סהכ שעות": None}])
                    save_data(pd.concat([df, new_row], ignore_index=True))
                    st.rerun()
            else:
                entry_time = active_shift.iloc[0]['כניסה']
                st.warning(f"אתה במשמרת פעילה החל מ- {entry_time}.")
                if st.button("🔴 יציאה ממשמרת", type="primary"):
                    idx = active_shift.index[-1]
                    df.at[idx, "יציאה"] = now_str
                    t1 = datetime.strptime(df.at[idx, "כניסה"], "%Y-%m-%d %H:%M")
                    t2 = datetime.strptime(now_str, "%Y-%m-%d %H:%M")
                    df.at[idx, "סהכ שעות"] = round((t2 - t1).total_seconds() / 3600, 2)
                    save_data(df)
                    st.balloons()
                    st.rerun()

    # ------------------------------------------
    # מבט מנהל (Manager View)
    # ------------------------------------------
    elif st.session_state.role == "manager":
        st.title("🚀 פאנל ניהול עסק מורחב")
        menu = st.sidebar.radio("ניווט מנהל:", ["📊 דשבורד ונוכחות", "⏱️ החתמה ותיקון שעות ידני", "👥 ניהול עובדים מורשים", "🤖 עוזר AI"])
        
        if not df.empty:
            df['תאריך'] = pd.to_datetime(df['כניסה'], errors='coerce').dt.date

        if menu == "📊 דשבורד ונוכחות":
            active_workers_df = df[df["יציאה"].isna()] if not df.empty else pd.DataFrame()
            active_count = len(active_workers_df)
            total_hours = df["סהכ שעות"].sum() if not df.empty else 0
            
            c1, c2, c3 = st.columns(3)
            c1.metric("עובדים כעת", active_count)
            c2.metric("סה\"כ שעות שנרשמו", f"{total_hours:.1f}")
            c3.metric("משמרות חריגות (>9ש')", len(df[df["סהכ שעות"] > 9]) if not df.empty else 0)

            st.markdown("---")
            st.subheader("⚡ עובדים פעילים (סגירת משמרת מיידית)")
            if active_count > 0:
                for idx, row in active_workers_df.iterrows():
                    col_name, col_btn = st.columns([3, 1])
                    with col_name:
                        st.markdown(f"**{row['שם עובד']}** (נכנס ב: {row['כניסה']})")
                    with col_btn:
                        if st.button(f"🔴 הוצא עכשיו", key=f"btn_{idx}"):
                            df.at[idx, "יציאה"] = now_str
                            t1 = datetime.strptime(df.at[idx, "כניסה"], "%Y-%m-%d %H:%M")
                            t2 = datetime.strptime(now_str, "%Y-%m-%d %H:%M")
                            df.at[idx, "סהכ שעות"] = round((t2 - t1).total_seconds() / 3600, 2)
                            save_data(df)
                            st.rerun()
            else:
                st.info("אין עובדים במשמרת כרגע.")

            st.markdown("---")
            st.subheader("📝 מאגר נתונים מלא")
            edited = st.data_editor(df, num_rows="dynamic", use_container_width=True, disabled=["כניסה", "יציאה", "סהכ שעות", "תאריך"])
            if st.button("💾 שמור שינויים בבסיס הנתונים"):
                save_data(edited)
                st.success("הנתונים נשמרו בהצלחה.")
                st.rerun()

        elif menu == "⏱️ החתמה ותיקון שעות ידני":
            st.subheader("תיקון נוכחות: סגירה/פתיחה של משמרת בזמן מותאם")
            st.write("כאן המנהל יכול להזין שעה ותאריך מדוייקים.")
            
            workers_list = load_workers()['שם עובד'].tolist()
            if not workers_list:
                st.warning("אין עובדים במערכת. אנא הוסף עובדים בלשונית 'ניהול עובדים מורשים'.")
            else:
                worker_name_raw = st.selectbox("1️⃣ בחר עובד:", workers_list)
                
                st.markdown("##### 2️⃣ בחר תאריך ושעה לביצוע הפעולה:")
                col_d, col_t = st.columns(2)
                with col_d:
                    selected_date = st.date_input("תאריך", ist_now.date())
                with col_t:
                    # התיקון שביקשת: step=60 מאפשר בחירה ברמת הדקה, והזמן מוצג לפי שעון ישראל
                    selected_time = st.time_input("שעה", ist_now.time(), step=60)
                    
                custom_dt_str = datetime.combine(selected_date, selected_time).strftime("%Y-%m-%d %H:%M")
                
                st.markdown("---")
                
                if worker_name_raw:
                    active_shift = df[(df["שם עובד"].astype(str).str.strip() == worker_name_raw) & (df["יציאה"].isna())]
                    
                    if active_shift.empty:
                        st.info(f"לעובד **{worker_name_raw}** אין משמרת פתוחה כרגע.")
                        if st.button(f"🟢 פתח משמרת החל מ- {custom_dt_str}", use_container_width=True):
                            new_row = pd.DataFrame([{"שם עובד": worker_name_raw, "כניסה": custom_dt_str, "יציאה": None, "סהכ שעות": None}])
                            save_data(pd.concat([df, new_row], ignore_index=True))
                            st.success(f"נפתחה משמרת ל-{worker_name_raw} בתאריך {custom_dt_str}")
                            st.rerun()
                    else:
                        entry_time = active_shift.iloc[0]['כניסה']
                        st.warning(f"שים לב: לעובד **{worker_name_raw}** יש משמרת פתוחה שהחלה ב- {entry_time}")
                        if st.button(f"🔴 סגור משמרת בתאריך ושעה שנבחרו ({custom_dt_str})", type="primary", use_container_width=True):
                            idx = active_shift.index[-1]
                            t1 = datetime.strptime(entry_time, "%Y-%m-%d %H:%M")
                            t2 = datetime.combine(selected_date, selected_time)
                            
                            if t2 < t1:
                                st.error("❌ שגיאה: זמן היציאה שבחרת מוקדם מזמן הכניסה של העובד! אי אפשר לסיים משמרת לפני שהתחילה.")
                            else:
                                df.at[idx, "יציאה"] = custom_dt_str
                                df.at[idx, "סהכ שעות"] = round((t2 - t1).total_seconds() / 3600, 2)
                                save_data(df)
                                st.success("משמרת נסגרה ועודכנה בהצלחה!")
                                st.rerun()

        elif menu == "👥 ניהול עובדים מורשים":
            st.subheader("🔒 רשימת גישה: מי מורשה להחתים שעון?")
            workers_df = load_workers()
            col_add1, col_add2 = st.columns([3, 1])
            with col_add1:
                new_worker = st.text_input("הוסף עובד חדש לרשימה (שם מלא / ת.ז):")
            with col_add2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("➕ הוסף למורשים", use_container_width=True):
                    if new_worker.strip():
                        if new_worker.strip() not in workers_df['שם עובד'].astype(str).str.strip().tolist():
                            new_row = pd.DataFrame([{"שם עובד": new_worker.strip()}])
                            save_workers(pd.concat([workers_df, new_row], ignore_index=True))
                            st.success(f"העובד '{new_worker.strip()}' נוסף בהצלחה!")
                            st.rerun()
                        else:
                            st.warning("עובד זה כבר קיים במערכת.")
            
            st.markdown("---")
            edited_workers = st.data_editor(workers_df, num_rows="dynamic", use_container_width=True)
            if st.button("💾 שמור רשימת עובדים מעודכנת"):
                save_workers(edited_workers)
                st.success("הרשאות הגישה עודכנו בהצלחה.")
                st.rerun()

        elif menu == "🤖 עוזר AI":
            st.subheader("ניתוח פעילות עם Google Gemini")
            API_KEY = st.secrets.get("GEMINI_API_KEY", "") 
            if API_KEY:
                genai.configure(api_key=API_KEY)
                best_model = "gemini-1.5-flash"
                try:
                    for m in genai.list_models():
                        if 'generateContent' in m.supported_generation_methods and 'gemini' in m.name.lower():
                            best_model = m.name
                            break
                except Exception: pass
                
                model = genai.GenerativeModel(best_model)
                st.caption(f"✅ מחובר למנוע: `{best_model}`")
                
                q = st.text_input("שאל על נתוני העבודה:")
                if q:
                    with st.spinner("מנתח..."):
                        try:
                            res = model.generate_content(f"נתוני משמרות:\n{df.to_string()}\nשאלה: {q}")
                            st.info(res.text)
                        except Exception as e:
                            st.error(f"שגיאת AI: {e}")