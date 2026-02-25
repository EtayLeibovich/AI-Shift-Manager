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
# 2. ניהול משאבים
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
    ist_now = datetime.utcnow() + timedelta(hours=2)
    now_str = ist_now.strftime("%Y-%m-%d %H:%M")

    # ------------------------------------------
    # מבט עובד זוטר
    # ------------------------------------------
    if st.session_state.role == "worker":
        st.title("🕒 אזור אישי - החתמת שעון")
        st.info(f"מחובר כ: **{st.session_state.user_name}** | לא ניתן לצפות בנתוני עובדים אחרים.")
        
        worker_name = st.session_state.user_name
        
        worker_shifts = df[df["שם עובד"].astype(str).str.strip() == worker_name]
        active_shift = worker_shifts[worker_shifts["יציאה"].isna()]
        
        st.markdown("<br>", unsafe_allow_html=True)
        col_w1, col_w2, col_w3 = st.columns([1, 2, 1])
        with col_w2:
            if active_shift.empty:
                if not worker_shifts.empty and pd.notna(worker_shifts.iloc[-1]['יציאה']):
                    last_exit = worker_shifts.iloc[-1]['יציאה']
                    st.success(f"אתה מחוץ למשמרת. (יציאה אחרונה נרשמה ב: {last_exit})")
                else:
                    st.success("אתה מחוץ למשמרת. יום נפלא!")
                    
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
    # מבט מנהל
    # ------------------------------------------
    elif st.session_state.role == "manager":
        st.title("🚀 פאנל ניהול עסק מורחב")
        menu = st.sidebar.radio("ניווט מנהל:", ["📊 דשבורד ונוכחות", "⏱️ החתמה ותיקון שעות", "👥 ניהול עובדים", "🤖 עוזר AI"])
        
        if menu == "📊 דשבורד ונוכחות":
            active_workers_df = df[df["יציאה"].isna()] if not df.empty else pd.DataFrame()
            active_count = len(active_workers_df)
            total_hours = df["סהכ שעות"].sum() if not df.empty else 0
            
            c1, c2, c3 = st.columns(3)
            c1.metric("עובדים כעת", active_count)
            c2.metric("סה\"כ שעות שנרשמו (היסטורי)", f"{total_hours:.1f}")
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

            # ==========================================
            # הפיצ'ר החדש: סינון חכם (Smart Filters)
            # ==========================================
            st.markdown("---")
            st.subheader("🔎 חיפוש וסינון חכם (BI)")
            
            if not df.empty and 'סהכ שעות' in df.columns:
                valid_df = df.copy()
                valid_df['datetime'] = pd.to_datetime(valid_df['כניסה'], errors='coerce')
                valid_df = valid_df.dropna(subset=['datetime'])
                
                if not valid_df.empty:
                    # יצירת עמודות עזר חכמות
                    valid_df['תאריך יומי'] = valid_df['datetime'].dt.date
                    valid_df['חודש'] = valid_df['datetime'].dt.strftime('%Y-%m')
                    
                    # ממיר את המספר של היום בשבוע לאותיות בעברית (0=שני, 6=ראשון)
                    day_mapping = {6: "א'", 0: "ב'", 1: "ג'", 2: "ד'", 3: "ה'", 4: "ו'", 5: "ש'"}
                    valid_df['יום בשבוע'] = valid_df['datetime'].dt.weekday.map(day_mapping)
                    
                    # שורת החיתוכים
                    col_f1, col_f2, col_f3 = st.columns(3)
                    with col_f1:
                        all_workers = ["הכל"] + valid_df['שם עובד'].unique().tolist()
                        selected_worker = st.selectbox("👤 סנן לפי עובד:", all_workers)
                    with col_f2:
                        all_months = ["הכל"] + sorted(valid_df['חודש'].unique().tolist(), reverse=True)
                        selected_month = st.selectbox("📅 סנן לפי חודש:", all_months)
                    with col_f3:
                        days_order = ["הכל", "א'", "ב'", "ג'", "ד'", "ה'", "ו'", "ש'"]
                        selected_day = st.selectbox("📆 סנן לפי יום:", days_order)
                        
                    # הפעלת הסינונים על הטבלה
                    filtered_df = valid_df.copy()
                    if selected_worker != "הכל":
                        filtered_df = filtered_df[filtered_df['שם עובד'] == selected_worker]
                    if selected_month != "הכל":
                        filtered_df = filtered_df[filtered_df['חודש'] == selected_month]
                    if selected_day != "הכל":
                        filtered_df = filtered_df[filtered_df['יום בשבוע'] == selected_day]
                        
                    st.write(f"**מציג {len(filtered_df)} משמרות שעונות על תנאי הסינון:**")
                    # מציגים למנהל רק את העמודות שרלוונטיות ונוחות לקריאה
                    st.dataframe(filtered_df[['שם עובד', 'כניסה', 'יציאה', 'סהכ שעות', 'יום בשבוע', 'חודש']].sort_values(by='כניסה', ascending=False), use_container_width=True)

                    # דוחות הסיכום הכלליים (נשאר כפי שהיה לבקשתך הקודמת)
                    st.markdown("---")
                    st.subheader("📈 דוחות שעות מסכמים (ללא סינון)")
                    
                    def get_sunday(dt):
                        days_to_subtract = (dt.weekday() + 1) % 7 
                        return (dt - timedelta(days=days_to_subtract)).date()
                    
                    valid_df['שבוע (מתחיל בראשון)'] = valid_df['datetime'].apply(get_sunday)

                    report_type = st.radio("בחר תצוגת סיכום שעות:", ["סיכום יומי", "סיכום שבועי", "סיכום חודשי"], horizontal=True)
                    
                    if report_type == "סיכום יומי":
                        summary = valid_df.groupby(['תאריך יומי', 'שם עובד'])['סהכ שעות'].sum().reset_index()
                        st.dataframe(summary.sort_values(by='תאריך יומי', ascending=False), use_container_width=True)
                        
                    elif report_type == "סיכום שבועי":
                        summary = valid_df.groupby(['שבוע (מתחיל בראשון)', 'שם עובד'])['סהכ שעות'].sum().reset_index()
                        summary.rename(columns={'שבוע (מתחיל בראשון)': 'תחילת שבוע (יום א\')'}, inplace=True)
                        st.dataframe(summary.sort_values(by="תחילת שבוע (יום א')", ascending=False), use_container_width=True)
                        
                    elif report_type == "סיכום חודשי":
                        summary = valid_df.groupby(['חודש', 'שם עובד'])['סהכ שעות'].sum().reset_index()
                        st.dataframe(summary.sort_values(by='חודש', ascending=False), use_container_width=True)
                else:
                    st.info("עדיין אין משמרות סגורות להצגת סיכומים.")
            else:
                st.info("אין נתונים זמינים.")

            st.markdown("---")
            st.subheader("📝 מאגר נתונים מלא לעריכה ישירה")
            edited = st.data_editor(df, num_rows="dynamic", use_container_width=True, disabled=["כניסה", "יציאה", "סהכ שעות"])
            if st.button("💾 שמור שינויים בבסיס הנתונים"):
                save_data(edited)
                st.success("הנתונים נשמרו בהצלחה.")
                st.rerun()

        elif menu == "⏱️ החתמה ותיקון שעות":
            st.subheader("תיקון נוכחות: סגירה/פתיחה ועריכת היסטוריה")
            workers_list = load_workers()['שם עובד'].tolist()
            if not workers_list:
                st.warning("אין עובדים במערכת. אנא הוסף עובדים בלשונית 'ניהול עובדים'.")
            else:
                worker_name_raw = st.selectbox("1️⃣ בחר עובד:", workers_list)
                action_type = st.radio("2️⃣ סוג פעולה:", ["פתיחה / סגירה של משמרת נוכחית", "עריכת משמרת שהסתיימה (תיקון שעות עבר)"], horizontal=True)
                
                st.markdown("---")
                
                if action_type == "פתיחה / סגירה של משמרת נוכחית":
                    st.markdown("##### בחר תאריך ושעה לביצוע הפעולה:")
                    col_d, col_t = st.columns(2)
                    with col_d:
                        selected_date = st.date_input("תאריך", ist_now.date())
                    with col_t:
                        selected_time = st.time_input("שעה", ist_now.time(), step=60)
                        
                    custom_dt_str = datetime.combine(selected_date, selected_time).strftime("%Y-%m-%d %H:%M")
                    
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
                                    st.error("❌ שגיאה: זמן היציאה שבחרת מוקדם מזמן הכניסה של העובד!")
                                else:
                                    df.at[idx, "יציאה"] = custom_dt_str
                                    df.at[idx, "סהכ שעות"] = round((t2 - t1).total_seconds() / 3600, 2)
                                    save_data(df)
                                    st.success("משמרת נסגרה ועודכנה בהצלחה!")
                                    st.rerun()

                elif action_type == "עריכת משמרת שהסתיימה (תיקון שעות עבר)":
                    closed_shifts = df[(df["שם עובד"].astype(str).str.strip() == worker_name_raw) & (df["יציאה"].notna())]
                    
                    if closed_shifts.empty:
                        st.info("אין משמרות קודמות שהסתיימו לעובד זה.")
                    else:
                        shift_dict = {idx: f"כניסה: {row['כניסה']} | יציאה: {row['יציאה']} ({row['סהכ שעות']} שעות)" for idx, row in closed_shifts.iterrows()}
                        selected_shift_idx = st.selectbox("בחירת משמרת לעריכה:", options=list(shift_dict.keys()), format_func=lambda x: shift_dict[x])
                        
                        selected_row = df.loc[selected_shift_idx]
                        orig_in_dt = datetime.strptime(selected_row['כניסה'], "%Y-%m-%d %H:%M")
                        orig_out_dt = datetime.strptime(selected_row['יציאה'], "%Y-%m-%d %H:%M")
                        
                        st.markdown("##### ערוך זמנים חדשים (ברמת הדקה):")
                        col_in1, col_in2 = st.columns(2)
                        with col_in1:
                            new_in_date = st.date_input("תאריך כניסה", orig_in_dt.date(), key="in_d")
                        with col_in2:
                            new_in_time = st.time_input("שעת כניסה", orig_in_dt.time(), step=60, key="in_t")
                        
                        col_out1, col_out2 = st.columns(2)
                        with col_out1:
                            new_out_date = st.date_input("תאריך יציאה", orig_out_dt.date(), key="out_d")
                        with col_out2:
                            new_out_time = st.time_input("שעת יציאה", orig_out_dt.time(), step=60, key="out_t")
                        
                        new_in_str = datetime.combine(new_in_date, new_in_time).strftime("%Y-%m-%d %H:%M")
                        new_out_str = datetime.combine(new_out_date, new_out_time).strftime("%Y-%m-%d %H:%M")
                        
                        st.markdown("---")
                        confirm_edit = st.checkbox("⚠️ אני מאשר/ת שאני רוצה לדרוס את נתוני המשמרת הקיימת ולעדכן לשעות החדשות")
                        
                        if st.button("💾 עדכן משמרת ושמור נתונים", type="primary", disabled=not confirm_edit):
                            t1 = datetime.strptime(new_in_str, "%Y-%m-%d %H:%M")
                            t2 = datetime.strptime(new_out_str, "%Y-%m-%d %H:%M")
                            
                            if t2 < t1:
                                st.error("❌ שגיאה: זמן היציאה שבחרת מוקדם מזמן הכניסה!")
                            else:
                                df.at[selected_shift_idx, "כניסה"] = new_in_str
                                df.at[selected_shift_idx, "יציאה"] = new_out_str
                                df.at[selected_shift_idx, "סהכ שעות"] = round((t2 - t1).total_seconds() / 3600, 2)
                                save_data(df)
                                st.success("המשמרת עודכנה בהצלחה!")
                                st.rerun()

        elif menu == "👥 ניהול עובדים":
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