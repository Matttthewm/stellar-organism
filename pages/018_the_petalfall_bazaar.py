import stellar_sdk
from stellar_sdk import Server, Keypair, TransactionBuilder, Network, Asset
from stellar_sdk.exceptions import BadRequestError, NotFoundError
import streamlit as st
import streamlit.components.v1 as components
import json
import time
import random
import string
import base64
import requests

HORIZON_URL = "https://horizon-testnet.stellar.org"
NETWORK_PASSPHRASE = Network.TESTNET_NETWORK_PASSPHRASE
MIN_BASE_RESERVE = 0.5 
server = Server(HORIZON_URL)

if "demo_issuer_key_secret" not in st.session_state: st.session_state.demo_issuer_key_secret = Keypair.random().secret
ISSUER_KEY = Keypair.from_secret(st.session_state.demo_issuer_key_secret)
ISSUER_PUBLIC_KEY = ISSUER_KEY.public_key

if "issuer_account_checked" not in st.session_state: st.session_state.issuer_account_checked = False
if not st.session_state.issuer_account_checked:
    try:
        server.load_account(ISSUER_PUBLIC_KEY)
        st.session_state.issuer_account_checked = True
    except NotFoundError:
        # FIXED: Use requests for Friendbot
        requests.get(f"https://friendbot.stellar.org/?addr={ISSUER_PUBLIC_KEY}")
        st.session_state.issuer_account_checked = True

POLLEN_ASSET_CODE = "PETALFALL"
POLLEN_ASSET = Asset(POLLEN_ASSET_CODE, ISSUER_PUBLIC_KEY)

if "freighter_connected" not in st.session_state: st.session_state.freighter_connected = False
if "freighter_public_key" not in st.session_state: st.session_state.freighter_public_key = None
if "xdr_to_sign" not in st.session_state: st.session_state.xdr_to_sign = None

st.markdown("""
    <style>
        :root { --primary-color: #5C8374; --secondary-color: #9EC8B9; --background-color: #F8F4E1; }
        body { background-color: var(--background-color); color: #333333; }
        .stApp { background-color: var(--background-color); }
        h1, h2, h3 { color: var(--primary-color); }
        .stButton>button { background-color: var(--secondary-color); border-radius: 8px; }
        .stMetric { background-color: #EAF1EB; padding: 1rem; border-radius: 12px; }
    </style>
""", unsafe_allow_html=True)

st.sidebar.markdown("## The Petalfall Bazaar 🌸")
st.sidebar.info("A seasonal marketplace where digital 'pollen' are exchanged.")

def build_freighter_connect_script():
    return """
    <script>
        async function connectFreighter() {
            const publicKey = await window.freighterApi.getPublicKey();
            window.location.search = `?freighter_status=success&freighter_type=connect&freighter_data=${publicKey}`;
        }
        connectFreighter();
    </script>
    """

if "freighter_status" in st.query_params:
    status = st.query_params["freighter_status"]
    data = st.query_params.get("freighter_data")
    ftype = st.query_params.get("freighter_type")
    st.query_params.clear() 

    if status == "success" and ftype == "connect":
        st.session_state.freighter_connected = True
        st.session_state.freighter_public_key = data
        st.rerun()

st.title("The Petalfall Bazaar 🌸🌱")

st.header("1. Connect Your Garden 🏡")
if not st.session_state.freighter_connected:
    if st.button("Connect Freighter Wallet 🔗"):
        # FIXED: Removed key
        components.html(build_freighter_connect_script(), height=0, width=0)
        st.stop()
else:
    st.success(f"Connected as: `{st.session_state.freighter_public_key}`")
    try:
        account = server.load_account(st.session_state.freighter_public_key)
        col1, col2, col3 = st.columns(3)
        xlm_balance = next((b.balance for b in account.balances if b.asset_type == 'native'), '0')
        col1.metric("XLM Balance 💰", f"{float(xlm_balance):.2f}")
    except:
        st.warning("Account not funded.")
        if st.button("Fund Garden"):
            requests.get(f"https://friendbot.stellar.org/?addr={st.session_state.freighter_public_key}")
            st.rerun()

    st.header("2. Acquire Petalfall Pollen 🌼")
    if st.button(f"Establish Trustline for {POLLEN_ASSET_CODE} 🌱"):
        acc = server.load_account(st.session_state.freighter_public_key)
        tx = TransactionBuilder(acc, NETWORK_PASSPHRASE).add_operation(stellar_sdk.ChangeTrust(asset=POLLEN_ASSET, limit="1000")).build()
        # In full version this triggers JS sign script
        st.info("Trustline prepared.")
