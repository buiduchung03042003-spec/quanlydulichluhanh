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
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
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
    with st.expander("➕ Tạo tour mới", expanded=False):
        with st.form("tour_form"):
            c1,c2,c3 = st.columns(3)
            name = c1.text_input("Tên tour *")
            destination = c2.text_input("Điểm đến *")
            departure = c3.date_input("Ngày khởi hành", value=date.today())
            c1,c2,c3,c4 = st.columns(4)
            return_date = c1.date_input("Ngày kết thúc", value=date.today())
            duration = c2.text_input("Thời lượng", "3N2Đ")
            capacity = c3.number_input("Sức chứa", min_value=1, value=45)
            price = c4.number_input("Giá bán/người", min_value=0.0, step=100000.0)
            cost = st.number_input("Giá vốn/người", min_value=0.0, step=100000.0)
            status = st.selectbox("Trạng thái", ["Đang bán","Tạm dừng","Đã kết thúc","Nháp"])
            description = st.text_area("Mô tả")
            submit = st.form_submit_button("Lưu tour", type="primary")
            if submit:
                if not name.strip() or not destination.strip():
                    st.error("Tên tour và điểm đến là bắt buộc.")
                elif cost > price and price > 0:
                    st.warning("Giá vốn đang cao hơn giá bán. Hãy kiểm tra lại.")
                else:
                    code = next_code("TOUR","tours")
                    execute("""INSERT INTO tours(code,name,destination,departure,return_date,duration,
                    capacity,price,cost,status,description) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                    (code,name,destination,str(departure),str(return_date),duration,capacity,price,cost,status,description))
                    st.success(f"Đã tạo {code}")
                    st.rerun()

    df = q("SELECT * FROM tours ORDER BY id DESC")
    if not df.empty:
        search = st.text_input("🔎 Tìm tour")
        if search:
            df = df[df.astype(str).apply(lambda x: x.str.contains(search, case=False).any(), axis=1)]
        show = df.copy()
        show["Giá bán"] = show["price"].map(money)
        show["Giá vốn"] = show["cost"].map(money)
        st.dataframe(show[["code","name","destination","departure","return_date","capacity","Giá bán","Giá vốn","status"]], use_container_width=True)
        st.download_button("⬇️ Xuất CSV", df.to_csv(index=False).encode("utf-8-sig"), "tours.csv","text/csv")
    else:
        st.info("Chưa có tour.")

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
        for table in ["tours","customers","bookings","guides","suppliers","operations","transactions"]:
            q(f"SELECT * FROM {table}").to_excel(writer,index=False,sheet_name=table[:31])
    st.download_button("⬇️ Tải toàn bộ Excel",output.getvalue(),"lu_hanh_data.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# -------------------------- SETTINGS ---------------------------
elif menu == "⚙️ Cài đặt":
    st.title("⚙️ Cài đặt hệ thống")
    st.subheader("Thông tin hệ thống")
    st.write("**Phiên bản:** 1.0")
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
