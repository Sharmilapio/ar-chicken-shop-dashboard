"""
A.R Chicken Shop - Interactive Data Analytics Dashboard
Run locally with:  streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

# ----------------------------------------------------------------------------
# PAGE CONFIG
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="A.R Chicken Shop - Dashboard",
    page_icon="🐔",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------------------------------------------------------------
# THEME / CSS  (dark navy, matches the reference design)
# ----------------------------------------------------------------------------
st.markdown("""
<style>
    .stApp { background-color: #0a1128; color: #e6ecf5; }
    section[data-testid="stSidebar"] { background-color: #0d1a3b; }
    h1, h2, h3, h4 { color: #ffffff !important; }
    .block-container { padding-top: 1.5rem; }

    .kpi-card {
        background: linear-gradient(145deg, #10214f, #0d1a3b);
        border-radius: 12px;
        padding: 16px 18px;
        border: 1px solid #1e3a6b;
        text-align: center;
    }
    .kpi-title { font-size: 13px; color: #9fb4d9; margin-bottom: 6px; }
    .kpi-value {
        font-size: clamp(16px, 1.6vw, 26px);
        font-weight: 700;
        color: #ffffff;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .kpi-delta-up { font-size: 12px; color: #4ade80; }
    .kpi-delta-down { font-size: 12px; color: #f87171; }

    .highlight-card {
        border-radius: 10px;
        padding: 12px 14px;
        text-align: center;
        color: white;
    }
    .highlight-title { font-size: 12px; opacity: 0.85; }
    .highlight-value { font-size: 17px; font-weight: 700; margin-top: 4px; }

    .insight-box {
        background-color: #0d1a3b;
        border: 1px solid #1e3a6b;
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 6px;
    }
    .rating-badge {
        text-align: center;
        background: linear-gradient(145deg, #10214f, #0d1a3b);
        border-radius: 12px;
        padding: 18px;
        border: 1px solid #ffd54a;
    }
</style>
""", unsafe_allow_html=True)

CHICKEN_TYPES = ["Broiler", "Country Chicken", "Boneless", "Leg Piece", "Wings"]
DEFAULT_RATES = {"Broiler": 180, "Country Chicken": 320, "Boneless": 260,
                  "Leg Piece": 220, "Wings": 200}
REQUIRED_COLS = ["Date", "Chicken_Type", "Sold_KG", "Cost_Per_KG", "Wastage_KG", "Festival_Normal"]


# ----------------------------------------------------------------------------
# LOGIN GATE
# ----------------------------------------------------------------------------
def check_login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if st.session_state.logged_in:
        return

    try:
        valid_user = st.secrets["credentials"]["username"]
        valid_pass = st.secrets["credentials"]["password"]
    except Exception:
        valid_user, valid_pass = "admin", "chicken123"

    l, c, r = st.columns([1, 1.1, 1])
    with c:
        st.markdown(
            "<h1 style='text-align:center; margin-top:60px;'>🐔</h1>"
            "<h2 style='text-align:center;'>A.R Chicken Shop</h2>"
            "<p style='text-align:center; color:#9fb4d9;'>Sign in to view your dashboard</p>",
            unsafe_allow_html=True,
        )
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("🔓 Login", use_container_width=True)

        if submitted:
            if username == valid_user and password == valid_pass:
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Incorrect username or password.")
    st.stop()


check_login()


# ----------------------------------------------------------------------------
# DEMO DATA GENERATOR (used only if no file uploaded / demo button pressed)
# ----------------------------------------------------------------------------
def generate_demo_data(months=2, seed=42):
    rng = np.random.default_rng(seed)
    start = pd.Timestamp("2026-01-01")
    days = months * 30
    dates = pd.date_range(start, periods=days, freq="D")

    festival_days = {"2026-01-15", "2026-01-14", "2026-02-14"}  # Pongal, Valentine's etc.
    cost_map = {"Broiler": 120, "Country Chicken": 220, "Boneless": 180,
                "Leg Piece": 150, "Wings": 130}

    rows = []
    for d in dates:
        is_sunday = d.dayofweek == 6
        is_festival = d.strftime("%Y-%m-%d") in festival_days
        rain_drop = rng.random() < 0.12

        for ct in CHICKEN_TYPES:
            base = rng.uniform(15, 35)
            if is_sunday:
                base *= 1.35
            if is_festival:
                base *= 1.8
            if rain_drop:
                base *= 0.6

            sold = round(max(base, 2), 1)
            wastage = round(sold * rng.uniform(0.02, 0.09), 2)

            rows.append({
                "Date": d,
                "Chicken_Type": ct,
                "Sold_KG": sold,
                "Cost_Per_KG": cost_map[ct],
                "Wastage_KG": wastage,
                "Festival_Normal": "Festival" if is_festival else "Normal",
            })
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------
# SHOP CATALOG
# ----------------------------------------------------------------------------
PRODUCTS = [
    {"id": "broiler_skin", "name": "Broiler Chicken (With Skin)", "unit": "kg",
     "price": 180, "emoji": "🍗", "desc": "Farm fresh broiler, skin-on, cleaned & ready to cook."},
    {"id": "broiler_noskin", "name": "Broiler Chicken (Without Skin)", "unit": "kg",
     "price": 190, "emoji": "🍗", "desc": "Skinless broiler, low fat, ready to cook."},
    {"id": "leg_piece", "name": "Chicken Leg Piece", "unit": "kg",
     "price": 220, "emoji": "🍖", "desc": "Juicy bone-in leg pieces."},
    {"id": "boneless", "name": "Boneless Chicken", "unit": "kg",
     "price": 260, "emoji": "🍗", "desc": "Premium boneless cuts, curry ready."},
    {"id": "country", "name": "Country Chicken (Naatu Kozhi)", "unit": "kg",
     "price": 320, "emoji": "🐓", "desc": "Farm-raised, traditional taste."},
    {"id": "wings", "name": "Chicken Wings", "unit": "kg",
     "price": 200, "emoji": "🍗", "desc": "Perfect for grilling & frying."},
]

SPECIALS = [
    {"id": "chili_chicken", "name": "Chili Chicken", "unit": "plate",
     "price": 150, "emoji": "🌶️", "desc": "Freshly made hot & spicy chili chicken.",
     "from_hour": 17, "to_hour": 23},
]

ORDERS_FILE = "shop_orders.csv"


def _cart_total():
    cart = st.session_state.get("cart", {})
    total = 0
    for pid, qty in cart.items():
        item = next((p for p in PRODUCTS + SPECIALS if p["id"] == pid), None)
        if item:
            total += item["price"] * qty
    return total


def _save_order(name, phone, address, payment_mode):
    cart = st.session_state.get("cart", {})
    lines = []
    for pid, qty in cart.items():
        item = next((p for p in PRODUCTS + SPECIALS if p["id"] == pid), None)
        if item:
            lines.append(f"{item['name']} x{qty}{item['unit']}")
    order_id = "ARC" + datetime.now().strftime("%Y%m%d%H%M%S")
    row = pd.DataFrame([{
        "Order_ID": order_id,
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Customer_Name": name,
        "Phone": phone,
        "Address": address,
        "Items": " | ".join(lines),
        "Total": _cart_total(),
        "Payment_Mode": payment_mode,
        "Status": "New",
    }])
    try:
        existing = pd.read_csv(ORDERS_FILE)
        combined = pd.concat([existing, row], ignore_index=True)
    except FileNotFoundError:
        combined = row
    combined.to_csv(ORDERS_FILE, index=False)
    return order_id


def render_shop_page():
    if "cart" not in st.session_state:
        st.session_state.cart = {}

    # ---- Top banner ----
    st.markdown("""
    <div style="background: linear-gradient(135deg, #7c2d12, #dc2626);
                border-radius: 14px; padding: 26px 30px; margin-bottom: 20px;
                display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap;">
        <div>
            <div style="font-size:13px; color:#fecaca; letter-spacing:1px;">MOUTH-WATERING</div>
            <div style="font-size:32px; font-weight:800; color:white;">FRESH CHICKEN, DAILY</div>
            <div style="color:#fecaca; margin-top:6px;">Farm Fresh Meats — cleaned, cut & delivered fresh</div>
        </div>
        <div style="font-size:60px;">🐔</div>
    </div>
    """, unsafe_allow_html=True)

    tab_shop, tab_cart, tab_orders = st.tabs(["🛒 Shop", f"🧺 Cart ({sum(st.session_state.cart.values())})", "📦 My Orders"])

    # ---------------- SHOP TAB ----------------
    with tab_shop:
        now_hour = datetime.now().hour

        st.markdown("### 🌶️ Evening Specials")
        for item in SPECIALS:
            is_open = item["from_hour"] <= now_hour < item["to_hour"]
            c1, c2, c3 = st.columns([0.6, 3, 1.2])
            with c1:
                st.markdown(f"<div style='font-size:40px; text-align:center;'>{item['emoji']}</div>", unsafe_allow_html=True)
            with c2:
                st.markdown(f"**{item['name']}** — ₹{item['price']} / {item['unit']}")
                st.caption(item["desc"])
                if not is_open:
                    st.caption(f"⏰ Available {item['from_hour']}:00 – {item['to_hour']}:00 only. Come back this evening!")
            with c3:
                if is_open:
                    qty = st.number_input("Qty", min_value=1, value=1, step=1, key=f"qty_{item['id']}", label_visibility="collapsed")
                    if st.button(f"Add to Cart", key=f"add_{item['id']}", use_container_width=True):
                        st.session_state.cart[item["id"]] = st.session_state.cart.get(item["id"], 0) + qty
                        st.success(f"Added {item['name']} to cart!")
                        st.rerun()
                else:
                    st.button("🔒 Not available now", key=f"locked_{item['id']}", disabled=True, use_container_width=True)
        st.markdown("---")

        st.markdown("### 🍗 Our Fresh Chicken Range")
        cols = st.columns(3)
        for i, item in enumerate(PRODUCTS):
            with cols[i % 3]:
                st.markdown(f"""<div class="insight-box" style="text-align:center; min-height:190px;">
                    <div style="font-size:38px;">{item['emoji']}</div>
                    <div style="font-weight:700; margin:6px 0 2px;">{item['name']}</div>
                    <div style="color:#9fb4d9; font-size:12px; margin-bottom:6px;">{item['desc']}</div>
                    <div style="color:#ffd54a; font-weight:700; font-size:16px;">₹{item['price']} / {item['unit']}</div>
                </div>""", unsafe_allow_html=True)
                qty = st.number_input("Qty (kg)", min_value=0.5, value=1.0, step=0.5, key=f"qty_{item['id']}")
                if st.button("🛒 Add to Cart", key=f"add_{item['id']}", use_container_width=True):
                    st.session_state.cart[item["id"]] = st.session_state.cart.get(item["id"], 0) + qty
                    st.success(f"Added {qty}kg {item['name']} to cart!")
                    st.rerun()
                st.write("")

    # ---------------- CART TAB ----------------
    with tab_cart:
        cart = st.session_state.cart
        if not cart:
            st.info("Your cart is empty. Add items from the Shop tab!")
        else:
            st.markdown("### 🧺 Your Cart")
            for pid in list(cart.keys()):
                item = next((p for p in PRODUCTS + SPECIALS if p["id"] == pid), None)
                if not item:
                    continue
                cc1, cc2, cc3, cc4 = st.columns([3, 1.2, 1.2, 0.8])
                with cc1:
                    st.markdown(f"**{item['emoji']} {item['name']}**")
                with cc2:
                    st.write(f"{cart[pid]} {item['unit']}")
                with cc3:
                    st.write(f"₹{item['price'] * cart[pid]:,.0f}")
                with cc4:
                    if st.button("❌", key=f"rm_{pid}"):
                        del st.session_state.cart[pid]
                        st.rerun()

            st.markdown("---")
            total = _cart_total()
            st.markdown(f"<h3 style='text-align:right;'>Total: ₹{total:,.0f}</h3>", unsafe_allow_html=True)

            st.markdown("### 📋 Delivery Details")
            with st.form("checkout_form"):
                name = st.text_input("Full Name")
                phone = st.text_input("Phone Number")
                address = st.text_area("Delivery Address")
                payment = st.selectbox("Payment Mode", ["Cash on Delivery", "UPI", "Card"])
                place_order = st.form_submit_button("✅ Place Order", use_container_width=True, type="primary")

            if place_order:
                if not name or not phone or not address:
                    st.error("Please fill in your name, phone, and address.")
                else:
                    order_id = _save_order(name, phone, address, payment)
                    st.session_state.cart = {}
                    st.success(f"🎉 Order placed! Your Order ID is **{order_id}**. We'll contact you shortly.")
                    st.balloons()

    # ---------------- ORDERS TAB ----------------
    with tab_orders:
        st.markdown("### 📦 Order History")
        try:
            orders_df = pd.read_csv(ORDERS_FILE)
            st.dataframe(orders_df.sort_values("Timestamp", ascending=False), use_container_width=True)
            st.download_button("Download Orders CSV", orders_df.to_csv(index=False).encode("utf-8"),
                                file_name="shop_orders.csv", mime="text/csv")
        except FileNotFoundError:
            st.info("No orders placed yet.")



st.sidebar.markdown("## 🐔 A.R Chicken Shop")
if st.sidebar.button("🔒 Logout"):
    st.session_state.logged_in = False
    st.rerun()

st.sidebar.markdown("---")
page = st.sidebar.radio("Navigate", ["🛒 Shop / Order", "📊 Analytics Dashboard"], index=0)
st.sidebar.markdown("---")

if page == "🛒 Shop / Order":
    render_shop_page()
    st.stop()

st.sidebar.markdown("### 📁 Dataset")

uploaded_file = st.sidebar.file_uploader(
    "Upload monthly sales CSV (any column names)",
    type=["csv"],
    help="You'll match your columns to what the dashboard needs in the next step."
)

use_demo = False
if uploaded_file is None:
    st.sidebar.caption("No file yet? Try a demo dataset:")
    use_demo = st.sidebar.button("🎲 Generate Demo Dataset")

st.sidebar.markdown("---")

# ----------------------------------------------------------------------------
# LOAD RAW DATA (before mapping)
# ----------------------------------------------------------------------------
raw_df = None
is_demo = False
if uploaded_file is not None:
    try:
        raw_df = pd.read_csv(uploaded_file)
    except Exception as e:
        st.error(f"Could not read the file: {e}")
        st.stop()
elif use_demo:
    raw_df = generate_demo_data()
    st.session_state["_demo_df"] = raw_df
    is_demo = True
elif "_demo_df" in st.session_state:
    raw_df = st.session_state["_demo_df"]
    is_demo = True

if raw_df is None:
    st.title("🐔 A.R Chicken Shop – Data Analytics Dashboard")
    st.info("👈 Upload a monthly sales CSV from the sidebar, or click **Generate Demo Dataset** to explore the dashboard first.")
    st.stop()

# ----------------------------------------------------------------------------
# COLUMN MAPPING  (works with ANY column names in the uploaded file)
# ----------------------------------------------------------------------------
NEEDED = {
    "Date": "Date of sale",
    "Chicken_Type": "Chicken type / item name",
    "Sold_KG": "Quantity sold (kg)",
    "Cost_Per_KG": "Your cost/purchase price per kg",
    "Wastage_KG": "Wastage quantity (kg)",
    "Festival_Normal": "Festival or Normal day label",
}

if is_demo:
    # Demo data already uses the standard names — skip the mapping UI.
    mapping = {k: k for k in NEEDED}
    const_values = {}
else:
    st.markdown("## 🧩 Step 1: Match your columns")
    st.caption("Your file's columns don't need to match any fixed names. "
               "Just tell the dashboard which of your columns means what — one time.")

    cols_available = ["-- Not in my file --"] + list(raw_df.columns)
    mapping = {}
    const_values = {}

    map_c1, map_c2 = st.columns(2)
    field_items = list(NEEDED.items())
    for i, (field, label) in enumerate(field_items):
        target_col = map_c1 if i % 2 == 0 else map_c2
        # guess a sensible default: exact/partial name match
        guess_idx = 0
        for j, c in enumerate(raw_df.columns):
            if field.lower().replace("_", "") in c.lower().replace("_", "").replace(" ", ""):
                guess_idx = j + 1
                break
        choice = target_col.selectbox(
            f"{field.replace('_', ' ')}  —  {label}",
            cols_available, index=guess_idx, key=f"map_{field}"
        )
        mapping[field] = choice
        if choice == "-- Not in my file --":
            if field in ("Sold_KG",):
                const_values[field] = target_col.number_input(
                    f"Enter a fixed value for '{field}' (required)", value=0.0, key=f"const_{field}"
                )
            elif field == "Cost_Per_KG":
                const_values[field] = target_col.number_input(
                    "No cost column? Enter a flat cost per kg to use for all rows",
                    value=100.0, key=f"const_{field}"
                )
            elif field == "Wastage_KG":
                const_values[field] = 0.0
            elif field == "Festival_Normal":
                const_values[field] = "Normal"
            elif field == "Chicken_Type":
                const_values[field] = "General"

    st.markdown("---")
    confirmed = st.button("✅ Confirm mapping & build dashboard", type="primary")
    if not confirmed and "mapping_confirmed" not in st.session_state:
        st.stop()
    if confirmed:
        st.session_state["mapping_confirmed"] = True
        st.session_state["mapping"] = mapping
        st.session_state["const_values"] = const_values
    mapping = st.session_state.get("mapping", mapping)
    const_values = st.session_state.get("const_values", const_values)

# ----------------------------------------------------------------------------
# BUILD STANDARDIZED DATAFRAME FROM THE MAPPING
# ----------------------------------------------------------------------------
df = pd.DataFrame()
for field in NEEDED:
    col = mapping.get(field)
    if col and col != "-- Not in my file --":
        df[field] = raw_df[col]
    else:
        df[field] = const_values.get(field, 0)

try:
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
except Exception:
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

bad_dates = df["Date"].isna().sum()
if bad_dates > 0:
    st.warning(f"⚠️ {bad_dates} row(s) had a date that couldn't be understood and were dropped.")
    df = df.dropna(subset=["Date"])

for numcol in ["Sold_KG", "Cost_Per_KG", "Wastage_KG"]:
    df[numcol] = pd.to_numeric(df[numcol], errors="coerce").fillna(0)

df["Chicken_Type"] = df["Chicken_Type"].astype(str).str.strip()
df["Festival_Normal"] = df["Festival_Normal"].astype(str).str.strip().str.title()
df["Festival_Normal"] = df["Festival_Normal"].where(
    df["Festival_Normal"].isin(["Festival", "Normal"]), "Normal"
)

if df.empty:
    st.error("No usable rows found after mapping. Please check your file and column selections.")
    st.stop()

# ----------------------------------------------------------------------------
# SIDEBAR - PRICE CONTROLS  (dynamic: built from whatever chicken types are in the data)
# ----------------------------------------------------------------------------
detected_types = sorted(df["Chicken_Type"].dropna().unique().tolist())

st.sidebar.markdown("### 💰 Rates (₹ / kg)")
st.sidebar.caption("Change any rate — everything below recalculates instantly.")

if "rates" not in st.session_state:
    st.session_state.rates = {}

rates = {}
for ct in detected_types:
    default_val = st.session_state.rates.get(ct, DEFAULT_RATES.get(ct, 200))
    rates[ct] = st.sidebar.number_input(
        ct, min_value=0, value=int(default_val), step=5, key=f"rate_{ct}"
    )
st.session_state.rates = rates

st.sidebar.markdown("---")

if not is_demo:
    with st.sidebar.expander("🔁 Upload a different file / change mapping"):
        if st.button("Reset mapping"):
            st.session_state.pop("mapping_confirmed", None)
            st.session_state.pop("mapping", None)
            st.session_state.pop("const_values", None)
            st.rerun()

# ----------------------------------------------------------------------------
# CALCULATIONS (driven by the editable sidebar rates)
# ----------------------------------------------------------------------------
df["Rate_Per_KG"] = df["Chicken_Type"].map(rates)
df["Revenue"] = df["Sold_KG"] * df["Rate_Per_KG"]
df["Cost"] = df["Sold_KG"] * df["Cost_Per_KG"]
df["Profit"] = df["Revenue"] - df["Cost"]
df["Wastage_Loss"] = df["Wastage_KG"] * df["Cost_Per_KG"]
df["Day_Type"] = np.where(df["Date"].dt.dayofweek >= 5, "Weekend", "Weekday")
df["Month"] = df["Date"].dt.to_period("M").astype(str)

# ----------------------------------------------------------------------------
# SIDEBAR FILTERS (applied on top of calculations)
# ----------------------------------------------------------------------------
st.sidebar.markdown("### 🔍 Filters")
months = sorted(df["Month"].unique())
sel_month = st.sidebar.selectbox("Month", ["All"] + months)
sel_type = st.sidebar.selectbox("Day Type", ["All", "Weekday", "Weekend"])
sel_fest = st.sidebar.selectbox("Festival / Normal", ["All", "Festival", "Normal"])

f = df.copy()
if sel_month != "All":
    f = f[f["Month"] == sel_month]
if sel_type != "All":
    f = f[f["Day_Type"] == sel_type]
if sel_fest != "All":
    f = f[f["Festival_Normal"] == sel_fest]

if f.empty:
    st.warning("No rows match the selected filters.")
    st.stop()

daily = f.groupby("Date").agg(
    Sold_KG=("Sold_KG", "sum"),
    Revenue=("Revenue", "sum"),
    Cost=("Cost", "sum"),
    Profit=("Profit", "sum"),
    Wastage_KG=("Wastage_KG", "sum"),
).reset_index()

# ----------------------------------------------------------------------------
# HEADER
# ----------------------------------------------------------------------------
st.markdown(
    f"""
    <h1 style='text-align:center; margin-bottom:0;'>🐔 A.R CHICKEN SHOP – DATA ANALYTICS DASHBOARD</h1>
    <p style='text-align:center; color:#9fb4d9; margin-top:0;'>Business Overview & Performance Insights &nbsp;|&nbsp; Rates editable live from the sidebar</p>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------------
# KPI ROW
# ----------------------------------------------------------------------------
total_revenue = daily["Revenue"].sum()
total_profit = daily["Profit"].sum()
total_sold = daily["Sold_KG"].sum()
total_wastage = daily["Wastage_KG"].sum()
profit_margin = (total_profit / total_revenue * 100) if total_revenue else 0

kpi_cols = st.columns(5)
kpis = [
    ("💰 Total Revenue", f"₹ {total_revenue:,.0f}"),
    ("📈 Total Profit", f"₹ {total_profit:,.0f}"),
    ("🍗 Total Sold (KG)", f"{total_sold:,.1f}"),
    ("🗑️ Total Wastage (KG)", f"{total_wastage:,.1f}"),
    ("📊 Profit Margin", f"{profit_margin:,.1f}%"),
]
for col, (title, val) in zip(kpi_cols, kpis):
    col.markdown(f"""<div class="kpi-card">
        <div class="kpi-title">{title}</div>
        <div class="kpi-value">{val}</div>
    </div>""", unsafe_allow_html=True)

st.write("")

# ----------------------------------------------------------------------------
# BUSINESS HIGHLIGHTS ROW
# ----------------------------------------------------------------------------
best_sales_day = daily.loc[daily["Revenue"].idxmax()]
worst_sales_day = daily.loc[daily["Revenue"].idxmin()]
best_profit_day = daily.loc[daily["Profit"].idxmax()]
worst_wastage_day = daily.loc[daily["Wastage_KG"].idxmax()]
fest_rows = f[f["Festival_Normal"] == "Festival"]
if not fest_rows.empty:
    fest_daily = fest_rows.groupby("Date")["Revenue"].sum()
    best_fest_day = (fest_daily.idxmax(), fest_daily.max())
else:
    best_fest_day = (None, 0)

hl_cols = st.columns(5)
highlight_data = [
    ("HIGHEST SALES DAY", best_sales_day["Date"].strftime("%d-%b-%Y"), f"₹ {best_sales_day['Revenue']:,.0f}", "#2563eb"),
    ("LOWEST SALES DAY", worst_sales_day["Date"].strftime("%d-%b-%Y"), f"₹ {worst_sales_day['Revenue']:,.0f}", "#dc2626"),
    ("HIGHEST PROFIT DAY", best_profit_day["Date"].strftime("%d-%b-%Y"), f"₹ {best_profit_day['Profit']:,.0f}", "#16a34a"),
    ("HIGHEST WASTAGE DAY", worst_wastage_day["Date"].strftime("%d-%b-%Y"), f"{worst_wastage_day['Wastage_KG']:.1f} KG", "#ca8a04"),
    ("BEST FESTIVAL DAY", best_fest_day[0].strftime("%d-%b-%Y") if best_fest_day[0] is not None else "N/A",
     f"₹ {best_fest_day[1]:,.0f}", "#7c3aed"),
]
for col, (title, date_str, val, color) in zip(hl_cols, highlight_data):
    col.markdown(f"""<div class="highlight-card" style="background:{color};">
        <div class="highlight-title">{title}</div>
        <div class="highlight-value">{date_str}</div>
        <div class="highlight-value">{val}</div>
    </div>""", unsafe_allow_html=True)

st.write("")

# ----------------------------------------------------------------------------
# ROW: DAILY TREND | PROFIT VS LOSS | FESTIVAL VS NORMAL
# ----------------------------------------------------------------------------
c1, c2, c3 = st.columns([1.3, 1, 1])

with c1:
    fig = px.line(daily, x="Date", y="Revenue", markers=True, title="Daily Sales Trend (Revenue)")
    fig.update_traces(line_color="#38bdf8")
    fig.update_layout(template="plotly_dark", plot_bgcolor="#0d1a3b", paper_bgcolor="#0d1a3b", height=320,
                       title_x=0.5, title_xanchor="center")
    st.plotly_chart(fig, use_container_width=True)

with c2:
    profit_days = (daily["Profit"] > 0).sum()
    loss_days = (daily["Profit"] <= 0).sum()
    fig = go.Figure(data=[go.Pie(
        labels=["Profit Days", "Loss Days"], values=[profit_days, loss_days],
        hole=0.55, marker_colors=["#22c55e", "#ef4444"]
    )])
    total_days = profit_days + loss_days
    center_pct = int(profit_days / total_days * 100) if total_days else 0
    fig.update_traces(textinfo='label+percent', textposition='inside', insidetextorientation='radial')
    fig.update_layout(template="plotly_dark", plot_bgcolor="#0d1a3b", paper_bgcolor="#0d1a3b",
                       height=320, title="Profit vs Loss Days", title_x=0.5, title_xanchor="center")
    # show a bold percentage in the donut center for quick readability
    fig.add_annotation(text=f"{center_pct}%", x=0.5, y=0.5, font=dict(size=20, color='white'), showarrow=False)
    st.plotly_chart(fig, width='stretch')

with c3:
    fn = f.groupby("Festival_Normal")["Revenue"].mean().reindex(["Festival", "Normal"]).fillna(0)
    fig = px.bar(x=fn.index, y=fn.values, color=fn.index,
                 color_discrete_map={"Festival": "#22c55e", "Normal": "#3b82f6"},
                 title="Festival vs Normal Days (Avg Sales)")
    fig.update_traces(texttemplate='%{y:.0f}', textposition='inside', textfont_color='white', insidetextanchor='middle')
    fig.update_layout(template="plotly_dark", plot_bgcolor="#0d1a3b", paper_bgcolor="#0d1a3b",
                       height=320, showlegend=False, xaxis_title="", yaxis_title="Avg Revenue (₹)", title_x=0.5, title_xanchor="center")
    st.plotly_chart(fig, width='stretch')

# ----------------------------------------------------------------------------
# ROW: TOP 5 PROFIT DAYS | WASTAGE ANALYSIS | CORRELATION HEATMAP
# ----------------------------------------------------------------------------
c4, c5, c6 = st.columns([1, 1.3, 1])

with c4:
    top5 = daily.nlargest(5, "Profit").sort_values("Profit")
    fig = px.bar(top5, x="Profit", y=top5["Date"].dt.strftime("%d-%b-%Y"), orientation="h",
                 title="Top 5 Profit Days", color_discrete_sequence=["#22c55e"])
    fig.update_traces(texttemplate='%{x:,.0f}', textposition='inside', textfont_color='white', insidetextanchor='middle')
    fig.update_layout(template="plotly_dark", plot_bgcolor="#0d1a3b", paper_bgcolor="#0d1a3b",
                       height=340, yaxis_title="", xaxis_title="Profit (₹)", title_x=0.5, title_xanchor="center")
    st.plotly_chart(fig, width='stretch')

with c5:
    fig = px.bar(daily, x="Date", y="Wastage_KG", title="Wastage Analysis (KG)",
                 color_discrete_sequence=["#f97316"])
    fig.update_traces(texttemplate='%{y:.1f}', textposition='inside', textfont_color='white', insidetextanchor='middle')
    fig.update_layout(template="plotly_dark", plot_bgcolor="#0d1a3b", paper_bgcolor="#0d1a3b", height=340, title_x=0.5, title_xanchor="center")
    st.plotly_chart(fig, width='stretch')

with c6:
    corr = daily[["Sold_KG", "Revenue", "Cost", "Profit", "Wastage_KG"]].corr()
    fig = px.imshow(corr, text_auto=".2f", color_continuous_scale="RdYlGn", zmin=-1, zmax=1,
                     title="Correlation Heatmap")
    fig.update_layout(template="plotly_dark", plot_bgcolor="#0d1a3b", paper_bgcolor="#0d1a3b", height=340, title_x=0.5, title_xanchor="center")
    st.plotly_chart(fig, width='stretch')

# ----------------------------------------------------------------------------
# MONTHLY PROFIT COMPARISON  (the core ask: re-upload each month -> compare)
# ----------------------------------------------------------------------------
st.markdown("### 📅 Monthly Profit Comparison")
monthly = df.groupby("Month").agg(
    Revenue=("Revenue", "sum"), Profit=("Profit", "sum"), Sold_KG=("Sold_KG", "sum")
).reset_index()
monthly["Margin_%"] = (monthly["Profit"] / monthly["Revenue"] * 100).round(1)

mc1, mc2 = st.columns([1.4, 1])
with mc1:
    fig = go.Figure()
    fig.add_bar(x=monthly["Month"], y=monthly["Revenue"], name="Revenue", marker_color="#3b82f6")
    fig.add_bar(x=monthly["Month"], y=monthly["Profit"], name="Profit", marker_color="#22c55e")
    fig.update_layout(template="plotly_dark", plot_bgcolor="#0d1a3b", paper_bgcolor="#0d1a3b",
                       barmode="group", height=320, title="Revenue vs Profit by Month", title_x=0.5, title_xanchor="center")
    st.plotly_chart(fig, use_container_width=True)
with mc2:
    st.dataframe(monthly.style.format({"Revenue": "₹{:,.0f}", "Profit": "₹{:,.0f}",
                                        "Sold_KG": "{:,.1f}", "Margin_%": "{:.1f}%"}),
                 use_container_width=True, height=320)

# ----------------------------------------------------------------------------
# AUTO-GENERATED INSIGHTS + OVERALL RATING
# ----------------------------------------------------------------------------
st.markdown("### 🔎 Key Business Insights")

weekday_avg = f[f["Day_Type"] == "Weekday"]["Revenue"].sum() / max((f["Day_Type"] == "Weekday").sum(), 1)
weekend_avg = f[f["Day_Type"] == "Weekend"]["Revenue"].sum() / max((f["Day_Type"] == "Weekend").sum(), 1)
weekend_pct = ((weekend_avg - weekday_avg) / weekday_avg * 100) if weekday_avg else 0

normal_avg = f[f["Festival_Normal"] == "Normal"]["Revenue"].sum() / max((f["Festival_Normal"] == "Normal").sum(), 1)
fest_avg = f[f["Festival_Normal"] == "Festival"]["Revenue"].sum() / max((f["Festival_Normal"] == "Festival").sum(), 1)
fest_pct = ((fest_avg - normal_avg) / normal_avg * 100) if normal_avg else 0

wastage_pct = (total_wastage / total_sold * 100) if total_sold else 0

insights = [
    f"✅ Festival days generate **{fest_pct:.1f}%** more revenue than normal days." if normal_avg else "✅ Not enough festival data yet to compare.",
    f"✅ Weekend sales are **{weekend_pct:.1f}%** {'higher' if weekend_pct >= 0 else 'lower'} than weekday sales.",
    f"✅ Wastage is **{wastage_pct:.1f}%** of total sold quantity.",
    f"✅ Current profit margin stands at **{profit_margin:.1f}%** based on the rates set in the sidebar.",
]

# Render insights as separate boxes but inside a centered column so width matches the rating badge
cb_l, cb_c, cb_r = st.columns([0.2, 4.6, 0.2])
with cb_c:
    for ins in insights:
        st.markdown(f"<div class='insight-box' style='text-align:center'>{ins}</div>", unsafe_allow_html=True)
    st.write("")

# compute rating
if profit_margin >= 25:
    rating, stars = "EXCELLENT", "⭐⭐⭐⭐⭐"
elif profit_margin >= 15:
    rating, stars = "GOOD", "⭐⭐⭐⭐"
elif profit_margin >= 5:
    rating, stars = "AVERAGE", "⭐⭐⭐"
else:
    rating, stars = "NEEDS ATTENTION", "⭐⭐"

# Larger, centered rating badge (more prominent)
st.write("")
rate_l, rate_c, rate_r = st.columns([0.2, 4.6, 0.2])
with rate_c:
    st.markdown(f"""<div class="rating-badge" style="padding:40px; width:100%; margin-bottom:8px;">
        <div style="font-size:14px; color:#9fb4d9; letter-spacing:1px;">OVERALL PERFORMANCE</div>
        <div style="font-size:36px; font-weight:800; color:#ffd54a; margin:12px 0;">{rating}</div>
        <div style="font-size:36px;">{stars}</div>
    </div>""", unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# DOWNLOADS
# ----------------------------------------------------------------------------
# extra spacing added here so this row (full data / chickenmetrics / monthly summary)
# sits further down below the wider rating badge
st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
# Single row for downloads and center branding, placed directly under the badge
d1, d2, d3 = st.columns([1.2, 1.4, 1.2])
with d1:
    st.download_button("⬇️ Download Full Data (with Revenue/Profit)",
                        df.to_csv(index=False).encode("utf-8"),
                        file_name="ar_chicken_full_data.csv", mime="text/csv",
                        width='stretch')
with d2:
    st.markdown(
        "<p style='text-align:center; color:#38bdf8; font-style:italic; "
        "letter-spacing:0.5px; margin-top:12px;'>"
        "✨ A.R ChickenMetrics — Smart Poultry Analytics ✨</p>",
        unsafe_allow_html=True,
    )
with d3:
    st.download_button("⬇️ Download Monthly Summary",
                        monthly.to_csv(index=False).encode("utf-8"),
                        file_name="ar_chicken_monthly_summary.csv", mime="text/csv",
                        width='stretch')