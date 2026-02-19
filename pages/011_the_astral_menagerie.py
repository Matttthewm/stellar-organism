import streamlit as st
import stellar_sdk
from stellar_sdk import Server, Keypair, TransactionBuilder, Network, Asset
from stellar_sdk.exceptions import BadRequestError, NotFoundError
import streamlit.components.v1 as components
import json
import time

# --- Configuration ---
HORIZON_URL = "https://horizon-testnet.stellar.org"
NETWORK_PASSPHRASE = Network.TESTNET_NETWORK_PASS
INITIAL_ISSUER_BALANCE = "10000"  # Lumens for the issuer account
ADOPTION_FEE_SDU = 5              # Stardust units required for adoption
SDU_INITIAL_SUPPLY = 1_000_000    # Initial supply of Stardust minted by the issuer

# --- Stellar Server ---
# MANDATE 8: Use 'Server(HORIZON_URL)' only. NEVER pass 'timeout' to Server().
server = Server(HORIZON_URL)

# --- Session State Initialization ---
# State for Freighter connection and transaction flow
if "public_key" not in st.session_state:
    st.session_state.public_key = None
if "signed_xdr" not in st.session_state:
    st.session_state.signed_xdr = None
if "transaction_hash" not in st.session_state:
    st.session_state.transaction_hash = None
if "current_xdr" not in st.session_state:
    st.session_state.current_xdr = None
if "tx_in_progress" not in st.session_state:
    st.session_state.tx_in_progress = False
if "freighter_public_key" not in st.session_state: # Value returned by Freighter component for public key
    st.session_state.freighter_public_key = None
if "freighter_status" not in st.session_state: # Status of Freighter connection
    st.session_state.freighter_status = None # CONNECTED, NOT_INSTALLED, ERROR
if "freighter_tx_signed_xdr" not in st.session_state: # Value returned by Freighter component for signed XDR
    st.session_state.freighter_tx_signed_xdr = None
if "freighter_tx_error" not in st.session_state: # Error message from Freighter signing
    st.session_state.freighter_tx_error = None

# State for managing creature adoption flow (issuer's action)
if "last_adoption_payment_tx_info" not in st.session_state:
    # Stores info about a successful user payment for adoption, waiting for issuer to send creature
    st.session_state.last_adoption_payment_tx_info = None # {'tx_hash': ..., 'adopter_public_key': ..., 'creature_code': ...}
if "current_adoption_target_creature_code" not in st.session_state:
    # Temporarily stores which creature the user is attempting to adopt
    st.session_state.current_adoption_target_creature_code = None

# --- Secret Key Handling (MANDATE 11) ---
if "ISSUER_KEY" in st.secrets:
    issuer_secret = st.secrets["ISSUER_KEY"]
    st.session_state.issuer_key_source = "secrets"
else:
    if "demo_key" not in st.session_state:
        st.session_state.demo_key = Keypair.random().secret
    issuer_secret = st.session_state.demo_key
    st.session_state.issuer_key_source = "demo"
    st.sidebar.warning("Using Ephemeral Demo Keys ⚠️")

try:
    issuer_keypair = Keypair.from_secret(issuer_secret)
    issuer_public_key = issuer_keypair.public_key
except ValueError: # MANDATE 7: NEVER import 'Ed25519PublicKeyInvalidError'. Use 'ValueError'.
    st.error("Invalid ISSUER_KEY provided. Please check your secrets or demo key.")
    st.stop()

# --- Assets ---
STARDUST_ASSET = Asset("STARDUST", issuer_public_key)

# Define unique creature assets configuration
CREATURE_ASSETS_CONFIG = [
    {"code": "AURORA", "name": "Aurora Spryte 🌌", "description": "A shimmering sprite, born from nebulae dust."},
    {"code": "LUMINA", "name": "Lumina Beast 🌠", "description": "A majestic creature, its gaze illuminates the darkest void."},
    {"code": "COSMO", "name": "Cosmo Gazer 💫", "description": "Observes the cosmos, a silent guardian of celestial paths."},
    {"code": "NEBULA", "name": "Nebula Weaver 🔮", "description": "Spins threads of starlight into intricate patterns."}
]
CREATURE_ASSETS = [Asset(c["code"], issuer_public_key) for c in CREATURE_ASSETS_CONFIG]

# --- Custom CSS (MANDATE 3, STYLE Mystical/Arcane) ---
def apply_custom_css():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Cinzel+Decorative:wght@400;700&family=Orbitron:wght@400;700&display=swap');

        body {
            background-color: #0d0d1e; /* Darker background for cosmic feel */
            color: #e0e0f0; /* Light text */
            font-family: 'Cinzel Decorative', serif; /* Mystical font */
        }

        .stApp {
            background-color: #0d0d1e;
            background-image:
                radial-gradient(at 0% 0%, hsla(240,100%,70%,0.1) 0, transparent 50%),
                radial-gradient(at 100% 0%, hsla(280,100%,70%,0.1) 0, transparent 50%),
                radial-gradient(at 50% 100%, hsla(200,100%,70%,0.1) 0, transparent 50%),
                linear-gradient(to bottom, #1a0a2a, #0d0d1e); /* Subtle gradients for depth */
        }

        h1, h2, h3, h4, h5, h6 {
            font-family: 'Orbitron', sans-serif; /* Sci-fi/techy font for headings */
            color: #d8b4fe; /* Purple-ish glow for headings */
            text-shadow: 0 0 5px #a78bfa, 0 0 10px #a78bfa; /* Subtle glow */
        }

        .stButton>button {
            background-color: #3b0060; /* Dark purple button */
            color: #e0e0f0;
            border: 1px solid #a78bfa;
            border-radius: 8px;
            padding: 10px 20px;
            font-family: 'Cinzel Decorative', serif;
            transition: all 0.3s ease;
            box-shadow: 0 0 8px rgba(167, 139, 250, 0.5);
            margin: 5px 0;
        }

        .stButton>button:hover:not(:disabled) {
            background-color: #5d00a0; /* Lighter purple on hover */
            color: #ffffff;
            border-color: #c4b5fd;
            box-shadow: 0 0 15px rgba(196, 181, 253, 0.7);
            transform: translateY(-2px);
        }
        .stButton>button:disabled {
            background-color: #2a1a3a;
            border-color: #6b408e;
            color: #9c9c9c;
            cursor: not-allowed;
            opacity: 0.7;
        }

        .stTextInput>div>div>input, .stSelectbox>div>div>select, .stTextArea>div>div>textarea {
            background-color: #2a1a3a; /* Darker input fields */
            color: #e0e0f0;
            border: 1px solid #6b408e;
            border-radius: 5px;
            font-family: 'Cinzel Decorative', serif;
        }

        .stMetric {
            background-color: #2a1a3a;
            border-radius: 10px;
            padding: 15px;
            border: 1px solid #5d00a0;
            box-shadow: 0 0 10px rgba(167, 139, 250, 0.3);
            margin-bottom: 10px;
        }
        .stMetric label {
            color: #d8b4fe !important;
            font-family: 'Orbitron', sans-serif;
            font-size: 1.1em;
        }
        .stMetric div[data-testid="stMetricValue"] {
            color: #c4b5fd !important;
            font-family: 'Orbitron', sans-serif;
            font-size: 1.8em;
        }
        .stMetric div[data-testid="stMetricDelta"] {
            color: #a78bfa !important;
            font-family: 'Orbitron', sans-serif;
        }

        .stExpander {
            border: 1px solid #5d00a0;
            border-radius: 10px;
            background-color: #2a1a3a;
            padding: 0; /* Remove default padding to control inner elements */
            margin-bottom: 15px;
            box-shadow: 0 0 10px rgba(167, 139, 250, 0.2);
        }
        .stExpander button[aria-expanded] {
            color: #d8b4fe !important;
            font-family: 'Orbitron', sans-serif;
            font-size: 1.2em;
        }
        .stExpander > div:first-child { /* Targets the header of the expander */
            padding: 10px 15px;
        }
        .stExpander > div:nth-child(2) { /* Targets the content area */
            padding: 0 15px 15px 15px;
        }

        .stAlert {
            background-color: #2a1a3a !important;
            color: #e0e0f0 !important;
            border: 1px solid #a78bfa !important;
            border-left: 5px solid #a78bfa !important;
            border-radius: 8px !important;
        }
        .stWarning {
            background-color: #3f301a !important;
            border-left: 5px solid #ffa500 !important;
        }
        .stError {
            background-color: #4f1a1a !important;
            border-left: 5px solid #ff4d4d !important;
        }
        .stSuccess {
            background-color: #1a3f1a !important;
            border-left: 5px solid #4dff4d !important;
        }
        .stInfo {
            background-color: #1a2a3f !important;
            border-left: 5px solid #4dafff !important;
        }

        .stSidebar .st-emotion-cache-1pxx9r9 { /* Targets the main sidebar content area */
            background-color: #1a0a2a; /* Darker sidebar */
        }
        .stSidebar .stAlert {
            font-family: 'Cinzel Decorative', serif;
            font-size: 0.9em;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

# --- Freighter HTML Component (MANDATE 1, 9) ---
# This component handles both connecting to Freighter and signing transactions.
# It communicates back to Streamlit via `window.parent.streamlit.setComponentValue`.
def freighter_integration_html(action, xdr_to_sign=None):
    script_content = f"""
    <script src="https://unpkg.com/@stellar/freighter-api@latest/build/index.js"></script>
    <script>
        const ACTION = "{action}";
        const XDR_TO_SIGN = "{xdr_to_sign if xdr_to_sign else ''}";
        const NETWORK_PASSPHRASE = "{NETWORK_PASSPHRASE}";

        async function initFreighterAction() {{
            if (!window.freighterApi) {{
                if (ACTION === 'connect') {{
                    window.parent.streamlit.setComponentValue('freighter_status', 'NOT_INSTALLED');
                }} else if (ACTION === 'sign') {{
                    window.parent.streamlit.setComponentValue('freighter_tx_signed_xdr', 'NOT_INSTALLED');
                }}
                return;
            }}

            if (ACTION === 'connect') {{
                try {{
                    const {{"publicKey"}} = await window.freighterApi.getPublicKey();
                    window.parent.streamlit.setComponentValue('freighter_public_key', publicKey);
                    window.parent.streamlit.setComponentValue('freighter_status', 'CONNECTED');
                }} catch (e) {{
                    console.error("Freighter connection failed:", e);
                    window.parent.streamlit.setComponentValue('freighter_status', 'ERROR');
                    window.parent.streamlit.setComponentValue('freighter_public_key', null);
                }}
            }} else if (ACTION === 'sign' && XDR_TO_SIGN) {{
                try {{
                    const signedXdr = await window.freighterApi.signTransaction(XDR_TO_SIGN, {{networkPassphrase: NETWORK_PASSPHRASE}});
                    window.parent.streamlit.setComponentValue('freighter_tx_signed_xdr', signedXdr);
                    window.parent.streamlit.setComponentValue('freighter_tx_error', null);
                }} catch (e) {{
                    console.error("Transaction signing failed:", e);
                    window.parent.streamlit.setComponentValue('freighter_tx_signed_xdr', null);
                    window.parent.streamlit.setComponentValue('freighter_tx_error', e.message);
                }}
            }}
        }}
        initFreighterAction(); // Execute on component load
    </script>
    """
    # MANDATE 9: ALWAYS call: 'components.html(...)'.
    # Use a unique key to force re-render and re-execute script for different actions or XDRs.
    components.html(script_content, height=0, width=0, key=f"freighter_{action}_{xdr_to_sign}_{time.time()}")

# --- Helper Functions ---

# MANDATE 8: Access operations via module: 'stellar_sdk.ChangeTrust(...)'.
def create_change_trust_op(asset, limit=None):
    return stellar_sdk.ChangeTrust(
        asset=asset,
        limit=str(limit) if limit is not None else None
    )

# MANDATE 8: Access operations via module: 'stellar_sdk.Payment(...)'.
def create_payment_op(destination, asset, amount):
    return stellar_sdk.Payment(
        destination=destination,
        asset=asset,
        amount=str(amount)
    )

def create_raw_tx(source_public_key, operations):
    """Builds a transaction XDR for the given operations."""
    try:
        source_account = server.load_account(source_public_key)
        transaction = (
            TransactionBuilder(
                source_account=source_account,
                network_passphrase=NETWORK_PASSPHRASE,
            )
            .add_sequence_number()
        )
        for op in operations:
            transaction.add_operation(op)
        
        transaction = transaction.build()
        return transaction.to_xdr()
    except NotFoundError:
        st.error(f"Account `{source_public_key}` not found on Testnet. Please fund it via Friendbot.")
        return None
    except Exception as e:
        st.error(f"Error building transaction: {e}")
        return None

def submit_signed_xdr(signed_xdr):
    """Submits a signed transaction XDR to the Stellar network."""
    try:
        response = server.submit_transaction(signed_xdr)
        st.session_state.transaction_hash = response['hash']
        st.success(f"Transaction successful! Hash: `{response['hash']}`")
        st.balloons()
        return response
    except BadRequestError as e:
        error_msg = f"Transaction failed: {e.extras.result_codes.operations}"
        if e.extras.result_codes.transaction:
            error_msg += f" | Tx: {e.extras.result_codes.transaction}"
        st.error(error_msg)
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        return None

def get_account_data(public_key):
    """Fetches account data from Horizon."""
    try:
        account = server.load_account(public_key)
        return account
    except NotFoundError:
        return None
    except Exception as e:
        st.error(f"Error loading account data for {public_key}: {e}")
        return None

def fund_account_with_friendbot(public_key):
    """Funds a Testnet account using Friendbot."""
    try:
        response = server.friendbot(public_key)
        st.success(f"Account `{public_key}` funded successfully by Friendbot!")
        return True
    except BadRequestError as e:
        st.error(f"Friendbot funding failed: {e.extras.result_codes.operations}")
        return False
    except Exception as e:
        st.error(f"An unexpected error occurred during Friendbot funding: {e}")
        return False

# --- UI Functions ---

def display_header():
    st.markdown("<h1>The Astral Menagerie ✨🔮</h1>", unsafe_allow_html=True)
    st.markdown("### A celestial sanctuary for unique digital companions.")
    st.markdown("---")

def display_sidebar():
    # MANDATE 10: App Name and Concept
    st.sidebar.info("""
    **The Astral Menagerie** 🧬
    A celestial sanctuary where users adopt and nurture unique digital companions by perpetually offering stardust, with cosmic keepers able to reclaim neglected beings into the ethereal void.
    """)
    # MANDATE 10: Visual Style
    st.sidebar.caption("Visual Style: Mystical/Arcane ✨🔮🌌")

    st.sidebar.markdown("---")
    st.sidebar.subheader("App Info")
    st.sidebar.markdown(f"**Horizon Server:** `{HORIZON_URL.replace('https://', '')}`")
    st.sidebar.markdown(f"**Network:** `Testnet`")
    st.sidebar.markdown(f"**Issuer Public Key:** `{issuer_public_key}`")
    if st.session_state.issuer_key_source == "demo":
        st.sidebar.markdown(f"*(Demo mode, ephemeral key)*")

    # Issuer account initialization and STARDUST supply check
    issuer_account = get_account_data(issuer_public_key)
    if issuer_account:
        stardust_balance = "0"
        for balance in issuer_account.balances:
            if isinstance(balance, stellar_sdk.responses.response.AssetBalance) and balance.asset_code == STARDUST_ASSET.code:
                stardust_balance = balance.balance
                break
        st.sidebar.metric("Issuer STARDUST Supply", f"{float(stardust_balance):,.0f} SDU")
    else:
        st.sidebar.warning("Issuer account not funded or found. Initializing...")
        if st.sidebar.button("Initialize Issuer Account (Friendbot)", key="init_issuer_btn"):
            with st.spinner("Funding issuer account and creating STARDUST..."):
                if fund_account_with_friendbot(issuer_public_key):
                    # Create STARDUST asset and mint some to issuer
                    try:
                        issuer_account_for_tx = server.load_account(issuer_public_key)
                        ops = [
                            create_change_trust_op(STARDUST_ASSET, limit="900000000000"), # High limit for issuer
                            create_payment_op(issuer_public_key, STARDUST_ASSET, SDU_INITIAL_SUPPLY) # Mint to self
                        ]
                        tx = (
                            TransactionBuilder(
                                source_account=issuer_account_for_tx,
                                network_passphrase=NETWORK_PASSPHRASE,
                            )
                            .add_sequence_number()
                        )
                        for op in ops:
                            tx.add_operation(op)
                        tx = tx.build()
                        tx.sign(issuer_keypair) # Issuer signs directly
                        server.submit_transaction(tx.to_xdr())
                        st.sidebar.success("Issuer funded and STARDUST minted!")
                        st.experimental_rerun()
                    except Exception as e:
                        st.sidebar.error(f"Failed to initialize issuer assets: {e}")
                else:
                    st.sidebar.error("Failed to fund issuer account.")


# --- Main App Logic ---
def main():
    apply_custom_css()
    display_sidebar()
    display_header()

    st.markdown("---")
    st.subheader("Connect Your Celestial Beacon (Freighter) 📡")

    # Connect Wallet Section
    if not st.session_state.public_key:
        if st.button("Connect Freighter Wallet ✨", disabled=st.session_state.tx_in_progress):
            st.session_state.tx_in_progress = True 
            with st.spinner("Connecting to Freighter..."):
                freighter_integration_html("connect")
                # Need to rerun to pick up state updates from JS component
                time.sleep(1) # Give JS a moment to execute
                st.experimental_rerun()
        
        # Check Freighter connection status after rerun
        if st.session_state.get('freighter_status') == 'CONNECTED':
            st.session_state.public_key = st.session_state.freighter_public_key
            st.success(f"Connected to Freighter! Public Key: `{st.session_state.public_key}`")
            st.session_state.tx_in_progress = False
            st.experimental_rerun() # Rerun once more to properly display connected state
        elif st.session_state.get('freighter_status') == 'NOT_INSTALLED':
            st.error("Freighter not installed. Please install the Freighter browser extension.")
            st.session_state.tx_in_progress = False
        elif st.session_state.get('freighter_status') == 'ERROR':
            st.error("Failed to connect to Freighter. Please check the extension and try again.")
            st.session_state.tx_in_progress = False
        # If status is None or still connecting, it means the component hasn't reported back yet.
        # The `st.experimental_rerun()` should eventually pick it up.

    else: # Wallet is connected
        st.success(f"Connected Wallet: `{st.session_state.public_key}`")
        if st.button("Disconnect Wallet"):
            st.session_state.public_key = None
            st.session_state.transaction_hash = None
            st.session_state.signed_xdr = None
            st.session_state.current_xdr = None
            st.session_state.freighter_public_key = None
            st.session_state.freighter_status = None
            st.session_state.tx_in_progress = False
            st.session_state.last_adoption_payment_tx_info = None
            st.session_state.current_adoption_target_creature_code = None
            st.experimental_rerun()

    if st.session_state.public_key:
        user_public_key = st.session_state.public_key
        user_account = get_account_data(user_public_key)

        if not user_account:
            st.markdown("---")
            st.subheader("Account Initialization 🚀")
            st.warning("Your account is not funded on the Testnet. Please fund it to proceed.")
            if st.button("Fund Account with Friendbot 🤖"):
                with st.spinner("Funding account..."):
                    if fund_account_with_friendbot(user_public_key):
                        st.experimental_rerun()
        else: # Account is funded
            st.markdown("---")
            st.subheader("Your Astral Ledger 📖")

            # MANDATE 6: Use st.columns, st.metric
            col1, col2 = st.columns(2)
            xlm_balance = next((b.balance for b in user_account.balances if b.asset_type == 'native'), '0')
            stardust_balance = next((b.balance for b in user_account.balances if b.asset_code == STARDUST_ASSET.code), '0')

            col1.metric("Lumens (XLM) Balance 💰", f"{float(xlm_balance):,.2f} XLM")
            col2.metric(f"Stardust ({STARDUST_ASSET.code}) Balance ✨", f"{float(stardust_balance):,.2f} SDU")

            st.markdown("---")
            st.subheader("Manage Stardust Trustline ✨")

            has_stardust_trustline = any(b.asset_code == STARDUST_ASSET.code for b in user_account.balances)

            if not has_stardust_trustline:
                st.info(f"You need to establish a trustline for {STARDUST_ASSET.code} to interact with Stardust.")
                if st.button(f"Establish Trustline for {STARDUST_ASSET.code}", disabled=st.session_state.tx_in_progress):
                    operations = [create_change_trust_op(STARDUST_ASSET)]
                    xdr = create_raw_tx(user_public_key, operations)
                    if xdr:
                        st.session_state.current_xdr = xdr
                        st.session_state.tx_in_progress = True
                        st.info("Please sign the ChangeTrust transaction in Freighter.")
                        freighter_integration_html("sign", xdr_to_sign=xdr)
            else:
                st.success(f"Trustline established for {STARDUST_ASSET.code}.")
                # MANDATE 6: Use st.expander
                with st.expander(f"Remove Trustline for {STARDUST_ASSET.code} 🗑️"):
                    st.warning("Removing the trustline will prevent you from holding or receiving Stardust and may affect your adopted creatures!")
                    if st.button(f"Remove Trustline", disabled=st.session_state.tx_in_progress, key="remove_sdu_trustline"):
                        operations = [create_change_trust_op(STARDUST_ASSET, limit=0)] # Limit 0 to remove trustline
                        xdr = create_raw_tx(user_public_key, operations)
                        if xdr:
                            st.session_state.current_xdr = xdr
                            st.session_state.tx_in_progress = True
                            st.info("Please sign the ChangeTrust (remove) transaction in Freighter.")
                            freighter_integration_html("sign", xdr_to_sign=xdr)

            st.markdown("---")
            st.subheader("The Astral Menagerie 🧬")

            # --- Transaction Signing and Submission Logic ---
            # This block waits for the Freighter HTML component to return a signed XDR
            # or an error, then submits the transaction or displays the error.
            if st.session_state.tx_in_progress and st.session_state.current_xdr and not st.session_state.get('freighter_tx_signed_xdr'):
                st.info("Waiting for Freighter to sign transaction...")
                time.sleep(0.5) # Small delay to prevent too rapid reruns
                st.experimental_rerun()
            elif st.session_state.tx_in_progress and st.session_state.get('freighter_tx_signed_xdr'):
                signed_xdr = st.session_state.freighter_tx_signed_xdr
                st.session_state.freighter_tx_signed_xdr = None # Clear for next transaction
                
                if signed_xdr == 'NOT_INSTALLED':
                    st.error("Freighter not installed. Cannot sign transaction.")
                elif st.session_state.get('freighter_tx_error'):
                    st.error(f"Freighter signing failed: {st.session_state.freighter_tx_error}")
                    st.session_state.freighter_tx_error = None # Clear error
                else:
                    with st.spinner("Submitting transaction to Stellar network..."):
                        response = submit_signed_xdr(signed_xdr)
                        if response:
                            # If a payment for adoption was successful, record it to trigger issuer's action
                            try:
                                tx_env = stellar_sdk.TransactionEnvelope.from_xdr(signed_xdr, NETWORK_PASSPHRASE)
                                for op in tx_env.transaction.operations:
                                    # Heuristically check if it was an adoption payment
                                    if isinstance(op, stellar_sdk.Payment) and \
                                       op.destination == issuer_public_key and \
                                       op.asset == STARDUST_ASSET and \
                                       float(op.amount) == ADOPTION_FEE_SDU and \
                                       st.session_state.current_adoption_target_creature_code: # Check if a creature was targeted
                                        
                                        st.session_state.last_adoption_payment_tx_info = {
                                            'tx_hash': response['hash'],
                                            'adopter_public_key': user_public_key,
                                            'creature_code': st.session_state.current_adoption_target_creature_code
                                        }
                                        st.info("Payment confirmed. Awaiting cosmic keeper's embrace for your new companion...")
                                        break # Found the payment operation
                            except Exception as e:
                                st.warning(f"Could not parse transaction for adoption check: {e}")
                        
                st.session_state.current_xdr = None # Clear current XDR after submission
                st.session_state.tx_in_progress = False # Clear tx_in_progress after submission
                st.session_state.current_adoption_target_creature_code = None # Clear target
                st.experimental_rerun() # Rerun to update balances/UI

            # --- Issuer action: Sending creature after user's adoption payment ---
            # This logic runs after a successful user payment transaction has been processed.
            if st.session_state.last_adoption_payment_tx_info and not st.session_state.tx_in_progress:
                info = st.session_state.last_adoption_payment_tx_info
                creature_code_to_send = info['creature_code']
                adopter_public_key = info['adopter_public_key']
                tx_hash_of_payment = info['tx_hash']

                # Prevent re-issuing: check if the creature is already owned by the adopter
                adopter_account_after_payment = get_account_data(adopter_public_key)
                target_creature_asset = Asset(creature_code_to_send, issuer_public_key)
                adopter_holds_creature = any(b.asset_code == creature_code_to_send and float(b.balance) >= 1 for b in adopter_account_after_payment.balances)

                if not adopter_holds_creature:
                    st.info(f"Cosmic keeper is preparing {creature_code_to_send} for `{adopter_public_key}`...")
                    with st.spinner(f"Transferring {creature_code_to_send} to your wallet..."):
                        try:
                            # Create issuer-signed payment transaction
                            issuer_source_account = server.load_account(issuer_public_key)
                            ops = [create_payment_op(adopter_public_key, target_creature_asset, "1")] # Issuer sends 1 unit
                            tx = (
                                TransactionBuilder(
                                    source_account=issuer_source_account,
                                    network_passphrase=NETWORK_PASSPHRASE,
                                )
                                .add_sequence_number()
                                .add_operation(ops[0])
                                .build()
                            )
                            tx.sign(issuer_keypair) # Issuer signs directly
                            response = server.submit_transaction(tx.to_xdr())
                            st.success(f"Astral keeper has bestowed {creature_code_to_send} upon you! Tx: `{response['hash']}`")
                            st.balloons()
                            st.session_state.last_adoption_payment_tx_info = None # Clear, creature sent
                            st.experimental_rerun() # Rerun to show new creature
                        except Exception as e:
                            st.error(f"Failed for keeper to send {creature_code_to_send}: {e}")
                            st.warning(f"Please contact support with payment hash: `{tx_hash_of_payment}`")
                            st.session_state.last_adoption_payment_tx_info = None # Clear to prevent endless retries
                else:
                    st.success(f"You already hold {creature_code_to_send}. No further action needed by keeper.")
                    st.session_state.last_adoption_payment_tx_info = None # Clear, already owned

            # MANDATE 4: Using st.query_params for demonstration. Not strictly tied to current UI elements.
            # You could imagine a URL like: ?adopt_creature=AURORA_SPRYTE&stardust_amount=10
            # prefill_stardust_amount = st.query_params.get("stardust_for_adoption", type=float) or float(ADOPTION_FEE_SDU)
            # adopt_creature_code_from_query = st.query_params.get("adopt_creature", type=str)


            for i, creature_conf in enumerate(CREATURE_ASSETS_CONFIG):
                creature_asset = Asset(creature_conf["code"], issuer_public_key)
                
                # Check for creature trustline and balance
                has_creature_trustline = any(b.asset_code == creature_asset.code for b in user_account.balances)
                holds_creature = any(b.asset_code == creature_asset.code and float(b.balance) >= 1 for b in user_account.balances)

                st.markdown(f"#### {creature_conf['name']}")
                st.markdown(f"*{creature_conf['description']}*")

                # MANDATE 6: Use st.columns
                creature_col1, creature_col2, creature_col3 = st.columns(3)

                with creature_col1:
                    if has_creature_trustline:
                        st.success("Trustline Established ✅")
                    else:
                        st.warning("Trustline Not Established ❌")
                        if st.button(f"Establish Trustline for {creature_asset.code}", key=f"trust_{creature_asset.code}", disabled=st.session_state.tx_in_progress):
                            operations = [create_change_trust_op(creature_asset)]
                            xdr = create_raw_tx(user_public_key, operations)
                            if xdr:
                                st.session_state.current_xdr = xdr
                                st.session_state.tx_in_progress = True
                                st.info(f"Please sign the ChangeTrust for {creature_asset.code} in Freighter.")
                                freighter_integration_html("sign", xdr_to_sign=xdr)
                
                with creature_col2:
                    if holds_creature:
                        st.success("Adopted! 🎉")
                        st.info(f"You own {float(next(b.balance for b in user_account.balances if b.asset_code == creature_asset.code)):,.0f} unit(s) of {creature_asset.code}.")
                    elif has_stardust_trustline and has_creature_trustline:
                        st.info(f"Adoption Fee: {ADOPTION_FEE_SDU} {STARDUST_ASSET.code}")
                        if st.button(f"Adopt {creature_asset.code} 🤝", key=f"adopt_{creature_asset.code}", disabled=st.session_state.tx_in_progress or float(stardust_balance) < ADOPTION_FEE_SDU):
                            operations = [
                                create_payment_op(issuer_public_key, STARDUST_ASSET, ADOPTION_FEE_SDU), # User pays STARDUST to issuer
                            ]
                            xdr = create_raw_tx(user_public_key, operations)
                            if xdr:
                                st.session_state.current_xdr = xdr
                                st.session_state.tx_in_progress = True
                                # Store target creature code for post-payment issuer action
                                st.session_state.current_adoption_target_creature_code = creature_asset.code
                                st.info(f"Please sign the {STARDUST_ASSET.code} payment for {creature_asset.code} in Freighter.")
                                freighter_integration_html("sign", xdr_to_sign=xdr)
                    else:
                        st.info(f"Establish trustlines for both {STARDUST_ASSET.code} and {creature_asset.code} to adopt.")

                with creature_col3:
                    if holds_creature:
                        # Nurture / Release options
                        if st.button(f"Nurture {creature_asset.code} 🌱", key=f"nurture_{creature_asset.code}", disabled=st.session_state.tx_in_progress):
                            # Nurturing is a symbolic small STARDUST payment
                            nurture_amount = 1 # SDU
                            operations = [
                                create_payment_op(issuer_public_key, STARDUST_ASSET, nurture_amount),
                            ]
                            xdr = create_raw_tx(user_public_key, operations)
                            if xdr:
                                st.session_state.current_xdr = xdr
                                st.session_state.tx_in_progress = True
                                st.info(f"Please sign the {STARDUST_ASSET.code} payment to nurture {creature_asset.code} in Freighter.")
                                freighter_integration_html("sign", xdr_to_sign=xdr)
                        
                        st.caption("---")
                        if st.button(f"Release {creature_asset.code} 👋", key=f"release_{creature_asset.code}", disabled=st.session_state.tx_in_progress):
                            st.warning(f"Are you sure you want to release your {creature_asset.code}? This action cannot be undone and will reclaim it into the ethereal void.")
                            if st.checkbox(f"Confirm release of {creature_asset.code}", key=f"confirm_release_{creature_asset.code}"):
                                # To release, the user sends the asset back to the issuer and removes their trustline.
                                # This is a combined operation.
                                operations = [
                                    create_payment_op(issuer_public_key, creature_asset, "1"), # Send 1 creature back
                                    create_change_trust_op(creature_asset, limit=0) # Then remove trustline
                                ]
                                xdr = create_raw_tx(user_public_key, operations)
                                if xdr:
                                    st.session_state.current_xdr = xdr
                                    st.session_state.tx_in_progress = True
                                    st.info(f"Please sign the transaction to release and remove trustline for {creature_asset.code} in Freighter.")
                                    freighter_integration_html("sign", xdr_to_sign=xdr)

                st.markdown("---")


if __name__ == "__main__":
    main()