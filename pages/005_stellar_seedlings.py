import streamlit as st
import stellar_sdk
from stellar_sdk import Server, Keypair, TransactionBuilder, Network, Asset
from stellar_sdk.exceptions import BadRequestError, NotFoundError
import json
import time

# --- Configuration ---
HORIZON_URL = "https://horizon-testnet.stellar.org"
NETWORK_PASSPHRASE = Network.TESTNET_NETWORK_PASSPHRASE

# --- Custom CSS ---
st.markdown("""
<style>
body { font-family: 'Open Sans', sans-serif; background-color: #f0f8ff; }
h1, h2 { font-family: 'Fredoka One', cursive; color: #4CAF50; }
.stButton>button { background-color: #FFD700; color: #8B4513; border-radius: 25px; border: 2px solid #DAA520; }
</style>
""", unsafe_allow_html=True)

# --- Sidebar Info ---
st.sidebar.info("🌱 **Stellar Seedlings**\n\nNurture digital flora in a gamified garden.")
st.sidebar.caption("Style: Playful / Gamified")

# --- SECRET KEY HANDLING (DEMO MODE FALLBACK) ---
if "demo_issuer" not in st.session_state:
    st.session_state.demo_issuer = Keypair.random()
if "demo_fund" not in st.session_state:
    st.session_state.demo_fund = Keypair.random()

# Try to load from secrets, otherwise use demo keys
if "SEEDLING_ISSUER_SEED" in st.secrets:
    SEEDLING_ISSUER_SEED = st.secrets["SEEDLING_ISSUER_SEED"]
    SEEDLING_ISSUER_KEYPAIR = Keypair.from_secret(SEEDLING_ISSUER_SEED)
else:
    SEEDLING_ISSUER_KEYPAIR = st.session_state.demo_issuer
    st.warning("⚠️ Running in DEMO MODE (Ephemeral Issuer).")

SEEDLING_ISSUER_PUBLIC_KEY = SEEDLING_ISSUER_KEYPAIR.public_key

if "GROW_FUND_SEED" in st.secrets:
    GROW_FUND_SEED = st.secrets["GROW_FUND_SEED"]
    GROW_FUND_KEYPAIR = Keypair.from_secret(GROW_FUND_SEED)
else:
    GROW_FUND_KEYPAIR = st.session_state.demo_fund

GROW_FUND_PUBLIC_KEY = GROW_FUND_KEYPAIR.public_key

# --- Custom Asset ---
SEEDLING_ASSET = Asset("SEEDLING", SEEDLING_ISSUER_PUBLIC_KEY)

# --- Helper Functions ---
@st.cache_resource
def get_server():
    return Server(HORIZON_URL)

def get_account_details(public_key):
    try:
        return get_server().load_account(public_key)
    except:
        return None

def submit_transaction(signed_xdr):
    try:
        resp = get_server().submit_transaction(signed_xdr)
        st.success(f"Success! Hash: {resp['hash']}")
        st.balloons()
        return resp
    except BadRequestError as e:
        st.error(f"Transaction failed: {e.extras.get('result_codes')}")
    except Exception as e:
        st.error(f"Error: {e}")

# --- Freighter JS ---
FREIGHTER_JS = """
<script>
    async function connectFreighter() {
        if (window.freighter) {
            const pk = await window.freighter.getPublicKey();
            window.location.href = `?public_key=${pk}`;
        } else { alert("Install Freighter!"); }
    }
    async function signTransaction(xdr) {
        if (window.freighter) {
            const signed = await window.freighter.signTransaction(xdr);
            window.location.href = `?signed_xdr=${encodeURIComponent(signed)}`;
        }
    }
</script>
"""
import streamlit.components.v1 as components
components.html(FREIGHTER_JS, height=0)

# --- Main Logic ---
st.title("✨ Stellar Seedlings 🚀")

# Query Params
qp = st.query_params
if "public_key" in qp:
    st.session_state.public_key = qp["public_key"]
if "signed_xdr" in qp:
    submit_transaction(qp["signed_xdr"])
    st.query_params.clear()

# Wallet Connect
if "public_key" not in st.session_state:
    st.button("Connect Wallet", on_click=lambda: components.html("<script>connectFreighter()</script>", height=0))
else:
    st.success(f"Connected: {st.session_state.public_key}")
    if st.button("Disconnect"):
        del st.session_state.public_key
        st.rerun()

    # Tabs
    tab1, tab2 = st.tabs(["🌱 Plant", "💰 Fund"])
    
    with tab1:
        st.write("Get a SEEDLING from the nursery.")
        if st.button("Plant Seedling"):
            try:
                # In demo mode, we need to ensure issuer is funded first
                # For this snippet, we assume issuer has funds or fail gracefully
                server = get_server()
                try:
                    server.load_account(SEEDLING_ISSUER_PUBLIC_KEY)
                except:
                    st.error("Demo Issuer account not funded! Please fund it on Testnet.")
                    st.write(f"Issuer: {SEEDLING_ISSUER_PUBLIC_KEY}")
                    st.stop()

                issuer_acc = server.load_account(SEEDLING_ISSUER_PUBLIC_KEY)
                tx = (
                    TransactionBuilder(issuer_acc, NETWORK_PASSPHRASE, 100)
                    .append_payment_op(st.session_state.public_key, SEEDLING_ASSET, "1")
                    .set_timeout(30)
                    .build()
                )
                tx.sign(SEEDLING_ISSUER_KEYPAIR)
                submit_transaction(tx.to_xdr())
            except Exception as e:
                st.error(f"Error: {e}")

    with tab2:
        st.write(f"Donate to: {GROW_FUND_PUBLIC_KEY}")
        amt = st.number_input("Amount", 1.0)
        if st.button("Donate"):
            try:
                acc = get_server().load_account(st.session_state.public_key)
                tx = (
                    TransactionBuilder(acc, NETWORK_PASSPHRASE, 100)
                    .append_payment_op(GROW_FUND_PUBLIC_KEY, Asset.native(), str(amt))
                    .set_timeout(30)
                    .build()
                )
                components.html(f"<script>signTransaction('{tx.to_xdr()}')</script>", height=0)
            except Exception as e:
                st.error(f"Error: {e}")
