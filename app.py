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
import base64
import os

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
    /* =====================================================================
       VIOLET THEME — Deep purple bg, violet/pink accents, stylish & modern
    ===================================================================== */

    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap');

    .stApp {
        background: linear-gradient(135deg, #0d0618 0%, #130a2b 50%, #0d0618 100%);
        color: #ede9fe;
        font-family: 'Inter', sans-serif;
    }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a0a35 0%, #0d0618 100%);
        border-right: 1px solid #6d28d940;
    }
    h1, h2, h3, h4 { color: #f3e8ff !important; }
    .block-container { padding-top: 1.5rem; }
    [data-testid="stSidebarNav"] { display: none !important; }

    /* Tabs */
    button[data-baseweb="tab"] { color: #a78bfa !important; }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #c084fc !important;
        border-bottom: 3px solid #a855f7 !important;
    }

    /* Text inputs */
    div[data-testid="stTextInput"] input {
        border-radius: 10px !important;
        border: 1px solid #7c3aed50 !important;
        background: #1a0a35 !important;
        color: #ede9fe !important;
    }

    /* Sidebar labels */
    div[data-testid="stSidebar"] label { color: #c4b5fd !important; }
    div[data-testid="stSidebar"] p    { color: #c4b5fd !important; }

    /* KPI cards */
    .kpi-card {
        background: linear-gradient(145deg, #2d1060, #1a0a35);
        border-radius: 16px;
        padding: 18px 20px;
        border: 1px solid #7c3aed50;
        text-align: center;
        box-shadow: 0 4px 20px rgba(139,92,246,0.15);
    }
    .kpi-title  { font-size: 13px; color: #a78bfa; margin-bottom: 6px; }
    .kpi-value  { font-size: 28px; font-weight: 800; color: #f3e8ff; }
    .kpi-delta-up   { font-size: 12px; color: #4ade80; }
    .kpi-delta-down { font-size: 12px; color: #f87171; }

    .highlight-card {
        border-radius: 12px;
        padding: 12px 14px;
        text-align: center;
        color: white;
    }
    .highlight-title { font-size: 12px; opacity: 0.85; }
    .highlight-value { font-size: 17px; font-weight: 700; margin-top: 4px; }

    .insight-box {
        background: linear-gradient(145deg, #2d1060, #1a0a35);
        border: 1px solid #7c3aed40;
        border-radius: 12px;
        padding: 14px 18px;
        margin-bottom: 8px;
        box-shadow: 0 2px 12px rgba(139,92,246,0.10);
    }
    .rating-badge {
        text-align: center;
        background: linear-gradient(145deg, #2d1060, #1a0a35);
        border-radius: 14px;
        padding: 18px;
        border: 1px solid #a855f7;
        box-shadow: 0 4px 20px rgba(168,85,247,0.20);
    }

    /* Dataframe */
    .stDataFrame { border: 1px solid #7c3aed40 !important; border-radius: 12px; }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: #0d0618; }
    ::-webkit-scrollbar-thumb { background: #7c3aed; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)

CHICKEN_TYPES = ["Broiler", "Country Chicken", "Boneless", "Leg Piece", "Wings"]
DEFAULT_RATES = {"Broiler": 180, "Country Chicken": 320, "Boneless": 260,
                  "Leg Piece": 220, "Wings": 200}
REQUIRED_COLS = ["Date", "Chicken_Type", "Sold_KG", "Cost_Per_KG", "Wastage_KG", "Festival_Normal"]


# ----------------------------------------------------------------------------
# ADMIN LOGIN (used only to protect Orders / Analytics — Shop stays public)
# ----------------------------------------------------------------------------
def _valid_credentials():
    try:
        return st.secrets["credentials"]["username"], st.secrets["credentials"]["password"]
    except Exception:
        return "admin", "chicken123"


# Query param helpers (wrap streamlit API differences across versions)
def get_query_params():
    # Modern Streamlit (>=1.30): st.query_params is a Mapping-like object.
    try:
        qp = st.query_params
        return {k: [v] for k, v in qp.items()}
    except Exception:
        pass
    if hasattr(st, "experimental_get_query_params"):
        try:
            return st.experimental_get_query_params()
        except Exception:
            pass
    # fallback: empty dict
    return {}


def set_query_params(**params):
    # Modern Streamlit (>=1.30): st.query_params supports item assignment.
    try:
        st.query_params.clear()
        for k, v in params.items():
            st.query_params[k] = v
        return True
    except Exception:
        pass
    if hasattr(st, "experimental_set_query_params"):
        try:
            return st.experimental_set_query_params(**params)
        except Exception:
            pass
    # fallback: store in session_state (best-effort)
    st.session_state["_qp_fallback"] = params
    return None


def is_admin_logged_in():
    return st.session_state.get("logged_in", False)


def render_login_form(context="sidebar"):
    valid_user, valid_pass = _valid_credentials()
    form_key = f"login_form_{context}"
    with st.form(form_key):
        username = st.text_input("Username", key=f"user_{context}")
        password = st.text_input("Password", type="password", key=f"pass_{context}")
        submitted = st.form_submit_button("🔓 Login", use_container_width=True)
    if submitted:
        if username == valid_user and password == valid_pass:
            st.session_state.logged_in = True
            # If this was the standalone login page, respect the ?next= query param and redirect
            if context == "standalone":
                params = get_query_params()
                next_target = params.get("next", ["dashboard"])[0] or "dashboard"
                # Map logical targets to query page values
                if next_target in ("orders", "dashboard", "admin"):
                    set_query_params(page=next_target)
                else:
                    set_query_params(page="dashboard")
                st.rerun()
            else:
                st.rerun()
        else:
            st.error("Incorrect username or password.")


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
ASSETS_DIR = "image"

def _img_b64(path):
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        return None


def _product_image_html(item_id, height="120px", filename=None):
    # If the product dict specifies an explicit filename (e.g. "chicken.png"),
    # use that directly instead of guessing <item_id>.<ext>.
    #
    # FIX: switched object-fit from "cover" to "contain" (with a matching
    # dark-navy background) so product photos are never cropped. "cover"
    # was scaling the image up to fill the box and slicing off whatever
    # didn't fit (e.g. the rooster's tail getting cut on the Country
    # Chicken card). "contain" shrinks the whole image to fit inside the
    # box instead, so the full photo is always visible.
    if filename:
        path = os.path.join(ASSETS_DIR, "products", filename)
        b64 = _img_b64(path)
        if b64:
            ext = filename.rsplit(".", 1)[-1].lower()
            mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp"}.get(ext, "png")
            return (f'<img src="data:image/{mime};base64,{b64}" '
                    f'style="width:100%; height:{height}; object-fit:contain; '
                    f'background:#0d1a3b; border-radius:10px; margin-bottom:8px;">')
        return None
    for ext in ("jpg", "jpeg", "png", "webp"):
        path = os.path.join(ASSETS_DIR, "products", f"{item_id}.{ext}")
        b64 = _img_b64(path)
        if b64:
            mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp"}[ext]
            return (f'<img src="data:image/{mime};base64,{b64}" '
                    f'style="width:100%; height:{height}; object-fit:contain; '
                    f'background:#0d1a3b; border-radius:10px; margin-bottom:8px;">')
    return None


def _category_image_html(filename, height="40px"):
    """Loads image/categories/<filename>. Returns None if not found (caller falls back to emoji)."""
    path = os.path.join(ASSETS_DIR, "categories", filename)
    b64 = _img_b64(path)
    if not b64:
        return None
    ext = filename.rsplit(".", 1)[-1].lower()
    mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp"}.get(ext, "png")
    return (f'<img src="data:image/{mime};base64,{b64}" '
            f'style="width:100%; height:{height}; object-fit:contain; '
            f'border-radius:8px;">')


PRODUCTS = [
    {"id": "broiler_skin", "name": "Broiler Chicken (With Skin)", "unit": "kg",
     "price": 180, "emoji": "🐔", "desc": "Farm fresh broiler, skin-on, cleaned & ready to cook."},
    {"id": "broiler_noskin", "name": "Broiler Chicken (Without Skin)", "unit": "kg",
     "price": 190, "emoji": "🍗", "desc": "Skinless broiler, low fat, ready to cook."},
    {"id": "leg_piece", "name": "Chicken Leg Piece", "unit": "kg",
     "price": 220, "emoji": "🍖", "desc": "Juicy bone-in leg pieces.", "image_file": "chicken.png"},
    {"id": "boneless", "name": "Boneless Chicken", "unit": "kg",
     "price": 260, "emoji": "🥩", "desc": "Premium boneless cuts, curry ready."},
    {"id": "country", "name": "Country Chicken (Naatu Kozhi)", "unit": "kg",
     "price": 320, "emoji": "🐓", "desc": "Farm-raised, traditional taste.", "image_file": "country.png"},
    {"id": "wings", "name": "Chicken Wings", "unit": "kg",
     "price": 200, "emoji": "🪽", "desc": "Perfect for grilling & frying."},
]

SPECIALS = [
    {"id": "chili_chicken", "name": "Chili Chicken", "unit": "plate",
     "price": 50, "emoji": "🌶️", "desc": "Freshly made hot & spicy chili chicken.",
     "from_hour": 17, "to_hour": 22},
]

ORDERS_FILE = "shop_orders.csv"
PREBOOKINGS_FILE = "prebookings.csv"

# ---- Bulk discount: Buy 10kg+ of broiler, get ₹10 off per kg ----
BULK_DISCOUNT_ITEM_IDS = {"broiler_skin", "broiler_noskin"}
BULK_DISCOUNT_THRESHOLD_KG = 10
BULK_DISCOUNT_PER_KG = 10


def _effective_price(item, qty):
    """Returns the per-unit price after applying the bulk discount, if eligible."""
    price = item["price"]
    if item["id"] in BULK_DISCOUNT_ITEM_IDS and qty >= BULK_DISCOUNT_THRESHOLD_KG:
        price = max(price - BULK_DISCOUNT_PER_KG, 0)
    return price


def _cart_total():
    cart = st.session_state.get("cart", {})
    total = 0
    for pid, qty in cart.items():
        item = next((p for p in PRODUCTS + SPECIALS if p["id"] == pid), None)
        if item:
            total += _effective_price(item, qty) * qty
    return total


def _save_order(name, phone, address, payment_mode):
    cart = st.session_state.get("cart", {})
    lines = []
    for pid, qty in cart.items():
        item = next((p for p in PRODUCTS + SPECIALS if p["id"] == pid), None)
        if item:
            eff_price = _effective_price(item, qty)
            tag = f" (bulk @₹{eff_price})" if eff_price < item["price"] else ""
            lines.append(f"{item['name']} x{qty}{item['unit']}{tag}")
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


def _save_prebooking(item_name, name, phone, qty, preferred_date):
    """Saves a pre-booking request for an out-of-hours special (e.g. Chili Chicken)."""
    pb_id = "PB" + datetime.now().strftime("%Y%m%d%H%M%S")
    row = pd.DataFrame([{
        "Prebooking_ID": pb_id,
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Customer_Name": name,
        "Phone": phone,
        "Item": item_name,
        "Qty": qty,
        "Preferred_Date": preferred_date.strftime("%Y-%m-%d"),
        "Status": "Pending",
    }])
    try:
        existing = pd.read_csv(PREBOOKINGS_FILE)
        combined = pd.concat([existing, row], ignore_index=True)
    except FileNotFoundError:
        combined = row
    combined.to_csv(PREBOOKINGS_FILE, index=False)
    return pb_id


def render_shop_page():
    if "cart" not in st.session_state:
        st.session_state.cart = {}
    cart_count = sum(st.session_state.cart.values())

    # ---- Nav bar CSS — violet theme ----
    st.markdown("""
    <style>
    /* Search input */
    .st-key-shop_search_query input {
        background-color: #1a0a35 !important;
        color: #ede9fe !important;
        border: 1px solid #7c3aed60 !important;
        box-shadow: 0 0 0 2px #7c3aed10 !important;
    }
    .st-key-shop_search_query input::placeholder { color: #7c5cbf !important; }

    /* Login / Cart buttons */
    .st-key-nav_login_btn button, .st-key-nav_admin_btn button, .st-key-nav_cart_btn button {
        background: linear-gradient(135deg, #2d1060, #1a0a35) !important;
        color: #c4b5fd !important;
        border: 1px solid #7c3aed60 !important;
        font-weight: 700 !important;
        box-shadow: 0 2px 12px rgba(124,58,237,0.2) !important;
    }
    .st-key-nav_login_btn button:hover {
        background: linear-gradient(135deg, #7c3aed, #a855f7) !important;
        color: #fff !important;
        border-color: #a855f7 !important;
    }
    .st-key-nav_cart_btn button:hover {
        background: linear-gradient(135deg, #6d28d9, #9333ea) !important;
        color: #fff !important;
        border-color: #9333ea !important;
    }
    .st-key-nav_admin_btn button { opacity: 0.75 !important; }

    .nav-box { height:64px; display:flex; align-items:center; box-sizing:border-box; }

    div[data-testid="column"]:has(.nav-box),
    div[data-testid="column"]:has(.st-key-shop_search_query),
    div[data-testid="column"]:has(.st-key-nav_login_btn),
    div[data-testid="column"]:has(.st-key-nav_admin_btn),
    div[data-testid="column"]:has(.st-key-nav_cart_btn) {
        display:flex; align-items:stretch;
    }
    .st-key-shop_search_query { height:64px; display:flex; align-items:center; }
    .st-key-shop_search_query > div,
    .st-key-shop_search_query > div > div,
    .st-key-shop_search_query [data-testid="stTextInput"],
    .st-key-shop_search_query [data-testid="stTextInput"] > div {
        height:64px !important; display:flex !important;
        align-items:center !important; width:100% !important;
    }
    .st-key-shop_search_query input {
        height:64px !important; min-height:64px !important;
        box-sizing:border-box !important;
        background: #1a0a35 !important;
        color: #ede9fe !important;
        border: 1px solid #7c3aed60 !important;
        border-radius: 12px !important;
        padding: 0 16px !important;
        font-size: 15px !important; width: 100% !important;
    }
    .st-key-shop_search_query input::placeholder { color: #7c5cbf !important; }
    .st-key-nav_login_btn, .st-key-nav_admin_btn, .st-key-nav_cart_btn {
        height:64px; display:flex; align-items:center;
    }
    .st-key-nav_login_btn button, .st-key-nav_admin_btn button, .st-key-nav_cart_btn button {
        height:64px !important; min-height:64px !important;
        width:100% !important;
        padding: 0 10px !important;
        display:flex !important; align-items:center !important;
        justify-content:center !important;
        white-space:nowrap !important; font-size:14px !important;
        box-sizing:border-box !important; border-radius:12px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # ---- Top nav bar (seamless single bar, no image logo) ----
    # If a suggestion chip was clicked on the previous run, apply it to the
    # search box BEFORE the widget is created below.
    if "_pending_search_query" in st.session_state:
        st.session_state["shop_search_query"] = st.session_state.pop("_pending_search_query")

    # NOTE: nav_login and nav_cart were too narrow before (0.55 / 0.75),
    # which clipped the button labels ("Login" showed as "Logi", "Cart (0)"
    # got cut off). Widened both and trimmed nav_search slightly to
    # compensate so the whole row still fits.
    nav_logo, nav_addr, nav_search, nav_login, nav_cart = st.columns(
        [2.0, 1.4, 3.9, 0.95, 1.05], gap="small"
    )

    with nav_logo:
        st.markdown("""
        <div class="nav-box" style="background: linear-gradient(135deg, #2d1060, #1a0a35);
                    padding: 0 16px; border-radius: 12px; gap:12px;
                    border: 1px solid #7c3aed50; white-space:nowrap;">
            <div style="background: linear-gradient(135deg, #a855f7, #7c3aed); color:white;
                        width:42px; height:42px; min-width:42px; border-radius:10px;
                        display:flex; align-items:center; justify-content:center;
                        font-weight:900; font-size:16px; letter-spacing:0.5px;">AR</div>
            <div>
                <div style="font-weight:900; color:#e879f9; font-size:17px; letter-spacing:0.3px; line-height:1.15; white-space:nowrap;">A.R CHICKEN SHOP</div>
                <div style="font-size:11px; color:#a78bfa; margin-top:2px; white-space:nowrap;">Farm fresh meats &amp; fresh cuts</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with nav_addr:
        st.markdown("""
        <div class="nav-box" style="background: linear-gradient(135deg, #2d1060, #1a0a35);
                    padding: 0 12px; gap:10px; border-radius: 12px;
                    border: 1px solid #7c3aed50;">
            <span style="font-size:20px;">📍</span>
            <div style="font-size:13px; color:#ede9fe; line-height:1.4;"><b>Address</b><br>
                <span style="color:#a78bfa; font-size:12px;">Coimbatore, Tamil Nadu</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with nav_search:
        search_query = st.text_input(
            "Search", placeholder="🔍 Search chicken, cuts...",
            key="shop_search_query", label_visibility="collapsed",
        )
        st.markdown(
            '<style>.st-key-shop_search_query, .st-key-shop_search_query > div, '
            '.st-key-shop_search_query input { width:100% !important; } '
            '.st-key-shop_search_query input { font-size:15px !important; }</style>',
            unsafe_allow_html=True,
        )

    with nav_login:
        if is_admin_logged_in():
            st.button("👤 Admin", key="nav_admin_btn", use_container_width=True, disabled=True)
        else:
            if st.button("👤 Login", key="nav_login_btn", use_container_width=True):
                # Navigate to the dedicated login page (/login) — this is the
                # ONLY login entry point in the app now.
                set_query_params(page="login")
                st.rerun()

    with nav_cart:
        if st.button(f"🛒 Cart ({cart_count})", key="nav_cart_btn", use_container_width=True):
            set_query_params(page="cart")
            st.rerun()

    # ---- Live suggestion dropdown (professional style, appears while typing) ----
    #
    # NOTE ON THE FIX BELOW:
    # Previously this block opened a `<div class="suggest-wrap">` with one
    # st.markdown() call, rendered several st.columns() rows in between,
    # and then closed the div with a second st.markdown() call. In
    # Streamlit each st.markdown() call renders into its OWN separate DOM
    # node, so the opening/closing tags never actually wrapped the columns
    # in between them — the white "suggest-wrap" background never applied
    # to the rows. Since `.suggest-row` sets dark text (color:#222) meant
    # to sit on that (never-rendered) white background, the text rendered
    # near-invisible directly on the app's dark navy page background.
    #
    # Fix: give each row its own self-contained background/shadow so it
    # doesn't depend on an outer wrapper div that Streamlit can't create
    # across multiple markdown/column calls.
    live_term = (search_query or "").strip().lower()
    if live_term:
        all_items = PRODUCTS + SPECIALS
        suggestions = [p for p in all_items if live_term in p["name"].lower()][:5]
        if suggestions:
            st.markdown("""
            <style>
            .suggest-wrap {
                background:#ffffff; border-radius:12px; padding:10px;
                box-shadow:0 6px 20px rgba(0,0,0,0.25); margin-top:-6px; margin-bottom:10px;
                border:1px solid #f0f0f0;
            }
            .suggest-row {
                display:flex; align-items:center; gap:10px; padding:10px 12px;
                border-radius:8px; color:#222; flex-wrap:wrap;
                background:#ffffff;                       /* FIX: self-contained bg */
                box-shadow:0 2px 8px rgba(0,0,0,0.10);      /* FIX: definition without wrapper */
                margin-bottom:6px;
            }
            .suggest-row:hover { background:#fff0f3; }
            .suggest-name { font-weight:600; font-size:15px; color:#222; white-space:nowrap; }
            .suggest-price { font-size:13px; color:#b0103c; font-weight:700; margin-left:auto; white-space:nowrap; }
            [class^="st-key-suggest_"] button {
                background:#ffffff !important; color:#b0103c !important;
                border:1px solid #eee !important; font-weight:700 !important;
                box-shadow:0 2px 6px rgba(0,0,0,0.12) !important; border-radius:8px !important;
                white-space:nowrap !important; min-width:80px !important;
            }
            [class^="st-key-suggest_"] button:hover {
                background:#fff0f3 !important; border-color:#b0103c !important;
            }
            </style>
            """, unsafe_allow_html=True)
            # Each row is rendered as its own self-contained white card (see
            # .suggest-row fix above) instead of relying on an outer wrapper
            # div that can't actually enclose the st.columns() rows.
            for s_idx, s_item in enumerate(suggestions):
                row_l, row_r = st.columns([6, 1.4], gap="small")
                with row_l:
                    st.markdown(
                        f'<div class="suggest-row">'
                        f'<span style="font-size:18px;">{s_item["emoji"]}</span>'
                        f'<span class="suggest-name">{s_item["name"]}</span>'
                        f'<span class="suggest-price">₹{s_item["price"]}/{s_item["unit"]}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                with row_r:
                    if st.button("Select", key=f"suggest_{s_idx}_{s_item['id']}", use_container_width=True):
                        st.session_state["_pending_search_query"] = s_item["name"]
                        st.rerun()
        else:
            st.markdown(
                '<div class="suggest-wrap" style="text-align:center; color:#999; '
                'font-size:13px; padding:12px; background:#ffffff; border-radius:12px; '
                'box-shadow:0 6px 20px rgba(0,0,0,0.25); margin-bottom:10px;">No matching items</div>',
                unsafe_allow_html=True,
            )

    st.write("")

    # ---- Top banner ----
    banner_mime = None
    banner_b64 = None
    for ext, mime in [("jpg", "jpeg"), ("jpeg", "jpeg"), ("png", "png"), ("webp", "webp")]:
        b64 = _img_b64(os.path.join(ASSETS_DIR, f"banner.{ext}"))
        if b64:
            banner_b64, banner_mime = b64, mime
            break


    # ---- Promo strip (A.R Bulk Club) ----
    p1, p2 = st.columns([3.2, 1])
    with p1:
        st.markdown("""
        <div style="background: linear-gradient(90deg, #b0103c, #e2557c); border-radius: 12px; padding: 16px 24px;
                    display:flex; align-items:center; gap:16px; height:88px; box-sizing:border-box;">
            <div style="background:white; border-radius:50%; width:52px; height:52px; display:flex;
                        align-items:center; justify-content:center; font-size:24px; flex-shrink:0;">🐔</div>
<div style="color:white;">
                <div style="font-weight:800; font-size:20px;">A.R Bulk Club</div>
                <div style="font-size:15px; opacity:0.9;">Buy 10kg+ Broiler & enjoy ₹10 off per kg, always.</div>
            </div>        </div>
        """, unsafe_allow_html=True)
    with p2:
        # Know More button — white background, height matched exactly to
        # the red "A.R Bulk Club" card (88px) so both sit flush together.
        st.markdown("""
        <style>
        .st-key-promo_know_more_btn { height:59px; display:flex; align-items:center; }
        .st-key-promo_know_more_btn button {
            background: linear-gradient(135deg, #be185d, #ec4899) !important;
            color:#ffffff !important;
            border: none !important;
            font-weight:700 !important;
            height:88px !important;
            min-height:88px !important;
            width:100% !important;
            border-radius:12px !important;
            box-shadow: 0 4px 18px rgba(236,72,153,0.35) !important;
            box-sizing:border-box !important;
            font-size:15px !important;
        }
        .st-key-promo_know_more_btn button:hover {
            background: linear-gradient(135deg, #9d174d, #db2777) !important;
            box-shadow: 0 6px 24px rgba(236,72,153,0.5) !important;
        }
        </style>
        """, unsafe_allow_html=True)
        if st.button("Know More", use_container_width=True, key="promo_know_more_btn"):
            st.toast("Buy 10kg or more of Broiler Chicken (with or without skin) and get ₹10 off per kg — applied automatically at checkout!")

    # ---- Explore by Category ----
    st.write("")
    cat_l, cat_r = st.columns([3, 1])
    with cat_l:
        st.markdown("**Explore by Category**")
        st.caption("Farm Fresh Meats — pick your cut")
    with cat_r:
        st.markdown(
            "<div style='text-align:right; color:#9fb4d9; font-size:13px;'>🛵 Delivery in <b>60 Minutes</b></div>",
            unsafe_allow_html=True,
        )
    cat_cols = st.columns(6)
    categories = [
        ("🐔", "Broiler", "hen.png"),
        ("🍗", "Leg Piece", "chicken.png"),
        ("🥩", "Boneless", "boneless.png"),
        ("🐓", "Country", "country.png"),
        ("🪽", "Wings", "wings.png"),
        ("🌶️", "Evening Special", "ready_to_cook.png"),
    ]
    for col, (emoji, label, img_file) in zip(cat_cols, categories):
        img_html = _category_image_html(img_file, height="40px")
        visual = img_html if img_html else f"<div style='font-size:24px;'>{emoji}</div>"
        col.markdown(
            f"<div style='text-align:center; background:linear-gradient(145deg,#2d1060,#1a0a35); border:1px solid #7c3aed50; "
            f"border-radius:12px; padding:10px 4px; box-shadow:0 2px 12px rgba(124,58,237,0.15);'>"
            f"<div style='height:40px; display:flex; align-items:center; justify-content:center;'>{visual}</div>"
            f"<div style='font-size:11px; color:#c4b5fd; margin-top:4px; font-weight:600;'>{label}</div></div>",
            unsafe_allow_html=True,
        )
    st.write("")

    tab_shop, tab_orders = st.tabs(["🛒 Shop", "📦 My Orders"])

    # ---------------- SHOP TAB ----------------
    with tab_shop:
        now_hour = datetime.now().hour

        st.markdown("###  Evening Specials")
        for item in SPECIALS:
            is_open = item["from_hour"] <= now_hour < item["to_hour"]

            def _fmt_hour(h):
                suffix = "AM" if h < 12 else "PM"
                h12 = h % 12
                if h12 == 0:
                    h12 = 12
                return f"{h12} {suffix}"

            c1, c2, c3 = st.columns([0.6, 3, 1.2])
            with c1:
                img_html = _product_image_html(item["id"], height="70px")
                visual = img_html if img_html else f"<div style='font-size:40px; text-align:center;'>{item['emoji']}</div>"
                st.markdown(visual, unsafe_allow_html=True)
            with c2:
                st.markdown(f"**{item['name']}** — ₹{item['price']} / {item['unit']}")
                st.caption(item["desc"])
                if is_open:
                    st.markdown(
                        f"<span style='color:#4ade80; font-weight:700; font-size:13px;'>"
                        f"✅ Available now ({_fmt_hour(item['from_hour'])} – {_fmt_hour(item['to_hour'])})</span>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.caption(f"⏰ Available {_fmt_hour(item['from_hour'])} – {_fmt_hour(item['to_hour'])} only. Come back this evening!")
                    st.markdown(
                        "<span style='color:#facc15; font-weight:600; font-size:13px;'>"
                        "📅 Want it today evening? You can pre-book — just let us know at least "
                        "<b>1 day in advance</b> and we'll have it ready for you!</span>",
                        unsafe_allow_html=True,
                    )
            with c3:
                if is_open:
                    qty = st.number_input("Qty", min_value=1, value=1, step=1, key=f"qty_{item['id']}", label_visibility="collapsed")
                    if st.button(f"Add to Cart", key=f"add_{item['id']}", use_container_width=True):
                        st.session_state.cart[item["id"]] = st.session_state.cart.get(item["id"], 0) + qty
                        st.session_state["show_inline_cart"] = True
                        st.rerun()
                else:
                    if st.button("📅 Pre-book for tomorrow", key=f"prebook_{item['id']}", use_container_width=True):
                        st.session_state[f"show_prebook_form_{item['id']}"] = True

                    if st.session_state.get(f"show_prebook_form_{item['id']}"):
                        with st.form(f"prebook_form_{item['id']}"):
                            pb_name = st.text_input("Your Name")
                            pb_phone = st.text_input("Phone Number")
                            pb_qty = st.number_input("Qty (plates)", min_value=1, value=1, step=1)
                            pb_date = st.date_input(
                                "Preferred Date",
                                min_value=datetime.now().date() + pd.Timedelta(days=1),
                            )
                            pb_submit = st.form_submit_button("Confirm Pre-booking")

                        if pb_submit:
                            if not pb_name or not pb_phone:
                                st.error("Please enter your name and phone number.")
                            else:
                                pb_id = _save_prebooking(item["name"], pb_name, pb_phone, pb_qty, pb_date)
                                st.success(
                                    f"🎉 Pre-booked! Your ID is **{pb_id}**. "
                                    f"We'll have it ready on {pb_date.strftime('%d-%b-%Y')} evening."
                                )
                                st.session_state[f"show_prebook_form_{item['id']}"] = False
        st.markdown("---")

        search_term = (search_query or "").strip().lower()
        filtered_products = [p for p in PRODUCTS if search_term in p["name"].lower()] if search_term else PRODUCTS

        if search_term:
            st.markdown(f"### 🍗 Search Results for “{search_query}” ({len(filtered_products)})")
        else:
            st.markdown("### 🍗 Our Fresh Chicken Range")

        if not filtered_products:
            st.info("No products match your search. Try a different term.")

        # ---- Product card CSS — uniform size, original navy aesthetic ----
        st.markdown("""
        <style>
        .product-card {
            background: linear-gradient(145deg, #2d1060, #1a0a35);
            border: 1px solid #7c3aed50;
            border-radius: 16px;
            padding: 16px 14px 12px 14px;
            text-align: center;
            height: 310px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: flex-start;
            box-shadow: 0 4px 20px rgba(124,58,237,0.18);
            box-sizing: border-box;
            overflow: hidden;
        }
        .product-card img {
            width: 100%;
            height: 130px;
            object-fit: contain;
            background: #0d0618;
            border-radius: 10px;
            margin-bottom: 8px;
            flex-shrink: 0;
        }
        .product-card .p-emoji {
            font-size: 42px;
            height: 130px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }
        .product-card .p-name {
            font-weight: 700;
            font-size: 14px;
            color: #f3e8ff;
            margin: 4px 0 2px;
            line-height: 1.3;
        }
        .product-card .p-desc {
            font-size: 11px;
            color: #a78bfa;
            margin-bottom: 4px;
            line-height: 1.3;
            flex-grow: 1;
        }
        .product-card .p-price {
            font-size: 17px;
            font-weight: 800;
            color: #e879f9;
            margin-top: 2px;
        }
        .product-card .p-discount {
            font-size: 11px;
            color: #4ade80;
            margin-top: 2px;
        }
        /* Qty input */
        [class^="st-key-qty_"] input,
        [class*=" st-key-qty_"] input {
            background: #1a0a35 !important;
            color: #ede9fe !important;
            border: 1px solid #7c3aed50 !important;
            border-radius: 8px !important;
        }
        /* Add to Cart button */
        [class^="st-key-add_"] button,
        [class*=" st-key-add_"] button {
            background: linear-gradient(90deg, #7c3aed, #a855f7) !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 10px !important;
            font-weight: 700 !important;
            box-shadow: 0 2px 12px rgba(168,85,247,0.35) !important;
        }
        [class^="st-key-add_"] button:hover,
        [class*=" st-key-add_"] button:hover {
            background: linear-gradient(90deg, #6d28d9, #9333ea) !important;
        }
        </style>
        """, unsafe_allow_html=True)

        cols = st.columns(3)
        for i, item in enumerate(filtered_products):
            with cols[i % 3]:
                img_html = _product_image_html(item["id"], height="130px", filename=item.get("image_file"))
                if img_html:
                    visual = img_html
                else:
                    visual = f'<div class="p-emoji">{item["emoji"]}</div>'
                discount_badge = ""
                if item["id"] in BULK_DISCOUNT_ITEM_IDS:
                    discount_badge = (
                        f'<div class="p-discount">🎉 Buy {BULK_DISCOUNT_THRESHOLD_KG}kg+ & save ₹{BULK_DISCOUNT_PER_KG}/kg</div>'
                    )
                card_html = (
                    f'<div class="product-card">'
                    f'{visual}'
                    f'<div class="p-name">{item["name"]}</div>'
                    f'<div class="p-desc">{item["desc"]}</div>'
                    f'<div class="p-price">₹{item["price"]} / {item["unit"]}</div>'
                    f'{discount_badge}'
                    f'</div>'
                )
                st.markdown(card_html, unsafe_allow_html=True)
                qty = st.number_input("Qty (kg)", min_value=0.5, value=1.0, step=0.5, key=f"qty_{item['id']}")
                if item["id"] in BULK_DISCOUNT_ITEM_IDS and qty >= BULK_DISCOUNT_THRESHOLD_KG:
                    st.caption(f"✅ Bulk discount applied: ₹{_effective_price(item, qty)}/kg")
                if st.button("🛒 Add to Cart", key=f"add_{item['id']}", use_container_width=True):
                    st.session_state.cart[item["id"]] = st.session_state.cart.get(item["id"], 0) + qty
                    st.session_state["show_inline_cart"] = True
                    st.rerun()
                st.write("")

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


def render_cart_page():
    """Standalone cart + checkout page — no login required."""
    st.markdown("""
    <style>
    section[data-testid="stSidebar"] { display: none !important; }
    /* violet theme for cart page inputs */
    div[data-testid="stTextInput"] input,
    div[data-testid="stTextArea"] textarea {
        background: #1a0a35 !important;
        color: #ede9fe !important;
        border: 1px solid #7c3aed60 !important;
        border-radius: 10px !important;
    }
    div[data-testid="stSelectbox"] > div {
        background: #1a0a35 !important;
        color: #ede9fe !important;
        border: 1px solid #7c3aed60 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Header with back button ──
    h1, h2 = st.columns([1, 5])
    with h1:
        if st.button("← Back to Shop", key="cart_back_btn"):
            set_query_params(page="")
            st.rerun()
    with h2:
        st.markdown("<h1 style='margin:0; color:#f3e8ff;'>🧺 Your Cart</h1>", unsafe_allow_html=True)

    st.markdown("---")

    cart = st.session_state.get("cart", {})

    if not cart:
        st.markdown("""
        <div style='text-align:center; padding:60px 20px;'>
            <div style='font-size:64px;'>🛒</div>
            <div style='font-size:22px; color:#a78bfa; margin-top:16px; font-weight:700;'>Your cart is empty!</div>
            <div style='font-size:15px; color:#7c5cbf; margin-top:8px;'>Go back to the shop and add some items.</div>
        </div>
        """, unsafe_allow_html=True)
        st.stop()

    # ── Cart items ──
    st.markdown("### 🛍️ Order Summary")
    for pid in list(cart.keys()):
        item = next((p for p in PRODUCTS + SPECIALS if p["id"] == pid), None)
        if not item:
            continue
        eff_price = _effective_price(item, cart[pid])
        with st.container():
            st.markdown(f"""
            <div style='background:linear-gradient(145deg,#2d1060,#1a0a35);
                        border:1px solid #7c3aed40; border-radius:12px;
                        padding:14px 20px; margin-bottom:10px;
                        display:flex; align-items:center; justify-content:space-between;'>
                <span style='font-size:16px; font-weight:700; color:#f3e8ff;'>{item['emoji']} {item['name']}</span>
                <span style='color:#a78bfa;'>{cart[pid]} {item['unit']}</span>
                <span style='color:#e879f9; font-weight:800; font-size:17px;'>₹{eff_price * cart[pid]:,.0f}</span>
            </div>
            """, unsafe_allow_html=True)
            if eff_price < item["price"]:
                st.caption(f"🎉 Bulk discount applied: ₹{item['price']} → ₹{eff_price}/{item['unit']}")
            if st.button("❌ Remove", key=f"cartpg_rm_{pid}"):
                del st.session_state.cart[pid]
                st.rerun()

    st.markdown("---")
    total = _cart_total()
    st.markdown(
        f"<div style='text-align:right; font-size:26px; font-weight:900; color:#e879f9;'>"
        f"Total: ₹{total:,.0f}</div>",
        unsafe_allow_html=True,
    )

    st.write("")
    st.markdown("### 📋 Delivery Details")

    with st.form("cart_page_checkout"):
        co1, co2 = st.columns(2)
        with co1:
            name    = st.text_input("Full Name",     placeholder="Enter your name")
            phone   = st.text_input("Phone Number",  placeholder="Enter phone number")
        with co2:
            address = st.text_area("Delivery Address", placeholder="Enter delivery address", height=120)
            payment = st.selectbox("Payment Mode", ["Cash on Delivery", "UPI", "Card"])

        b1, b2 = st.columns(2)
        with b1:
            place_order = st.form_submit_button("✅ Place Order", use_container_width=True, type="primary")
        with b2:
            clear_cart  = st.form_submit_button("🗑️ Clear Cart",  use_container_width=True)

    if place_order:
        if not name or not phone or not address:
            st.error("Please fill in your name, phone, and address.")
        else:
            order_id = _save_order(name, phone, address, payment)
            st.session_state.cart = {}
            st.success(f"🎉 Order placed! Your Order ID is **{order_id}**. We'll contact you shortly.")
            st.balloons()

    if clear_cart:
        st.session_state.cart = {}
        st.rerun()


def render_orders_page():
    st.markdown(
        "<h1 style='text-align:center;'>📦 Customer Orders</h1>"
        "<p style='text-align:center; color:#9fb4d9;'>Everything customers have ordered from the Shop page</p>",
        unsafe_allow_html=True,
    )
    try:
        orders_df = pd.read_csv(ORDERS_FILE)
    except FileNotFoundError:
        st.info("No orders placed yet. Once customers check out from the Shop page, they'll show up here.")
        return

    orders_df["Timestamp"] = pd.to_datetime(orders_df["Timestamp"], errors="coerce")
    orders_df = orders_df.sort_values("Timestamp", ascending=False)

    # ---- Summary KPIs ----
    total_orders = len(orders_df)
    total_revenue = orders_df["Total"].sum()
    unique_customers = orders_df["Phone"].nunique()
    avg_order = orders_df["Total"].mean() if total_orders else 0

    k1, k2, k3, k4 = st.columns(4)
    for col, (title, val) in zip(
        [k1, k2, k3, k4],
        [
            ("📦 Total Orders", f"{total_orders}"),
            ("💰 Total Order Value", f"₹ {total_revenue:,.0f}"),
            ("👥 Unique Customers", f"{unique_customers}"),
            ("📊 Avg Order Value", f"₹ {avg_order:,.0f}"),
        ],
    ):
        col.markdown(f"""<div class="kpi-card">
            <div class="kpi-title">{title}</div>
            <div class="kpi-value">{val}</div>
        </div>""", unsafe_allow_html=True)

    st.write("")

    # ---- Filters ----
    f1, f2 = st.columns(2)
    with f1:
        search_name = st.text_input("🔍 Search by customer name or phone")
    with f2:
        status_filter = st.selectbox("Status", ["All"] + sorted(orders_df["Status"].dropna().unique().tolist()))

    filtered = orders_df.copy()
    if search_name:
        mask = (filtered["Customer_Name"].astype(str).str.contains(search_name, case=False, na=False) |
                filtered["Phone"].astype(str).str.contains(search_name, case=False, na=False))
        filtered = filtered[mask]
    if status_filter != "All":
        filtered = filtered[filtered["Status"] == status_filter]

    st.markdown(f"### 🧾 Order List ({len(filtered)})")
    st.dataframe(
        filtered[["Order_ID", "Timestamp", "Customer_Name", "Phone", "Address",
                  "Items", "Total", "Payment_Mode", "Status"]],
        use_container_width=True,
        height=420,
    )

    st.download_button(
        "⬇️ Download All Orders (CSV)",
        orders_df.to_csv(index=False).encode("utf-8"),
        file_name="shop_orders.csv", mime="text/csv",
    )


def render_prebookings_page():
    st.markdown(
        "<h1 style='text-align:center;'>📅 Pre-bookings</h1>"
        "<p style='text-align:center; color:#9fb4d9;'>Evening Special items customers have pre-booked in advance</p>",
        unsafe_allow_html=True,
    )
    # Force all 4 KPI cards to equal height
    st.markdown("""
    <style>
    .pb-kpi-row { display: flex; gap: 16px; margin-bottom: 16px; }
    .pb-kpi-card {
        flex: 1;
        background: linear-gradient(145deg, #2d1060, #1a0a35);
        border: 1px solid #7c3aed50;
        border-radius: 16px;
        padding: 20px 16px;
        text-align: center;
        box-shadow: 0 4px 20px rgba(124,58,237,0.15);
        min-height: 110px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        box-sizing: border-box;
    }
    .pb-kpi-title { font-size: 13px; color: #a78bfa; margin-bottom: 10px; font-weight: 600; }
    .pb-kpi-value { font-size: 30px; font-weight: 800; color: #f3e8ff; }
    </style>
    """, unsafe_allow_html=True)

    try:
        pb_df = pd.read_csv(PREBOOKINGS_FILE)
    except FileNotFoundError:
        st.info("No pre-bookings yet. Once customers pre-book an Evening Special, they'll show up here.")
        return

    pb_df["Timestamp"] = pd.to_datetime(pb_df["Timestamp"], errors="coerce")

    def _pb_total(row):
        item = next((p for p in SPECIALS if p["name"] == row["Item"]), None)
        return item["price"] * row["Qty"] if item else 0

    pb_df["Total"] = pb_df.apply(_pb_total, axis=1)
    pb_df = pb_df.sort_values("Preferred_Date")

    # ---- Summary KPIs — equal size cards ----
    total_prebookings = len(pb_df)
    total_value = pb_df["Total"].sum()
    unique_customers = pb_df["Phone"].nunique()
    pending_count = (pb_df["Status"] == "Pending").sum()

    st.markdown(f"""
    <div class="pb-kpi-row">
        <div class="pb-kpi-card">
            <div class="pb-kpi-title">📅 Total Pre-bookings</div>
            <div class="pb-kpi-value">{total_prebookings}</div>
        </div>
        <div class="pb-kpi-card">
            <div class="pb-kpi-title">💰 Total Value</div>
            <div class="pb-kpi-value">₹ {total_value:,.0f}</div>
        </div>
        <div class="pb-kpi-card">
            <div class="pb-kpi-title">👥 Unique Customers</div>
            <div class="pb-kpi-value">{unique_customers}</div>
        </div>
        <div class="pb-kpi-card">
            <div class="pb-kpi-title">⏳ Pending</div>
            <div class="pb-kpi-value">{pending_count}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.write("")

    # ---- Filters ----
    f1, f2 = st.columns(2)
    with f1:
        search_name = st.text_input("🔍 Search by customer name or phone", key="pb_search")
    with f2:
        status_filter = st.selectbox("Status", ["All"] + sorted(pb_df["Status"].dropna().unique().tolist()), key="pb_status")

    filtered = pb_df.copy()
    if search_name:
        mask = (filtered["Customer_Name"].astype(str).str.contains(search_name, case=False, na=False) |
                filtered["Phone"].astype(str).str.contains(search_name, case=False, na=False))
        filtered = filtered[mask]
    if status_filter != "All":
        filtered = filtered[filtered["Status"] == status_filter]

    st.markdown(f"### 🧾 Pre-booking List ({len(filtered)})")
    st.dataframe(
        filtered[["Prebooking_ID", "Timestamp", "Customer_Name", "Phone", "Item", "Qty",
                  "Preferred_Date", "Total", "Status"]],
        use_container_width=True,
        height=420,
    )

    st.download_button(
        "⬇️ Download Pre-bookings (CSV)",
        pb_df.to_csv(index=False).encode("utf-8"),
        file_name="prebookings.csv", mime="text/csv",
    )


def render_admin_dashboard():
    st.markdown("<h1 style='text-align:center;'>📊 Admin Dashboard</h1>", unsafe_allow_html=True)
    # Orders table + simple KPIs
    try:
        orders_df = pd.read_csv(ORDERS_FILE)
    except FileNotFoundError:
        st.info("No orders placed yet.")
        return

    total_orders = len(orders_df)
    total_revenue = orders_df["Total"].sum()
    unique_customers = orders_df["Phone"].nunique()
    k1, k2, k3 = st.columns(3)
    k1.metric("Total Orders", total_orders)
    k2.metric("Total Revenue", f"₹{total_revenue:,.0f}")
    k3.metric("Unique Customers", unique_customers)

    st.markdown("---")
    st.markdown("### 📦 Recent Orders")
    st.dataframe(orders_df.sort_values("Timestamp", ascending=False).head(50), use_container_width=True)



params = get_query_params()
route_page = params.get("page", [""])[0]
route_next = params.get("next", [""])[0]
ADMIN_ROUTES = ("dashboard", "admin", "orders")

# ---------------------------------------------------------------------------
# /cart — public cart + checkout page. No login required.
# ---------------------------------------------------------------------------
if route_page == "cart":
    st.markdown("""
        <style>
        section[data-testid="stSidebar"] { display: none !important; }
        </style>
    """, unsafe_allow_html=True)
    render_cart_page()
    st.stop()

# ---------------------------------------------------------------------------
# /login — standalone page. No sidebar, no nav, nothing but the form.
# ---------------------------------------------------------------------------
if route_page == "login":
    if is_admin_logged_in():
        set_query_params(page=route_next if route_next in ADMIN_ROUTES else "dashboard")
        st.rerun()
    st.markdown("""
        <style>
        section[data-testid="stSidebar"] { display: none !important; }

        /* --- Login page polish -------------------------------------------------
           The password field's native "show/hide password" eye icon and
           Streamlit's built-in "Press Enter to submit form" hint were
           rendering in light/default colors, overlapping each other and
           clashing with the dark theme. Give the input more right-padding
           so typed/placeholder text never runs under the eye icon, and
           restyle the hint to sit neatly below the field in dark colors
           instead of floating as a stray white tooltip box. */
        div[data-testid="stTextInput"] input {
            padding-right: 44px !important;
            background-color: #10214f !important;
            color: #e6ecf5 !important;
            border: 1px solid #1e3a6b !important;
        }
        div[data-testid="stTextInput"] button {
            color: #9fb4d9 !important;
        }
        div[data-testid="InputInstructions"] {
            background: transparent !important;
            color: #6b7fa3 !important;
            font-size: 11px !important;
            text-align: right !important;
            opacity: 0.8;
        }
        </style>
    """, unsafe_allow_html=True)
    st.markdown("<h1 style='text-align:center;'>🔒 Admin Login</h1>", unsafe_allow_html=True)
    # Wider center column (was 1:1:1, cramping the password field + eye
    # icon together) so there's breathing room on both desktop and mobile.
    l, c, r = st.columns([1, 1.6, 1])
    with c:
        render_login_form(context="standalone")
    st.stop()

# ---------------------------------------------------------------------------
# Public storefront — the default route. No sidebar / nav bar at all here;
# admins reach navigation only by logging in (via the header Login/Cart).
# ---------------------------------------------------------------------------
if route_page not in ADMIN_ROUTES:
    st.markdown("""
        <style>
        section[data-testid="stSidebar"] { display: none !important; }
        </style>
    """, unsafe_allow_html=True)
    render_shop_page()
    st.stop()

# ---------------------------------------------------------------------------
# Everything below is admin-only (dashboard / orders). Not logged in yet?
# Bounce straight to /login and come right back here after success.
# ---------------------------------------------------------------------------
if not is_admin_logged_in():
    set_query_params(page="login", next=route_page)
    st.rerun()

st.sidebar.markdown("## 🐔 A.R Chicken Shop — Admin")
st.sidebar.markdown("---")

admin_page = st.sidebar.radio(
    "Navigate",
    ["📊 Analytics Dashboard", "📦 Customer Orders", "📅 Pre-bookings"],
    index=1 if route_page == "orders" else (2 if route_page == "prebookings" else 0),
)
if st.sidebar.button("🚪 Logout", use_container_width=True):
    st.session_state.logged_in = False
    set_query_params(page="")
    st.rerun()

st.sidebar.markdown("---")

if admin_page == "📦 Customer Orders":
    render_orders_page()
    st.stop()

if admin_page == "📅 Pre-bookings":
    render_prebookings_page()
    st.stop()

# Falls through to the full Analytics Dashboard (dataset upload, mapping,
# rates, filters, charts) below.

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
c1, c2, c3 = st.columns([1, 1, 1])

with c1:
    fig = px.line(daily, x="Date", y="Revenue", markers=True, title="Daily Sales Trend (Revenue)")
    fig.update_traces(line_color="#38bdf8")
    fig.update_layout(template="plotly_dark", plot_bgcolor="#0d1a3b", paper_bgcolor="#0d1a3b",
                       height=340, title_x=0.5, title_xanchor='center', title_font_size=12, title_font_color="#ffffff", margin=dict(t=40))
    st.plotly_chart(fig, use_container_width=True)

with c2:
    profit_days = (daily["Profit"] > 0).sum()
    loss_days = (daily["Profit"] <= 0).sum()
    fig = go.Figure(data=[go.Pie(
        labels=["Profit Days", "Loss Days"], values=[profit_days, loss_days],
        hole=0.55, marker_colors=["#22c55e", "#ef4444"]
    )])
    fig.update_layout(template="plotly_dark", plot_bgcolor="#0d1a3b", paper_bgcolor="#0d1a3b",
                       height=340, title="Profit vs Loss Days", title_x=0.5, title_xanchor='center', title_font_size=12, title_font_color="#ffffff", margin=dict(t=40))
    st.plotly_chart(fig, use_container_width=True)

with c3:
    fn = f.groupby("Festival_Normal")["Revenue"].mean().reindex(["Festival", "Normal"]).fillna(0)
    fig = px.bar(x=fn.index, y=fn.values, color=fn.index,
                 color_discrete_map={"Festival": "#22c55e", "Normal": "#3b82f6"},
                 title="Festival vs Normal Days (Avg Sales)")
    fig.update_layout(template="plotly_dark", plot_bgcolor="#0d1a3b", paper_bgcolor="#0d1a3b",
                       height=340, title_x=0.5, title_xanchor='center', title_font_size=12, title_font_color="#ffffff", showlegend=False, xaxis_title="", yaxis_title="Avg Revenue (₹)", margin=dict(t=40))
    st.plotly_chart(fig, use_container_width=True)

# ----------------------------------------------------------------------------
# ROW: TOP 5 PROFIT DAYS | WASTAGE ANALYSIS | CORRELATION HEATMAP
# ----------------------------------------------------------------------------
c4, c5, c6 = st.columns([1, 1, 1])

with c4:
    top5 = daily.nlargest(5, "Profit").sort_values("Profit")
    fig = px.bar(top5, x="Profit", y=top5["Date"].dt.strftime("%d-%b-%Y"), orientation="h",
                 title="Top 5 Profit Days", color_discrete_sequence=["#22c55e"])
    fig.update_layout(template="plotly_dark", plot_bgcolor="#0d1a3b", paper_bgcolor="#0d1a3b",
                       height=340, title_x=0.5, title_xanchor='center', title_font_size=12, title_font_color="#ffffff", yaxis_title="", xaxis_title="Profit (₹)", margin=dict(t=40))
    st.plotly_chart(fig, use_container_width=True)

with c5:
    fig = px.bar(daily, x="Date", y="Wastage_KG", title="Wastage Analysis (KG)",
                 color_discrete_sequence=["#f97316"])
    fig.update_layout(template="plotly_dark", plot_bgcolor="#0d1a3b", paper_bgcolor="#0d1a3b",
                       height=340, title_x=0.5, title_xanchor='center', title_font_size=12, title_font_color="#ffffff", margin=dict(t=40))
    st.plotly_chart(fig, use_container_width=True)

with c6:
    corr = daily[["Sold_KG", "Revenue", "Cost", "Profit", "Wastage_KG"]].corr()
    fig = px.imshow(corr, text_auto=".2f", color_continuous_scale="RdYlGn", zmin=-1, zmax=1,
                     title="Correlation Heatmap")
    fig.update_layout(template="plotly_dark", plot_bgcolor="#0d1a3b", paper_bgcolor="#0d1a3b",
                       height=340, title_x=0.5, title_xanchor='center', title_font_size=12, title_font_color="#ffffff", margin=dict(t=40))
    st.plotly_chart(fig, use_container_width=True)

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
                       barmode="group", height=340, title="Revenue vs Profit by Month", title_x=0.5, title_xanchor='center', title_font_size=12, title_font_color="#ffffff", margin=dict(t=40))
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
for ins in insights:
    st.markdown(f"<div class='insight-box'>{ins}</div>", unsafe_allow_html=True)

if profit_margin >= 25:
    rating, stars = "EXCELLENT", "⭐⭐⭐⭐⭐"
elif profit_margin >= 15:
    rating, stars = "GOOD", "⭐⭐⭐⭐"
elif profit_margin >= 5:
    rating, stars = "AVERAGE", "⭐⭐⭐"
else:
    rating, stars = "NEEDS ATTENTION", "⭐⭐"

st.markdown("<div style='height:26px;'></div>", unsafe_allow_html=True)
rate_l, rate_c, rate_r = st.columns([0.6, 2.4, 0.6])
with rate_c:
    st.markdown(f"""<div class="rating-badge" style="padding:32px;">
        <div style="font-size:15px; color:#9fb4d9; letter-spacing:1px;">OVERALL PERFORMANCE</div>
        <div style="font-size:30px; font-weight:800; color:#ffd54a; margin:12px 0;">{rating}</div>
        <div style="font-size:32px;">{stars}</div>
    </div>""", unsafe_allow_html=True)
st.markdown("<div style='height:34px;'></div>", unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# DOWNLOADS
# ----------------------------------------------------------------------------
st.write("")
d1, d2, d3 = st.columns([1.2, 1.4, 1.2])
with d1:
    st.download_button("⬇️ Download Full Data (with Revenue/Profit)",
                        df.to_csv(index=False).encode("utf-8"),
                        file_name="ar_chicken_full_data.csv", mime="text/csv",
                        use_container_width=True)
with d2:
    st.markdown(
        "<div style='display:flex; align-items:center; justify-content:center; "
        "height:44px; white-space:nowrap;'>"
        "<p style='color:#38bdf8; font-style:italic; letter-spacing:0.5px; "
        "margin:0; font-size:14px;'>✨ A.R ChickenMetrics — Smart Poultry Analytics ✨</p>"
        "</div>",
        unsafe_allow_html=True,
    )
with d3:
    st.download_button("⬇️ Download Monthly Summary",
                        monthly.to_csv(index=False).encode("utf-8"),
                        file_name="ar_chicken_monthly_summary.csv", mime="text/csv",
                        use_container_width=True)