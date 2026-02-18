import streamlit as st
import streamlit.components.v1 as components
import stellar_sdk
from stellar_sdk import Server, Keypair, TransactionBuilder, Network, Asset
from stellar_sdk.exceptions import BadRequestError, NotFoundError
import json
import time # For simulating network delays or unique identifiers
import hashlib # For creating unique whisper IDs from content
import urllib.parse # For URL encoding query parameters

# --- CRITICAL IMPORT RULES (MANDATE 7) ---
# Always include 'import stellar_sdk' at the top: CHECK
# Then: 'from stellar_sdk import Server, Keypair, TransactionBuilder, Network, Asset': CHECK
# Then: 'from stellar_sdk.exceptions import BadRequestError, NotFoundError': CHECK
# NEVER import 'Ed25519PublicKeyInvalidError'. Use 'ValueError': CHECK (Will use ValueError if needed)
# NEVER import 'AssetType': CHECK

# --- GLOBAL CONFIGURATION ---
HORIZON_URL = "https://horizon-testnet.stellar.org"
NETWORK_PASSPHRASE = Network.TESTNET_NETWORK_PASSPHRASE
SERVER = Server(HORIZON_URL) # --- STELLAR SERVER RULES (MANDATE 8): NEVER pass 'timeout' to Server() ---

# --- SECRET KEY HANDLING (MANDATE 11) ---
if "ISSUER_SECRET_KEY" in st.secrets:
    ISSUER_SECRET_KEY = st.secrets["ISSUER_SECRET_KEY"]
else:
    if "demo_issuer_key_secret" not in st.session_state:
        st.session_state.demo_issuer_key_secret = Keypair.random().secret
    ISSUER_SECRET_KEY = st.session_state.demo_issuer_key_secret
    st.sidebar.warning("Using Ephemeral Demo Keys for Issuer. Data is not permanent across sessions. Refresh will lose issuer state.")

ISSUER_KEYPAIR = Keypair.from_secret(ISSUER_SECRET_KEY)
ISSUER_PUBLIC_KEY = ISSUER_KEYPAIR.public_key

# Define the Spectral Whisper Token
WHISPER_ASSET_CODE = "WHISPER"
WHISPER_ASSET = Asset(WHISPER_ASSET_CODE, ISSUER_PUBLIC_KEY)

# --- Session State Initialization ---
if 'freighter_connected' not in st.session_state:
    st.session_state.freighter_connected = False
if 'freighter_public_key' not in st.session_state:
    st.session_state.freighter_public_key = None
if 'whispers' not in st.session_state:
    st.session_state.whispers = {} # {whisper_id: {'sender': public_key, 'message': message, 'timestamp': time, 'tx_hash': tx_hash}}
if 'account_balances' not in st.session_state:
    st.session_state.account_balances = {}
if 'pending_tx_purpose' not in st.session_state: # To track what a signed XDR was for
    st.session_state.pending_tx_purpose = None
if 'pending_whisper_content' not in st.session_state: # To store full content for whisper
    st.session_state.pending_whisper_content = None

# --- Custom Retro/Pixel-Art CSS (MANDATE 3) ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap');

    html, body, [class*="st-emotion-cache"] {
        font-family: 'Press Start 2P', monospace;
        background-color: #0d0d0d; /* Dark background */
        color: #00ff00; /* Neon green text */
        overflow-x: hidden;
    }

    h1, h2, h3, h4, h5, h6, .stMarkdown, .stLabel, .stButton>button, .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        font-family: 'Press Start 2P', monospace;
        color: #00ff00;
        text-shadow: 0 0 5px #00ff00; /* Subtle neon glow */
    }
    
    .st-emotion-cache-1r6dm7f { /* This targets the overall main content area */
        background-color: #1a1a1a;
        border: 2px solid #00cc00; /* Neon border */
        box-shadow: 0 0 10px #00cc00;
        padding: 10px;
        border-radius: 5px;
    }

    .stButton>button {
        background-color: #003300; /* Darker green button */
        color: #00ff00;
        border: 2px solid #00ff00;
        border-radius: 3px;
        padding: 8px 15px;
        text-transform: uppercase;
        box-shadow: 0 0 5px #00ff00;
        transition: all 0.2s;
    }
    .stButton>button:hover {
        background-color: #004400;
        box-shadow: 0 0 15px #00ff00;
        cursor: pointer;
    }
    .stButton>button:active {
        background-color: #002200;
        box-shadow: 0 0 2px #00ff00;
    }

    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        background-color: #0a0a0a;
        color: #00ff00;
        border: 1px solid #00aa00;
        border-radius: 3px;
        padding: 5px;
    }
    .stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus {
        border-color: #00ff00;
        box-shadow: 0 0 8px #00ff00;
        outline: none;
    }

    .st-emotion-cache-eq8hrv { /* Targets st.metric label */
        color: #00cc00;
    }
    .st-emotion-cache-1pgaj74 { /* Targets st.metric value */
        color: #00ff00;
        text-shadow: 0 0 8px #00ff00;
    }
    
    .stAlert {
        background-color: #2a2a00; /* Dark yellow/green */
        color: #ffff00;
        border: 1px solid #ffff00;
        box-shadow: 0 0 5px #ffff00;
    }
    .stWarning {
        background-color: #332200; /* Dark orange */
        color: #ffaa00;
        border: 1px solid #ffaa00;
        box-shadow: 0 0 5px #ffaa00;
    }
    .stSuccess {
        background-color: #002a00; /* Dark green */
        color: #00ff00;
        border: 1px solid #00ff00;
        box-shadow: 0 0 5px #00ff00;
    }
    .stError {
        background-color: #330000; /* Dark red */
        color: #ff0000;
        border: 1px solid #ff0000;
        box-shadow: 0 0 5px #ff0000;
    }
    
    .stExpander, .stInfo {
        background-color: #151515;
        border: 1px dashed #008800; /* Dashed border for panels */
        padding: 10px;
        border-radius: 3px;
        margin-bottom: 10px;
    }
    .stExpander > div > div > p { /* Expander header text */
        color: #00ff00;
    }
    
    /* Hide Streamlit footer and header */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True
)

# --- Freighter Integration HTML/JS (MANDATE 1 & 9) ---
# This single hidden component listens for messages from its parent (Streamlit)
# and sends results back by updating the parent's URL query parameters.
FREIGHTER_HTML = f"""
<script src="https://unpkg.com/@stellar/freighter-api@1.2.0/build/freighter.min.js"></script>
<script>
    function updateParentQueryParam(key, value) {{
        const url = new URL(window.parent.location.href);
        url.searchParams.set(key, value);
        window.parent.location.href = url.toString();
    }}

    async function connectFreighter() {{
        try {{
            const publicKey = await window.freighterApi.getPublicKey();
            const data = {{ type: 'freighter_connected', data: {{ publicKey: publicKey }} }};
            updateParentQueryParam('freighter_response', encodeURIComponent(JSON.stringify(data)));
        }} catch (error) {{
            console.error("Freighter connection failed:", error);
            const data = {{ type: 'freighter_error', data: error.message }};
            updateParentQueryParam('freighter_response', encodeURIComponent(JSON.stringify(data)));
        }}
    }}

    async function signTransaction(xdr, networkPassphrase) {{
        try {{
            const signedXDR = await window.freighterApi.signTransaction(xdr, {{ networkPassphrase: networkPassphrase }});
            const data = {{ type: 'transaction_signed', data: {{ signedXDR: signedXDR }} }};
            updateParentQueryParam('freighter_response', encodeURIComponent(JSON.stringify(data)));
        }} catch (error) {{
            console.error("Transaction signing failed:", error);
            const data = {{ type: 'freighter_error', data: error.message }};
            updateParentQueryParam('freighter_response', encodeURIComponent(JSON.stringify(data)));
        }}
    }}

    // Listen for messages from Streamlit parent frame
    window.addEventListener('message', async (event) => {{
        // Ensure the message is from the expected origin and has the correct structure
        if (event.data && event.data.type) {{
            if (event.data.type === 'connectFreighter') {{
                connectFreighter();
            }} else if (event.data.type === 'signTransaction') {{
                const {{ xdr, networkPassphrase }} = event.data.data;
                signTransaction(xdr, networkPassphrase);
            }}
        }}
    }});
</script>
"""
# --- HTML COMPONENT RULES (MANDATE 9) ---
# ALWAYS use: 'import streamlit.components.v1 as components'
# ALWAYS call: 'components.html(...)'. NEVER call 'html(...)' directly from 'streamlit'.
components.html(FREIGHTER_HTML, height=0, width=0, key="freighter_script_loader")


# --- Utility Functions ---

def send_message_to_freighter_iframe(message_type, data=None):
    """
    Sends a message from Streamlit to the embedded Freighter iframe.
    This works by rendering a temporary HTML component that executes JS to post a message.
    """
    js_code = f"""
    <script>
        // Assuming the Freighter iframe is the first one in the document
        const freighterIframe = window.parent.document.querySelector('iframe');
        if (freighterIframe && freighterIframe.contentWindow) {{
            freighterIframe.contentWindow.postMessage({{ type: '{message_type}', data: {json.dumps(data)} }}, '*');
        }} else {{
            console.error("Freighter iframe not found or not ready.");
        }}
    </script>
    """
    components.html(js_code, height=0, width=0, key=f"send_msg_to_freighter_{time.time()}")


def handle_freighter_response():
    """Reads messages from the JS component (via query_params) and updates session state. (MANDATE 4)"""
    response_encoded = st.query_params.get("freighter_response")
    if response_encoded:
        response_str = urllib.parse.unquote(response_encoded)
        try:
            response = json.loads(response_str)
            if response['type'] == 'freighter_connected':
                st.session_state.freighter_connected = True
                st.session_state.freighter_public_key = response['data']['publicKey']
                st.success(f"Freighter Connected! Public Key: {st.session_state.freighter_public_key[:8]}...")
            elif response['type'] == 'transaction_signed':
                st.session_state.signed_xdr = response['data']['signedXDR']
                # The next step would typically be to submit this XDR to Horizon.
                # This will be handled after this function returns and `st.rerun` occurs.
            elif response['type'] == 'freighter_error':
                st.error(f"Freighter Error: {response['data']}")
            
            # Clear the query param to avoid re-processing by setting it to an empty string.
            st.query_params["freighter_response"] = ""
            st.rerun() # Rerun to remove the query param and update UI
        except json.JSONDecodeError:
            st.error("Error decoding Freighter response from query parameters.")
        except Exception as e:
            st.error(f"An unexpected error occurred while processing Freighter response: {e}")

def get_account_details(public_key):
    """Fetches account details from Horizon."""
    try:
        account = SERVER.load_account(public_key=public_key)
        st.session_state.account_balances[public_key] = {}
        for balance in account.balances:
            asset_code = balance.asset_code if hasattr(balance, 'asset_code') else 'XLM'
            st.session_state.account_balances[public_key][asset_code] = balance.balance
        return account
    except NotFoundError:
        st.session_state.account_balances[public_key] = {} # Account doesn't exist
        return None
    except Exception as e:
        st.error(f"Error loading account {public_key}: {e}")
        return None

def fund_account(target_public_key):
    """Funds an account using the issuer keypair."""
    try:
        source_account = SERVER.load_account(ISSUER_PUBLIC_KEY)
        transaction = (
            TransactionBuilder(
                source_account=source_account,
                network_passphrase=NETWORK_PASSPHRASE,
            )
            .append_create_account_op(
                destination=target_public_key,
                starting_balance="10" # Start with 10 XLM
            )
            .set_base_fee(100)
            .build()
        )
        transaction.sign(ISSUER_KEYPAIR)
        SERVER.submit_transaction(transaction)
        st.success(f"Account {target_public_key[:8]}... funded with 10 XLM!")
        get_account_details(target_public_key) # Refresh balances
    except BadRequestError as e:
        st.error(f"Funding failed: {e.extras.get('result_codes', {}).get('transaction', 'Unknown error')}")
    except Exception as e:
        st.error(f"An unexpected error occurred during funding: {e}")

def create_whisper_asset_and_account():
    """
    Ensures the issuer account exists.
    For simplicity, no explicit "asset creation" is needed beyond the issuer having keys.
    """
    try:
        try:
            SERVER.load_account(ISSUER_PUBLIC_KEY)
            st.sidebar.caption(f"Issuer Account: {ISSUER_PUBLIC_KEY[:8]}...")
        except NotFoundError:
            st.sidebar.warning(f"Issuer account {ISSUER_PUBLIC_KEY[:8]}... not found. Attempting to fund via Friendbot (Testnet only)...")
            try:
                # Friendbot only works on testnet.
                friendbot_url = f"https://friendbot.stellar.org/?addr={ISSUER_PUBLIC_KEY}"
                import requests
                response = requests.get(friendbot_url)
                if response.status_code == 200:
                    SERVER.load_account(ISSUER_PUBLIC_KEY) # Verify it now exists
                    st.sidebar.success(f"Issuer account {ISSUER_PUBLIC_KEY[:8]}... created/funded via Friendbot!")
                else:
                    st.sidebar.error(f"Friendbot funding failed (Status: {response.status_code}): {response.text}")
                    st.stop()
            except Exception as e:
                st.sidebar.error(f"Error with Friendbot: {e}")
                st.stop()
    except Exception as e:
        st.error(f"Error during issuer setup: {e}")
        st.stop()

# --- UI Components ---

def display_account_info(public_key, is_freighter_user=True):
    """Displays account balances and funding options. (MANDATE 6)"""
    st.subheader(f"Account: {public_key[:8]}... {'(Your Freighter Wallet)' if is_freighter_user else '(Issuer)'}")
    
    account_details = get_account_details(public_key)

    col1, col2 = st.columns(2) # MANDATE 6: st.columns
    if account_details:
        for asset_code, balance in st.session_state.account_balances[public_key].items():
            st.metric(f"{asset_code} Balance", f"{float(balance):.2f}") # MANDATE 6: st.metric
        
        # Check if user trusts WHISPER asset
        if is_freighter_user and WHISPER_ASSET_CODE not in st.session_state.account_balances[public_key]:
            col1.warning(f"You don't trust {WHISPER_ASSET_CODE}. You cannot receive whispers without a trustline.")
            if col2.button(f"Create {WHISPER_ASSET_CODE} Trustline", key=f"trustline_btn_{public_key}"):
                st.session_state.pending_tx_purpose = 'create_trustline'
                create_trustline(public_key)
    else:
        st.warning("Account does not exist on the network.")
        if is_freighter_user:
            if st.button("Fund Your Account (10 XLM via Issuer)", key=f"fund_btn_{public_key}"):
                fund_account(public_key)
        else:
            st.info("Issuer account needs to be funded (e.g., via Friendbot for Testnet).")

def create_trustline(public_key):
    """Initiates a ChangeTrust operation via Freighter. (MANDATE 8: Access operations via module)"""
    try:
        source_account = SERVER.load_account(public_key)
        transaction = (
            TransactionBuilder(
                source_account=source_account,
                network_passphrase=NETWORK_PASSPHRASE,
            )
            .append_change_trust_op( # MANDATE 8: stellar_sdk.ChangeTrust
                asset=WHISPER_ASSET,
                limit="1000000000" # High limit
            )
            .set_base_fee(100)
            .build()
        )
        xdr = transaction.to_xdr()
        send_message_to_freighter_iframe('signTransaction', {'xdr': xdr, 'networkPassphrase': NETWORK_PASSPHRASE})
        st.info("Awaiting Freighter signature for trustline...")
    except NotFoundError:
        st.error("Account not found. Please fund your account first.")
    except Exception as e:
        st.error(f"Error building trustline transaction: {e}")

def submit_signed_xdr(signed_xdr):
    """Submits a signed XDR to the Stellar network."""
    try:
        tx_result = SERVER.submit_transaction(signed_xdr)
        st.success("Transaction successful!")
        st.json(tx_result)
        get_account_details(st.session_state.freighter_public_key) # Refresh balances
        return tx_result
    except BadRequestError as e:
        st.error(f"Transaction failed: {e.extras.get('result_codes', {}).get('transaction', 'Unknown error')}")
        st.error(f"Problem account: {st.session_state.freighter_public_key}")
        st.json(e.response.text)
    except Exception as e:
        st.error(f"An unexpected error occurred during transaction submission: {e}")
    return None

def transmit_whisper(sender_public_key, message_content):
    """Creates a payment to the issuer with the message as a memo."""
    
    if not message_content:
        st.error("Whisper message cannot be empty!")
        return

    try:
        source_account = SERVER.load_account(sender_public_key)
        
        # Max memo size for text is 28 bytes.
        if len(message_content.encode('utf-8')) > 28:
            st.warning("Whisper message is too long (>28 bytes) for direct on-chain storage. It will be truncated for the transaction memo (though full content is stored locally for demo).")
            memo_content = message_content.encode('utf-8')[:28].decode('utf-8', errors='ignore')
        else:
            memo_content = message_content
            
        transaction = (
            TransactionBuilder(
                source_account=source_account,
                network_passphrase=NETWORK_PASSPHRASE,
            )
            .append_payment_op(
                destination=ISSUER_PUBLIC_KEY,
                asset=Asset.native(), # XLM
                amount="0.1" # Cost to transmit a whisper
            )
            .add_memo(stellar_sdk.MemoText(memo_content)) # Store whisper in memo
            .set_base_fee(100)
            .build()
        )
        xdr = transaction.to_xdr()
        send_message_to_freighter_iframe('signTransaction', {'xdr': xdr, 'networkPassphrase': NETWORK_PASSPHRASE})
        st.info("Awaiting Freighter signature for whisper transmission...")
    except NotFoundError:
        st.error("Your account not found. Please fund it first.")
    except BadRequestError as e:
        st.error(f"Error during whisper transmission: {e.extras.get('result_codes', {}).get('transaction', 'Unknown error')}")
    except Exception as e:
        st.error(f"An unexpected error occurred building whisper transaction: {e}")


def process_signed_xdr_for_whisper(signed_xdr, original_message):
    """
    Submits the signed XDR for a whisper transmission and registers the whisper locally.
    This function is called after Freighter returns a signed XDR for a whisper.
    """
    tx_result = submit_signed_xdr(signed_xdr)
    if tx_result:
        whisper_id = hashlib.sha256(original_message.encode('utf-8')).hexdigest()
        st.session_state.whispers[whisper_id] = {
            'sender': st.session_state.freighter_public_key,
            'message': original_message, # Store the full message, not just the truncated memo
            'timestamp': time.time(),
            'tx_hash': tx_result['hash']
        }
        st.success(f"Spectral Whisper Transmitted! ID: {whisper_id[:8]}...")
    

# --- Main App Logic ---

# Sidebar (MANDATE 10)
with st.sidebar:
    st.info("""
    # The Spectral Radiogram 📻🧬
    _A pixel-art dApp where users transmit ephemeral, tokenized "spectral whispers" and "tune in" to receive them, navigating a mysterious digital aether with patronage and discovery mechanics._
    """) # MANDATE 10: App Name and Concept
    st.caption("✨ Visual Style: Retro/Pixel-Art ✨") # MANDATE 10: Visual Style
    st.markdown("---")

    st.subheader("Freighter Connection")
    if not st.session_state.freighter_connected:
        if st.button("Connect Freighter 🚀"):
            send_message_to_freighter_iframe('connectFreighter')
            st.info("Awaiting Freighter connection...")
    else:
        st.success(f"Connected: {st.session_state.freighter_public_key[:8]}...")
        if st.button("Disconnect Freighter 🔒"):
            st.session_state.freighter_connected = False
            st.session_state.freighter_public_key = None
            st.session_state.account_balances = {}
            st.session_state.pending_tx_purpose = None
            st.session_state.pending_whisper_content = None
            st.success("Freighter disconnected.")
            st.rerun()

    st.markdown("---")
    st.subheader("System Info")
    st.caption(f"Horizon: {HORIZON_URL.split('//')[1]}")
    st.caption(f"Network: {NETWORK_PASSPHRASE.split(' ')[0]}") # Just 'Testnet' or 'Public'
    st.caption(f"Issuer: {ISSUER_PUBLIC_KEY[:8]}...")
    st.metric("Total Whispers Transmitted", len(st.session_state.whispers)) # MANDATE 6: st.metric

# Handle Freighter responses pushed into query_params by the JS component (MANDATE 4)
handle_freighter_response()

# Check if a transaction needs to be submitted after Freighter signing
if 'signed_xdr' in st.session_state and st.session_state.signed_xdr:
    st.info("Transaction signed by Freighter. Submitting to network...")
    
    if st.session_state.pending_tx_purpose == 'create_trustline':
        submit_signed_xdr(st.session_state.signed_xdr)
    elif st.session_state.pending_tx_purpose == 'transmit_whisper':
        if st.session_state.pending_whisper_content:
            process_signed_xdr_for_whisper(st.session_state.signed_xdr, st.session_state.pending_whisper_content)
            st.session_state.pending_whisper_content = None
        else:
            st.error("Signed whisper XDR received, but original content missing. Whisper not registered.")
    else:
        st.error("Signed XDR received, but purpose is unknown. Transaction not submitted.")

    # Clear pending state after processing or if purpose is unknown
    st.session_state.signed_xdr = None # Clear once processed or attempted
    st.session_state.pending_tx_purpose = None # Clear purpose

    st.rerun() # Rerun to clear pending state and update UI


# --- Main Content Area --- (MANDATE 6: Clean UI)
st.title("The Spectral Radiogram 📻") # MANDATE 5: Emojis only

st.markdown("""
Welcome, voyager, to the ethereal expanse of the Spectral Radiogram. Here, thoughts and feelings
crystallize into **Spectral Whispers** — ephemeral tokens adrift in the digital aether.
Transmit your own, or tune in to the echoes of others.
""")

st.subheader("Your Connection Status")
if st.session_state.freighter_connected:
    display_account_info(st.session_state.freighter_public_key)
else:
    st.warning("Please connect your Freighter wallet in the sidebar to interact with the Radiogram.")

st.markdown("---")

# Section: Transmit a Spectral Whisper
with st.expander("📡 Transmit a Spectral Whisper", expanded=True): # MANDATE 6: st.expander
    st.markdown("""
    Craft a message to imbue into the aether. A small offering of **0.1 XLM**
    is required to broadcast your whisper across the network.
    """)
    
    if st.session_state.freighter_connected:
        user_balance_xlm = float(st.session_state.account_balances.get(st.session_state.freighter_public_key, {}).get('XLM', 0))
        
        whisper_message = st.text_area(
            "Your Whisper (max ~28 characters for on-chain memo, full message stored here for demo):",
            key="whisper_input",
            max_chars=200 # Allow longer for local storage, but warn for memo
        )
        
        can_transmit = user_balance_xlm >= 0.1 and bool(whisper_message)
        
        if not can_transmit:
            if not bool(whisper_message):
                st.info("Type your message above to enable transmission.")
            if user_balance_xlm < 0.1:
                st.error("Insufficient XLM balance to transmit a whisper. Please fund your account above.")
        
        if st.button("Broadcast Whisper 🔊", disabled=not can_transmit): # MANDATE 5: Emojis only
            st.session_state.pending_tx_purpose = 'transmit_whisper'
            st.session_state.pending_whisper_content = whisper_message # Store full content
            transmit_whisper(st.session_state.freighter_public_key, whisper_message)
    else:
        st.info("Connect your Freighter wallet to transmit whispers.")

st.markdown("---")

# Section: Tune In to Whispers
with st.expander("👂 Tune In to Whispers", expanded=True): # MANDATE 6: st.expander
    st.markdown("""
    Scan the frequencies and discover the spectral whispers floating in the digital haze.
    """)

    if not st.session_state.whispers:
        st.info("The aether is silent... Be the first to transmit a whisper!")
    else:
        whisper_keys = sorted(st.session_state.whispers.keys(), key=lambda k: st.session_state.whispers[k]['timestamp'], reverse=True)
        
        selected_whisper_id = st.query_params.get("whisper_id") # MANDATE 4: st.query_params
        
        col_list, col_detail = st.columns([1, 2]) # MANDATE 6: st.columns

        with col_list:
            st.write("### Frequencies")
            for w_id in whisper_keys:
                whisper = st.session_state.whispers[w_id]
                sender_short = whisper['sender'][:4] + "..." + whisper['sender'][-4:]
                preview = whisper['message'][:30] + "..." if len(whisper['message']) > 30 else whisper['message']
                
                if st.button(f"🧬 {sender_short}: _{preview}_", key=f"whisper_select_{w_id}", help=f"Click to view whisper by {sender_short}"): # MANDATE 5: Emojis only
                    # Update query_params and rerun (MANDATE 4: st.query_params)
                    st.query_params["whisper_id"] = w_id
                    st.rerun()

        with col_detail:
            st.write("### Radiogram Display")
            if selected_whisper_id and selected_whisper_id in st.session_state.whispers:
                whisper = st.session_state.whispers[selected_whisper_id]
                st.subheader(f"Whisper ID: {selected_whisper_id[:8]}...")
                st.markdown(f"**From:** `{whisper['sender']}`")
                st.markdown(f"**Broadcast Time:** {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(whisper['timestamp']))}")
                st.markdown(f"**Transaction Hash:** `{whisper['tx_hash'][:8]}...` ([View on StellarExpert](https://testnet.stellarexpert.io/tx/{whisper['tx_hash']}))")
                st.markdown("---")
                st.write("### Message:")
                st.markdown(f"> __{whisper['message']}__")
            else:
                st.info("Select a whisper from the 'Frequencies' to tune in.")

st.markdown("---")

# Final check and setup for issuer account
create_whisper_asset_and_account()