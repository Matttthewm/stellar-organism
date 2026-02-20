import streamlit as st
import streamlit.components.v1 as components
import stellar_sdk
from stellar_sdk import Server, Keypair, TransactionBuilder, Network, Asset
from stellar_sdk.exceptions import BadRequestError, NotFoundError
import requests

# --- CONFIGURATION ---
HORIZON_URL = "[https://horizon-testnet.stellar.org](https://horizon-testnet.stellar.org)"
NETWORK_PASSPHRASE = Network.TESTNET_NETWORK_PASSPHRASE # FIXED: Typo fixed here
SPONSORSHIP_AMOUNT_XLM = "1"  
PRESERVATION_THRESHOLD = 3   

if "demo_issuer_key_secret" not in st.session_state:
    st.session_state.demo_issuer_key_secret = Keypair.random().secret
ISSUER_KEY_SECRET = st.session_state.demo_issuer_key_secret
ISSUER_KEYPAIR = Keypair.from_secret(ISSUER_KEY_SECRET)
st.session_state.is_demo_mode = True

server = Server(HORIZON_URL)

if 'freighter_public_key' not in st.session_state: st.session_state.freighter_public_key = None
if 'is_connected' not in st.session_state: st.session_state.is_connected = False
if 'tx_hash' not in st.session_state: st.session_state.tx_hash = None

# --- Custom Swiss Design CSS ---
st.markdown(
    """
    <style>
    @import url('[https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600&display=swap](https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600&display=swap)');
    html, body, [class*="st-"] { font-family: 'IBM Plex Sans', sans-serif; color: #333; line-height: 1.6; }
    body { background-color: #f0f2f6; }
    h1, h2, h3, h4 { font-weight: 500; color: #1a1a1a; }
    h1 { font-size: 2.5em; border-bottom: 2px solid #ddd; padding-bottom: 0.5em; margin-bottom: 1em; }
    .stButton > button { background-color: #e6e6e6; color: #333; border: 1px solid #ccc; border-radius: 4px; padding: 0.6em 1.2em; font-weight: 500; }
    .stButton > button:hover { background-color: #d9d9d9; }
    .stMetric { background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 1em; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """,
    unsafe_allow_html=True
)

# --- Freighter Logic via Query Params ---
def build_freighter_js(action, xdr=None):
    if action == "connect":
        return """
        <script src="[https://unpkg.com/@stellar/freighter-api@1.2.0/build/freighter.min.js](https://unpkg.com/@stellar/freighter-api@1.2.0/build/freighter.min.js)"></script>
        <script>
            async function connect() {
                const pk = await window.freighterApi.getPublicKey();
                window.location.search = `?f_action=connect&fpk=${pk}`;
            }
            connect();
        </script>
        """
    elif action == "sign":
        return f"""
        <script src="[https://unpkg.com/@stellar/freighter-api@1.2.0/build/freighter.min.js](https://unpkg.com/@stellar/freighter-api@1.2.0/build/freighter.min.js)"></script>
        <script>
            async function signTx() {{
                const signed = await window.freighterApi.signTransaction("{xdr}", {{ network: "TESTNET" }});
                window.location.search = `?f_action=sign&signed_xdr=${{encodeURIComponent(signed)}}`;
            }}
            signTx();
        </script>
        """

# Process incoming params
if "f_action" in st.query_params:
    action = st.query_params["f_action"]
    if action == "connect" and "fpk" in st.query_params:
        st.session_state.freighter_public_key = st.query_params["fpk"]
        st.session_state.is_connected = True
    elif action == "sign" and "signed_xdr" in st.query_params:
        signed_xdr = st.query_params["signed_xdr"]
        try:
            res = server.submit_transaction(signed_xdr)
            st.session_state.tx_hash = res['hash']
            st.success(f"Echo Sponsored! Tx Hash: `{res['hash']}`")
            st.balloons()
        except Exception as e:
            st.error(f"Transaction failed: {e}")
    st.query_params.clear()
    st.rerun()

# --- Sidebar UI ---
with st.sidebar:
    st.info("### 🧬 Ephemeral Echoes\n\nCraft fleeting digital messages or art pieces whose existence is tied to community sponsorship, with a mechanism for preservation into a collective archival constellation.")
    st.markdown("---")
    if st.session_state.is_connected:
        st.success("Freighter Connected! ✅")
        st.write(f"`{st.session_state.freighter_public_key[:10]}...`")
        if st.button("Disconnect Freighter 🚫"):
            st.session_state.is_connected = False
            st.session_state.freighter_public_key = None
            st.rerun()
    else:
        st.warning("Freighter Not Connected.")
        if st.button("Connect Freighter 🚀"):
            components.html(build_freighter_js("connect"), height=0, width=0)

    st.markdown("---")
    st.subheader("Issuer Status (Demo)")
    if "demo_issuer_funded" not in st.session_state:
        try:
            requests.get(f"[https://friendbot.stellar.org/?addr=](https://friendbot.stellar.org/?addr=){ISSUER_KEYPAIR.public_key}")
            st.session_state.demo_issuer_funded = True
            st.success("Demo Issuer Funded!")
        except Exception as e:
            st.error("Failed to fund demo issuer.")

# --- Main UI ---
st.title("🧬 Ephemeral Echoes")
st.markdown("---")

col1, col2 = st.columns(2)
try:
    issuer_acc = server.load_account(ISSUER_KEYPAIR.public_key)
    col1.metric("Issuer Account Balance", f"{float(issuer_acc.balances[0].balance):.2f} XLM")
except:
    col1.metric("Issuer Account Balance", "Loading...")

col2.metric("Preservation Threshold", f"{PRESERVATION_THRESHOLD} sponsorships")
st.markdown("---")

st.subheader("✍️ Craft Your Echo")
if st.session_state.is_connected:
    user_message = st.text_input("Your Fleeting Message (Max 28 characters for memo)", max_chars=28)

    if st.button(f"Sponsor Echo ({SPONSORSHIP_AMOUNT_XLM} XLM) ✨"):
        if user_message:
            try:
                source_account = server.load_account(st.session_state.freighter_public_key)
                transaction = (
                    TransactionBuilder(source_account, NETWORK_PASSPHRASE, 100)
                    .append_payment_op(destination=ISSUER_KEYPAIR.public_key, amount=SPONSORSHIP_AMOUNT_XLM, asset=Asset.native())
                    .add_text_memo(user_message)
                    .build()
                )
                components.html(build_freighter_js("sign", transaction.to_xdr()), height=0, width=0)
                st.info("Awaiting signature in Freighter...")
            except Exception as e:
                st.error("Account not found. Please fund it first.")
else:
    st.info("Please connect your Freighter wallet to craft and sponsor echoes.")

st.markdown("---")
st.subheader("📜 Current Echoes & Archive")

@st.cache_data(ttl=30)
def get_echo_sponsorships():
    memo_sponsorships = {}
    total_payments = 0
    try:
        payments = server.payments().for_account(ISSUER_KEYPAIR.public_key).limit(100).order(desc=True).call()
        for payment in payments['_embedded']['records']:
            if payment['type'] == 'payment' and payment['transaction_memo_type'] == 'text':
                memo_text = payment['transaction_memo']
                if memo_text not in memo_sponsorships:
                    memo_sponsorships[memo_text] = []
                memo_sponsorships[memo_text].append(payment['transaction_hash'])
                total_payments += 1
    except: pass
    return memo_sponsorships, total_payments

echo_sponsorships, total_sponsorships_count = get_echo_sponsorships()
st.metric("Total Echo Sponsorships", total_sponsorships_count)

if not echo_sponsorships:
    st.info("No echoes have been sponsored yet. Be the first! 🌟")
else:
    with st.expander("✨ Preserved Echoes (Archival Constellation)", expanded=True):
        for memo, sponsorships in echo_sponsorships.items():
            if len(set(sponsorships)) >= PRESERVATION_THRESHOLD:
                st.markdown(f"**\"{memo}\"** – Sponsored **{len(set(sponsorships))}** times (Preserved! 🌠)")
                
    with st.expander("🌬️ Fleeting Echoes", expanded=True):
        for memo, sponsorships in echo_sponsorships.items():
            if len(set(sponsorships)) < PRESERVATION_THRESHOLD:
                count = len(set(sponsorships))
                st.markdown(f"**\"{memo}\"** – Sponsored **{count}** times ({PRESERVATION_THRESHOLD - count} more needed)")
                st.progress(min(100, int((count / PRESERVATION_THRESHOLD) * 100)))
