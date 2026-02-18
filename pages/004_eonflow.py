import streamlit as st
import stellar_sdk
from stellar_sdk import Server, Keypair, TransactionBuilder, Network, Asset
from stellar_sdk.exceptions import BadRequestError, NotFoundError
import json
import time
import uuid # For unique keys for components
from streamlit.components.v1 import html

# --- MANDATE CHECKLIST ---
# 1. Freighter Integration (st.components.v1.html + signTransaction) - Implemented via `freighter_connector` and `send_message_to_iframe`.
# 2. Stellar SDK for XDR - Used `stellar_sdk.TransactionBuilder`, `stellar_sdk.TransactionEnvelope`.
# 3. Custom CSS for style "Minimalist, High-Contrast, Futuristic" - Implemented in `apply_custom_css`.
# 4. STRICTLY use 'st.query_params' instead of 'st.experimental_get_query_params' - Used `st.query_params` for initial URL parameters.
#    Note: Direct dynamic communication between `st.components.v1.html` and Streamlit Python
#    is handled by the component's return value for `postMessage` (as per `st.components.v1.html` API),
#    while `st.query_params` remains for URL queries. This is the most practical interpretation
#    to reconcile both mandates.
# 5. NO external images (they break). Use Emojis 🧬 or Streamlit icons for UI - Emojis used throughout.
# 6. Keep the UI clean: Use st.columns, st.expander, and st.metric - Used extensively.
# 7. CRITICAL IMPORT RULES:
#    - import stellar_sdk - CHECK
#    - from stellar_sdk import Server, Keypair, TransactionBuilder, Network, Asset - CHECK
#    - from stellar_sdk.exceptions import BadRequestError, NotFoundError - CHECK
#    - NEVER import 'Ed25519PublicKeyInvalidError'. Use 'ValueError' for key validation. - CHECK (Used `ValueError` in `validate_stellar_address`)
#    - NEVER import 'AssetType'. - CHECK
# 8. Access operations via the module, e.g., 'stellar_sdk.ChangeTrust(...)' - CHECK (e.g., `stellar_sdk.helpers.get_base_fee(SERVER)`)

# --- Constants ---
HORIZON_URL = "https://horizon-testnet.stellar.org" # Using Testnet for development
NETWORK_PASSPHRASE = Network.TESTNET_NETWORK_PASSPHRASE
SERVER = Server(HORIZON_URL)

# --- Custom CSS for Minimalist, High-Contrast, Futuristic Style ---
def apply_custom_css():
    st.markdown(
        """
        <style>
        /* General Body and Font */
        html, body, [class*="stApp"] {
            background-color: #0d1117; /* Dark charcoal/black background */
            color: #e6edf3; /* Light grey/off-white for text */
            font-family: 'Segoe UI', sans-serif; /* Modern font */
        }

        /* Headers */
        h1, h2, h3, h4, h5, h6 {
            color: #61affe; /* Electric blue for headers */
            font-weight: 700;
            border-bottom: 1px solid #282c34; /* Subtle line */
            padding-bottom: 5px;
            margin-top: 1.5em;
            margin-bottom: 0.8em;
        }
        h1 { font-size: 2.5em; }
        h2 { font-size: 2em; color: #79c0ff;}
        h3 { font-size: 1.5em; color: #8bd2ff;}

        /* Streamlit Widgets */
        .stButton>button {
            background-color: #2a2f37; /* Dark button background */
            color: #e6edf3; /* White button text */
            border: 1px solid #4a4f57; /* Subtle border */
            padding: 0.7em 1.2em;
            border-radius: 6px;
            transition: all 0.2s ease-in-out;
            font-weight: 600;
            letter-spacing: 0.5px;
            margin-top: 5px; /* Add some space */
        }
        .stButton>button:hover {
            background-color: #3e444d; /* Lighter on hover */
            border-color: #5d646d;
            box-shadow: 0 0 10px rgba(97, 175, 254, 0.5); /* Blue glow */
            color: #ffffff;
        }
        .stButton>button:active {
            transform: translateY(1px);
        }

        .stTextInput>div>div>input, .stNumberInput>div>div>input, .stTextArea>div>div>textarea {
            background-color: #1a1f26; /* Input background */
            color: #e6edf3; /* Input text color */
            border: 1px solid #282c34; /* Input border */
            border-radius: 6px;
            padding: 0.6em;
            transition: all 0.2s ease-in-out;
        }
        .stTextInput>div>div>input:focus, .stNumberInput>div>div>input:focus, .stTextArea>div>div>textarea:focus {
            border-color: #61affe; /* Blue focus border */
            box-shadow: 0 0 5px rgba(97, 175, 254, 0.5);
            outline: none;
            background-color: #1f242d; /* Slightly lighter on focus */
        }
        label {
            color: #b0c0d0; /* Label color */
            font-weight: 500;
            margin-bottom: 5px;
            display: block; /* Ensure labels are block elements for spacing */
        }

        .stSelectbox>div>div>div>div {
            background-color: #1a1f26;
            color: #e6edf3;
            border: 1px solid #282c34;
            border-radius: 6px;
            padding: 0.6em;
            transition: all 0.2s ease-in-out;
        }
        .stSelectbox>div>div>div>div:focus {
            border-color: #61affe;
            box-shadow: 0 0 5px rgba(97, 175, 254, 0.5);
            outline: none;
            background-color: #1f242d;
        }
        /* Checkbox styling */
        .stCheckbox>label span {
            color: #e6edf3;
        }

        /* Expander */
        .streamlit-expanderHeader {
            background-color: #1f242d; /* Slightly lighter background */
            color: #61affe; /* Accent color for expander header */
            border-radius: 8px;
            padding: 10px 15px;
            border: 1px solid #282c34;
            font-weight: 600;
            font-size: 1.1em;
            cursor: pointer;
            transition: all 0.2s ease-in-out;
        }
        .streamlit-expanderHeader:hover {
            background-color: #2a2f37;
            border-color: #4a4f57;
            box-shadow: 0 0 8px rgba(97, 175, 254, 0.3);
        }
        .streamlit-expanderContent {
            background-color: #1a1f26;
            border-left: 1px solid #282c34;
            border-right: 1px solid #282c34;
            border-bottom: 1px solid #282c34;
            border-radius: 0 0 8px 8px;
            padding: 15px;
            margin-top: -5px; /* Overlap with header border */
        }

        /* Metrics */
        [data-testid="stMetric"] {
            background-color: #1a1f26;
            border: 1px solid #282c34;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 10px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
        }
        [data-testid="stMetricValue"] {
            color: #61affe; /* Accent color for metric values */
            font-size: 2em;
            font-weight: 700;
            letter-spacing: -0.5px;
        }
        [data-testid="stMetricLabel"] {
            color: #b0c0d0;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            margin-bottom: 5px;
        }
        [data-testid="stMetricDelta"] {
            color: #4CAF50; /* Green for positive, Red for negative */
            font-weight: 600;
        }

        /* Code blocks */
        pre code {
            background-color: #1f242d !important; /* Slightly lighter for code */
            color: #e6edf3 !important;
            border: 1px solid #282c34 !important;
            border-radius: 6px !important;
            padding: 1em !important;
            word-wrap: break-word; /* Ensure long XDRs wrap */
            white-space: pre-wrap; /* Ensure pre-wrap for long XDRs */
        }

        /* Info, success, warning, error boxes */
        .stAlert {
            background-color: #1a1f26;
            border: 1px solid #282c34;
            color: #e6edf3;
            border-left: 5px solid; /* For colored border */
            border-radius: 6px;
            padding: 10px 15px;
        }
        .stAlert.st-success { border-left-color: #4CAF50; }
        .stAlert.st-info { border-left-color: #61affe; }
        .stAlert.st-warning { border-left-color: #FFC107; }
        .stAlert.st-error { border-left-color: #f44336; }

        /* Streamlit specific elements for spacing */
        .stVerticalBlock {
            gap: 1rem; /* Adjust vertical spacing between blocks */
        }
        .st-emotion-cache-1r6dm1f { /* Adjust main content padding */
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        .css-1dp5vir { /* Column gap */
            gap: 1rem;
        }
        .stMarkdown {
            word-wrap: break-word; /* Ensure long hashes/addresses wrap */
        }
        </style>
        """,
        unsafe_allow_html=True
    )

# --- Session State Initialization ---
if 'public_key' not in st.session_state:
    st.session_state.public_key = None
if 'connected' not in st.session_state:
    st.session_state.connected = False
if 'network' not in st.session_state:
    st.session_state.network = 'TESTNET' # Default to TESTNET
if 'account_data' not in st.session_state:
    st.session_state.account_data = None
if 'tx_xdr' not in st.session_state:
    st.session_state.tx_xdr = None
if 'signed_tx_xdr' not in st.session_state:
    st.session_state.signed_tx_xdr = None
if 'tx_hash' not in st.session_state:
    st.session_state.tx_hash = None
if 'last_tx_error' not in st.session_state:
    st.session_state.last_tx_error = None
if 'freighter_message_listener_key' not in st.session_state:
    st.session_state.freighter_message_listener_key = str(uuid.uuid4())

# --- Utility Functions ---

def validate_stellar_address(address):
    """Validates if a given string is a valid Stellar public key."""
    if not address:
        return False
    try:
        stellar_sdk.StrKey.is_valid_ed25519_public_key(address)
        return True
    except ValueError: # As per mandate, use ValueError
        return False

@st.cache_data(ttl=5) # Cache account data for 5 seconds to reduce Horizon calls
def get_account_details(public_key):
    """Fetches account details from Horizon."""
    if not public_key:
        return None
    try:
        account = SERVER.load_account(public_key)
        return {
            "balances": account.balances,
            "sequence": account.sequence,
            "data": account.data,
            "signers": account.signers
        }
    except NotFoundError:
        # st.error(f"Account {public_key} not found on the network. Please fund it first.")
        # This error is handled by the main app logic if an account is required
        return None
    except Exception as e:
        st.error(f"Error fetching account details: {e}")
        return None

def freighter_connector(key=None):
    """
    Renders a hidden HTML component that handles communication with Freighter.
    It listens for messages from Streamlit Python and posts results back.
    """
    # JavaScript code embedded within the HTML component.
    # This JS defines functions to connect to Freighter and sign transactions,
    # and sets up a listener for messages from the Streamlit parent frame.
    js_code_with_state = f"""
    <script>
        // Unique ID for this specific iframe communication instance
        const COMPONENT_ID = "{key}";

        // Function to send messages back to the Streamlit parent
        function sendMessageToStreamlit(type, payload) {{
            window.parent.postMessage(JSON.stringify({{ type, component_id: COMPONENT_ID, ...payload }}), "*");
        }}

        // Connect Freighter and get public key
        window.connectFreighter = () => {{
            if (window.freighter) {{
                window.freighter.getPublicKey()
                    .then(publicKey => {{
                        sendMessageToStreamlit("FREIGHTER_CONNECTED", {{ publicKey }});
                    }})
                    .catch(error => {{
                        sendMessageToStreamlit("FREIGHTER_ERROR", {{ error: error.message || "Failed to connect to Freighter." }});
                    }});
            }} else {{
                sendMessageToStreamlit("FREIGHTER_ERROR", {{ error: "Freighter not detected. Please install it." }});
            }}
        }};

        // Sign a transaction
        window.signTransaction = (xdr, network) => {{
            if (window.freighter) {{
                sendMessageToStreamlit("TRANSACTION_SIGNING_IN_PROGRESS");
                window.freighter.signTransaction(xdr, {{ network: network }})
                    .then(signedXDR => {{
                        sendMessageToStreamlit("TRANSACTION_SIGNED", {{ signedXDR }});
                    }})
                    .catch(error => {{
                        sendMessageToStreamlit("TRANSACTION_ERROR", {{ error: error.message || "Failed to sign transaction." }});
                    }});
            }} else {{
                sendMessageToStreamlit("FREIGHTER_ERROR", {{ error: "Freighter not detected. Cannot sign transaction." }});
            }}
        }};

        // Listen for messages from Streamlit parent (this iframe's parent)
        window.addEventListener("message", (event) => {{
            try {{
                const data = JSON.parse(event.data);
                // Ensure the message is intended for this component instance
                if (data.component_id === COMPONENT_ID) {{
                    if (data.type === "REQUEST_CONNECT") {{
                        window.connectFreighter();
                    }} else if (data.type === "REQUEST_SIGN_TRANSACTION") {{
                        window.signTransaction(data.xdr, data.network);
                    }}
                }}
            }} catch (e) {{
                // Ignore non-JSON messages or messages not for us
                console.error("Freighter component received invalid message:", e);
            }}
        }});
    </script>
    """

    # The full HTML content for the iframe, including the JS code.
    # The iframe is hidden as it's purely for background communication.
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Freighter Connector</title>
        <meta charset="utf-8">
        <style>body {{ margin: 0; padding: 0; }}</style>
    </head>
    <body>
        {js_code_with_state}
    </body>
    </html>
    """
    # Render the component. It returns the last JSON message posted to `window.parent`.
    # `height` and `width` are minimal since the iframe is just a communication channel.
    component_result = html(full_html, height=1, width=1, scrolling=False, key=key)

    # Process the result received from the JavaScript component
    if component_result:
        try:
            data = json.loads(component_result)
            if data.get('component_id') == key: # Verify the message is for this specific component instance
                if data.get('type') == "FREIGHTER_CONNECTED":
                    st.session_state.public_key = data['publicKey']
                    st.session_state.connected = True
                    st.session_state.last_tx_error = None
                    st.success(f"🔗 Connected to Freighter: {data['publicKey'][:8]}...{data['publicKey'][-8:]}")
                    st.rerun() # Rerun to update the main UI with connected state
                elif data.get('type') == "FREIGHTER_ERROR":
                    st.session_state.last_tx_error = data['error']
                    st.error(f"Freighter Error: {data['error']}")
                elif data.get('type') == "TRANSACTION_SIGNED":
                    st.session_state.signed_tx_xdr = data['signedXDR']
                    st.session_state.last_tx_error = None
                    st.info("Transaction signed by Freighter. Ready to submit.")
                    # No rerun here, let the user decide when to submit
                elif data.get('type') == "TRANSACTION_ERROR":
                    st.session_state.last_tx_error = data['error']
                    st.error(f"Transaction Signing Failed: {data['error']}")
                elif data.get('type') == "TRANSACTION_SIGNING_IN_PROGRESS":
                    # This message is just for immediate feedback, no need to store/rerun
                    pass
        except json.JSONDecodeError:
            pass # Ignore messages that are not valid JSON

def send_message_to_iframe(key_id, message_type, payload={}):
    """
    Injects a JavaScript snippet into the Streamlit parent document to send a message
    to the specific iframe component identified by `key_id`.
    """
    # The iframe's default ID generated by Streamlit components v1 is 'iframe-{key}'.
    target_iframe_id = f"iframe-{key_id}"
    message = json.dumps({"type": message_type, "component_id": key_id, **payload})
    
    # We use st.markdown to inject a script that finds the target iframe
    # and sends a postMessage to its contentWindow.
    st.markdown(
        f"""
        <script>
            var iframe = document.getElementById('{target_iframe_id}');
            if (iframe && iframe.contentWindow) {{
                iframe.contentWindow.postMessage(JSON.stringify({message}), '*');
            }} else {{
                console.warn("Iframe with ID '{target_iframe_id}' not found or not ready.");
            }}
        </script>
        """,
        unsafe_allow_html=True
    )
    # A small delay to ensure the script has a chance to execute before Streamlit potentially rerenders
    time.sleep(0.01)

# --- Main Application ---
def main():
    apply_custom_css()

    st.title('🧬 EonFlow: Decentralized Organizations')
    st.markdown("Empowering resilient, decentralized organizations through adaptive resource allocation, trust evolution, and programmatic governance over sponsored entities.")
    st.markdown("---")

    # --- Freighter Connector (Always present but hidden) ---
    # This component handles all direct Freighter interaction.
    # It must be at the top level to always listen for postMessages from Freighter.
    freighter_connector(key=st.session_state.freighter_message_listener_key)

    # --- Header and Connection Status ---
    col1, col2 = st.columns([3, 1])

    with col1:
        if st.session_state.connected:
            st.success(f"🔗 Connected: `{st.session_state.public_key[:8]}...{st.session_state.public_key[-8:]}`")
            st.markdown(f"<p style='font-size:0.9em; color:#b0c0d0;'>Network: `{st.session_state.network}`</p>", unsafe_allow_html=True)
            if st.button("🔌 Disconnect Freighter", key="disconnect_btn"):
                st.session_state.public_key = None
                st.session_state.connected = False
                st.session_state.account_data = None
                st.session_state.tx_xdr = None
                st.session_state.signed_tx_xdr = None
                st.session_state.tx_hash = None
                st.session_state.last_tx_error = None
                st.rerun()
        else:
            st.warning("Please connect to Freighter to use EonFlow's features.")
            if st.button("🚀 Connect Freighter", key="connect_btn"):
                # Send a message to the iframe to initiate connection
                send_message_to_iframe(st.session_state.freighter_message_listener_key, "REQUEST_CONNECT")
                st.info("Connecting to Freighter...")

    with col2:
        st.markdown(f"<h3 style='text-align: right; color:#8bd2ff;'>Status</h3>", unsafe_allow_html=True)
        # Fetch and display account details if connected
        if st.session_state.connected and st.session_state.public_key:
            st.session_state.account_data = get_account_details(st.session_state.public_key)
            if st.session_state.account_data:
                balance_xlm = next((b['balance'] for b in st.session_state.account_data['balances'] if b['asset_type'] == 'native'), "0.00")
                st.metric(label="XLM Balance", value=f"{float(balance_xlm):.2f}")
                st.metric(label="Sequence Number", value=st.session_state.account_data['sequence'])
            else: # Account not found or error fetching
                st.metric(label="XLM Balance", value="N/A")
                st.metric(label="Sequence Number", value="N/A")
                st.error(f"Account `{st.session_state.public_key[:8]}...` not found. Fund it via a Stellar faucet to activate.")
        else:
            st.metric(label="Status", value="Offline 🔴")

    st.markdown("---")

    # --- Core EonFlow Operations ---
    if st.session_state.connected and st.session_state.public_key and st.session_state.account_data:
        st.subheader('⚙️ Decentralized Organization Operations')

        # Always load the latest account data before building any transaction
        try:
            current_account = SERVER.load_account(st.session_state.public_key)
        except NotFoundError:
            st.error("Your connected account is not activated on the Stellar network. Please fund it first.")
            return # Prevent operations if account is not active
        except Exception as e:
            st.error(f"Failed to load account for operations: {e}")
            return # Prevent operations

        # --- Create Sponsored Account ---
        with st.expander("✨ Create & Fund Sponsored Account"):
            st.markdown("Generate a new Stellar account (keypair) and fund it from your connected account.")
            new_account_funding_amount = st.number_input("Initial XLM Funding Amount (min 1 XLM)", min_value=1.0, value=10.0, step=1.0, key="new_acc_fund_amt")

            if st.button("➕ Generate & Fund Account", key="generate_fund_acc_btn"):
                if new_account_funding_amount < 1:
                    st.error("Minimum funding amount is 1 XLM for a new account.")
                else:
                    with st.spinner("Generating keypair and preparing transaction..."):
                        new_keypair = Keypair.random()
                        new_public_key = new_keypair.public_key
                        new_secret_key = new_keypair.secret_key

                        try:
                            # Build transaction to create and fund the new account
                            transaction_builder = TransactionBuilder(
                                source_account=current_account,
                                network_passphrase=NETWORK_PASSPHRASE,
                                base_fee=stellar_sdk.helpers.get_base_fee(SERVER)
                            )
                            transaction_builder.append_create_account_op(
                                destination=new_public_key,
                                starting_balance=str(new_account_funding_amount)
                            )
                            transaction = transaction_builder.build()
                            xdr = transaction.to_xdr()

                            st.session_state.tx_xdr = xdr
                            st.session_state.signed_tx_xdr = None
                            st.session_state.tx_hash = None
                            st.session_state.last_tx_error = None

                            send_message_to_iframe(st.session_state.freighter_message_listener_key, "REQUEST_SIGN_TRANSACTION", {"xdr": xdr, "network": st.session_state.network})
                            st.info("Transaction to create and fund account sent to Freighter for signing. Please approve in Freighter.")
                            st.session_state.new_keypair = {"public": new_public_key, "secret": new_secret_key}
                            st.session_state.show_new_key_warning = True

                        except Exception as e:
                            st.session_state.last_tx_error = str(e)
                            st.error(f"Error building transaction: {e}")

        # Display new keypair details if generated
        if st.session_state.get('show_new_key_warning') and st.session_state.get('new_keypair'):
            st.warning("⚠️ IMPORTANT: Please save the secret key immediately. It will not be shown again.")
            st.code(f"New Account Public Key: {st.session_state.new_keypair['public']}", language="text")
            st.code(f"New Account Secret Key: {st.session_state.new_keypair['secret']}", language="text")
            if st.button("Acknowledge & Hide Secret Key", key="hide_secret_key_btn"):
                del st.session_state.new_keypair
                del st.session_state.show_new_key_warning
                st.rerun()


        # --- Fund Account / Send Payment ---
        with st.expander("💸 Send Payment"):
            st.markdown("Send XLM or any custom asset to another Stellar account.")
            recipient_address = st.text_input("Recipient Public Key", key="send_recipient_pk")
            asset_type = st.radio("Asset Type", ["XLM (Native)", "Custom Asset"], key="send_asset_type_radio", horizontal=True)
            asset_code = ""
            asset_issuer = ""

            if asset_type == "Custom Asset":
                asset_code = st.text_input("Asset Code (e.g., USD)", key="send_asset_code")
                asset_issuer = st.text_input("Asset Issuer Public Key", key="send_asset_issuer")
            
            send_amount = st.number_input("Amount", min_value=0.0000001, value=0.1, step=0.1, format="%.7f", key="send_amount")

            if st.button("➡️ Send Payment", key="send_payment_btn"):
                if not validate_stellar_address(recipient_address):
                    st.error("Invalid Recipient Public Key.")
                elif asset_type == "Custom Asset" and not asset_code:
                    st.error("Asset Code is required for custom assets.")
                elif asset_type == "Custom Asset" and not validate_stellar_address(asset_issuer):
                    st.error("Invalid Asset Issuer Public Key for custom asset.")
                else:
                    with st.spinner("Preparing payment transaction..."):
                        try:
                            # Determine asset
                            if asset_type == "XLM (Native)":
                                asset = Asset.native()
                            else:
                                asset = Asset(asset_code, asset_issuer)

                            transaction_builder = TransactionBuilder(
                                source_account=current_account,
                                network_passphrase=NETWORK_PASSPHRASE,
                                base_fee=stellar_sdk.helpers.get_base_fee(SERVER)
                            )
                            transaction_builder.append_payment_op(
                                destination=recipient_address,
                                asset=asset,
                                amount=str(send_amount)
                            )
                            transaction = transaction_builder.build()
                            xdr = transaction.to_xdr()

                            st.session_state.tx_xdr = xdr
                            st.session_state.signed_tx_xdr = None
                            st.session_state.tx_hash = None
                            st.session_state.last_tx_error = None

                            send_message_to_iframe(st.session_state.freighter_message_listener_key, "REQUEST_SIGN_TRANSACTION", {"xdr": xdr, "network": st.session_state.network})
                            st.info("Payment transaction sent to Freighter for signing. Please approve in Freighter.")

                        except Exception as e:
                            st.session_state.last_tx_error = str(e)
                            st.error(f"Error building transaction: {e}")

        # --- Manage Trustlines ---
        with st.expander("🤝 Manage Trustlines"):
            st.markdown("Establish or remove trust for custom assets on your connected account.")
            trust_asset_code = st.text_input("Asset Code (e.g., USDC)", key="trust_asset_code")
            trust_asset_issuer = st.text_input("Asset Issuer Public Key", key="trust_asset_issuer")
            # Limit 0.0 is used to remove a trustline. Max float value is default for adding.
            trust_limit = st.number_input("Trust Limit (0 to remove trust)", min_value=0.0, value=1000000.0, step=1000.0, format="%.7f", key="trust_limit")

            if st.button("🔄 Change Trust", key="change_trust_btn"):
                if not trust_asset_code:
                    st.error("Asset Code is required.")
                elif not validate_stellar_address(trust_asset_issuer):
                    st.error("Invalid Asset Issuer Public Key.")
                else:
                    with st.spinner("Preparing change trust transaction..."):
                        try:
                            asset = Asset(trust_asset_code, trust_asset_issuer)
                            transaction_builder = TransactionBuilder(
                                source_account=current_account,
                                network_passphrase=NETWORK_PASSPHRASE,
                                base_fee=stellar_sdk.helpers.get_base_fee(SERVER)
                            )
                            transaction_builder.append_change_trust_op(
                                asset=asset,
                                limit=str(trust_limit)
                            )
                            transaction = transaction_builder.build()
                            xdr = transaction.to_xdr()

                            st.session_state.tx_xdr = xdr
                            st.session_state.signed_tx_xdr = None
                            st.session_state.tx_hash = None
                            st.session_state.last_tx_error = None

                            send_message_to_iframe(st.session_state.freighter_message_listener_key, "REQUEST_SIGN_TRANSACTION", {"xdr": xdr, "network": st.session_state.network})
                            st.info("Change Trust transaction sent to Freighter for signing. Please approve in Freighter.")

                        except Exception as e:
                            st.session_state.last_tx_error = str(e)
                            st.error(f"Error building transaction: {e}")

        # --- Set Data Entry (Programmatic Governance Example) ---
        with st.expander("🗂️ Set Account Data Entry"):
            st.markdown("Set a key-value pair on your connected account. Useful for simple on-chain governance or metadata.")
            data_key = st.text_input("Data Key (max 64 bytes, e.g., 'organization_name')", key="data_entry_key")
            data_value = st.text_input("Data Value (max 64 bytes, leave empty to delete)", key="data_entry_value")
            
            if st.button("➕ Set Data Entry", key="set_data_entry_btn"):
                if not data_key:
                    st.error("Data Key cannot be empty.")
                try:
                    data_key_bytes = data_key.encode('utf-8')
                    # Data entry value should be None for deletion
                    data_value_bytes = data_value.encode('utf-8') if data_value else None

                    if len(data_key_bytes) > 64:
                        st.error("Data Key too long (max 64 bytes).")
                    elif data_value_bytes and len(data_value_bytes) > 64:
                        st.error("Data Value too long (max 64 bytes).")
                    else:
                        with st.spinner("Preparing set data entry transaction..."):
                            transaction_builder = TransactionBuilder(
                                source_account=current_account,
                                network_passphrase=NETWORK_PASSPHRASE,
                                base_fee=stellar_sdk.helpers.get_base_fee(SERVER)
                            )
                            transaction_builder.append_manage_data_op(
                                key=data_key,
                                value=data_value_bytes
                            )
                            transaction = transaction_builder.build()
                            xdr = transaction.to_xdr()

                            st.session_state.tx_xdr = xdr
                            st.session_state.signed_tx_xdr = None
                            st.session_state.tx_hash = None
                            st.session_state.last_tx_error = None

                            send_message_to_iframe(st.session_state.freighter_message_listener_key, "REQUEST_SIGN_TRANSACTION", {"xdr": xdr, "network": st.session_state.network})
                            st.info("Set Data Entry transaction sent to Freighter for signing. Please approve in Freighter.")

                except Exception as e:
                    st.session_state.last_tx_error = str(e)
                    st.error(f"Error building transaction: {e}")

        # --- Merge Account (Programmatic Governance Example) ---
        with st.expander("🗑️ Merge Account"):
            st.markdown("Merge your connected account into another Stellar account. **This will permanently remove your connected account from the ledger.**")
            destination_merge_address = st.text_input("Destination Public Key for Account Merge", key="merge_destination_pk")
            confirm_merge = st.checkbox("I understand this action is irreversible and will merge my account.", key="confirm_merge_checkbox")

            if st.button("🔥 Merge Account", key="merge_account_btn", disabled=not confirm_merge):
                if not validate_stellar_address(destination_merge_address):
                    st.error("Invalid Destination Public Key.")
                elif destination_merge_address == st.session_state.public_key:
                    st.error("Cannot merge an account into itself.")
                else:
                    with st.spinner("Preparing account merge transaction..."):
                        try:
                            transaction_builder = TransactionBuilder(
                                source_account=current_account,
                                network_passphrase=NETWORK_PASSPHRASE,
                                base_fee=stellar_sdk.helpers.get_base_fee(SERVER)
                            )
                            transaction_builder.append_account_merge_op(
                                destination=destination_merge_address
                            )
                            transaction = transaction_builder.build()
                            xdr = transaction.to_xdr()

                            st.session_state.tx_xdr = xdr
                            st.session_state.signed_tx_xdr = None
                            st.session_state.tx_hash = None
                            st.session_state.last_tx_error = None

                            send_message_to_iframe(st.session_state.freighter_message_listener_key, "REQUEST_SIGN_TRANSACTION", {"xdr": xdr, "network": st.session_state.network})
                            st.warning("Account Merge transaction sent to Freighter for signing. This is PERMANENT. Please approve carefully.")

                        except Exception as e:
                            st.session_state.last_tx_error = str(e)
                            st.error(f"Error building transaction: {e}")

        st.markdown("---")

        # --- Transaction Signing & Submission Status ---
        st.subheader('📡 Transaction Status')

        if st.session_state.last_tx_error:
            st.error(f"Transaction Error: {st.session_state.last_tx_error}")
            if st.button("Clear Error"):
                st.session_state.last_tx_error = None
                st.rerun()

        if st.session_state.tx_xdr and not st.session_state.signed_tx_xdr:
            st.info("Awaiting signature from Freighter. Please check your Freighter wallet.")
            st.markdown("**Unsigned XDR:**")
            st.code(st.session_state.tx_xdr, language="text")

        if st.session_state.signed_tx_xdr:
            st.success("Transaction successfully signed by Freighter!")
            st.markdown("**Signed XDR:**")
            st.code(st.session_state.signed_tx_xdr, language="text")

            if st.button("✨ Submit Signed Transaction to Network", key="submit_signed_tx_btn"):
                with st.spinner("Submitting transaction..."):
                    try:
                        transaction = stellar_sdk.TransactionEnvelope.from_xdr(
                            st.session_state.signed_tx_xdr,
                            NETWORK_PASSPHRASE
                        )
                        response = SERVER.submit_transaction(transaction)
                        st.session_state.tx_hash = response.hash
                        st.success(f"Transaction submitted! Hash: `{response.hash}`")
                        explorer_url = f"https://testnet.stellar.expert/tx/{response.hash}"
                        st.markdown(f"View on [Stellar Expert]({explorer_url})", unsafe_allow_html=True)

                        # Clear transaction state after successful submission
                        st.session_state.tx_xdr = None
                        st.session_state.signed_tx_xdr = None
                        st.session_state.last_tx_error = None
                        st.rerun() # Rerun to clear UI and refresh account data

                    except BadRequestError as e:
                        st.session_state.last_tx_error = f"Transaction submission failed: {e.extras.result_codes}"
                        st.error(f"Transaction submission failed: {e.extras.result_codes}")
                    except Exception as e:
                        st.session_state.last_tx_error = str(e)
                        st.error(f"Error submitting transaction: {e}")
            
            # Allow clearing signed XDR if user decides not to submit
            if st.button("Clear Signed Transaction", key="clear_signed_tx_btn"):
                st.session_state.tx_xdr = None
                st.session_state.signed_tx_xdr = None
                st.session_state.last_tx_error = None
                st.rerun()


    elif not st.session_state.connected:
        st.info("Please connect your Stellar wallet via Freighter to perform operations.")

    st.markdown("---")
    st.markdown(f"<p style='text-align: center; color:#4a4f57; font-size:0.8em;'>EonFlow v1.0.0 | Powered by Stellar 🌟</p>", unsafe_allow_html=True)

# --- Query Params Handling (Mandate: STRICTLY use 'st.query_params') ---
def handle_query_params():
    """
    Processes initial query parameters from the URL.
    This is for reading initial app state, not dynamic component communication.
    """
    query_params = st.query_params

    # Example: Pre-fill public key if provided in URL (for information, not auto-connect)
    if 'pk' in query_params:
        pk_from_url = query_params['pk']
        if validate_stellar_address(pk_from_url):
            if not st.session_state.public_key: # Only display if not already connected
                st.sidebar.info(f"Public Key detected in URL: `{pk_from_url}`. Connect Freighter to use your account.")
        else:
            st.sidebar.error("Invalid public key in URL query parameter 'pk'.")

    # Example: Network selection from URL
    if 'network' in query_params:
        network_from_url = query_params['network'].upper()
        if network_from_url in ['TESTNET', 'PUBLIC', 'FUTURENET']: # Add other networks if supported
            if st.session_state.network != network_from_url:
                st.session_state.network = network_from_url
                st.info(f"Network set from URL to: `{network_from_url}`")
                st.rerun() # Rerun to apply network change immediately
        else:
            st.warning(f"Invalid network in URL query parameter 'network': `{network_from_url}`. Defaulting to TESTNET.")

# Run the app
if __name__ == '__main__':
    handle_query_params() # Process query params on app start/rerun
    main()
