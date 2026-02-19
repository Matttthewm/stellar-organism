import streamlit as st
import streamlit.components.v1 as components

# MANDATE 7: CRITICAL IMPORT RULES
import stellar_sdk
from stellar_sdk import Server, Keypair, TransactionBuilder, Network, Asset
from stellar_sdk.exceptions import BadRequestError, NotFoundError

# --- CONFIGURATION ---
HORIZON_URL = "https://horizon-testnet.stellar.org"
NETWORK_PASSPHRASE = Network.TESTNET_PASSPHRASE
SPONSORSHIP_AMOUNT_XLM = "1"  # Amount in XLM for initial sponsorship
PRESERVATION_THRESHOLD = 3   # Number of unique sponsorships needed for preservation

# MANDATE 11: SECRET KEY HANDLING
if "ISSUER_ACCOUNT_SECRET" in st.secrets:
    ISSUER_KEY_SECRET = st.secrets["ISSUER_ACCOUNT_SECRET"]
    ISSUER_KEYPAIR = Keypair.from_secret(ISSUER_KEY_SECRET)
    st.session_state.is_demo_mode = False
else:
    if "demo_issuer_key_secret" not in st.session_state:
        st.session_state.demo_issuer_key_secret = Keypair.random().secret
    ISSUER_KEY_SECRET = st.session_state.demo_issuer_key_secret
    ISSUER_KEYPAIR = Keypair.from_secret(ISSUER_KEY_SECRET)
    st.session_state.is_demo_mode = True
    st.warning("🚨 Using Ephemeral Demo Keys for the Issuer Account! 🚨")
    st.info(f"Demo Issuer Public Key: `{ISSUER_KEYPAIR.public_key}`")

# MANDATE 8: STELLAR SERVER RULES
server = Server(HORIZON_URL)

# --- HELPER FUNCTIONS ---
def submit_transaction(signed_xdr: str):
    """Submits a signed XDR to the Stellar network."""
    try:
        transaction_result = server.submit_transaction(signed_xdr)
        st.session_state.tx_hash = transaction_result['hash']
        st.success(f"Transaction successful! 🎉 Hash: `{st.session_state.tx_hash}`")
        st.balloons()
        return transaction_result
    except BadRequestError as e:
        st.error(f"Transaction failed! 😞 {e.response.text}")
        st.session_state.tx_hash = None
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        st.session_state.tx_hash = None
        return None

# MANDATE 1: Freighter Integration (st.components.v1.html + signTransaction)
# MANDATE 9: HTML COMPONENT RULES
def FreighterComponent(command: str = None, xdr: str = None, key=None):
    """
    Streamlit component for Freighter interactions (connect and sign).
    It takes a 'command' ('connect' or 'sign') and an 'xdr' (if command is 'sign').
    Returns a dictionary with 'type' and 'payload' via Streamlit.setComponentValue.
    """
    js_code = f"""
    <script src="https://unpkg.com/@stellar/freighter-api@1.2.0/build/freighter.min.js"></script>
    <script>
        window.Streamlit.setComponentReady(); // Indicate component is ready

        async function executeFreighterCommand() {{
            const command = "{command}"; // Passed from Python
            const xdr_to_sign = "{xdr if xdr else ''}"; // Passed from Python
            
            let result = {{ type: 'noop' }};

            if (command === 'connect') {{
                try {{
                    const publicKey = await window.FreighterApi.getPublicKey();
                    result = {{ type: 'freighter_connected', publicKey: publicKey }};
                }} catch (error) {{
                    result = {{ type: 'freighter_error', message: error.message }};
                }}
            }} else if (command === 'sign' && xdr_to_sign) {{
                try {{
                    const signedXDR = await window.FreighterApi.signTransaction(xdr_to_sign, {{ network: '{NETWORK_PASSPHRASE}' }});
                    result = {{ type: 'transaction_signed', signedXDR: signedXDR }};
                }} catch (error) {{
                    result = {{ type: 'freighter_error', message: error.message }};
                }}
            }}
            
            // Only set component value if there's a meaningful result
            if (result.type !== 'noop' && window.Streamlit) {{
                window.Streamlit.setComponentValue(result);
            }}
        }}

        // Execute command once the component loads/reruns
        executeFreighterCommand();
    </script>
    """
    # Using `height=0, width=0` makes it invisible.
    # A unique key is critical to ensure re-execution when `command` or `xdr` changes.
    return components.html(js_code, height=0, width=0, key=key, default={'type': 'noop'})

# --- STREAMLIT APP ---

# MANDATE 3: Custom CSS for style "Minimalist/Swiss-Design"
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');
    
    html, body, [class*="st-"] {
        font-family: 'IBM Plex Sans', sans-serif;
        color: #333;
        line-height: 1.6;
    }
    body {
        background-color: #f0f2f6;
    }
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 700px; /* Swiss design often implies structured layouts */
    }
    h1, h2, h3, h4, h5, h6 {
        font-weight: 500;
        color: #1a1a1a;
    }
    h1 {
        font-size: 2.5em;
        border-bottom: 2px solid #ddd;
        padding-bottom: 0.5em;
        margin-bottom: 1em;
    }
    .stButton > button {
        background-color: #e6e6e6; /* Light grey button */
        color: #333;
        border: 1px solid #ccc;
        border-radius: 4px;
        padding: 0.6em 1.2em;
        font-weight: 500;
        transition: all 0.2s ease-in-out;
    }
    .stButton > button:hover {
        background-color: #d9d9d9;
        border-color: #bbb;
    }
    .stTextInput > div > div > input, .stTextArea > div > div > textarea {
        border-radius: 4px;
        border: 1px solid #ccc;
        padding: 0.5em 0.8em;
    }
    .stTextInput > div > div > input:focus, .stTextArea > div > div > textarea:focus {
        border-color: #888;
        box-shadow: 0 0 0 1px #888;
        outline: none;
    }
    .stMetric {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 1em;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .stAlert {
        border-radius: 4px;
    }
    .stProgress > div > div > div > div {
        background-color: #4CAF50; /* A touch of green for progress */
    }
    .css-1d391kg.e16fv1bt2 { /* Adjust sidebar header for better contrast */
        color: #1a1a1a;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.set_page_config(
    page_title="Ephemeral Echoes",
    page_icon="🧬", # MANDATE 5: NO external images. Use Emojis 🧬 only.
    layout="centered",
    initial_sidebar_state="expanded",
)

# Initialize session state variables
if 'freighter_public_key' not in st.session_state:
    st.session_state.freighter_public_key = None
if 'is_connected' not in st.session_state:
    st.session_state.is_connected = False
if 'signed_xdr' not in st.session_state:
    st.session_state.signed_xdr = None
if 'tx_hash' not in st.session_state:
    st.session_state.tx_hash = None
if 'freighter_component_key' not in st.session_state:
    st.session_state.freighter_component_key = 0 # To force re-render freighter component
if 'trigger_freighter_connect' not in st.session_state:
    st.session_state.trigger_freighter_connect = False
if 'trigger_freighter_sign' not in st.session_state:
    st.session_state.trigger_freighter_sign = {'status': False, 'xdr': None}

# MANDATE 10: SIDEBAR MANDATE
with st.sidebar:
    st.info("### 🧬 Ephemeral Echoes\n\nCraft fleeting digital messages or art pieces whose existence is tied to community sponsorship, with a mechanism for preservation into a collective archival constellation.")
    st.markdown("---")
    st.caption("✨ Visual Style: Minimalist / Swiss-Design")
    st.markdown("---")
    st.subheader("Your Freighter Connection")
    if st.session_state.is_connected:
        st.success("Freighter Connected! ✅")
        st.write(f"Public Key: `{st.session_state.freighter_public_key}`")
        if st.button("Disconnect Freighter 🚫", key="disconnect_freighter"):
            st.session_state.freighter_public_key = None
            st.session_state.is_connected = False
            st.session_state.signed_xdr = None
            st.session_state.tx_hash = None
            st.session_state.freighter_component_key += 1 # Rerender Freighter JS
            st.experimental_rerun()
    else:
        st.warning("Freighter Not Connected.")
        if st.button("Connect Freighter 🚀", key="connect_freighter_sidebar"):
            st.session_state.trigger_freighter_connect = True
            st.experimental_rerun()

    st.markdown("---")
    st.subheader("Issuer Account")
    st.write(f"Public Key: `{ISSUER_KEYPAIR.public_key}`")
    if st.session_state.is_demo_mode:
        st.caption("This is a demo issuer account, funded automatically for testnet transactions.")
        # Ensure the demo issuer account is funded on testnet
        if "demo_issuer_funded" not in st.session_state:
            try:
                friendbot_response = server.friendbot(ISSUER_KEYPAIR.public_key)
                st.session_state.demo_issuer_funded = True
                st.sidebar.success("Demo Issuer Funded! (Testnet)")
            except Exception as e:
                st.sidebar.error(f"Failed to fund demo issuer: {e}")
        else:
            st.sidebar.caption("Demo Issuer already funded.")

# --- Freighter Component Logic ---
# This component acts as an invisible bridge for Freighter interactions.
# It's always rendered, but only executes commands when triggered via session state.

# Process connect command
if st.session_state.trigger_freighter_connect:
    st.session_state.trigger_freighter_connect = False # Reset trigger
    with st.spinner("Connecting to Freighter..."):
        freighter_connect_result = FreighterComponent(
            command='connect',
            key=f"freighter_connect_op_{st.session_state.freighter_component_key}"
        )
    if freighter_connect_result and freighter_connect_result['type'] == 'freighter_connected':
        st.session_state.freighter_public_key = freighter_connect_result['publicKey']
        st.session_state.is_connected = True
        st.session_state.freighter_component_key += 1 # Increment key for next use
        st.experimental_rerun() # Rerun to update UI with connection status
    elif freighter_connect_result and freighter_connect_result['type'] == 'freighter_error':
        st.error(f"Freighter connection failed: {freighter_connect_result['message']}")
        st.session_state.is_connected = False
        st.session_state.freighter_component_key += 1
        st.experimental_rerun()

# Process sign command
if st.session_state.trigger_freighter_sign['status']:
    xdr_to_sign_temp = st.session_state.trigger_freighter_sign['xdr']
    st.session_state.trigger_freighter_sign = {'status': False, 'xdr': None} # Reset trigger

    with st.spinner("Awaiting Freighter signature..."):
        freighter_sign_result = FreighterComponent(
            command='sign',
            xdr=xdr_to_sign_temp,
            key=f"freighter_sign_op_{st.session_state.freighter_component_key}"
        )

    if freighter_sign_result and freighter_sign_result['type'] == 'transaction_signed':
        signed_xdr = freighter_sign_result['signedXDR']
        submit_transaction(signed_xdr)
        st.session_state.freighter_component_key += 1
        st.experimental_rerun()
    elif freighter_sign_result and freighter_sign_result['type'] == 'freighter_error':
        st.error(f"Freighter signing failed: {freighter_sign_result['message']}")
        st.session_state.freighter_component_key += 1
    elif freighter_sign_result and freighter_sign_result['type'] == 'noop':
        st.warning("Freighter did not return a signature. Did you cancel the transaction?")
        st.session_state.freighter_component_key += 1


st.title("🧬 Ephemeral Echoes")

st.markdown("---")

# MANDATE 6: Use st.columns, st.expander, and st.metric.
col1, col2 = st.columns(2)

# Display Issuer Account info
if st.session_state.is_demo_mode:
    try:
        col1.metric("Issuer Account Balance", f"{float(server.load_account(ISSUER_KEYPAIR.public_key).get_balance('XLM')):.2f} XLM")
    except NotFoundError:
        col1.error("Issuer account not found on network. Please fund it (Testnet only).")
        st.stop() # Cannot proceed without issuer account
else:
    try:
        col1.metric("Issuer Account Balance", f"{float(server.load_account(ISSUER_KEYPAIR.public_key).get_balance('XLM')):.2f} XLM")
    except NotFoundError:
        col1.error("Issuer account not found on network. Ensure ISSUER_ACCOUNT_SECRET is valid and account is funded.")
        st.stop() # Cannot proceed without issuer account

col2.metric("Preservation Threshold", f"{PRESERVATION_THRESHOLD} sponsorships")

st.markdown("---")

st.subheader("✍️ Craft Your Echo")
if st.session_state.is_connected:
    user_message = st.text_input(
        "Your Fleeting Message (Max 28 characters for memo)",
        key="echo_message_input",
        max_chars=28,
        help="This message will be attached to your sponsorship transaction."
    )

    if st.button(f"Sponsor Echo ({SPONSORSHIP_AMOUNT_XLM} XLM) ✨", key="sponsor_echo_button"):
        if not user_message:
            st.warning("Please enter a message for your echo.")
        else:
            try:
                # Load sender (Freighter) account
                source_account = server.load_account(st.session_state.freighter_public_key)

                # Build payment transaction
                transaction = (
                    TransactionBuilder(
                        source_account=source_account,
                        network_passphrase=NETWORK_PASSPHRASE,
                        base_fee=stellar_sdk.FeeBumpTransaction.DEFAULT_BASE_FEE
                    )
                    .append_payment_op(
                        destination=ISSUER_KEYPAIR.public_key,
                        amount=SPONSORSHIP_AMOUNT_XLM,
                        asset=Asset.native(),
                    )
                    .add_text_memo(user_message) # MANDATE 2: Stellar SDK for XDR (using memo)
                    .build()
                )

                xdr_to_sign = transaction.to_xdr()
                st.session_state.trigger_freighter_sign = {'status': True, 'xdr': xdr_to_sign} # Trigger signing
                st.experimental_rerun()

            except NotFoundError:
                st.error(f"Your connected account (`{st.session_state.freighter_public_key[:10]}...`) does not exist on the Testnet. Please fund it using the [Friendbot](https://friendbot.stellar.org/?addr={st.session_state.freighter_public_key}).")
            except ValueError as e: # MANDATE 7: Use ValueError for key errors
                st.error(f"Invalid public key: {e}")
            except Exception as e:
                st.error(f"An error occurred: {e}")

else:
    st.info("Please connect your Freighter wallet to craft and sponsor echoes.")

st.markdown("---")

st.subheader("📜 Current Echoes & Archive")

@st.cache_data(ttl=30) # Cache for 30 seconds
def get_echo_sponsorships():
    """Fetches and aggregates sponsorships for echoes."""
    memo_sponsorships = {} # memo_text -> list of (source_account_id, tx_hash)
    total_payments = 0

    try:
        # Fetch payments to the issuer account
        # We need to ensure we fetch enough history. Let's get up to 200 payments.
        payments = server.payments().for_account(ISSUER_KEYPAIR.public_key).limit(200).order(desc=True).call()
        
        for payment in payments['_embedded']['records']:
            # Only consider native asset payments with a text memo
            if (payment['type'] == 'payment' and 
                payment['asset_type'] == 'native' and 
                payment['transaction_memo_type'] == 'text'):
                
                memo_text = payment['transaction_memo']
                if memo_text not in memo_sponsorships:
                    memo_sponsorships[memo_text] = []
                
                # Count each distinct payment operation as a sponsorship.
                # (source_account, transaction_hash) pair ensures that if one account sends multiple
                # payments in separate transactions, or if multiple ops exist in one tx, it's counted correctly.
                # For simplicity, let's just count unique transaction hashes for a given memo.
                tx_id_for_memo = (payment['transaction_hash'])
                if tx_id_for_memo not in [tx_id for _, tx_id in memo_sponsorships[memo_text]]:
                    memo_sponsorships[memo_text].append((payment['source_account'], payment['transaction_hash']))
                    total_payments += 1
                    
    except Exception as e:
        st.error(f"Error fetching sponsorships: {e}")
        return {}, 0
    return memo_sponsorships, total_payments

echo_sponsorships, total_sponsorships_count = get_echo_sponsorships()

st.metric("Total Echo Sponsorships", total_sponsorships_count, help="Total number of times echoes have been sponsored.")

if not echo_sponsorships:
    st.info("No echoes have been sponsored yet. Be the first! 🌟")
else:
    preserved_echoes = {}
    fleeting_echoes = {}

    for memo, sponsorships_list in echo_sponsorships.items():
        unique_sponsorship_count = len(sponsorships_list) # Each (source, tx_hash) is a unique sponsorship
        if unique_sponsorship_count >= PRESERVATION_THRESHOLD:
            preserved_echoes[memo] = unique_sponsorship_count
        else:
            fleeting_echoes[memo] = unique_sponsorship_count
    
    # Sort for consistent display
    preserved_echoes = dict(sorted(preserved_echoes.items(), key=lambda item: item[1], reverse=True))
    fleeting_echoes = dict(sorted(fleeting_echoes.items(), key=lambda item: item[1], reverse=True))

    with st.expander("✨ Preserved Echoes (Archival Constellation)"): # MANDATE 6: st.expander
        st.markdown(
            """
            These echoes have garnered enough community support to be enshrined in the Archival Constellation.
            Their messages resonate beyond the fleeting moment.
            """
        )
        if preserved_echoes:
            for memo, count in preserved_echoes.items():
                st.markdown(f"**\"__{memo}__\"** – Sponsored **{count}** times (Preserved! 🌠)")
        else:
            st.info("No echoes have reached the preservation threshold yet.")

    with st.expander("🌬️ Fleeting Echoes"): # MANDATE 6: st.expander
        st.markdown(
            """
            These echoes are still seeking more sponsorship to achieve preservation.
            Their existence is ephemeral; support them before they fade!
            """
        )
        if fleeting_echoes:
            for memo, count in fleeting_echoes.items():
                progress = min(100, (count / PRESERVATION_THRESHOLD) * 100)
                st.markdown(f"**\"__{memo}__\"** – Sponsored **{count}** times ({PRESERVATION_THRESHOLD - count} more needed)")
                st.progress(progress)
        else:
            st.info("All sponsored echoes are either preserved or there are no fleeting echoes.")

st.markdown("---")
st.caption(f"Horizon URL: `{HORIZON_URL}`")
st.caption(f"Network Passphrase: `{NETWORK_PASSPHRASE}`")

# MANDATE 4: STRICTLY use 'st.query_params'
st.sidebar.markdown("---")
st.sidebar.subheader("App State Info")
st.sidebar.write(f"Current Query Params: `{dict(st.query_params)}`")
if "highlight_echo" in st.query_params:
    highlight_message = st.query_params["highlight_echo"]
    st.sidebar.info(f"💡 Query Parameter: Highlighted Echo: **`{highlight_message}`**")
    # A full implementation would now visually highlight the echo matching `highlight_message` in the main content.