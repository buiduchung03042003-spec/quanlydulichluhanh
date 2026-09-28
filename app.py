import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import date, datetime
import io
import json
import hashlib

# ============================================================
# LỮ HÀNH PRO - STREAMLIT TOUR OPERATOR MANAGEMENT
# Chạy: streamlit run app.py
# ============================================================

st.set_page_config(
    page_title="Lữ Hành Pro",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB = "lu_hanh.db"

# ------------------------- DATABASE ---------------------------
def get_conn():
    conn = sqlite3.connect(DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'admin'
    );

    CREATE TABLE IF NOT EXISTS tours(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        destination TEXT,
        departure TEXT,
        return_date TEXT,
        duration TEXT,
        capacity INTEGER DEFAULT 0,
        price REAL DEFAULT 0,
        cost REAL DEFAULT 0,
        status TEXT DEFAULT 'Đang bán',
        description TEXT,
        tour_type TEXT DEFAULT 'Tour trọn gói',
        category TEXT DEFAULT 'Nội địa',
        departure_point TEXT,
        itinerary TEXT,
        transport TEXT,
        hotel_standard TEXT,
        meals TEXT,
        included TEXT,
        excluded TEXT,
        child_price REAL DEFAULT 0,
        infant_price REAL DEFAULT 0,
        single_supplement REAL DEFAULT 0,
        min_pax INTEGER DEFAULT 1,
        booking_deadline TEXT,
        cancellation_policy TEXT,
        meeting_point TEXT,
        contact_name TEXT,
        contact_phone TEXT,
        contact_email TEXT,
        image_url TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS tour_days(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tour_id INTEGER NOT NULL,
        day_no INTEGER NOT NULL,
        title TEXT NOT NULL,
        activities TEXT,
        meals TEXT,
        hotel TEXT,
        distance TEXT,
        notes TEXT,
        FOREIGN KEY(tour_id) REFERENCES tours(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS customers(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        phone TEXT NOT NULL,
        email TEXT,
        dob TEXT,
        gender TEXT,
        id_number TEXT,
        address TEXT,
        customer_type TEXT DEFAULT 'Cá nhân',
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS bookings(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        customer_id INTEGER NOT NULL,
        tour_id INTEGER NOT NULL,
        pax INTEGER NOT NULL,
        unit_price REAL NOT NULL,
        discount REAL DEFAULT 0,
        total REAL NOT NULL,
        paid REAL DEFAULT 0,
        payment_status TEXT DEFAULT 'Chưa thanh toán',
        booking_status TEXT DEFAULT 'Đã xác nhận',
        booking_date TEXT DEFAULT CURRENT_TIMESTAMP,
        notes TEXT,
        FOREIGN KEY(customer_id) REFERENCES customers(id),
        FOREIGN KEY(tour_id) REFERENCES tours(id)
    );

    CREATE TABLE IF NOT EXISTS guides(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        phone TEXT,
        email TEXT,
        languages TEXT,
        license_no TEXT,
        area TEXT,
        daily_fee REAL DEFAULT 0,
        status TEXT DEFAULT 'Sẵn sàng',
        notes TEXT
    );

    CREATE TABLE IF NOT EXISTS suppliers(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        supplier_type TEXT NOT NULL,
        phone TEXT,
        email TEXT,
        address TEXT,
        contact_person TEXT,
        rating REAL DEFAULT 0,
        notes TEXT
    );

    CREATE TABLE IF NOT EXISTS operations(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tour_id INTEGER NOT NULL,
        guide_id INTEGER,
        vehicle_supplier_id INTEGER,
        hotel_supplier_id INTEGER,
        restaurant_supplier_id INTEGER,
        status TEXT DEFAULT 'Chuẩn bị',
        checklist_vehicle INTEGER DEFAULT 0,
        checklist_hotel INTEGER DEFAULT 0,
        checklist_guide INTEGER DEFAULT 0,
        checklist_guestlist INTEGER DEFAULT 0,
        checklist_insurance INTEGER DEFAULT 0,
        notes TEXT,
        FOREIGN KEY(tour_id) REFERENCES tours(id)
    );

    CREATE TABLE IF NOT EXISTS transactions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        trans_date TEXT NOT NULL,
        trans_type TEXT NOT NULL,
        category TEXT,
        amount REAL NOT NULL,
        booking_id INTEGER,
        description TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)
    # Demo admin: admin / admin123
    password = hashlib.sha256("admin123".encode()).hexdigest()
    cur.execute("INSERT OR IGNORE INTO users(username,password,role) VALUES(?,?,?)",
                ("admin", password, "admin"))
    conn.commit()
    conn.close()

init_db()

# -------------------- DATABASE MIGRATION ----------------------
def ensure_tour_columns():
    """Tự động bổ sung các trường Tour mới cho CSDL cũ."""
    conn = get_conn()
    cur = conn.cursor()
    existing = {row[1] for row in cur.execute("PRAGMA table_info(tours)").fetchall()}
    columns = {
        "tour_type": "TEXT DEFAULT 'Tour trọn gói'",
        "category": "TEXT DEFAULT 'Nội địa'",
        "departure_point": "TEXT",
        "itinerary": "TEXT",
        "transport": "TEXT",
        "hotel_standard": "TEXT",
        "meals": "TEXT",
        "included": "TEXT",
        "excluded": "TEXT",
        "child_price": "REAL DEFAULT 0",
        "infant_price": "REAL DEFAULT 0",
        "single_supplement": "REAL DEFAULT 0",
        "min_pax": "INTEGER DEFAULT 1",
        "booking_deadline": "TEXT",
        "cancellation_policy": "TEXT",
        "meeting_point": "TEXT",
        "contact_name": "TEXT",
        "contact_phone": "TEXT",
        "contact_email": "TEXT",
        "image_url": "TEXT",
        "notes": "TEXT",
    }
    for name, definition in columns.items():
        if name not in existing:
            cur.execute(f"ALTER TABLE tours ADD COLUMN {name} {definition}")
    conn.commit()
    conn.close()

ensure_tour_columns()

# ------------------------- HELPERS ----------------------------
def q(sql, params=(), one=False):
    conn = get_conn()
    df = pd.read_sql_query(sql, conn, params=params)
    conn.close()
    return df.iloc[0].to_dict() if one and not df.empty else df

def execute(sql, params=()):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
    last = cur.lastrowid
    conn.close()
    return last

def money(x):
    try:
        return f"{float(x):,.0f} ₫"
    except:
        return "0 ₫"

def next_code(prefix, table):
    df = q(f"SELECT code FROM {table} WHERE code LIKE ?", (prefix+"%",))
    nums = []
    for c in df["code"].tolist():
        try: nums.append(int(str(c).replace(prefix,"")))
        except: pass
    n = max(nums, default=0) + 1
    return f"{prefix}{n:04d}"

def valid_phone(phone):
    digits = "".join(ch for ch in str(phone) if ch.isdigit())
    return len(digits) in (10, 11) and digits.startswith("0")

def safe_int(v, default=0):
    try: return int(v)
    except: return default

def safe_float(v, default=0):
    try: return float(v)
    except: return default

# ----------------------- VOICE TO TEXT ------------------------
def voice_to_text(label="🎙️ Nhập bằng giọng nói"):
    audio = st.audio_input(label)
    if audio:
        try:
            import speech_recognition as sr
            r = sr.Recognizer()
            with sr.AudioFile(audio) as source:
                data = r.record(source)
            text = r.recognize_google(data, language="vi-VN")
            st.success("Đã nhận diện giọng nói.")
            return text
        except ImportError:
            st.error("Chưa cài SpeechRecognition. Chạy: pip install -r requirements.txt")
        except Exception as e:
            st.warning("Không nhận diện được giọng nói. Kiểm tra microphone và Internet.")
    return ""

# ------------------------- LOGIN ------------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

def login():
    st.title("✈️ Lữ Hành Pro")
    st.subheader("Hệ thống quản lý doanh nghiệp du lịch lữ hành")
    with st.form("login"):
        u = st.text_input("Tên đăng nhập", value="admin")
        p = st.text_input("Mật khẩu", type="password")
        ok = st.form_submit_button("Đăng nhập", type="primary")
        if ok:
            h = hashlib.sha256(p.encode()).hexdigest()
            user = q("SELECT * FROM users WHERE username=? AND password=?", (u,h), one=True)
            if user:
                st.session_state.logged_in = True
                st.session_state.user = user
                st.rerun()
            else:
                st.error("Sai tài khoản hoặc mật khẩu.")
    st.info("Tài khoản mẫu: admin | Mật khẩu: admin123")

if not st.session_state.logged_in:
    login()
    st.stop()

# ------------------------- SIDEBAR -----------------------------
with st.sidebar:
    st.title("✈️ LỮ HÀNH PRO")
    st.caption(f"Xin chào: {st.session_state.user['username']}")
    menu = st.radio(
        "MENU",
        ["📊 Tổng quan","🗺️ Tour","👥 Khách hàng","🎫 Booking",
         "🧭 Điều hành","🎤 Hướng dẫn viên","🏨 Nhà cung cấp",
         "💰 Tài chính","📈 Báo cáo","🎙️ Voice-to-Text","💾 Sao lưu dữ liệu",
         "⚙️ Cài đặt"],
    )
    if st.button("🚪 Đăng xuất", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

# ------------------------- DASHBOARD ---------------------------
if menu == "📊 Tổng quan":
    st.title("📊 Tổng quan doanh nghiệp")
    tours = q("SELECT * FROM tours")
    customers = q("SELECT * FROM customers")
    bookings = q("SELECT * FROM bookings")
    guides = q("SELECT * FROM guides")
    rev = bookings["total"].sum() if not bookings.empty else 0
    paid = bookings["paid"].sum() if not bookings.empty else 0
    pax = bookings["pax"].sum() if not bookings.empty else 0

    a,b,c,d,e = st.columns(5)
    a.metric("🗺️ Tour", len(tours))
    b.metric("👥 Khách hàng", len(customers))
    c.metric("🎫 Booking", len(bookings))
    d.metric("💰 Doanh thu", money(rev))
    e.metric("👤 Số khách", int(pax))

    st.divider()
    col1,col2 = st.columns(2)
    with col1:
        st.subheader("Doanh thu theo tour")
        if not bookings.empty:
            chart = bookings.merge(tours[["id","name"]], left_on="tour_id", right_on="id")
            chart = chart.groupby("name", as_index=False)["total"].sum()
            fig = px.bar(chart, x="name", y="total", labels={"name":"Tour","total":"Doanh thu"})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Chưa có booking.")
    with col2:
        st.subheader("Tình hình thanh toán")
        due = rev - paid
        st.metric("Đã thu", money(paid))
        st.metric("Còn phải thu", money(due))
        st.metric("Tỷ lệ thu", f"{paid/rev*100:.1f}%" if rev else "0%")

    st.subheader("⚠️ Kiểm soát nghiệp vụ")
    warnings = []
    if not bookings.empty:
        bad = bookings[bookings["paid"] > bookings["total"]]
        if len(bad): warnings.append(f"{len(bad)} booking có số tiền thu vượt tổng tiền.")
    if not tours.empty:
        bad = tours[(tours["price"] < 0) | (tours["cost"] < 0)]
        if len(bad): warnings.append(f"{len(bad)} tour có giá/giá vốn âm.")
    if warnings:
        for w in warnings: st.error(w)
    else:
        st.success("Không phát hiện lỗi nghiệp vụ cơ bản.")

# --------------------------- TOURS -----------------------------
elif menu == "🗺️ Tour":
    st.title("🗺️ Quản lý Tour")
    st.caption("Hồ sơ tour mở rộng: thông tin sản phẩm, lịch trình, dịch vụ, giá, điều kiện và liên hệ.")

    tab1, tab2, tab3 = st.tabs(["➕ Tạo / cập nhật Tour", "📋 Danh sách Tour", "🗓️ Lịch trình từng ngày"])

    # --------------------- CREATE TOUR ---------------------
    with tab1:
        with st.form("tour_form", clear_on_submit=True):
            st.subheader("1. Thông tin cơ bản")
            c1, c2, c3 = st.columns(3)
            name = c1.text_input("Tên tour *", placeholder="VD: Vũng Tàu - Đà Lạt 3N2Đ")
            tour_type = c2.selectbox("Loại tour", [
                "Tour trọn gói", "Tour ghép đoàn", "Tour riêng",
                "Tour MICE", "Team Building", "Inbound", "Outbound"
            ])
            category = c3.selectbox("Thị trường", ["Nội địa", "Quốc tế", "Inbound", "Outbound"])

            c1, c2, c3 = st.columns(3)
            destination = c1.text_input("Điểm đến chính *", placeholder="Đà Lạt, Nha Trang...")
            departure_point = c2.text_input("Điểm khởi hành", placeholder="Vũng Tàu / TP.HCM")
            meeting_point = c3.text_input("Điểm tập trung", placeholder="Bến xe / văn phòng / khách sạn")

            c1, c2, c3, c4 = st.columns(4)
            departure = c1.date_input("Ngày khởi hành", value=date.today())
            return_date = c2.date_input("Ngày kết thúc", value=date.today())
            duration = c3.text_input("Thời lượng", "3N2Đ")
            capacity = c4.number_input("Sức chứa tối đa", min_value=1, value=45, step=1)

            c1, c2, c3 = st.columns(3)
            min_pax = c1.number_input("Số khách tối thiểu", min_value=1, value=1)
            booking_deadline = c2.date_input("Hạn chốt booking", value=date.today())
            status = c3.selectbox("Trạng thái", ["Đang bán", "Tạm dừng", "Đã kết thúc", "Nháp", "Hết chỗ"])

            st.subheader("2. Giá tour")
            c1, c2, c3, c4 = st.columns(4)
            price = c1.number_input("Giá bán người lớn", min_value=0.0, step=100000.0)
            cost = c2.number_input("Giá vốn người lớn", min_value=0.0, step=100000.0)
            child_price = c3.number_input("Giá trẻ em", min_value=0.0, step=100000.0)
            infant_price = c4.number_input("Giá em bé", min_value=0.0, step=50000.0)
            single_supplement = st.number_input("Phụ thu phòng đơn", min_value=0.0, step=100000.0)

            st.subheader("3. Dịch vụ tour")
            c1, c2 = st.columns(2)
            transport = c1.text_input("Phương tiện", placeholder="Xe 29 chỗ, máy bay, tàu...")
            hotel_standard = c2.text_input("Tiêu chuẩn lưu trú", placeholder="3★ / 4★ / 5★ / Homestay")
            meals = st.text_area("Ăn uống", placeholder="Bữa sáng ngày 1-3; trưa ngày 1-2; tối ngày 1-2...")
            c1, c2 = st.columns(2)
            included = c1.text_area("Dịch vụ bao gồm", placeholder="Xe, khách sạn, ăn uống, vé tham quan, HDV, bảo hiểm...")
            excluded = c2.text_area("Dịch vụ không bao gồm", placeholder="VAT, đồ uống, chi phí cá nhân, phụ thu phòng đơn...")

            st.subheader("4. Nội dung & điều kiện")
            itinerary = st.text_area(
                "Tóm tắt hành trình",
                placeholder="Ngày 1: ...\nNgày 2: ...\nNgày 3: ..."
            )
            cancellation_policy = st.text_area(
                "Điều kiện hủy / đổi tour",
                placeholder="Quy định đặt cọc, hủy trước ngày khởi hành, đổi tên..."
            )
            description = st.text_area("Mô tả / giới thiệu tour", placeholder="Giới thiệu sản phẩm, điểm nổi bật...")
            notes = st.text_area("Ghi chú nội bộ", placeholder="Lưu ý điều hành, yêu cầu đặc biệt...")

            st.subheader("5. Thông tin liên hệ & hình ảnh")
            c1, c2, c3 = st.columns(3)
            contact_name = c1.text_input("Nhân viên phụ trách")
            contact_phone = c2.text_input("Điện thoại tư vấn")
            contact_email = c3.text_input("Email tư vấn")
            image_url = st.text_input("Link hình ảnh đại diện (tùy chọn)")

            submit = st.form_submit_button("💾 Lưu Tour", type="primary", use_container_width=True)

            if submit:
                if not name.strip() or not destination.strip():
                    st.error("Tên tour và điểm đến là bắt buộc.")
                elif return_date < departure:
                    st.error("Ngày kết thúc không được trước ngày khởi hành.")
                elif booking_deadline > departure:
                    st.error("Hạn chốt booking không nên sau ngày khởi hành.")
                elif min_pax > capacity:
                    st.error("Số khách tối thiểu không được lớn hơn sức chứa.")
                elif cost > price and price > 0:
                    st.warning("Giá vốn đang cao hơn giá bán. Vẫn có thể lưu nhưng cần kiểm tra lại.")
                else:
                    code = next_code("TOUR", "tours")
                    tour_id = execute("""
                        INSERT INTO tours(
                            code,name,destination,departure,return_date,duration,capacity,
                            price,cost,status,description,tour_type,category,departure_point,
                            itinerary,transport,hotel_standard,meals,included,excluded,
                            child_price,infant_price,single_supplement,min_pax,booking_deadline,
                            cancellation_policy,meeting_point,contact_name,contact_phone,
                            contact_email,image_url,notes
                        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """, (
                        code, name.strip(), destination.strip(), str(departure), str(return_date),
                        duration.strip(), int(capacity), float(price), float(cost), status,
                        description, tour_type, category, departure_point, itinerary, transport,
                        hotel_standard, meals, included, excluded, float(child_price),
                        float(infant_price), float(single_supplement), int(min_pax),
                        str(booking_deadline), cancellation_policy, meeting_point, contact_name,
                        contact_phone, contact_email, image_url, notes
                    ))
                    st.success(f"Đã tạo tour {code}.")
                    st.info("Bạn có thể sang tab 'Lịch trình từng ngày' để nhập chi tiết Day 1, Day 2, Day 3...")
                    st.rerun()

    # --------------------- TOUR LIST ---------------------
    with tab2:
        df = q("SELECT * FROM tours ORDER BY departure DESC, id DESC")
        if not df.empty:
            search = st.text_input("🔎 Tìm theo mã, tên tour, điểm đến, loại tour")
            if search:
                mask = df.astype(str).apply(
                    lambda col: col.str.contains(search, case=False, na=False)
                ).any(axis=1)
                df = df[mask]

            # Thống kê nhanh
            a, b, c, d = st.columns(4)
            a.metric("Tổng tour", len(df))
            b.metric("Đang bán", int((df["status"] == "Đang bán").sum()))
            c.metric("Nội địa", int((df["category"] == "Nội địa").sum()))
            d.metric("Quốc tế", int((df["category"] == "Quốc tế").sum()))

            show = df.copy()
            show["Giá NL"] = show["price"].map(money)
            show["Giá TE"] = show["child_price"].map(money)
            show["Giá EB"] = show["infant_price"].map(money)
            show["Giá vốn"] = show["cost"].map(money)

            cols = [
                "code", "name", "tour_type", "category", "departure_point",
                "destination", "departure", "return_date", "duration",
                "capacity", "min_pax", "Giá NL", "Giá TE", "Giá EB",
                "hotel_standard", "transport", "status"
            ]
            available_cols = [x for x in cols if x in show.columns]
            st.dataframe(show[available_cols], use_container_width=True, hide_index=True)

            # Chi tiết tour
            st.subheader("🔍 Xem chi tiết tour")
            records = df.to_dict("records")
            selected = st.selectbox(
                "Chọn tour",
                records,
                format_func=lambda x: f"{x['code']} — {x['name']} — {x['destination']}"
            )
            if selected:
                left, right = st.columns([1, 1])
                with left:
                    if selected.get("image_url"):
                        st.image(selected["image_url"], caption=selected["name"], use_container_width=True)
                    st.markdown(f"### {selected['name']}")
                    st.write(f"**Mã tour:** {selected['code']}")
                    st.write(f"**Loại:** {selected.get('tour_type','')}")
                    st.write(f"**Thị trường:** {selected.get('category','')}")
                    st.write(f"**Khởi hành:** {selected.get('departure_point','')}")
                    st.write(f"**Điểm tập trung:** {selected.get('meeting_point','')}")
                    st.write(f"**Điểm đến:** {selected.get('destination','')}")
                    st.write(f"**Thời gian:** {selected.get('departure','')} → {selected.get('return_date','')} ({selected.get('duration','')})")
                    st.write(f"**Phương tiện:** {selected.get('transport','')}")
                    st.write(f"**Lưu trú:** {selected.get('hotel_standard','')}")
                    st.write(f"**Trạng thái:** {selected.get('status','')}")
                with right:
                    st.markdown("### 💰 Bảng giá")
                    st.write(f"Người lớn: **{money(selected.get('price',0))}**")
                    st.write(f"Trẻ em: **{money(selected.get('child_price',0))}**")
                    st.write(f"Em bé: **{money(selected.get('infant_price',0))}**")
                    st.write(f"Phụ thu phòng đơn: **{money(selected.get('single_supplement',0))}**")
                    st.write(f"Sức chứa: **{selected.get('capacity',0)} khách**")
                    st.write(f"Tối thiểu: **{selected.get('min_pax',1)} khách**")
                    st.write(f"Hạn chốt: **{selected.get('booking_deadline','')}**")
                    st.markdown("### 🍽️ Ăn uống")
                    st.write(selected.get("meals","") or "Chưa cập nhật")
                    st.markdown("### ✅ Bao gồm")
                    st.write(selected.get("included","") or "Chưa cập nhật")
                    st.markdown("### ❌ Không bao gồm")
                    st.write(selected.get("excluded","") or "Chưa cập nhật")

                st.markdown("### 📝 Hành trình tóm tắt")
                st.text(selected.get("itinerary","") or "Chưa cập nhật")
                st.markdown("### 📌 Điều kiện hủy / đổi")
                st.write(selected.get("cancellation_policy","") or "Chưa cập nhật")
                st.markdown("### 📞 Liên hệ")
                st.write(
                    f"{selected.get('contact_name','')} | "
                    f"{selected.get('contact_phone','')} | "
                    f"{selected.get('contact_email','')}"
                )

            st.download_button(
                "⬇️ Xuất danh sách tour CSV",
                df.to_csv(index=False).encode("utf-8-sig"),
                "tours_full.csv",
                "text/csv"
            )
        else:
            st.info("Chưa có tour.")

    # --------------------- DAILY ITINERARY ---------------------
    with tab3:
        tours = q("SELECT id,code,name,duration FROM tours ORDER BY id DESC")
        if tours.empty:
            st.info("Hãy tạo tour trước khi nhập lịch trình.")
        else:
            tour = st.selectbox(
                "Chọn tour để lập lịch trình",
                tours.to_dict("records"),
                format_func=lambda x: f"{x['code']} — {x['name']} ({x['duration']})"
            )
            st.subheader("➕ Thêm một ngày trong chương trình")
            with st.form("tour_day_form"):
                c1, c2 = st.columns(2)
                day_no = c1.number_input("Ngày thứ", min_value=1, value=1, step=1)
                title = c2.text_input("Tiêu đề ngày", placeholder="Ngày 1: Vũng Tàu → Đà Lạt")

                activities = st.text_area(
                    "Hoạt động / điểm tham quan",
                    placeholder="06:00 tập trung...\n09:00 tham quan...\n12:00 ăn trưa..."
                )
                c1, c2, c3 = st.columns(3)
                meals_day = c1.text_input("Bữa ăn", placeholder="Sáng / Trưa / Tối")
                hotel_day = c2.text_input("Khách sạn", placeholder="Tên khách sạn")
                distance = c3.text_input("Cự ly / thời gian di chuyển", placeholder="180 km / 4 giờ")
                notes_day = st.text_area("Ghi chú ngày")
                save_day = st.form_submit_button("💾 Lưu ngày", type="primary")

                if save_day:
                    if not title.strip():
                        st.error("Tiêu đề ngày là bắt buộc.")
                    else:
                        execute("""
                            INSERT INTO tour_days(
                                tour_id,day_no,title,activities,meals,hotel,distance,notes
                            ) VALUES(?,?,?,?,?,?,?,?)
                        """, (
                            tour["id"], int(day_no), title.strip(), activities,
                            meals_day, hotel_day, distance, notes_day
                        ))
                        st.success(f"Đã thêm Ngày {day_no}.")
                        st.rerun()

            days = q(
                "SELECT * FROM tour_days WHERE tour_id=? ORDER BY day_no,id",
                (tour["id"],)
            )
            if not days.empty:
                st.subheader("📅 Chương trình chi tiết")
                for _, d in days.iterrows():
                    with st.expander(f"Ngày {int(d['day_no'])}: {d['title']}", expanded=True):
                        st.write("**Hoạt động:**")
                        st.write(d["activities"] or "—")
                        c1, c2, c3 = st.columns(3)
                        c1.write(f"**Ăn uống:** {d['meals'] or '—'}")
                        c2.write(f"**Khách sạn:** {d['hotel'] or '—'}")
                        c3.write(f"**Di chuyển:** {d['distance'] or '—'}")
                        st.write(f"**Ghi chú:** {d['notes'] or '—'}")
            else:
                st.info("Tour này chưa có lịch trình từng ngày.")


# ------------------------ CUSTOMERS ----------------------------
elif menu == "👥 Khách hàng":
    st.title("👥 Quản lý khách hàng")
    with st.expander("➕ Thêm khách hàng"):
        with st.form("customer_form"):
            c1,c2,c3 = st.columns(3)
            name = c1.text_input("Họ tên *")
            phone = c2.text_input("Số điện thoại *")
            email = c3.text_input("Email")
            c1,c2,c3 = st.columns(3)
            dob = c1.date_input("Ngày sinh", value=date(2000,1,1))
            gender = c2.selectbox("Giới tính", ["Nam","Nữ","Khác"])
            customer_type = c3.selectbox("Loại khách",["Cá nhân","Doanh nghiệp","Đoàn","Trẻ em","Người cao tuổi"])
            id_number = st.text_input("CCCD/Hộ chiếu")
            address = st.text_input("Địa chỉ")
            notes = st.text_area("Ghi chú")
            if st.form_submit_button("Lưu khách hàng", type="primary"):
                if not name.strip() or not valid_phone(phone):
                    st.error("Họ tên bắt buộc và số điện thoại phải hợp lệ.")
                else:
                    code=next_code("KH","customers")
                    execute("""INSERT INTO customers(code,name,phone,email,dob,gender,id_number,address,customer_type,notes)
                    VALUES(?,?,?,?,?,?,?,?,?,?)""",(code,name,phone,email,str(dob),gender,id_number,address,customer_type,notes))
                    st.success(f"Đã tạo khách hàng {code}")
                    st.rerun()
    df=q("SELECT * FROM customers ORDER BY id DESC")
    if not df.empty:
        st.dataframe(df[["code","name","phone","email","dob","gender","customer_type","id_number"]],use_container_width=True)
    else: st.info("Chưa có khách hàng.")

# -------------------------- BOOKINGS ---------------------------
elif menu == "🎫 Booking":
    st.title("🎫 Quản lý Booking")
    customers=q("SELECT id,code,name,phone FROM customers ORDER BY name")
    tours=q("SELECT id,code,name,price,capacity,departure FROM tours WHERE status!='Đã kết thúc' ORDER BY departure")
    if customers.empty or tours.empty:
        st.warning("Cần có ít nhất 1 khách hàng và 1 tour trước khi tạo booking.")
    else:
        with st.expander("➕ Tạo booking", expanded=True):
            with st.form("booking_form"):
                c1,c2,c3=st.columns(3)
                c=c1.selectbox("Khách hàng",customers.to_dict("records"),format_func=lambda x:f"{x['code']} - {x['name']} - {x['phone']}")
                t=c2.selectbox("Tour",tours.to_dict("records"),format_func=lambda x:f"{x['code']} - {x['name']} - {money(x['price'])}")
                pax=c3.number_input("Số khách",min_value=1,value=1)
                discount=c1.number_input("Giảm giá",min_value=0.0,step=50000.0)
                unit_price=float(t["price"])
                total=max(0,unit_price*pax-discount)
                c2.metric("Tổng tiền",money(total))
                paid=c3.number_input("Đã thanh toán",min_value=0.0,max_value=total,value=0.0,step=100000.0)
                status=c1.selectbox("Trạng thái booking",["Đã xác nhận","Chờ xác nhận","Đã hủy","Hoàn tất"])
                notes=st.text_area("Ghi chú")
                if st.form_submit_button("Lưu booking",type="primary"):
                    # Kiểm tra sức chứa theo các booking chưa hủy
                    used=q("""SELECT COALESCE(SUM(pax),0) n FROM bookings
                              WHERE tour_id=? AND booking_status!='Đã hủy'""",(t["id"],),one=True)["n"]
                    if int(used)+int(pax)>int(t["capacity"]):
                        st.error(f"Vượt sức chứa tour. Đã giữ {used}/{t['capacity']} chỗ.")
                    elif paid>total:
                        st.error("Tiền đã thanh toán không được vượt tổng booking.")
                    else:
                        pay_status="Đã thanh toán đủ" if paid==total else ("Đã thanh toán một phần" if paid>0 else "Chưa thanh toán")
                        code=next_code("BK","bookings")
                        bid=execute("""INSERT INTO bookings(code,customer_id,tour_id,pax,unit_price,discount,total,paid,payment_status,booking_status,notes)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?)""",(code,c["id"],t["id"],pax,unit_price,discount,total,paid,pay_status,status,notes))
                        if paid>0:
                            execute("""INSERT INTO transactions(code,trans_date,trans_type,category,amount,booking_id,description)
                            VALUES(?,?,?,?,?,?,?)""",(next_code("PT","transactions"),str(date.today()),"Thu","Tiền tour",paid,bid,f"Thu booking {code}"))
                        st.success(f"Đã tạo booking {code}")
                        st.rerun()
    df=q("""SELECT b.code, c.code customer_code,c.name customer,t.code tour_code,t.name tour,
            b.pax,b.unit_price,b.discount,b.total,b.paid,b.payment_status,b.booking_status,b.booking_date
            FROM bookings b JOIN customers c ON c.id=b.customer_id JOIN tours t ON t.id=b.tour_id
            ORDER BY b.id DESC""")
    if not df.empty:
        view=df.copy()
        for col in ["unit_price","discount","total","paid"]: view[col]=view[col].map(money)
        st.dataframe(view,use_container_width=True)
    else: st.info("Chưa có booking.")

# ------------------------- OPERATIONS --------------------------
elif menu == "🧭 Điều hành":
    st.title("🧭 Điều hành tour")
    tours=q("SELECT id,code,name,departure,return_date FROM tours ORDER BY departure")
    guides=q("SELECT id,code,name,phone FROM guides WHERE status='Sẵn sàng' ORDER BY name")
    suppliers=q("SELECT id,code,name,supplier_type FROM suppliers ORDER BY name")
    if tours.empty:
        st.info("Hãy tạo tour trước.")
    else:
        with st.expander("➕ Lập kế hoạch điều hành"):
            with st.form("operation"):
                t=st.selectbox("Tour",tours.to_dict("records"),format_func=lambda x:f"{x['code']} - {x['name']} ({x['departure']})")
                g=st.selectbox("Hướng dẫn viên",guides.to_dict("records"),index=0 if not guides.empty else None,format_func=lambda x:f"{x['code']} - {x['name']}") if not guides.empty else None
                hotels=suppliers[suppliers["supplier_type"]=="Khách sạn"]
                vehicles=suppliers[suppliers["supplier_type"]=="Vận chuyển"]
                restaurants=suppliers[suppliers["supplier_type"]=="Nhà hàng"]
                def pick(df,label):
                    return st.selectbox(label,df.to_dict("records"),format_func=lambda x:f"{x['code']} - {x['name']}") if not df.empty else None
                h=pick(hotels,"Khách sạn")
                v=pick(vehicles,"Đơn vị vận chuyển")
                r=pick(restaurants,"Nhà hàng")
                status=st.selectbox("Trạng thái",["Chuẩn bị","Đã xác nhận","Đang chạy","Hoàn tất","Có sự cố"])
                st.caption("Checklist")
                a,b,c,d,e=st.columns(5)
                cv=a.checkbox("Xe")
                ch=b.checkbox("KS")
                cg=c.checkbox("HDV")
                cl=d.checkbox("DS khách")
                ci=e.checkbox("Bảo hiểm")
                notes=st.text_area("Ghi chú điều hành")
                if st.form_submit_button("Lưu kế hoạch",type="primary"):
                    execute("""INSERT INTO operations(tour_id,guide_id,vehicle_supplier_id,hotel_supplier_id,restaurant_supplier_id,status,
                    checklist_vehicle,checklist_hotel,checklist_guide,checklist_guestlist,checklist_insurance,notes)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (t["id"],g["id"] if g else None,v["id"] if v else None,h["id"] if h else None,r["id"] if r else None,status,int(cv),int(ch),int(cg),int(cl),int(ci),notes))
                    st.success("Đã lưu kế hoạch điều hành.")
                    st.rerun()
    df=q("""SELECT o.id,t.code tour_code,t.name tour,t.departure,g.name guide,
            o.status,o.checklist_vehicle,o.checklist_hotel,o.checklist_guide,
            o.checklist_guestlist,o.checklist_insurance,o.notes
            FROM operations o JOIN tours t ON t.id=o.tour_id
            LEFT JOIN guides g ON g.id=o.guide_id ORDER BY o.id DESC""")
    if not df.empty:
        st.dataframe(df,use_container_width=True)

# -------------------------- GUIDES ----------------------------
elif menu == "🎤 Hướng dẫn viên":
    st.title("🎤 Quản lý hướng dẫn viên")
    with st.expander("➕ Thêm HDV"):
        with st.form("guide_form"):
            c1,c2,c3=st.columns(3)
            name=c1.text_input("Họ tên *")
            phone=c2.text_input("Số điện thoại")
            email=c3.text_input("Email")
            languages=st.text_input("Ngoại ngữ")
            license_no=st.text_input("Số thẻ HDV")
            area=st.text_input("Khu vực phụ trách")
            daily_fee=st.number_input("Phí/ngày",min_value=0.0,step=100000.0)
            status=st.selectbox("Trạng thái",["Sẵn sàng","Đang dẫn tour","Nghỉ","Tạm khóa"])
            notes=st.text_area("Ghi chú")
            if st.form_submit_button("Lưu HDV",type="primary"):
                if not name.strip(): st.error("Tên HDV bắt buộc.")
                else:
                    code=next_code("HDV","guides")
                    execute("""INSERT INTO guides(code,name,phone,email,languages,license_no,area,daily_fee,status,notes)
                    VALUES(?,?,?,?,?,?,?,?,?,?)""",(code,name,phone,email,languages,license_no,area,daily_fee,status,notes))
                    st.success(f"Đã tạo {code}"); st.rerun()
    df=q("SELECT * FROM guides ORDER BY id DESC")
    if not df.empty:
        view=df.copy(); view["daily_fee"]=view["daily_fee"].map(money)
        st.dataframe(view,use_container_width=True)

# ------------------------- SUPPLIERS ---------------------------
elif menu == "🏨 Nhà cung cấp":
    st.title("🏨 Nhà cung cấp dịch vụ")
    with st.expander("➕ Thêm nhà cung cấp"):
        with st.form("supplier_form"):
            c1,c2,c3=st.columns(3)
            name=c1.text_input("Tên nhà cung cấp *")
            supplier_type=c2.selectbox("Loại",["Khách sạn","Vận chuyển","Nhà hàng","Điểm tham quan","Bảo hiểm","Khác"])
            phone=c3.text_input("Điện thoại")
            email=st.text_input("Email")
            address=st.text_input("Địa chỉ")
            contact=st.text_input("Người liên hệ")
            rating=st.slider("Đánh giá",0.0,5.0,4.0,0.1)
            notes=st.text_area("Ghi chú")
            if st.form_submit_button("Lưu nhà cung cấp",type="primary"):
                if not name.strip(): st.error("Tên nhà cung cấp bắt buộc.")
                else:
                    code=next_code("NCC","suppliers")
                    execute("""INSERT INTO suppliers(code,name,supplier_type,phone,email,address,contact_person,rating,notes)
                    VALUES(?,?,?,?,?,?,?,?,?)""",(code,name,supplier_type,phone,email,address,contact,rating,notes))
                    st.success(f"Đã tạo {code}"); st.rerun()
    df=q("SELECT * FROM suppliers ORDER BY id DESC")
    if not df.empty: st.dataframe(df,use_container_width=True)

# -------------------------- FINANCE ----------------------------
elif menu == "💰 Tài chính":
    st.title("💰 Tài chính & công nợ")
    b=q("SELECT * FROM bookings")
    tr=q("SELECT * FROM transactions ORDER BY id DESC")
    rev=b["total"].sum() if not b.empty else 0
    paid=b["paid"].sum() if not b.empty else 0
    costs=tr.loc[tr["trans_type"]=="Chi","amount"].sum() if not tr.empty else 0
    c1,c2,c3,c4=st.columns(4)
    c1.metric("Doanh thu",money(rev))
    c2.metric("Đã thu",money(paid))
    c3.metric("Công nợ",money(rev-paid))
    c4.metric("Chi phí ghi nhận",money(costs))
    st.divider()
    with st.expander("➕ Ghi nhận thu/chi"):
        with st.form("transaction"):
            c1,c2,c3=st.columns(3)
            typ=c1.selectbox("Loại",["Thu","Chi"])
            trans_date=c2.date_input("Ngày",value=date.today())
            category=c3.text_input("Hạng mục","Chi phí tour")
            amount=st.number_input("Số tiền",min_value=0.0,step=100000.0)
            description=st.text_input("Nội dung")
            if st.form_submit_button("Lưu giao dịch",type="primary"):
                if amount<=0: st.error("Số tiền phải lớn hơn 0.")
                else:
                    code=next_code("GD","transactions")
                    execute("""INSERT INTO transactions(code,trans_date,trans_type,category,amount,description)
                    VALUES(?,?,?,?,?,?)""",(code,str(trans_date),typ,category,amount,description))
                    st.success(f"Đã ghi nhận {code}"); st.rerun()
    if not tr.empty:
        view=tr.copy(); view["amount"]=view["amount"].map(money)
        st.dataframe(view,use_container_width=True)

# -------------------------- REPORTS ---------------------------
elif menu == "📈 Báo cáo":
    st.title("📈 Báo cáo & phân tích")
    b=q("""SELECT b.*,t.name tour,t.destination,c.name customer
           FROM bookings b JOIN tours t ON t.id=b.tour_id JOIN customers c ON c.id=b.customer_id""")
    if b.empty:
        st.info("Chưa có dữ liệu để báo cáo.")
    else:
        b["margin"]=b["total"]-b["pax"]*b["tour_id"].map(
            q("SELECT id,cost FROM tours").set_index("id")["cost"].to_dict()
        )
        c1,c2,c3=st.columns(3)
        c1.metric("Doanh thu",money(b.total.sum()))
        c2.metric("Số khách",int(b.pax.sum()))
        c3.metric("Booking",len(b))
        bytour=b.groupby("tour",as_index=False).agg(Doanh_thu=("total","sum"),Khach=("pax","sum"),Booking=("id","count"))
        st.subheader("Doanh thu theo tour")
        fig=px.bar(bytour,x="tour",y="Doanh_thu",text_auto=True)
        st.plotly_chart(fig,use_container_width=True)
        st.subheader("Bảng báo cáo")
        st.dataframe(bytour,use_container_width=True)
        st.download_button("⬇️ Xuất báo cáo CSV",bytour.to_csv(index=False).encode("utf-8-sig"),"bao_cao_tour.csv","text/csv")

# ---------------------- VOICE TO TEXT -------------------------
elif menu == "🎙️ Voice-to-Text":
    st.title("🎙️ Voice-to-Text tiếng Việt")
    st.write("Nói vào microphone, hệ thống chuyển giọng nói thành văn bản để dùng làm ghi chú tour, điều hành hoặc mô tả.")
    text = voice_to_text()
    if text:
        st.text_area("Văn bản nhận diện",value=text,height=180)
        st.download_button("⬇️ Lưu TXT",text.encode("utf-8"),"voice_note.txt","text/plain")
    st.info("Tính năng nhận diện dùng dịch vụ Google Speech Recognition nên cần Internet.")

# ---------------------- BACKUP / RESTORE ----------------------
elif menu == "💾 Sao lưu dữ liệu":
    st.title("💾 Sao lưu & khôi phục")
    st.warning("Hãy sao lưu định kỳ. File SQLite chứa toàn bộ dữ liệu khách hàng, booking và tài chính.")
    if st.button("📦 Tạo bản sao lưu SQLite",type="primary"):
        with open(DB,"rb") as f:
            st.download_button("⬇️ Tải file lu_hanh.db",f.read(),"lu_hanh_backup.db","application/octet-stream")
    st.subheader("Xuất dữ liệu Excel")
    output=io.BytesIO()
    with pd.ExcelWriter(output,engine="openpyxl") as writer:
        for table in ["tours","tour_days","customers","bookings","guides","suppliers","operations","transactions"]:
            q(f"SELECT * FROM {table}").to_excel(writer,index=False,sheet_name=table[:31])
    st.download_button("⬇️ Tải toàn bộ Excel",output.getvalue(),"lu_hanh_data.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# -------------------------- SETTINGS ---------------------------
elif menu == "⚙️ Cài đặt":
    st.title("⚙️ Cài đặt hệ thống")
    st.subheader("Thông tin hệ thống")
    st.write("**Phiên bản:** 2.0 - Tour nâng cao")
    st.write("**Cơ sở dữ liệu:** SQLite")
    st.write("**Ngôn ngữ:** Tiếng Việt")
    st.write("**Voice-to-Text:** Google Speech Recognition")
    st.divider()
    st.subheader("Đổi mật khẩu tài khoản hiện tại")
    with st.form("password"):
        old=st.text_input("Mật khẩu cũ",type="password")
        new=st.text_input("Mật khẩu mới",type="password")
        confirm=st.text_input("Nhập lại",type="password")
        if st.form_submit_button("Đổi mật khẩu"):
            h=hashlib.sha256(old.encode()).hexdigest()
            current=q("SELECT * FROM users WHERE username=? AND password=?",(st.session_state.user["username"],h),one=True)
            if not current: st.error("Mật khẩu cũ không đúng.")
            elif len(new)<6: st.error("Mật khẩu mới tối thiểu 6 ký tự.")
            elif new!=confirm: st.error("Mật khẩu xác nhận không khớp.")
            else:
                nh=hashlib.sha256(new.encode()).hexdigest()
                execute("UPDATE users SET password=? WHERE username=?",(nh,st.session_state.user["username"]))
                st.success("Đã đổi mật khẩu.")

st.caption("Lữ Hành Pro • Hệ thống mẫu quản lý doanh nghiệp du lịch lữ hành • Dữ liệu lưu bằng SQLite")
