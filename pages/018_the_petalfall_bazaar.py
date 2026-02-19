# CRITICAL IMPORT RULES - Mandate 7
import stellar_sdk
from stellar_sdk import Server, Keypair, TransactionBuilder, Network, Asset
from stellar_sdk.exceptions import BadRequestError, NotFoundError

# HTML COMPONENT RULES - Mandate 9
import streamlit as st
import streamlit.components.v1 as components

import json
import time
import random
import string
import base64

# --- Configuration ---
HORIZON_URL = "https://horizon-testnet.stellar.org"
NETWORK_PASSPHRASE = Network.TESTNET_NETWORK_PASSPHRASE
MIN_BASE_RESERVE = 0.5 # XLM
MIN_BALANCE_PER_ENTRY = 0.5 # XLM for each new entry (account, trustline, data entry)

# --- Stellar Server & Issuer Key ---
# STELLAR SERVER RULES - Mandate 8
server = Server(HORIZON_URL)

# SECRET KEY HANDLING - Mandate 11
ISSUER_KEY: Keypair
if "ISSUER_KEY" in st.secrets:
    ISSUER_KEY = Keypair.from_secret(st.secrets["ISSUER_KEY"])
    st.sidebar.success("Using configured Issuer Key. 🔑")
else:
    if "demo_issuer_key_secret" not in st.session_state:
        st.session_state.demo_issuer_key_secret = Keypair.random().secret
    ISSUER_KEY = Keypair.from_secret(st.session_state.demo_issuer_key_secret)
    st.sidebar.warning("Using Ephemeral Demo Issuer Key (resets on app restart). ⚠️")

ISSUER_PUBLIC_KEY = ISSUER_KEY.public_key

# Ensure issuer account exists and has funds if it's a demo key
# This block runs only once at the start or if session_state resets.
if "issuer_account_checked" not in st.session_state:
    st.session_state.issuer_account_checked = False

if not st.session_state.issuer_account_checked:
    try:
        server.load_account(ISSUER_PUBLIC_KEY)
        st.session_state.issuer_account_checked = True
    except NotFoundError:
        st.warning(f"Demo Issuer account `{ISSUER_PUBLIC_KEY[:8]}...` not found. Funding it now via Friendbot...")
        try:
            stellar_sdk.FederationServer.testnet_friendbot_url(ISSUER_PUBLIC_KEY)
            time.sleep(3) # Give friendbot a moment
            server.load_account(ISSUER_PUBLIC_KEY) # Verify it's funded
            st.success("Demo Issuer account funded! 🌱")
            st.session_state.issuer_account_checked = True
        except Exception as e:
            st.error(f"Failed to fund demo issuer account: {e}. Please refresh and try again.")
            st.stop()
    except BadRequestError as e:
        st.error(f"Error loading issuer account: {e}. Please check your configuration.")
        st.stop()
    
# --- Custom Assets (Pollen) ---
POLLEN_ASSET_CODE = "PETALFALL" # Our custom pollen asset
POLLEN_ASSET = Asset(POLLEN_ASSET_CODE, ISSUER_PUBLIC_KEY)

# --- Session State Initialization ---
if "freighter_connected" not in st.session_state:
    st.session_state.freighter_connected = False
if "freighter_public_key" not in st.session_state:
    st.session_state.freighter_public_key = None
if "xdr_to_sign" not in st.session_state:
    st.session_state.xdr_to_sign = None
if "transaction_result" not in st.session_state:
    st.session_state.transaction_result = None
if "last_tx_hash" not in st.session_state:
    st.session_state.last_tx_hash = None
if "account_details_cache" not in st.session_state:
    st.session_state.account_details_cache = {}


# --- Custom CSS (Organic/Nature-Inspired) - Mandate 3 ---
# Emojis 🧬 only - Mandate 5
st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Merriweather:wght@300;400;700&family=Lora:wght@400;700&display=swap');
        
        :root {
            --primary-color: #5C8374; /* Dark Teal Green */
            --secondary-color: #9EC8B9; /* Light Sage Green */
            --accent-color: #FFC06C; /* Soft Orange/Peach */
            --background-color: #F8F4E1; /* Creamy White */
            --text-color: #333333; /* Dark Grey */
            --card-background: #EAF1EB; /* Very Light Green */
            --border-color: #B2D8C9; /* Muted Cyan-Green */
            --font-family-header: 'Merriweather', serif;
            --font-family-body: 'Lora', serif;
        }

        body {
            font-family: var(--font-family-body);
            color: var(--text-color);
            background-color: var(--background-color);
        }

        .stApp {
            background-color: var(--background-color);
            color: var(--text-color);
        }

        h1, h2, h3, h4, h5, h6 {
            font-family: var(--font-family-header);
            color: var(--primary-color);
        }
        
        /* Streamlit components styling */
        .stButton>button {
            background-color: var(--secondary-color);
            color: var(--text-color);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 0.6em 1.2em;
            font-size: 1em;
            cursor: pointer;
            transition: all 0.2s ease-in-out;
        }
        .stButton>button:hover {
            background-color: var(--primary-color);
            color: var(--background-color);
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        }
        
        .stTextInput>div>div>input, .stTextArea>div>div>textarea {
            border-radius: 8px;
            border: 1px solid var(--border-color);
            padding: 0.5em 0.8em;
            background-color: var(--card-background);
            color: var(--text-color);
        }
        .stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus {
            border-color: var(--primary-color);
            box-shadow: 0 0 0 0.1rem var(--primary-color);
        }

        .stMetric {
            background-color: var(--card-background);
            padding: 1rem;
            border-radius: 12px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
            border: 1px solid var(--border-color);
        }
        .stMetric>div[data-testid="stMetricValue"] {
            font-family: var(--font-family-header);
            color: var(--accent-color);
            font-size: 1.8em;
        }
        .stMetric>div[data-testid="stMetricLabel"] {
            color: var(--primary-color);
            font-size: 0.9em;
            font-weight: bold;
        }
        .stMetric>div[data-testid="stMetricDelta"] {
            color: var(--text-color);
            font-size: 0.8em;
        }
        
        .stExpander {
            background-color: var(--card-background);
            border-radius: 12px;
            border: 1px solid var(--border-color);
            padding: 0.5rem 1rem;
            margin-bottom: 1rem;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
        }
        .stExpander>div[data-testid="stExpanderForm"]>div { /* For the content inside */
             padding-top: 1rem;
             padding-bottom: 0.5rem;
        }
        .stExpander summary {
            font-family: var(--font-family-header);
            color: var(--primary-color);
            font-weight: bold;
            font-size: 1.1em;
        }

        .stAlert {
            border-radius: 8px;
            border-left: 5px solid;
            padding: 0.8em 1em;
        }
        .stAlert.st-emotion-cache-12fmw51.e1nx5ymc3 { /* Specific class for info alerts */
            background-color: #D6EADF; /* Light greenish for info */
            border-color: #8CC0A3; /* Darker green border */
        }
        .stAlert.st-emotion-cache-12fmw51.e1nx5ymc2 { /* Specific class for warning alerts */
            background-color: #FFF3CD; /* Light yellow for warning */
            border-color: #FFDA89; /* Darker yellow border */
        }
        .stAlert.st-emotion-cache-12fmw51.e1nx5ymc1 { /* Specific class for success alerts */
            background-color: #D4EDDA; /* Light green for success */
            border-color: #28A745; /* Green border */
        }

        /* Sidebar Styling */
        .st-emotion-cache-1fusmsm.e1fqkh3o2 { /* This targets the sidebar content area */
            background-color: var(--card-background);
            border-right: 1px solid var(--border-color);
        }
        .st-emotion-cache-z5fcl4.ezrtsby0 { /* This targets the sidebar header */
            background-color: var(--primary-color);
            color: var(--background-color);
            padding: 1rem;
            font-family: var(--font-family-header);
            font-size: 1.5em;
            text-align: center;
        }

        /* For info box in sidebar */
        .stSidebar .stAlert.st-emotion-cache-12fmw51.e1nx5ymc3 {
            background-color: var(--secondary-color);
            border-color: var(--primary-color);
            color: var(--text-color);
        }
        
        .stMarkdown {
            color: var(--text-color);
        }

    </style>
    """,
    unsafe_allow_html=True
)

# --- Sidebar Mandate 10 ---
st.sidebar.markdown("## The Petalfall Bazaar 🌸")
st.sidebar.info(
    "A seasonal marketplace where digital 'pollen' (specific custom assets) "
    "are exchanged between 'flowering accounts' to foster unique digital 'seed' (NFTs) creation, "
    "mimicking plant propagation and seasonal resource cycles."
)
st.sidebar.caption("Visual Style: Organic/Nature-Inspired 🌿")
st.sidebar.markdown("---")
st.sidebar.caption(f"Pollen Asset Issuer: `{ISSUER_PUBLIC_KEY[:8]}...`")
st.sidebar.caption(f"Pollen Asset Code: `{POLLEN_ASSET_CODE}`")
st.sidebar.markdown("---")

# --- Freighter Integration (st.components.v1.html + signTransaction) - Mandate 1 & 9 ---
# This hidden component serves as a container for our JavaScript.
# The actual communication is done by dynamically updating query_params via JS redirect.
components.html("", height=0, width=0, key="freighter_js_listener")


def build_freighter_connect_script():
    """Generates the JS to connect Freighter and send data back via query_params."""
    return f"""
    <script>
        // Make sure freighterApi is loaded
        if (typeof freighterApi === 'undefined') {{
            const script = document.createElement('script');
            script.src = 'https://unpkg.com/@stellar/freighter-api@latest/dist/freighter.min.js';
            script.onload = connectFreighter;
            document.head.appendChild(script);
        }} else {{
            connectFreighter();
        }}

        async function connectFreighter() {{
            try {{
                const publicKey = await freighterApi.getPublicKey();
                const url = new URL(window.location.href);
                url.searchParams.set('freighter_status', 'success');
                url.searchParams.set('freighter_data', publicKey);
                url.searchParams.set('freighter_type', 'connect');
                window.location.href = url.toString();
            }} catch (error) {{
                const url = new URL(window.location.href);
                url.searchParams.set('freighter_status', 'error');
                url.searchParams.set('freighter_data', error.message);
                url.searchParams.set('freighter_type', 'connect');
                window.location.href = url.toString();
            }}
        }}
    </script>
    """

def build_freighter_sign_script(xdr: str):
    """Generates the JS to sign an XDR with Freighter and send data back via query_params."""
    return f"""
    <script>
        // Make sure freighterApi is loaded
        if (typeof freighterApi === 'undefined') {{
            const script = document.createElement('script');
            script.src = 'https://unpkg.com/@stellar/freighter-api@latest/dist/freighter.min.js';
            script.onload = signXDR;
            document.head.appendChild(script);
        }} else {{
            signXDR();
        }}

        async function signXDR() {{
            try {{
                const signedXDR = await freighterApi.signTransaction('{xdr}', {{ network: '{NETWORK_PASSPHRASE}' }});
                const url = new URL(window.location.href);
                url.searchParams.set('freighter_status', 'success');
                url.searchParams.set('freighter_data', signedXDR);
                url.searchParams.set('freighter_type', 'sign');
                window.location.href = url.toString();
            }} catch (error) {{
                const url = new URL(window.location.href);
                url.searchParams.set('freighter_status', 'error');
                url.searchParams.set('freighter_data', error.message);
                url.searchParams.set('freighter_type', 'sign');
                window.location.href = url.toString();
            }}
        }}
    </script>
    """

def handle_freighter_response():
    """
    Listens for messages from the Freighter HTML component via `st.query_params`
    (Mandate 4: STRICTLY use 'st.query_params').
    """
    if "freighter_status" in st.query_params:
        status = st.query_params["freighter_status"]
        data = st.query_params.get("freighter_data")
        freighter_type = st.query_params.get("freighter_type")

        # Clear query params immediately to avoid re-processing on subsequent reruns
        st.query_params.clear() 

        if status == "success":
            if freighter_type == "connect":
                st.session_state.freighter_connected = True
                st.session_state.freighter_public_key = data
                st.success(f"Freighter Connected! Public Key: `{data[:8]}...` 🌿")
                st.rerun() # Rerun to update UI with connected state
            elif freighter_type == "sign":
                st.session_state.transaction_result = {"status": "success", "signed_xdr": data}
                st.success("Transaction signed by Freighter! Submitting... ✨")
                st.rerun() # Rerun to submit the signed transaction
        else:
            st.error(f"Freighter Error: {data} 🐛")
            st.session_state.freighter_connected = False
            st.session_state.freighter_public_key = None
            st.session_state.xdr_to_sign = None
            st.session_state.transaction_result = None
            st.rerun() # Rerun to clear any pending states

# --- Helper Functions ---
def get_account_details(public_key: str):
    """
    Fetches account details from Horizon, with caching.
    """
    if public_key in st.session_state.account_details_cache:
        # Simple cache invalidation for demonstration; more robust solutions exist.
        cached_time, account_data = st.session_state.account_details_cache[public_key]
        if time.time() - cached_time < 5: # Cache for 5 seconds
            return account_data

    try:
        account = server.load_account(public_key)
        st.session_state.account_details_cache[public_key] = (time.time(), account)
        return account
    except NotFoundError:
        st.warning(f"Account `{public_key[:8]}...` not found on Testnet. Please fund it using the friendbot. 💧")
        return None
    except BadRequestError as e:
        st.error(f"Error loading account `{public_key[:8]}...`: {e} 🚧")
        return None

def submit_signed_transaction(signed_xdr: str):
    """Submits a signed XDR to Horizon and handles the response."""
    try:
        tx_result = server.submit_transaction(signed_xdr)
        st.success(f"Transaction submitted successfully! 🔗 Hash: `{tx_result['hash'][:10]}...`")
        st.markdown(f"[View on StellarExpert](https://testnet.stellar.expert/tx/{tx_result['hash']})")
        st.session_state.last_tx_hash = tx_result['hash']
        st.session_state.xdr_to_sign = None # Clear transaction pending signature
        st.session_state.transaction_result = None # Clear result
        st.balloons()
        st.rerun()
        return tx_result
    except BadRequestError as e:
        error_message = f"Transaction failed: {e.extras.get('result_codes', {}).get('transaction', 'Unknown error')}"
        if e.extras and e.extras.get('result_codes', {}).get('operations'):
            op_errors = e.extras['result_codes']['operations']
            error_message += f"\nOperation errors: {', '.join(op_errors)}"
        st.error(f"{error_message} 🥀")
        st.session_state.xdr_to_sign = None
        st.session_state.transaction_result = None
        # st.exception(e) # Uncomment for detailed debugging
    except Exception as e:
        st.error(f"An unexpected error occurred: {e} 🌳")
        st.session_state.xdr_to_sign = None
        st.session_state.transaction_result = None


# --- Main Application Logic ---
st.title("The Petalfall Bazaar 🌸🌱")
st.markdown("A seasonal marketplace for digital 'pollen' and unique 'seeds'.")
st.markdown("---")

handle_freighter_response() # Check for Freighter responses on every rerun

# 1. Freighter Connection & Account Status
st.header("1. Connect Your Garden 🏡")
if not st.session_state.freighter_connected:
    connect_button = st.button("Connect Freighter Wallet 🔗", key="connect_freighter_btn")
    if connect_button:
        # Embed JS to connect Freighter and trigger a redirect with query params
        components.html(build_freighter_connect_script(), height=0, width=0, key="freighter_connect_executor")
        st.info("Awaiting Freighter connection... please approve in your wallet. ⏳")
        st.stop() # Stop further execution until redirect happens
else:
    st.success(f"Connected as: `{st.session_state.freighter_public_key}`")
    account = get_account_details(st.session_state.freighter_public_key)
    if account:
        col1, col2, col3 = st.columns(3)
        xlm_balance = next((b.balance for b in account.balances if b.asset_type == 'native'), '0')
        pollen_balance = next((b.balance for b in account.balances if b.asset_code == POLLEN_ASSET_CODE and b.asset_issuer == ISSUER_PUBLIC_KEY), '0')
        num_trustlines = len([b for b in account.balances if b.asset_type != 'native'])

        with col1:
            st.metric("XLM Balance 💰", f"{float(xlm_balance):.2f}")
        with col2:
            st.metric(f"{POLLEN_ASSET_CODE} Pollen 🌼", f"{float(pollen_balance):.2f}")
        with col3:
            st.metric("Trustlines 🌳", num_trustlines)

        # Calculate minimum required balance
        # Base reserve is 0.5 XLM. Each subentry (trustline, signer, data entry) adds 0.5 XLM.
        # Account itself counts as one entry.
        min_required_xlm = (account.num_subentries + 2) * MIN_BASE_RESERVE # +1 for base account, +1 for potential data entry
        st.info(f"Your account needs at least **{min_required_xlm:.2f} XLM** for reserves. Current balance: **{float(xlm_balance):.2f} XLM**")
        
        # Display ManageData entries as "Seeds"
        seed_data_entries = {k: v for k, v in account.data.items() if k.startswith("seed_creation_")}
        if seed_data_entries:
            st.subheader("Your Blossoming Seeds 🌱")
            st.markdown("These are unique data entries on your account, representing your cultivated seeds:")
            for key, value in seed_data_entries.items():
                try:
                    # Data values are base64 encoded by Stellar, decode to utf-8 for display
                    decoded_value = base64.b64decode(value).decode('utf-8')
                    st.markdown(f"- **{key.replace('seed_creation_', 'Seed ')}**: *Pollen Origin: {decoded_value}*")
                except Exception:
                    st.markdown(f"- **{key.replace('seed_creation_', 'Seed ')}**: *Invalid data value*")
        else:
            st.info("You haven't propagated any seeds yet. Cultivate some pollen and get started! 🧑‍🌾")
    
    # Allow user to disconnect
    if st.button("Disconnect Freighter 💔", key="disconnect_freighter_btn"):
        st.session_state.freighter_connected = False
        st.session_state.freighter_public_key = None
        st.session_state.xdr_to_sign = None
        st.session_state.transaction_result = None
        st.session_state.account_details_cache = {} # Clear cache
        st.query_params.clear() # Clear any pending params
        st.rerun()

st.markdown("---")

# --- Transaction Signing & Submission Logic ---
# This block handles the intermediate step of signing with Freighter
if st.session_state.xdr_to_sign:
    st.subheader("Sign Transaction with Freighter ✨")
    st.info("A transaction is ready for your signature. Please approve it in your Freighter wallet. ✍️")
    st.text_area("Transaction XDR (Read-only)", st.session_state.xdr_to_sign, height=150, disabled=True)
    
    # Trigger Freighter signing directly in HTML component
    components.html(build_freighter_sign_script(st.session_state.xdr_to_sign), height=0, width=0, key="freighter_sign_executor")
    st.stop() # Stop further execution until signed transaction comes back via query params
elif st.session_state.transaction_result and st.session_state.transaction_result["status"] == "success":
    st.subheader("Submitting Transaction... 🚀")
    signed_xdr = st.session_state.transaction_result["signed_xdr"]
    submit_signed_transaction(signed_xdr)
    st.stop() # Stop after submission

# Main dApp functions only accessible if Freighter is connected
if st.session_state.freighter_connected:
    user_account = get_account_details(st.session_state.freighter_public_key)
    
    # Check if user account is funded enough to do anything
    if not user_account:
        st.error("Your account is not funded. Please fund it via the friendbot (e.g., [Stellar Laboratory](https://laboratory.stellar.org/#account-creator?network=testnet)). 🛑")
        st.stop()

    st.header("2. Acquire Petalfall Pollen 🌼")
    st.markdown("To grow new seeds, you first need some Petalfall Pollen. Establish a trustline and then collect some from the faucet!")

    has_pollen_trustline = False
    pollen_balance = 0.0

    for balance in user_account.balances:
        if balance.asset_code == POLLEN_ASSET_CODE and balance.asset_issuer == ISSUER_PUBLIC_KEY:
            has_pollen_trustline = True
            pollen_balance = float(balance.balance)
            break
    
    if not has_pollen_trustline:
        st.warning(f"You need a trustline for {POLLEN_ASSET_CODE}. This allows your account to hold the asset. 🌿")
        if st.button(f"Establish Trustline for {POLLEN_ASSET_CODE} 🌱", key="trustline_btn"):
            try:
                # Need to load account again for fresh sequence number just before building TX
                source_account = server.load_account(st.session_state.freighter_public_key)
                transaction = TransactionBuilder(
                    source_account=source_account,
                    network_passphrase=NETWORK_PASSPHRASE,
                    base_fee=100
                ).add_operation(
                    stellar_sdk.ChangeTrust(
                        asset=POLLEN_ASSET,
                        limit="100000000000" # A very large limit, effectively infinite for practical purposes
                    )
                ).set_timeout(300).build()
                
                st.session_state.xdr_to_sign = transaction.to_xdr()
                st.rerun()
            except Exception as e:
                st.error(f"Error building trustline transaction: {e} 🚧")
    else:
        st.success(f"Trustline for {POLLEN_ASSET_CODE} established! Your current balance: **{pollen_balance:.2f} 🌼**")
        st.markdown("---")
        st.subheader("Pollen Faucet 💧")
        st.markdown("Receive some complimentary Petalfall Pollen to get started with your cultivation! (Issuer-signed transaction)")
        
        col_faucet_input, col_faucet_button = st.columns([0.7, 0.3])
        with col_faucet_input:
            pollen_amount = st.number_input("Amount of Pollen to collect 🌼", min_value=1, max_value=100, value=10, key="faucet_amount")
        with col_faucet_button:
            st.markdown("<br>", unsafe_allow_html=True) # Spacer for alignment
            if st.button(f"Collect {pollen_amount} Pollen", key="collect_pollen_btn"):
                try:
                    # Issuer signs this transaction - no Freighter needed for this part
                    issuer_account = server.load_account(ISSUER_PUBLIC_KEY)
                    transaction = TransactionBuilder(
                        source_account=issuer_account,
                        network_passphrase=NETWORK_PASSPHRASE,
                        base_fee=100
                    ).add_operation(
                        stellar_sdk.Payment(
                            destination=st.session_state.freighter_public_key,
                            asset=POLLEN_ASSET,
                            amount=str(float(pollen_amount))
                        )
                    ).set_timeout(300).build()
                    
                    transaction.sign(ISSUER_KEY) # Issuer's key signs
                    submit_signed_transaction(transaction.to_xdr())

                except Exception as e:
                    st.error(f"Error distributing pollen: {e} 🐛")
                    # st.exception(e)

    st.markdown("---")

    st.header("3. Propagate a Unique Seed 🌱")
    st.markdown("Cultivate a new digital 'seed' by paying pollen and recording a unique data entry on your account. This is your seed! 🏷️")
    st.info(f"**Cost to propagate a seed**: 1 {POLLEN_ASSET_CODE} 🌼 (paid to the Bazaar Issuer)")
    st.info(f"**Reserve increase for data entry**: {MIN_BALANCE_PER_ENTRY} XLM 💰 (permanently reserved on your account)")

    if pollen_balance < 1.0:
        st.warning("You need at least 1 PETALFALL Pollen to propagate a seed. 🐝")
    elif float(user_account.balances[0].balance) < (user_account.num_subentries + 2) * MIN_BASE_RESERVE: # +2 for base account + new data entry
        st.warning(f"Your XLM balance is too low to create a new data entry. You need at least {(user_account.num_subentries + 2) * MIN_BASE_RESERVE:.2f} XLM for reserves. 💰")
    else:
        seed_name_hint = st.text_input("Give your seed a unique identifier (optional, auto-generated if empty). e.g., 'GiantSunflowerSeed' 🌻", key="seed_name_input")
        if st.button("Propagate Seed! 🌱", key="propagate_seed_btn"):
            try:
                # Need to load account again for fresh sequence number just before building TX
                source_account = server.load_account(st.session_state.freighter_public_key)

                # Generate unique seed ID
                if not seed_name_hint:
                    seed_id_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
                    seed_id = f"seed_creation_{int(time.time())}_{seed_id_suffix}"
                else:
                    # Sanitize the seed_name_hint to be a valid ManageData key
                    sanitized_name = "".join(c for c in seed_name_hint if c.isalnum()).lower()
                    seed_id = f"seed_creation_{sanitized_name}_{int(time.time())}"
                
                # The data value will be the pollen asset code used, indicating source
                seed_data_value = POLLEN_ASSET_CODE

                transaction = TransactionBuilder(
                    source_account=source_account,
                    network_passphrase=NETWORK_PASSPHRASE,
                    base_fee=100
                ).add_operation(
                    # Operation 1: Pay 1 Pollen to the Issuer (the cost)
                    stellar_sdk.Payment(
                        destination=ISSUER_PUBLIC_KEY,
                        asset=POLLEN_ASSET,
                        amount="1.0" 
                    )
                ).add_operation(
                    # Operation 2: Add a unique data entry to the user's account (the seed)
                    stellar_sdk.ManageData(
                        data_name=seed_id,
                        data_value=seed_data_value.encode('utf-8') # Must be bytes, max 64 bytes
                    )
                ).set_timeout(300).build()
                
                st.session_state.xdr_to_sign = transaction.to_xdr()
                st.rerun()

            except Exception as e:
                st.error(f"Error building seed propagation transaction: {e} 🐛")
                # st.exception(e)
else:
    st.info("Please connect your Freighter wallet to interact with The Petalfall Bazaar. 🌷")

st.markdown("---")
if st.session_state.last_tx_hash:
    st.caption(f"Last Transaction Hash: [{st.session_state.last_tx_hash[:10]}...](https://testnet.stellar.expert/tx/{st.session_state.last_tx_hash}) 🔎")