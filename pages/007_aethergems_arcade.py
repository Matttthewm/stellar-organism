import streamlit as st
import streamlit.components.v1 as components

# CRITICAL IMPORT RULES:
# - Always include 'import stellar_sdk' at the top.
# - Then: 'from stellar_sdk import Server, Keypair, TransactionBuilder, Network, Asset'
# - Then: 'from stellar_sdk.exceptions import BadRequestError, NotFoundError'
# - NEVER import 'Ed225519PublicKeyInvalidError'. Use 'ValueError'.
# - NEVER import 'AssetType'.
import stellar_sdk
from stellar_sdk import Server, Keypair, TransactionBuilder, Network, Asset
from stellar_sdk.exceptions import BadRequestError, NotFoundError

# --- CONFIGURATION ---
HORIZON_URL = "https://horizon-testnet.stellar.org"
NETWORK_PASSPHRASE = Network.TESTNET_NETWORK_PASSPHRASE

# AetherGem Asset details
AETHERGEM_CODE = "AGEM" # The code for the AetherGem custom asset

# --- GLOBAL HELPER FUNCTIONS ---

def load_stellar_server():
    """Loads and returns the Stellar Horizon server instance."""
    # STELLAR SERVER RULES: Use 'Server(HORIZON_URL)' only. NEVER pass 'timeout' to Server().
    return Server(HORIZON_URL)

def get_issuer_keypair():
    """
    Handles secret key loading for the AetherGem issuer/collector account.
    Implements Demo Mode fallback.
    """
    # SECRET KEY HANDLING:
    # - NEVER assume 'st.secrets' exists or has keys.
    # - ALWAYS implement a 'Demo Mode' fallback.
    if "ISSUER_KEY" in st.secrets:
        key = st.secrets["ISSUER_KEY"]
    else:
        if "demo_key" not in st.session_state:
            st.session_state.demo_key = Keypair.random().secret
            # --- Friendbot Funding for Demo Key (Essential for functional demo) ---
            # Note: This is a network request and might take a moment.
            # In a production app, this would be managed differently.
            try:
                friendbot_url = f"https://friendbot.stellar.org/?addr={Keypair.from_secret(st.session_state.demo_key).public_key}"
                import requests
                response = requests.get(friendbot_url)
                if response.status_code != 200:
                    st.error(f"Friendbot funding failed for demo key: {response.text}")
            except Exception as e:
                st.error(f"Friendbot funding exception: {e}")

        key = st.session_state.demo_key
        st.sidebar.warning("⚠️ Using Ephemeral Demo Keys for AetherGem Issuer/Collector.")
        st.sidebar.caption("💡 Friendbot funding might be requested for the demo key upon first load.")
    return Keypair.from_secret(key)

# Initialize issuer keypair and public key once
ISSUER_KEYPAIR = get_issuer_keypair()
ISSUER_PUBLIC_KEY = ISSUER_KEYPAIR.public_key
AETHERGEM_ASSET = Asset(AETHERGEM_CODE, ISSUER_PUBLIC_KEY)

# --- FRONTEND (Streamlit UI) ---

st.set_page_config(layout="wide", page_title="AetherGems Arcade 👾")

# Custom CSS for style "Retro/Pixel-Art"
# MANDATE 3: Custom CSS for style "Retro/Pixel-Art"
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap');

    /* General Body and App Styling */
    body {
        font-family: 'Press Start 2P', cursive;
        background-color: #1a1a2e; /* Deep space dark blue */
        color: #e0e0e0; /* Light gray for contrast */
    }
    .stApp {
        background-color: #1a1a2e;
    }

    /* Headings */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Press Start 2P', cursive;
        color: #ffcc00; /* Vibrant gold for titles */
        text-shadow: 2px 2px #990000; /* Retro pixel-art shadow effect */
        margin-bottom: 15px;
        margin-top: 25px;
    }
    h1 { font-size: 2.5em; }
    h2 { font-size: 2em; }
    h3 { font-size: 1.5em; }

    /* Buttons */
    .stButton>button {
        font-family: 'Press Start 2P', cursive;
        background-color: #007bff; /* Bright blue */
        color: white;
        border: 3px solid #0056b3; /* Darker blue border */
        border-radius: 0px; /* Sharp corners for retro look */
        box-shadow: 4px 4px #0056b3; /* Simulated 3D pixel-art shadow */
        padding: 10px 20px;
        transition: all 0.1s ease; /* Smooth transition for hover effects */
        line-height: 1.2; /* Adjust text height for pixel font */
        margin-top: 10px;
        margin-bottom: 10px;
    }
    .stButton>button:hover {
        background-color: #0056b3;
        box-shadow: 2px 2px #0056b3; /* Smaller shadow on hover to simulate press */
        transform: translate(2px, 2px); /* Moves button down/right */
    }

    /* Metrics */
    .stMetric {
        border: 2px solid #ffcc00; /* Gold border */
        border-radius: 0px;
        background-color: #330033; /* Dark cosmic purple */
        padding: 15px;
        margin-bottom: 15px;
        box-shadow: 4px 4px #990000; /* Red shadow for depth */
        text-align: center;
    }
    .stMetric > div:first-child { /* The label */
        font-family: 'Press Start 2P', cursive;
        color: #ffcc00;
        font-size: 0.85em;
        text-transform: uppercase;
        margin-bottom: 5px;
    }
    .stMetric > div:nth-child(2) > div:first-child { /* The value */
        font-family: 'Press Start 2P', cursive;
        color: #00ff00; /* Bright neon green for values */
        font-size: 1.7em;
        text-shadow: 1px 1px #009900;
    }
    .stMetric > div:nth-child(2) > div:nth-child(2) { /* The delta */
        font-family: 'Press Start 2P', cursive;
        color: #00ffff; /* Cyan for deltas */
        font-size: 0.9em;
    }

    /* Alerts and Warnings */
    .stAlert {
        border: 2px solid #ffcc00;
        border-radius: 0px;
        background-color: #330033;
        box-shadow: 3px 3px #990000;
        padding: 10px;
        margin-bottom: 15px;
    }
    .stAlert > div > div > p {
        font-family: 'Press Start 2P', cursive;
        color: #e0e0e0;
    }
    .stAlert.stWarning {
        background-color: #4a3300; /* Darker orange for warning */
        border-color: #ff9900;
        box-shadow: 3px 3px #cc6600;
    }
    .stAlert.stSuccess {
        background-color: #003300; /* Darker green for success */
        border-color: #00cc00;
        box-shadow: 3px 3px #006600;
    }
    .stAlert.stError {
        background-color: #330000; /* Darker red for error */
        border-color: #ff0000;
        box-shadow: 3px 3px #990000;
    }
    .stAlert.stInfo {
        background-color: #000033; /* Darker blue for info */
        border-color: #0000ff;
        box-shadow: 3px 3px #000066;
    }

    /* Text Inputs and Text Areas */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        font-family: 'Press Start 2P', cursive;
        background-color: #2b2b40; /* Slightly lighter than background */
        color: #00ff00; /* Neon green text */
        border: 2px solid #007bff; /* Blue border */
        border-radius: 0px;
        padding: 8px;
        margin-top: 5px;
    }

    /* Expander */
    .stExpander {
        border: 2px solid #ffcc00;
        border-radius: 0px;
        background-color: #330033;
        box-shadow: 3px 3px #990000;
        padding: 10px;
        margin-top: 15px;
    }
    .stExpander > div > div > p {
        font-family: 'Press Start 2P', cursive;
        color: #ffcc00;
        font-size: 0.9em;
    }
    .stExpander > div > div { /* Target the header */
        background-color: #2b002b; /* Slightly different background for header */
        padding: 8px 10px;
    }
    .stExpanderContent {
        padding-top: 10px;
    }

    /* Sidebar Styling */
    .css-r6z2z6 { /* Target sidebar main content area */
        background-color: #2b002b !important; /* Darker purple for sidebar */
    }
    .css-1lcbmhc { /* Sidebar header/title */
        font-family: 'Press Start 2P', cursive;
        color: #ffcc00;
        text-shadow: 1px 1px #990000;
        padding-bottom: 10px;
    }
    .sidebar .stButton > button {
        background-color: #ff9900; /* Orange button for sidebar */
        border-color: #cc6600;
        box-shadow: 4px 4px #cc6600;
    }
    .sidebar .stButton > button:hover {
        background-color: #cc6600;
        box-shadow: 2px 2px #cc6600;
        transform: translate(2px, 2px);
    }
    </style>
    """,
    unsafe_allow_html=True
)

# MANDATE 10: SIDEBAR MANDATE: App Name and Concept at the very top.
st.sidebar.info(
    "## 👾 AetherGems Arcade 👾\n\n"
    "A cosmic pixel-art arcade where players adopt, nurture, and evolve unique 'AetherGem' digital sprites, "
    "feeding them Stellar assets to uncover their full potential on the ledger."
)
# MANDATE 10: Show the 'Visual Style' in the sidebar as a badge/caption.
st.sidebar.caption("✨ **Visual Style:** Retro/Pixel-Art ✨")

st.title("🌌 AetherGems Arcade 🌠")

# Initialize session state variables
if "freighter_connected" not in st.session_state:
    st.session_state.freighter_connected = False
if "public_key" not in st.session_state:
    st.session_state.public_key = None
if "xlm_balance" not in st.session_state: # To show user XLM balance
    st.session_state.xlm_balance = 0.0
if "aethergem_level" not in st.session_state:
    st.session_state.aethergem_level = 0
if "aethergem_sprite" not in st.session_state:
    st.session_state.aethergem_sprite = "🥚" # Default egg sprite
if "aethergem_balance" not in st.session_state:
    st.session_state.aethergem_balance = 0
if "tx_status" not in st.session_state:
    st.session_state.tx_status = ""

# --- Freighter Integration JavaScript Component ---
# MANDATE 1: Freighter Integration (st.components.v1.html + signTransaction).
# MANDATE 9: HTML COMPONENT RULES: ALWAYS use 'import streamlit.components.v1 as components', ALWAYS call 'components.html(...)'.
FREIGHTER_COMPONENT_JS = """
<script src="https://unpkg.com/@stellar/freighter-api@latest/build/index.js"></script>
<script>
    // This script does not directly interact with Streamlit's query params.
    // Instead, it's set up to be called by Python, which then redirects to update query params.
    // This separation makes the component cleaner and relies on Streamlit's page rerun.
</script>
"""
components.html(FREIGHTER_COMPONENT_JS, height=0, width=0) # Hidden component

# --- Stellar Helper Functions ---

# MANDATE 8: STELLAR SERVER RULES: Server(HORIZON_URL) only.
server = load_stellar_server()

def get_account_data(public_key):
    """Fetches account data and updates session state."""
    if not public_key:
        return None
    try:
        account = server.load_account(public_key)
        # Update XLM balance
        for balance in account.balances:
            if balance.asset_type == 'native':
                st.session_state.xlm_balance = float(balance.balance)
                break
        else:
            st.session_state.xlm_balance = 0.0

        # Update AetherGem balance and state
        st.session_state.aethergem_balance = 0
        for balance in account.balances:
            if balance.asset_code == AETHERGEM_CODE and balance.asset_issuer == ISSUER_PUBLIC_KEY:
                st.session_state.aethergem_balance = float(balance.balance)
                break

        # Load AetherGem level and sprite from account data entries
        st.session_state.aethergem_level = 0
        st.session_state.aethergem_sprite = "🥚" # Default
        for key, value in account.data.items():
            try:
                decoded_key = bytes.fromhex(key).decode('utf-8')
                decoded_value = bytes.fromhex(value).decode('utf-8')
                if decoded_key == 'aethergem_level':
                    st.session_state.aethergem_level = int(decoded_value)
                elif decoded_key == 'aethergem_sprite':
                    st.session_state.aethergem_sprite = decoded_value
            except (UnicodeDecodeError, ValueError):
                # Handle cases where data entry might not be UTF-8 or hex
                pass
        return account
    except NotFoundError:
        return None # Account does not exist
    except Exception as e:
        st.error(f"Error loading account data: {e}")
        return None

def submit_transaction(transaction_xdr):
    """Submits a signed transaction to the Stellar network."""
    try:
        response = server.submit_transaction(transaction_xdr)
        st.session_state.tx_status = f"✅ Transaction successful! Hash: {response['hash']}"
        st.success(f"Transaction successful! Hash: {response['hash']}")
        st.expander("Transaction Details").json(response) # MANDATE 6: Use st.expander
        # Force refresh account data after transaction
        get_account_data(st.session_state.public_key)
        return True
    except BadRequestError as e:
        error_message = e.extras.get('result_codes', {}).get('transaction', 'Unknown error')
        st.session_state.tx_status = f"❌ Transaction failed: {error_message}"
        st.error(f"Transaction failed: {error_message}")
        if 'result_codes' in e.extras:
            st.expander("Error Details").json(e.extras) # MANDATE 6: Use st.expander
        return False
    except Exception as e:
        st.session_state.tx_status = f"❌ An unexpected error occurred: {e}"
        st.error(f"An unexpected error occurred: {e}")
        return False

# --- Transaction Builders ---
# MANDATE 8: Access operations via module: 'stellar_sdk.ChangeTrust(...)'.

def build_trustline_tx(user_public_key):
    """Builds an XDR for establishing a trustline to AetherGem asset."""
    try:
        account = server.load_account(user_public_key)
        op = stellar_sdk.ChangeTrust(
            asset=AETHERGEM_ASSET,
            limit="1000000000", # Arbitrarily high limit for custom asset
            source=user_public_key
        )
        transaction = TransactionBuilder(
            source_account=account,
            network_passphrase=NETWORK_PASSPHRASE,
            base_fee=100
        ).add_operation(op).set_timeout(100).build()
        return transaction.to_xdr()
    except Exception as e:
        st.error(f"Error building trustline transaction: {e}")
        return None

def build_initial_gem_data_tx(user_public_key):
    """Builds an XDR for the user to set their initial AetherGem level and sprite."""
    try:
        account = server.load_account(user_public_key)
        initial_level_op = stellar_sdk.ManageData(
            data_name="aethergem_level",
            data_value="1".encode('utf-8'),
            source=user_public_key
        )
        initial_sprite_op = stellar_sdk.ManageData(
            data_name="aethergem_sprite",
            data_value="🥚".encode('utf-8'),
            source=user_public_key
        )
        transaction = TransactionBuilder(
            source_account=account,
            network_passphrase=NETWORK_PASSPHRASE,
            base_fee=100
        ).add_operation(initial_level_op).add_operation(initial_sprite_op).set_timeout(100).build()
        return transaction.to_xdr()
    except Exception as e:
        st.error(f"Error building initial gem data transaction: {e}")
        return None

def build_issuer_mint_gem_tx(user_public_key):
    """Builds and signs an XDR for the issuer to send 1 AetherGem to the user."""
    try:
        issuer_account = server.load_account(ISSUER_PUBLIC_KEY)
        payment_op = stellar_sdk.Payment(
            destination=user_public_key,
            asset=AETHERGEM_ASSET,
            amount="1",
            source=ISSUER_PUBLIC_KEY
        )
        tx_builder = TransactionBuilder(
            source_account=issuer_account,
            network_passphrase=NETWORK_PASSPHRASE,
            base_fee=100
        ).add_operation(payment_op).set_timeout(100)
        
        tx = tx_builder.build()
        tx.sign(ISSUER_KEYPAIR) # Issuer signs this transaction
        return tx.to_xdr()
    except Exception as e:
        st.error(f"Error building issuer mint transaction: {e}")
        return None

def build_feed_gem_tx(user_public_key, amount_xlm="0.1"):
    """Builds an XDR for feeding the AetherGem (sends XLM to collector)."""
    try:
        account = server.load_account(user_public_key)
        op = stellar_sdk.Payment(
            destination=ISSUER_PUBLIC_KEY, # Collector account is the issuer account
            asset=Asset.native(), # XLM
            amount=amount_xlm,
            source=user_public_key
        )
        transaction = TransactionBuilder(
            source_account=account,
            network_passphrase=NETWORK_PASSPHRASE,
            base_fee=100
        ).add_operation(op).set_timeout(100).build()
        return transaction.to_xdr()
    except Exception as e:
        st.error(f"Error building feed gem transaction: {e}")
        return None

def build_evolve_gem_tx(user_public_key, new_level, new_sprite):
    """Builds an XDR for evolving the AetherGem (updates data entries)."""
    try:
        account = server.load_account(user_public_key)
        op_level = stellar_sdk.ManageData(
            data_name="aethergem_level",
            data_value=str(new_level).encode('utf-8'),
            source=user_public_key
        )
        op_sprite = stellar_sdk.ManageData(
            data_name="aethergem_sprite",
            data_value=new_sprite.encode('utf-8'),
            source=user_public_key
        )
        transaction = TransactionBuilder(
            source_account=account,
            network_passphrase=NETWORK_PASSPHRASE,
            base_fee=100
        ).add_operation(op_level).add_operation(op_sprite).set_timeout(100).build()
        return transaction.to_xdr()
    except Exception as e:
        st.error(f"Error building evolve gem transaction: {e}")
        return None

# --- AetherGem Game Logic ---
# MANDATE 5: NO external images. Use Emojis 🧬 only.
GEM_EVOLUTION_MAP = {
    1: "🥚", # Egg
    2: "🌱", # Seedling
    3: "🐛", # Larva
    4: "🦋", # Chrysalis / Emerging Sprite
    5: "🌟", # Young AetherGem
    6: "💎", # Fully Evolved AetherGem
}
FEED_COST_XLM = 0.1 # Cost to feed in XLM
EVOLUTION_LEVELS = list(GEM_EVOLUTION_MAP.keys())[1:] # Levels where evolution happens (2, 3, 4, 5, 6)

def get_next_sprite_info(current_level):
    next_level = current_level + 1
    if next_level in GEM_EVOLUTION_MAP:
        return next_level, GEM_EVOLUTION_MAP[next_level]
    return None, None # Max level reached or not eligible

def get_current_sprite_emoji(level):
    return GEM_EVOLUTION_MAP.get(level, "❓")

def check_and_update_gem_state():
    """Refreshes gem state from Stellar ledger and updates session state."""
    if st.session_state.public_key:
        get_account_data(st.session_state.public_key)
        st.session_state.aethergem_sprite = get_current_sprite_emoji(st.session_state.aethergem_level)

# --- UI Layout and Interaction ---

# Handle query parameters for Freighter callbacks
# MANDATE 4: STRICTLY use 'st.query_params' instead of 'st.experimental_get_query_params'.
query_params = st.query_params

if "freighter_pk" in query_params and not st.session_state.freighter_connected:
    pk = query_params["freighter_pk"]
    try:
        Keypair.from_public_key(pk) # Validate public key format
        st.session_state.public_key = pk
        st.session_state.freighter_connected = True
        st.session_state.tx_status = "✨ Connected to Freighter!"
        st.query_params.clear() # Clear query params to prevent re-processing
        # Initial load of account data
        get_account_data(pk)
        check_and_update_gem_state()
        st.experimental_rerun() # Rerun to update UI after connection
    except ValueError: # MANDATE: Use ValueError for public key validation
        st.session_state.tx_status = "❌ Invalid public key received from Freighter."
        st.error("Received an invalid public key from Freighter. Please try again.")
        st.query_params.clear()
    except Exception as e:
        st.session_state.tx_status = f"❌ Error connecting: {e}"
        st.error(f"Error connecting to Freighter: {e}")
        st.query_params.clear()
elif "signed_xdr" in query_params:
    signed_xdr = query_params["signed_xdr"]
    st.session_state.tx_status = "⏳ Submitting transaction..."
    if submit_transaction(signed_xdr):
        # Transaction was successful, clear signed_xdr to prevent re-submission
        st.query_params.clear()
        check_and_update_gem_state() # Update state after successful tx
        st.experimental_rerun() # Rerun to update UI after transaction
    else:
        st.session_state.tx_status += " Check error message above."
        st.query_params.clear() # Still clear to avoid re-attempting a failed tx
elif "freighter_error" in query_params:
    error_msg = query_params["freighter_error"]
    st.session_state.tx_status = f"❌ Freighter Error: {error_msg}"
    st.error(f"Freighter Error: {error_msg}")
    st.query_params.clear()

st.sidebar.markdown("---")

# Freighter Connection Section
st.sidebar.header("🚀 Freighter Wallet")
if not st.session_state.freighter_connected:
    if st.sidebar.button("Connect Freighter"):
        # JavaScript to connect to Freighter and then redirect with public key
        js_connect_script = f"""
            <script>
                if (window.FreighterApi) {{
                    window.FreighterApi.getPublicKey().then(publicKey => {{
                        window.location.href = window.location.origin + window.location.pathname + '?freighter_pk=' + publicKey;
                    }}).catch(error => {{
                        window.location.href = window.location.origin + window.location.pathname + '?freighter_error=' + (error.message || 'Connection failed');
                    }});
                }} else {{
                    window.location.href = window.location.origin + window.location.pathname + '?freighter_error=' + 'Freighter not detected. Please install it.';
                }}
            </script>
            """
        components.html(js_connect_script, height=0) # MANDATE 9: components.html
        st.session_state.tx_status = "⏳ Awaiting Freighter connection..."
        st.sidebar.warning("Please approve the connection in Freighter.")
        st.experimental_rerun() # Rerun to pick up query params faster
else:
    st.sidebar.success("✅ Connected to Freighter!")
    st.sidebar.markdown(f"**Public Key:** `{st.session_state.public_key[:8]}...{st.session_state.public_key[-8:]}`")
    st.sidebar.metric("XLM Balance", f"{st.session_state.xlm_balance:.2f} XLM") # MANDATE 6: Use st.metric
    if st.sidebar.button("Disconnect"):
        st.session_state.freighter_connected = False
        st.session_state.public_key = None
        st.session_state.xlm_balance = 0.0
        st.session_state.aethergem_level = 0
        st.session_state.aethergem_sprite = "🥚"
        st.session_state.aethergem_balance = 0
        st.session_state.tx_status = ""
        st.experimental_rerun()

st.sidebar.markdown("---")
st.markdown("---")

if st.session_state.tx_status:
    st.markdown(f"#### Transaction Status:")
    st.info(st.session_state.tx_status)
st.markdown("---")


if st.session_state.freighter_connected:
    user_account = get_account_data(st.session_state.public_key)
    if user_account is None:
        st.warning("Your account does not exist on the Stellar Testnet. Please fund it using Friendbot.")
        st.markdown(f"Click here to fund your account: [Friendbot](https://friendbot.stellar.org/?addr={st.session_state.public_key}) 🚀")
        st.stop()
    
    # Refresh button
    if st.button("🔄 Refresh AetherGem Status"):
        check_and_update_gem_state()

    st.header("My AetherGem 💎")
    
    # MANDATE 6: Use st.columns
    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown(f"<div style='font-size: 150px; text-align: center;'>{st.session_state.aethergem_sprite}</div>", unsafe_allow_html=True)
    with col2:
        st.metric("AetherGem Level", st.session_state.aethergem_level) # MANDATE 6: Use st.metric
        st.metric("AetherGem Balance", f"{st.session_state.aethergem_balance:.0f} {AETHERGEM_CODE}") # MANDATE 6: Use st.metric
        
        # Determine if user has trustline and AGEM
        has_trustline = False
        for balance in user_account.balances:
            if balance.asset_code == AETHERGEM_CODE and balance.asset_issuer == ISSUER_PUBLIC_KEY:
                has_trustline = True
                break

        if not has_trustline:
            st.warning("You need to establish a trustline to adopt an AetherGem.")
            if st.button(f"Set Trustline for {AETHERGEM_CODE} 🛡️"):
                xdr = build_trustline_tx(st.session_state.public_key)
                if xdr:
                    # JavaScript to sign XDR and then redirect with signed XDR
                    js_sign_script = f"""
                        <script>
                            window.FreighterApi.signTransaction('{xdr}', {{ network: 'TESTNET' }}).then(signedXDR => {{
                                window.location.href = window.location.origin + window.location.pathname + '?signed_xdr=' + signedXDR;
                            }}).catch(error => {{
                                window.location.href = window.location.origin + window.location.pathname + '?freighter_error=' + (error.message || 'Signing failed');
                            }});
                        </script>
                        """
                    components.html(js_sign_script, height=0) # MANDATE 9: components.html
                    st.session_state.tx_status = "⏳ Awaiting Freighter signature for Trustline..."
                    st.experimental_rerun()
        elif st.session_state.aethergem_balance < 1 and st.session_state.aethergem_level == 0:
            st.success("Trustline established! Now, adopt your AetherGem!")
            if st.button("Adopt Your AetherGem 🧬"):
                # First, issuer sends 1 AGEM to user
                issuer_mint_xdr = build_issuer_mint_gem_tx(st.session_state.public_key)
                if issuer_mint_xdr:
                    st.session_state.tx_status = "⏳ Initiating AetherGem transfer from Arcade..."
                    if submit_transaction(issuer_mint_xdr):
                        st.session_state.tx_status = "✅ AetherGem transferred! Now, please sign to activate your gem."
                        # Second, user signs to set their initial gem data
                        user_initial_data_xdr = build_initial_gem_data_tx(st.session_state.public_key)
                        if user_initial_data_xdr:
                            js_sign_script = f"""
                                <script>
                                    window.FreighterApi.signTransaction('{user_initial_data_xdr}', {{ network: 'TESTNET' }}).then(signedXDR => {{
                                        window.location.href = window.location.origin + window.location.pathname + '?signed_xdr=' + signedXDR;
                                    }}).catch(error => {{
                                        window.location.href = window.location.origin + window.location.pathname + '?freighter_error=' + (error.message || 'Signing failed');
                                    }});
                                </script>
                                """
                            components.html(js_sign_script, height=0) # MANDATE 9: components.html
                            st.session_state.tx_status = "⏳ Awaiting Freighter signature to initialize your AetherGem data..."
                            st.experimental_rerun()
                else:
                    st.error("Could not build transaction to mint AetherGem. Please check logs.")
        else: # User has an AetherGem (balance >= 1 and level is initialized)
            st.markdown("### Nurture & Evolve!")
            
            # MANDATE 6: Use st.columns
            feed_col, evolve_col = st.columns(2)
            with feed_col:
                st.write(f"Feed your AetherGem {FEED_COST_XLM} XLM to increase its level!")
                if st.button("Feed AetherGem 💰"):
                    # Add a small buffer for transaction fees on top of the feed cost
                    if st.session_state.xlm_balance < FEED_COST_XLM + 0.0001: 
                        st.error(f"Insufficient XLM balance. You need at least {FEED_COST_XLM} XLM + fees.")
                    else:
                        xdr = build_feed_gem_tx(st.session_state.public_key, str(FEED_COST_XLM))
                        if xdr:
                            js_sign_script = f"""
                                <script>
                                    window.FreighterApi.signTransaction('{xdr}', {{ network: 'TESTNET' }}).then(signedXDR => {{
                                        window.location.href = window.location.origin + window.location.pathname + '?signed_xdr=' + signedXDR;
                                    }}).catch(error => {{
                                        window.location.href = window.location.origin + window.location.pathname + '?freighter_error=' + (error.message || 'Signing failed');
                                    }});
                                </script>
                                """
                            components.html(js_sign_script, height=0) # MANDATE 9: components.html
                            st.session_state.tx_status = "⏳ Awaiting Freighter signature to feed your AetherGem..."
                            st.experimental_rerun()
            
            # Evolve Gem
            with evolve_col:
                next_level, next_sprite = get_next_sprite_info(st.session_state.aethergem_level)
                if next_level and next_level <= max(GEM_EVOLUTION_MAP.keys()):
                    st.write(f"Your AetherGem can evolve to level {next_level} ({next_sprite})!")
                    if st.button(f"Evolve AetherGem to Level {next_level} ⬆️"):
                        xdr = build_evolve_gem_tx(st.session_state.public_key, next_level, next_sprite)
                        if xdr:
                            js_sign_script = f"""
                                <script>
                                    window.FreighterApi.signTransaction('{xdr}', {{ network: 'TESTNET' }}).then(signedXDR => {{
                                        window.location.href = window.location.origin + window.location.pathname + '?signed_xdr=' + signedXDR;
                                    }}).catch(error => {{
                                        window.location.href = window.location.origin + window.location.pathname + '?freighter_error=' + (error.message || 'Signing failed');
                                    }});
                                </script>
                                """
                            components.html(js_sign_script, height=0) # MANDATE 9: components.html
                            st.session_state.tx_status = "⏳ Awaiting Freighter signature to evolve your AetherGem..."
                            st.experimental_rerun()
                else:
                    if st.session_state.aethergem_level >= max(GEM_EVOLUTION_MAP.keys()):
                        st.info("Your AetherGem is at its maximum evolution! Well done! ✨")
                    else:
                        st.info(f"Feed your AetherGem more to reach level {next_level or 'next'} for the next evolution!")

else:
    st.info("Connect your Freighter wallet in the sidebar to begin your AetherGems adventure! 🎮")
    st.markdown("<p style='text-align: center; font-size: 100px;'>🌌👾🌠</p>", unsafe_allow_html=True) # MANDATE 5: Emojis only, no external images.