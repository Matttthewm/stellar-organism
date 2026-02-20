import streamlit as st
import stellar_sdk
from stellar_sdk import Server, Keypair, TransactionBuilder, Network, Asset
from stellar_sdk.exceptions import BadRequestError, NotFoundError
import streamlit.components.v1 as components
import asyncio
import json
import requests

# --- Configuration ---
HORIZON_URL = "https://horizon-testnet.stellar.org"
NETWORK_PASSPHRASE = Network.TESTNET_NETWORK_PASSPHRASE
SERVER = Server(HORIZON_URL)

# --- Session State Initialization ---
if "freighter_public_key" not in st.session_state:
    st.session_state.freighter_public_key = None
if "current_entropic_state" not in st.session_state:
    st.session_state.current_entropic_state = 0.5  # A value between 0 and 1 (0 = stable, 1 = unstable)
if "tx_in_progress" not in st.session_state:
    st.session_state.tx_in_progress = False
if "signed_xdr" not in st.session_state:
    st.session_state.signed_xdr = None
if "freighter_callback_registered" not in st.session_state:
    st.session_state.freighter_callback_registered = False

# --- Helper Functions ---
async def fetch_account_details(public_key):
    try:
        account = await SERVER.load_account(public_key)
        return account
    except NotFoundError:
        return None
    except Exception as e:
        st.error(f"Error loading account {public_key}: {e}")
        return None

def submit_transaction_to_horizon(xdr_signed):
    try:
        response = SERVER.submit_transaction(xdr_signed)
        return response
    except BadRequestError as e:
        st.error(f"Stellar transaction error: {json.dumps(e.extras, indent=2)}")
        return None
    except Exception as e:
        st.error(f"Failed to submit transaction: {e}")
        return None

# --- Freighter JavaScript Component ---
FREIGHTER_JS_COMPONENT = """
<script src="https://unpkg.com/@stellar/freighter-api@latest/build/index.js"></script>
<script>
    const streamlit = window.parent.streamlit; 

    async function connectFreighter() {
        try {
            if (!(await window.freighterApi.isConnected())) {
                await window.freighterApi.connect();
            }
            const publicKey = await window.freighterApi.getPublicKey();
            streamlit.send({ type: 'freighter_connected', publicKey: publicKey });
        } catch (error) {
            streamlit.send({ type: 'freighter_error', message: error.message });
        }
    }

    async function signTransaction(xdr, networkPassphrase) {
        try {
            const signedXDR = await window.freighterApi.signTransaction(xdr, { networkPassphrase });
            streamlit.send({ type: 'transaction_signed', signedXDR: signedXDR });
        } catch (error) {
            streamlit.send({ type: 'freighter_error', message: error.message });
        }
    }

    window.addEventListener('message', async (event) => {
        if (event.source === window.parent && event.data && event.data.streamlitMessage) {
            const message = event.data.streamlitMessage;
            if (message.type === 'connect') {
                await connectFreighter();
            } else if (message.type === 'sign') {
                await signTransaction(message.xdr, message.networkPassphrase);
            }
        }
    });

    window.freighterApi.isConnected().then(connected => {
        if (connected) {
            window.freighterApi.getPublicKey().then(publicKey => {
                streamlit.send({ type: 'freighter_connected', publicKey: publicKey });
            });
        }
    });
</script>
"""

# --- Custom CSS ---
CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700&family=Roboto+Mono:wght@400;700&display=swap');
    body { background-color: #0d1117; color: #c9d1d9; font-family: 'Roboto Mono', monospace; line-height: 1.6; }
    h1, h2, h3, h4, h5, h6 { color: #58a6ff; font-family: 'Montserrat', sans-serif; text-shadow: 0px 0px 5px rgba(88, 166, 255, 0.4); }
    .stApp { background-color: #0d1117; }
    .stButton>button { background-color: #21262d; border: 1px solid #30363d; color: #58a6ff; border-radius: 5px; padding: 0.5em 1em; cursor: pointer; }
    .stButton>button:hover { background-color: #30363d; border-color: #58a6ff; box-shadow: 0px 0px 8px rgba(88, 166, 255, 0.6); }
    .stTextInput>div>div>input, .stSelectbox>div>div>select, .stTextArea>div>div>textarea { background-color: #161b22; border: 1px solid #30363d; color: #c9d1d9; border-radius: 5px; }
    div[data-testid="stMetricValue"] { color: #58a6ff; font-family: 'Roboto Mono', monospace; font-size: 2.5em; text-shadow: 0px 0px 10px rgba(88, 166, 255, 0.8); }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# --- Freighter Bridge Setup ---
components.html(FREIGHTER_JS_COMPONENT, height=0, width=0)

def send_to_freighter_component(message):
    components.html(
        f"""
        <script>
            const iframe = document.querySelector('iframe[title="st.html"]');
            if (iframe && iframe.contentWindow) {{
                iframe.contentWindow.postMessage({{ streamlitMessage: {json.dumps(message)} }}, '*');
            }}
        </script>
        """,
        height=0, width=0
    )

if "streamlit_msg" in st.query_params:
    try:
        message_str = st.query_params["streamlit_msg"]
        message_data = json.loads(message_str)
        if message_data.get("type") == "freighter_connected":
            st.session_state.freighter_public_key = message_data["publicKey"]
            st.success(f"Freighter Connected! Public Key: `{message_data['publicKey'][:10]}...`")
            st.session_state.tx_in_progress = False
            st.query_params.pop("streamlit_msg")
            st.rerun()
        elif message_data.get("type") == "transaction_signed":
            st.session_state.signed_xdr = message_data["signedXDR"]
            st.success("Transaction signed by Freighter!")
            st.query_params.pop("streamlit_msg")
            st.rerun()
        elif message_data.get("type") == "freighter_error":
            st.session_state.tx_in_progress = False
            st.error(f"Freighter Error: {message_data['message']}")
            st.query_params.pop("streamlit_msg")
            st.rerun()
    except Exception as e:
        pass

# --- Secret Key Handling ---
if "ISSUER_KEY" in st.secrets:
    ISSUER_SECRET = st.secrets["ISSUER_KEY"]
else:
    if "demo_key" not in st.session_state:
        st.session_state.demo_key = Keypair.random().secret
    ISSUER_SECRET = st.session_state.demo_key
    st.sidebar.warning("Using Ephemeral Demo Keys for Issuer.")

try:
    ISSUER_KEYPAIR = Keypair.from_secret(ISSUER_SECRET)
    ISSUER_PUBLIC_KEY = ISSUER_KEYPAIR.public_key
except ValueError:
    st.error("Invalid ISSUER_KEY.")
    st.stop()

# FIXED: Removed underscores from Asset codes
FRAGMENT_A = Asset("FRAGA", ISSUER_PUBLIC_KEY)
FRAGMENT_B = Asset("FRAGB", ISSUER_PUBLIC_KEY)

# --- Sidebar ---
st.sidebar.info(
    "**The Entropic Equation Engine**\n\n"
    "🧬 A self-organizing network where users deploy abstract 'equations' (Stellar accounts) "
    "that utilize passive offers to exchange 'solution fragments' (custom assets) "
    "in an attempt to stabilize a system-wide entropic state, with system-level clawbacks "
    "applied to destabilizing contributions."
)
st.sidebar.caption("Visual Style: Abstract/Mathematical 📐")

st.sidebar.markdown("---")
st.sidebar.write("### System Status")
delta_val = f"{abs(st.session_state.current_entropic_state - 0.5):.4f}"
delta_color = "off"
delta_label = "Balanced"

if st.session_state.current_entropic_state < 0.45:
    delta_color = "inverse"
    delta_label = "Low Entropy (Cooling)"
elif st.session_state.current_entropic_state > 0.55:
    delta_color = "inverse"
    delta_label = "High Entropy (Heating)"

st.sidebar.metric(label="Entropic State", value=f"{st.session_state.current_entropic_state:.4f}", delta=delta_label, delta_color=delta_color)
st.sidebar.caption("Optimal entropic state is 0.5. Deviations indicate instability.")
st.sidebar.markdown("---")

# --- Main App ---
st.title("The Entropic Equation Engine 🧬")
st.subheader("Orchestrating Solution Fragments for System Stabilization")

st.header("1. Connect Your Equation Account (Freighter) 🔗")
if not st.session_state.freighter_public_key:
    if st.button("Connect Freighter Wallet"):
        send_to_freighter_component({"type": "connect"})
        st.session_state.tx_in_progress = True 
        st.info("Awaiting Freighter connection...")
else:
    st.success(f"Connected to Freighter Public Key: `{st.session_state.freighter_public_key}`")
    account_details = asyncio.run(fetch_account_details(st.session_state.freighter_public_key))
    if account_details:
        xlm_balance = next((b.balance for b in account_details.balances if b.asset_type == 'native'), '0.0000000')
        st.write(f"Balance: **{xlm_balance} XLM**")
    else:
        st.warning("Freighter account not found on Testnet. Fund it below!")

if st.session_state.freighter_public_key:
    st.header("2. Initialize Network State (Testnet) 🧪")
    col1, col2 = st.columns([1,2])
    with col1:
        if st.button("Fund Equation Account (XLM via Friendbot)"):
            try:
                # FIXED: Uses requests for Friendbot instead of SERVER.friendbot()
                requests.get(f"https://friendbot.stellar.org/?addr={st.session_state.freighter_public_key}")
                st.success("Equation Account funded by Friendbot!")
                st.rerun()
            except Exception as e:
                st.error(f"An error occurred: {e}")
    with col2:
        st.write("System Issuer Public Key:")
        st.code(ISSUER_PUBLIC_KEY)

st.header("3. Orchestrate Solution Fragments ⚛️")
if not st.session_state.freighter_public_key:
    st.warning("Please connect your Freighter wallet first to manage fragments.")
else:
    equation_pk = st.session_state.freighter_public_key
    equation_account_details = asyncio.run(fetch_account_details(equation_pk))

    if equation_account_details:
        has_trust_a = any(b.asset == FRAGMENT_A for b in equation_account_details.balances)
        has_trust_b = any(b.asset == FRAGMENT_B for b in equation_account_details.balances)

        col1, col2 = st.columns(2)
        with col1:
            if not has_trust_a:
                if st.button(f"Trust FRAGA"):
                    source_account = asyncio.run(fetch_account_details(equation_pk))
                    transaction = TransactionBuilder(source_account=source_account, network_passphrase=NETWORK_PASSPHRASE).append_change_trust_op(asset=FRAGMENT_A, limit="100000000000").set_timeout(300).build()
                    send_to_freighter_component({"type": "sign", "xdr": transaction.to_xdr(), "networkPassphrase": NETWORK_PASSPHRASE})
                    st.session_state.tx_in_progress = True
            else:
                st.success("✅ Trustline for FRAGA established.")

        with col2:
            if not has_trust_b:
                if st.button(f"Trust FRAGB"):
                    source_account = asyncio.run(fetch_account_details(equation_pk))
                    transaction = TransactionBuilder(source_account=source_account, network_passphrase=NETWORK_PASSPHRASE).append_change_trust_op(asset=FRAGMENT_B, limit="100000000000").set_timeout(300).build()
                    send_to_freighter_component({"type": "sign", "xdr": transaction.to_xdr(), "networkPassphrase": NETWORK_PASSPHRASE})
                    st.session_state.tx_in_progress = True
            else:
                st.success("✅ Trustline for FRAGB established.")

        if st.session_state.tx_in_progress and st.session_state.signed_xdr:
            response = submit_transaction_to_horizon(st.session_state.signed_xdr)
            if response: st.success("Trustline established!")
            st.session_state.signed_xdr = None
            st.session_state.tx_in_progress = False
            st.rerun()

        st.subheader("Acquire Fragments")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Request 10 FRAGA"):
                issuer_account = asyncio.run(fetch_account_details(ISSUER_PUBLIC_KEY))
                tx = TransactionBuilder(source_account=issuer_account, network_passphrase=NETWORK_PASSPHRASE).append_payment_op(destination=equation_pk, asset=FRAGMENT_A, amount="10").set_timeout(300).build()
                tx.sign(ISSUER_KEYPAIR)
                submit_transaction_to_horizon(tx.to_xdr())
                st.success("10 FRAGA received!")
                st.rerun()
        with c2:
            if st.button("Request 10 FRAGB"):
                issuer_account = asyncio.run(fetch_account_details(ISSUER_PUBLIC_KEY))
                tx = TransactionBuilder(source_account=issuer_account, network_passphrase=NETWORK_PASSPHRASE).append_payment_op(destination=equation_pk, asset=FRAGMENT_B, amount="10").set_timeout(300).build()
                tx.sign(ISSUER_KEYPAIR)
                submit_transaction_to_horizon(tx.to_xdr())
                st.success("10 FRAGB received!")
                st.rerun()

st.header("4. Create Entropic Offers 🔄")
if st.session_state.freighter_public_key and equation_account_details:
    col1, col2 = st.columns(2)
    with col1:
        selling_asset_choice = st.selectbox("Selling Asset:", options=[FRAGMENT_A.code, FRAGMENT_B.code, "XLM"])
        amount = st.text_input("Amount (to sell):", value="1.0")
    with col2:
        buying_asset_choice = st.selectbox("Buying Asset:", options=[opt for opt in [FRAGMENT_A.code, FRAGMENT_B.code, "XLM"] if opt != selling_asset_choice])
        price = st.text_input("Price:", value="1.0")

    def get_asset(choice):
        if choice == "XLM": return Asset.native()
        if choice == FRAGMENT_A.code: return FRAGMENT_A
        return FRAGMENT_B

    if st.button("Deploy Passive Offer"):
        sell_ass = get_asset(selling_asset_choice)
        buy_ass = get_asset(buying_asset_choice)
        tx = TransactionBuilder(source_account=equation_account_details, network_passphrase=NETWORK_PASSPHRASE).append_manage_buy_offer_op(selling=sell_ass, buying=buy_ass, amount=amount, price=price, offer_id=0).set_timeout(300).build()
        send_to_freighter_component({"type": "sign", "xdr": tx.to_xdr(), "networkPassphrase": NETWORK_PASSPHRASE})
        st.session_state.tx_in_progress = True
