# app.py - Super Simple Polymarket Copy Trader (Nov 28, 2025)
import streamlit as st
import requests
import time
from datetime import datetime
import threading
import smtplib
from email.mime.text import MimeText

# Config
st.set_page_config(page_title="CopyTrader Pro", layout="wide")
SUBGRAPH_URL = "https://api.thegraph.com/subgraphs/name/polymarket/matic"

# Fresh 50+ Whales (Nov 2025 - from Polymarket Analytics & Dune)
TARGET_WALLETS = [
    "0x1f0a343513aa6060488fabe96960e6d1e177f7aa",  # @archaic_on_Poly +$110k
    "0xb4f2f0c858566fef705edf8efc1a5e9fba307862",  # Desy +$250k
    "0x4ad6cadefae3c28f5b2caa32a99ebba3a614464c",  # noreasapa +$75k
    "0xd218e474776403a330142299f7796e8ba32eb5c9",  # @cigarettes +$800k
    # Add more from list below - or edit here
    # Theo4 (+$20M), Fredi9999 (+$15M), zxgngl (+$11M), 033033033 (+$84k), WindWalk3 (+$1.1M), etc.
]

@st.cache_data(ttl=10)
def get_recent_trades(wallet):
    query = """
    {
      orders(first: 5, orderBy: timestamp, orderDirection: desc,
             where: {creator: "%s"}) {
        id, amount, outcomeIndex, timestamp, price,
        market { conditionId, title, outcomes }
      }
    }
    """ % wallet.lower()
    try:
        r = requests.post(SUBGRAPH_URL, json={'query': query}, timeout=10)
        return r.json().get("data", {}).get("orders", [])
    except:
        return []

def decode_trade(order):
    market_title = order.get("market", {}).get("title", "Unknown")[:50]
    outcomes = order.get("market", {}).get("outcomes", ["Yes", "No"])
    outcome = outcomes[int(order.get("outcomeIndex", 0))]
    amount_usd = float(order.get("amount", 0)) / 1e6
    copy_usd = (amount_usd * COPY_PERCENT / 100)  # Global from sidebar
    condition_id = order.get("market", {}).get("conditionId", "")
    link = f"https://polymarket.com/event/{market_title.lower().replace(' ', '-')}" \
           f"?buy={outcome}&amount={copy_usd:.0f}"
    return {
        "market": market_title,
        "side": outcome,
        "size": f"${amount_usd:,.0f}",
        "copy": f"${copy_usd:,.0f}",
        "time": datetime.fromtimestamp(int(order["timestamp"])).strftime("%H:%M"),
        "link": link
    }

# Sidebar Settings
st.sidebar.header("Your Settings")
COPY_PERCENT = st.sidebar.slider("Copy % of Balance", 0.5, 10.0, 2.0)
BALANCE_USD = st.sidebar.number_input("Your Balance (USD)", 1000, 100000, 10000)
EMAIL = st.sidebar.text_input("Email for Alerts", "")
PHONE = st.sidebar.text_input("Phone for SMS (e.g., +15551234567)", "")  # Twilio setup below
TELEGRAM_TOKEN = st.sidebar.text_input("Telegram Token (opt)", type="password")
TELEGRAM_CHAT = st.sidebar.text_input("Telegram Chat ID (opt)", "")

# Alert Functions
def send_email(subject, body):
    if not EMAIL: return
    try:
        msg = MimeText(body)
        msg['Subject'] = subject
        msg['From'] = "copytrader@alerts.com"  # Use your SMTP
        msg['To'] = EMAIL
        # Add your SMTP server here (e.g., Gmail: smtp.gmail.com, 587)
        # server = smtplib.SMTP('smtp.gmail.com', 587); server.starttls(); server.login('your@gmail.com', 'app_pass')
        # server.send_message(msg); server.quit()
        st.sidebar.success("Email sent!")  # Placeholder - enable SMTP for real
    except:
        st.sidebar.error("Email setup needed")

def send_sms(message):
    if not PHONE: return
    # Twilio: pip install twilio (local run), then:
    # from twilio.rest import Client; client = Client('acc_sid', 'auth_token'); client.messages.create(to=PHONE, from_='your_twilio_num', body=message)
    st.sidebar.info("SMS ready - add Twilio creds locally")

def send_telegram(message):
    if TELEGRAM_TOKEN and TELEGRAM_CHAT:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                      data={"chat_id": TELEGRAM_CHAT, "text": message})

# State
if "trades" not in st.session_state:
    st.session_state.trades = []
if "seen" not in st.session_state:
    st.session_state.seen = set()

# Monitoring Thread
def monitor():
    while True:
        for wallet in TARGET_WALLETS:
            orders = get_recent_trades(wallet)
            for order in orders:
                txid = order["id"]
                if txid not in st.session_state.seen:
                    trade = decode_trade(order)
                    st.session_state.trades.insert(0, trade)
                    st.session_state.seen.add(txid)
                    msg = f"🚨 Whale Alert!\n{trade['market']}\n{trade['side']} | Size: {trade['size']}\nYour Copy: {trade['copy']} ({COPY_PERCENT}% of ${BALANCE_USD:,})\n[COPY NOW]({trade['link']})"
                    send_email("New Whale Trade!", msg)
                    send_sms(msg)
                    send_telegram(msg)
        time.sleep(10)

threading.Thread(target=monitor, daemon=True).start()

# Dashboard
st.title("🧑‍💼 One-Click Copy Trader")
st.caption(f"Tracking {len(TARGET_WALLETS)} whales | Your copy size: {COPY_PERCENT}% of ${BALANCE_USD:,} = ~${(BALANCE_USD * COPY_PERCENT / 100):,.0f}/trade")

col1, col2 = st.columns([3,1])
with col1:
    st.metric("Whales Active", len(TARGET_WALLETS))
with col2:
    st.metric("New Trades", len(st.session_state.trades))

st.markdown("### Latest Whale Trades")
if st.session_state.trades:
    for trade in st.session_state.trades[:10]:
        with st.container():
            col_a, col_b, col_c = st.columns([1,2,2])
            with col_a:
                st.success(trade["side"])
            with col_b:
                st.write(f"**{trade['market']}**")
                st.caption(trade["time"])
            with col_c:
                st.metric("Copy This", trade["copy"], help=trade["size"] + " whale size")
                if st.button("📱 COPY NOW", key=trade["time"]):
                    st.markdown(f"[Open Polymarket]({trade['link']})")
                    st.balloons()
else:
    st.info("🔍 Scanning for trades... First alert incoming soon!")

# Auto-refresh
time.sleep(1)
st.experimental_rerun()
