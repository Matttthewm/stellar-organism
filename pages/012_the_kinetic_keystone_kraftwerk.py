import streamlit as st
import streamlit.components.v1 as components
import json
import time

# CRITICAL IMPORT RULES (Mandate #7)
import stellar_sdk
from stellar_sdk import Server, Keypair, TransactionBuilder, Network, Asset
from stellar_sdk.exceptions import BadRequestError, NotFoundError

# Configuration
APP_NAME = "The Kinetic Keystone Kraftwerk ⚙️"
APP_CONCEPT = "A decentralized, industrial-themed art engine where users collaborate to construct intricate, self-sustaining Rube Goldberg-esque contraptions by linking asset-based components and triggering chain reactions via sequence manipulations."
HORIZON_URL = "https://horizon-testnet.stellar.org/"
NETWORK_PASSPHRASE = Network.TESTNET_NETWORK_PASSPHRASE
KRAFTWERK_ASSET_CODE = "KWC" # Kinetic Kraftwerk Component

# --- Mandate #11: Secret Key Handling (Issuer Key) ---
# This key will be used to issue KWC tokens.
if "ISSUER_KEY" in st.secrets:
    ISSUER_SECRET_KEY = st.secrets["ISSUER_KEY"]
else:
    if "demo_issuer_key" not in st.session_state:
        st.session_state.demo_issuer_key = Keypair.random().secret
    ISSUER_SECRET_KEY = st.session_state.demo_issuer_key
    st.warning("⚠️ Using Ephemeral Demo Issuer Keys. Restart app to reset.", icon="🛠️")

ISSUER_KEYPAIR = Keypair.from_secret(ISSUER_SECRET_KEY)
ISSUER_PUBLIC_KEY = ISSUER_KEYPAIR.public_key

# --- Mandate #8: Stellar Server Rules ---
server = Server(HORIZON_URL)

# --- Session State Initialization ---
if "freighter_pk" not in st.session_state:
    st.session_state.freighter_pk = None
if "account_details" not in st.session_state:
    st.session_state.account_details = None
if "kraftwerk_components" not in st.session_state:
    st.session_state.kraftwerk_components = {} # {id: {type, connections}}
if "next_component_id" not in st.session_state:
    st.session_state.next_component_id = 1
if "freighter_tx_result" not in st.session_state:
    st.session_state.freighter_tx_result = None

# --- Mandate #3: Custom CSS for style "Industrial/Blueprint" ---
custom_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;700&display=swap');

    :root {
        --primary-background: #001f3f; /* Dark blueprint blue */
        --secondary-background: #003366; /* Slightly lighter blue */
        --text-color: #e0f2f7; /* Light blueprint text */
        --accent-color: #ffaa00; /* Industrial yellow/orange */
        --border-color: #005090; /* Medium blue for borders */
        --warning-color: #ff4500; /* Safety orange for warnings */
        --success-color: #28a745; /* Green for success */
        --font-family: 'Roboto Mono', monospace;
    }

    body {
        background-color: var(--primary-background);
        color: var(--text-color);
        font-family: var(--font-family);
    }

    .stApp {
        background-color: var(--primary-background);
        color: var(--text-color);
        font-family: var(--font-family);
    }

    /* Streamlit components styling */
    .stMarkdown, .stText, .stLabel, .stButton, .stTextInput, .stSelectbox, .stExpander, .stMetric, .stAlert {
        color: var(--text-color);
        font-family: var(--font-family);
    }
    h1, h2, h3, h4, h5, h6 {
        color: var(--accent-color);
    }

    .stButton>button {
        background-color: var(--secondary-background);
        color: var(--text-color);
        border: 1px solid var(--border-color);
        border-radius: 4px;
        padding: 8px 16px;
        transition: all 0.2s ease-in-out;
        box-shadow: 2px 2px 5px rgba(0, 0, 0, 0.4);
    }
    .stButton>button:hover {
        background-color: var(--border-color);
        color: var(--accent-color);
        transform: translateY(-2px);
        box-shadow: 4px 4px 8px rgba(0, 0, 0, 0.6);
    }
    .stButton>button:active {
        background-color: var(--primary-background);
        transform: translateY(0);
        box-shadow: 1px 1px 3px rgba(0, 0, 0, 0.3);
    }

    .stTextInput>div>div>input, .stSelectbox>div>div>select {
        background-color: var(--primary-background);
        color: var(--text-color);
        border: 1px solid var(--border-color);
        border-radius: 4px;
        padding: 8px;
    }
    .stSelectbox>div>div>label { /* Fix for selectbox label color */
        color: var(--text-color);
    }

    .stExpander {
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 10px;
        background-color: var(--secondary-background);
        box-shadow: 3px 3px 7px rgba(0, 0, 0, 0.5);
    }
    .stExpander details summary {
        color: var(--accent-color);
        font-weight: bold;
    }

    .stMetric {
        background-color: var(--secondary-background);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 10px;
        margin-bottom: 10px;
        box-shadow: 2px 2px 5px rgba(0, 0, 0, 0.4);
    }
    .stMetric > div > div:first-child { /* Label */
        color: var(--text-color);
        font-size: 0.9em;
    }
    .stMetric > div > div:last-child { /* Value */
        color: var(--accent-color);
        font-size: 1.8em;
        font-weight: bold;
    }

    .stAlert {
        background-color: var(--secondary-background);
        border-left: 5px solid var(--accent-color);
        color: var(--text-color);
        padding: 10px;
        border-radius: 4px;
    }
    .stAlert.st-warning {
        border-left-color: var(--warning-color);
    }
    .stAlert.st-success {
        border-left-color: var(--success-color);
    }

    .stSpinner > div {
        color: var(--accent-color);
    }

    /* Sidebar specific styles */
    .st-emotion-cache-vk33gh { /* Target the sidebar main div */
        background-color: var(--secondary-background);
        border-right: 1px solid var(--border-color);
        box-shadow: inset -5px 0 10px rgba(0, 0, 0, 0.3);
    }
    .st-emotion-cache-vk33gh .st-emotion-cache-1pxazr7 { /* Target markdown in sidebar */
        color: var(--text-color);
    }
    .st-emotion-cache-vk33gh .stInfo {
        background-color: var(--primary-background);
        border-left: 5px solid var(--accent-color);
        color: var(--text-color);
    }

    /* Badge for visual style */
    .visual-style-badge {
        display: inline-block;
        background-color: var(--accent-color);
        color: var(--primary-background);
        padding: 5px 10px;
        border-radius: 5px;
        font-weight: bold;
        font-size: 0.8em;
        margin-top: 10px;
        box-shadow: 1px 1px 3px rgba(0, 0, 0, 0.3);
    }

    /* Kraftwerk component display */
    .component-card {
        background-color: var(--primary-background);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 10px;
        min-height: 120px; /* Ensure cards have similar height */
        box-shadow: 3px 3px 7px rgba(0, 0, 0, 0.5);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .component-card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
        border-bottom: 1px dashed var(--border-color);
        padding-bottom: 5px;
    }
    .component-card-header h4 {
        margin: 0;
        color: var(--accent-color);
    }
    .component-card-body {
        font-size: 0.9em;
    }
    .component-card-body strong {
        color: var(--text-color);
    }
    .component-card-body span {
        color: var(--text-color);
    }

    .connection-pill {
        display: inline-block;
        background-color: var(--border-color);
        color: var(--text-color);
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 0.75em;
        margin-right: 5px;
        margin-bottom: 5px;
        border: 1px solid var(--accent-color);
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# --- Mandate #1 & #9: Freighter Integration (st.components.v1.html) ---
# JavaScript to connect to Freighter and return public key / sign transaction
# This JS uses `window.location.reload()` after updating query parameters
# to trigger a Streamlit rerun, which is how Streamlit processes query params.
FREIGHTER_JS_QP = """
<script>
    async function updateQueryParam(key, value) {
        const url = new URL(window.location);
        url.searchParams.set(key, value);
        window.history.pushState({}, '', url);
        // Force Streamlit to re-run by reloading the page with new query params
        window.location.reload(); 
    }

    async function removeQueryParam(key) {
        const url = new URL(window.location);
        url.searchParams.delete(key);
        window.history.pushState({}, '', url);
        window.location.reload();
    }

    async function connectFreighter() {
        try {
            if (!window.freighter) {
                await updateQueryParam('freighterError', 'Freighter extension not found!');
                return;
            }
            const publicKey = await window.freighter.getPublicKey();
            await updateQueryParam('publicKey', publicKey);
        } catch (error) {
            await updateQueryParam('freighterError', error.message || 'Failed to connect to Freighter.');
        }
    }

    async function signAndSubmitTransaction(xdr, networkPassphrase) {
        try {
            if (!window.freighter) {
                await updateQueryParam('freighterError', 'Freighter extension not found for signing!');
                return;
            }
            const signedXDR = await window.freighter.signTransaction(xdr, { networkPassphrase });
            await updateQueryParam('signedXDR', signedXDR);
        } catch (error) {
            await updateQueryParam('freighterError', error.message || 'Failed to sign transaction.');
        }
    }

    // Listen for messages from Streamlit to trigger functions
    window.addEventListener('message', async event => {
        if (event.data === 'connectFreighter') {
            await connectFreighter();
        } else if (event.data && typeof event.data === 'string' && event.data.startsWith('signTransaction:')) {
            const payload = JSON.parse(event.data.substring('signTransaction:'.length));
            await signAndSubmitTransaction(payload.xdr, payload.networkPassphrase);
        }
    });
</script>
"""
# Mandate #9: ALWAYS call components.html(...)
components.html(FREIGHTER_JS_QP, height=0, width=0)

# --- Utility Functions ---
def send_message_to_freighter_js(message):
    # This embeds a script that posts a message to the parent window (which contains the Freighter JS)
    components.html(
        f"""
        <script>
            window.parent.postMessage('{message}', '*');
        </script>
        """,
        height=0, width=0
    )

def fetch_account_details(public_key):
    try:
        account = server.load_account(public_key)
        st.session_state.account_details = account
        return account
    except NotFoundError:
        st.session_state.account_details = None
        return None
    except Exception as e:
        st.error(f"⚠️ Error fetching account details: {e}", icon="⛔")
        st.session_state.account_details = None
        return None

def fund_account(public_key):
    try:
        response = server.friendbot(public_key).call()
        st.success(f"🤖 Account funded by Friendbot!", icon="✅")
        time.sleep(2) # Give Horizon time to update
        fetch_account_details(public_key) # Refresh account details
    except BadRequestError as e:
        st.error(f"❌ Failed to fund account: {e.extras.get('result_codes', {}).get('operations', ['Unknown Error'])[0]}", icon="⛔")
    except Exception as e:
        st.error(f"❌ An unexpected error occurred during funding: {e}", icon="⛔")

def submit_xdr_to_stellar(xdr):
    try:
        with st.spinner("⏳ Submitting transaction to Stellar network..."):
            response = server.submit_transaction(xdr)
        st.success(f"✅ Transaction submitted successfully! Hash: `{response['hash'][:10]}...`", icon="🎉")
        st.balloons()
        return True
    except BadRequestError as e:
        st.error(f"❌ Transaction submission failed (Bad Request): {e.extras.get('result_codes', {}).get('operations', ['Unknown Error'])[0]}", icon="⛔")
        return False
    except Exception as e:
        st.error(f"❌ An unexpected error occurred during transaction submission: {e}", icon="⛔")
        return False

def build_and_sign_xdr_with_freighter(source_public_key, operations, memo=None):
    try:
        account = server.load_account(source_public_key)
        builder = TransactionBuilder(
            source_account=account,
            network_passphrase=NETWORK_PASSPHRASE,
            base_fee=stellar_sdk.helpers.get_base_fee(server)
        )
        for op in operations:
            builder.add_operation(op)
        if memo:
            builder.add_memo(memo)
        transaction = builder.build()
        xdr = transaction.to_xdr()

        st.session_state.freighter_tx_result = None # Clear previous result
        # Special format for JS listener: action:payload
        payload_str = json.dumps({
            'xdr': xdr,
            'networkPassphrase': NETWORK_PASSPHRASE
        }, separators=(',', ':'))
        send_message_to_freighter_js(f"signTransaction:{payload_str}")
        st.info("Awaiting Freighter signature... please confirm in your wallet.", icon="⏳")
    except NotFoundError:
        st.error(f"Account `{source_public_key[:8]}...` not found. Please fund it.", icon="⛔")
    except Exception as e:
        st.error(f"Error building transaction: {e}", icon="⛔")

# --- Mandate #4: Process Query Parameters (st.query_params) ---
query_params = st.query_params

if "publicKey" in query_params:
    st.session_state.freighter_pk = query_params["publicKey"]
    st.query_params.clear() # Clear to prevent re-processing on refresh
    st.rerun()

if "signedXDR" in query_params:
    st.session_state.freighter_tx_result = {"status": "signed", "xdr": query_params["signedXDR"]}
    st.query_params.clear()
    st.rerun()

if "freighterError" in query_params:
    st.session_state.freighter_tx_result = {"status": "error", "message": query_params["freighterError"]}
    st.query_params.clear()
    st.rerun()

# Handle Freighter response after signing
if st.session_state.freighter_tx_result:
    if st.session_state.freighter_tx_result["status"] == "signed":
        signed_xdr = st.session_state.freighter_tx_result["xdr"]
        if submit_xdr_to_stellar(signed_xdr):
            # If successful, refresh account details and state relevant to the transaction
            fetch_account_details(st.session_state.freighter_pk)
            # Re-fetch components if a component was sent/received
            st.session_state.freighter_tx_result = None # Clear result
            st.rerun()
    elif st.session_state.freighter_tx_result["status"] == "error":
        st.error(f"❌ Freighter signing failed: {st.session_state.freighter_tx_result['message']}", icon="⛔")
        st.session_state.freighter_tx_result = None # Clear result

# --- Main App ---

st.title(APP_NAME)
st.markdown("### Decentralized Rube Goldberg Art Engine")

# --- Mandate #10: Sidebar Content ---
with st.sidebar:
    st.info(f"""
    **APP NAME:** {APP_NAME}
    **CONCEPT:** {APP_CONCEPT}
    """)
    st.markdown('<div class="visual-style-badge">Visual Style: Industrial/Blueprint 🎨</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.header("Connection 🔌")

    if st.session_state.freighter_pk:
        st.success(f"✅ Connected to Freighter!", icon="🔗")
        st.caption(f"**Public Key:** `{st.session_state.freighter_pk[:8]}...{st.session_state.freighter_pk[-8:]}`")
        if st.button("Disconnect Freighter 🔒"):
            st.session_state.freighter_pk = None
            st.session_state.account_details = None
            st.session_state.freighter_tx_result = None
            st.rerun()
    else:
        st.warning("⚠️ Not connected to Freighter.", icon="🚫")
        if st.button("Connect to Freighter 🔗"):
            # Trigger JS to connect
            send_message_to_freighter_js("connectFreighter")
            st.info("Awaiting Freighter connection... please approve in your wallet.", icon="⏳")

    st.markdown("---")
    st.header("Your Kraftwerk Account 🏦")

    if st.session_state.freighter_pk:
        if st.session_state.account_details is None:
            st.info("Fetching account details...", icon="🔍")
            fetch_account_details(st.session_state.freighter_pk)
            st.rerun()
        else:
            xlm_balance = 0.0
            kwc_balance = 0.0
            has_trustline = False

            for balance in st.session_state.account_details.balances:
                if balance.asset_type == "native":
                    xlm_balance = float(balance.balance)
                elif balance.asset_code == KRAFTWERK_ASSET_CODE and balance.asset_issuer == ISSUER_PUBLIC_KEY:
                    kwc_balance = float(balance.balance)
                    has_trustline = True

            st.metric(label="XLM Balance", value=f"{xlm_balance:.2f} XLM 💰")
            st.metric(label="KWC Components", value=f"{kwc_balance:.0f} KWC ⚙️")

            if xlm_balance < 1.0: # Check for minimal balance to ensure account is active
                st.warning("Your account needs XLM to operate. Fund it with Friendbot.", icon="💸")
                if st.button("Fund Account with Friendbot 🤖"):
                    fund_account(st.session_state.freighter_pk)
                    st.rerun()
            elif not has_trustline:
                st.warning(f"You need a trustline for {KRAFTWERK_ASSET_CODE} to receive components.", icon="🤝")
                if st.button(f"Create Trustline for {KRAFTWERK_ASSET_CODE} 🤝"):
                    asset = Asset(KRAFTWERK_ASSET_CODE, ISSUER_PUBLIC_KEY)
                    # Mandate #8: Access operations via module
                    change_trust_op = stellar_sdk.ChangeTrust(asset=asset, limit="100000000000") # Large limit
                    build_and_sign_xdr_with_freighter(st.session_state.freighter_pk, [change_trust_op])
                    st.rerun()
            st.caption(f"Issuer: `{ISSUER_PUBLIC_KEY[:8]}...{ISSUER_PUBLIC_KEY[-8:]}`")
    else:
        st.info("Connect Freighter to see account details.", icon="❓")

st.markdown("---")

st.header("🔩 Kraftwerk Component Forge")
st.write("Acquire new components to expand your contraption.")

if st.session_state.freighter_pk and st.session_state.account_details:
    # Check if trustline exists
    kwc_trustline_exists = False
    for balance in st.session_state.account_details.balances:
        if balance.asset_code == KRAFTWERK_ASSET_CODE and balance.asset_issuer == ISSUER_PUBLIC_KEY:
            kwc_trustline_exists = True
            break

    if not kwc_trustline_exists:
        st.warning(f"You must establish a trustline for `{KRAFTWERK_ASSET_CODE}` in the sidebar before forging components.", icon="🚫")
    else:
        col1, col2 = st.columns(2)
        with col1:
            component_type = st.selectbox(
                "Select Component Type 🛠️",
                options=["SPRING", "LEVER", "GEAR", "PULLEY", "ACTUATOR"],
                help="Each component type has a unique role in the chain reaction."
            )
        with col2:
            num_components = st.number_input(
                "Quantity to Forge", min_value=1, max_value=10, value=1, step=1,
                help="Mint multiple components at once."
            )

        if st.button(f"Forge {num_components} {component_type}(s) ✨"):
            asset = Asset(KRAFTWERK_ASSET_CODE, ISSUER_PUBLIC_KEY)
            operations = []
            for _ in range(num_components):
                # Mandate #8: Access operations via module
                operations.append(stellar_sdk.Payment(
                    destination=st.session_state.freighter_pk,
                    asset=asset,
                    amount="1" # Each KWC represents one component
                ))
            
            # Sign with Issuer Keypair (as issuer is sending payment)
            # This is a transaction signed by the *issuer*, not the user via Freighter.
            try:
                issuer_account = server.load_account(ISSUER_PUBLIC_KEY)
                tx_builder = TransactionBuilder(
                    source_account=issuer_account,
                    network_passphrase=NETWORK_PASSPHRASE,
                    base_fee=stellar_sdk.helpers.get_base_fee(server)
                )
                for op in operations:
                    tx_builder.add_operation(op)
                tx_builder.add_memo(stellar_sdk.MemoText(f"Forge {num_components} {component_type}(s) for {st.session_state.freighter_pk[:8]}..."))
                transaction = tx_builder.build()
                transaction.sign(ISSUER_KEYPAIR)
                
                with st.spinner(f"Forging {num_components} {component_type}(s)..."):
                    response = server.submit_transaction(transaction)
                st.success(f"✅ Components forged! Tx Hash: `{response['hash'][:10]}...`", icon="🎉")
                
                # Update user's local components and refresh balances
                for _ in range(num_components):
                    component_id = f"KWC-{st.session_state.next_component_id:04d}" # Pad with leading zeros
                    st.session_state.kraftwerk_components[component_id] = {
                        "type": component_type,
                        "connections": []
                    }
                    st.session_state.next_component_id += 1
                fetch_account_details(st.session_state.freighter_pk)
                st.rerun()

            except BadRequestError as e:
                st.error(f"❌ Forging failed: {e.extras.get('result_codes', {}).get('operations', ['Unknown Error'])[0]}", icon="⛔")
            except Exception as e:
                st.error(f"❌ An unexpected error occurred during forging: {e}", icon="⛔")

else:
    st.info("Connect your Freighter wallet and ensure your account has a trustline to forge components.", icon="❓")

st.markdown("---")

st.header("🏗️ Your Kraftwerk Assembly Line")
st.write("Arrange and link your components to build intricate contraptions.")

if st.session_state.kraftwerk_components:
    sorted_components = sorted(st.session_state.kraftwerk_components.items(), key=lambda item: item[0])
    num_cols = 3 # Mandate #6: Use st.columns
    cols = st.columns(num_cols)
    col_idx = 0

    st.markdown("### Existing Components")
    for comp_id, comp_data in sorted_components:
        with cols[col_idx]:
            st.markdown(f"""
            <div class="component-card">
                <div class="component-card-header">
                    <h4>{comp_data['type']}</h4>
                    <span>ID: {comp_id}</span>
                </div>
                <div class="component-card-body">
                    <strong>Connections:</strong> {', '.join([f'<span class="connection-pill">{c}</span>' for c in comp_data['connections']]) if comp_data['connections'] else 'None'}
                </div>
            </div>
            """, unsafe_allow_html=True)
        col_idx = (col_idx + 1) % num_cols

    st.markdown("### Link Components 🔗")
    # Mandate #6: Use st.expander
    with st.expander("Configure Component Linkages"):
        available_components = list(st.session_state.kraftwerk_components.keys())
        if len(available_components) >= 2:
            source_comp = st.selectbox("Select Source Component", available_components, key="link_source")
            
            # Filter target components to not include the source and not already linked
            target_options = [c for c in available_components if c != source_comp]
            
            if source_comp:
                current_connections = st.session_state.kraftwerk_components[source_comp]["connections"]
                target_options = [c for c in target_options if c not in current_connections]
                
            target_comp = st.selectbox("Select Target Component", target_options, key="link_target")

            if source_comp and target_comp:
                if st.button(f"Link {source_comp} to {target_comp} ➡️"):
                    st.session_state.kraftwerk_components[source_comp]["connections"].append(target_comp)
                    st.success(f"🔗 Linked {source_comp} to {target_comp}!", icon="✅")
                    st.rerun()
            elif source_comp and not target_comp:
                st.info("No available components to link, or all are already linked from the source.", icon="ℹ️")
            else:
                st.info("Select at least two distinct components to link.", icon="ℹ️")
        else:
            st.info("You need at least two components to link them.", icon="ℹ️")

    st.markdown("### Trigger Reaction Sequence 💥")
    if st.session_state.kraftwerk_components:
        start_component_options = [c for c, data in st.session_state.kraftwerk_components.items() if data['type'] == 'SPRING']
        if not start_component_options:
            st.warning("You need at least one 'SPRING' component to start a reaction sequence.", icon="⚠️")
        else:
            start_node = st.selectbox("Select Starting Component to Trigger", start_component_options, key="trigger_start_node")
            if st.button(f"Initiate Kinetic Reaction from {start_node} ▶️"):
                st.write(f"Initiating sequence from **{start_node}**...")
                reaction_log = []
                visited = set()
                queue = [(start_node, 0)] # (component_id, depth)

                # Mandate #6: Use st.expander
                with st.expander("Live Reaction Log"):
                    while queue:
                        current_comp_id, depth = queue.pop(0)
                        if current_comp_id in visited:
                            continue

                        visited.add(current_comp_id)
                        comp_data = st.session_state.kraftwerk_components.get(current_comp_id)
                        if comp_data:
                            log_message = f"({'⚡' * (depth + 1)}) {current_comp_id} ({comp_data['type']}) activates!"
                            reaction_log.append(log_message)
                            st.text(log_message)
                            time.sleep(0.1) # Simulate delay
                            
                            for connected_comp_id in comp_data["connections"]:
                                if connected_comp_id in st.session_state.kraftwerk_components and connected_comp_id not in visited:
                                    queue.append((connected_comp_id, depth + 1))
                        else:
                            log_message = f"({'❌' * (depth + 1)}) Unknown component: {current_comp_id}. Chain breaks!"
                            reaction_log.append(log_message)
                            st.text(log_message)
                            break # Chain breaks if component not found

                st.success("🎉 Kinetic reaction complete!", icon="✅")
    else:
        st.info("Forge some components first to start building your Kraftwerk!", icon="❓")

else:
    st.info("No components forged yet. Head to the 'Kraftwerk Component Forge' to get started!", icon="❓")