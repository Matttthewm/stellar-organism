import streamlit as st
import streamlit.components.v1 as components
import stellar_sdk
from stellar_sdk import Server, Keypair, TransactionBuilder, Network, Asset
from stellar_sdk.exceptions import BadRequestError, NotFoundError
import time
import json
import base64

# --- 0. Constants and Initial Setup ---
APP_NAME = "The Mycelial Bloom 🍄🌱"
HORIZON_URL = "https://horizon-testnet.stellar.org" # Using Testnet for demo purposes
NETWORK_PASSPHRASE = Network.TESTNET_NETWORK_PASSPHRASE
SPORE_ASSET_CODE = "SPOR" # Max 12 chars for asset code
XLM_TO_SPORE_RATE = 100 # 1 XLM = 100 SPORs

server = Server(HORIZON_URL)

# --- 1. Custom Organic/Nature-Inspired CSS ---
custom_css = """
<style>
    :root {
        --primary-color: #4CAF50; /* A vibrant green */
        --background-color: #F8F5EE; /* Light cream/beige */
        --secondary-background-color: #E6EAD0; /* Soft green-yellow */
        --text-color: #2F4F4F; /* Dark slate grey */
        --font-family: 'Georgia', serif, 'Palatino Linotype', 'Book Antiqua';
        --border-radius: 12px;
        --box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    }

    body {
        font-family: var(--font-family);
        color: var(--text-color);
        background-color: var(--background-color);
    }

    .stApp {
        background-color: var(--background-color);
    }

    /* Main container and block styling */
    .stApp > header {
        background-color: transparent;
    }
    .stApp > div:first-child { /* Main content area */
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    /* Titles and Headers */
    h1, h2, h3, h4, h5, h6 {
        color: var(--primary-color);
        font-family: var(--font-family);
    }
    h1 {
        font-size: 2.5em;
        text-align: center;
        margin-bottom: 1.5em;
    }
    .stExpander {
        border-radius: var(--border-radius);
        box-shadow: var(--box-shadow);
        background-color: white; /* Card-like background */
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .stExpander > div > div > div > button { /* Expander header button */
        color: var(--primary-color) !important;
        font-weight: bold;
    }

    /* Buttons */
    .stButton > button {
        background-color: var(--primary-color);
        color: white;
        border-radius: var(--border-radius);
        border: none;
        padding: 0.75rem 1.5rem;
        font-weight: bold;
        transition: all 0.2s ease-in-out;
        box-shadow: var(--box-shadow);
    }
    .stButton > button:hover {
        background-color: #36853C; /* Darker green */
        transform: translateY(-2px);
    }

    /* Text Inputs */
    .stTextInput > div > div > input {
        border-radius: var(--border-radius);
        border: 1px solid #CED4DA;
        padding: 0.5rem 1rem;
        background-color: white;
        color: var(--text-color);
    }
    .stTextInput > div > div > input:focus {
        border-color: var(--primary-color);
        box-shadow: 0 0 0 0.2rem rgba(76, 175, 80, 0.25);
    }

    /* Sidebar Styling */
    .css-1d391kg { /* Target for sidebar container */
        background-color: var(--secondary-background-color) !important;
        border-right: 1px solid rgba(0,0,0,0.05);
        border-radius: 0 var(--border-radius) var(--border-radius) 0;
    }
    .sidebar .sidebar-content {
        background-color: var(--secondary-background-color);
    }

    /* Info boxes, warnings */
    .stAlert {
        border-radius: var(--border-radius);
    }
    .stInfo {
        background-color: #e0f2f1; /* Light teal */
        color: #00796B; /* Dark teal */
        border-left: 5px solid #00796B;
    }
    .stWarning {
        background-color: #fffde7; /* Light yellow */
        color: #ffb300; /* Amber */
        border-left: 5px solid #ffb300;
    }
    .stSuccess {
        background-color: #e8f5e9; /* Light green */
        color: #388e3c; /* Dark green */
        border-left: 5px solid #388e3c;
    }

    /* Metrics */
    [data-testid="stMetric"] {
        background-color: white;
        border-radius: var(--border-radius);
        box-shadow: var(--box-shadow);
        padding: 1rem;
        margin-bottom: 1rem;
    }
    [data-testid="stMetricLabel"] {
        color: var(--primary-color);
        font-weight: bold;
    }
    [data-testid="stMetricValue"] {
        color: var(--text-color);
        font-size: 2.5em;
    }
    [data-testid="stMetricDelta"] {
        color: #6A7B76; /* Muted green-grey */
    }

    /* Selectbox */
    .stSelectbox > div > div > div {
        border-radius: var(--border-radius);
        border: 1px solid #CED4DA;
        background-color: white;
    }
    .stSelectbox > label {
        color: var(--text-color);
        font-weight: bold;
    }

    /* General containers */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }

</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# --- 2. Session State Initialization ---
if "public_key" not in st.session_state:
    st.session_state.public_key = None
if "balances" not in st.session_state:
    st.session_state.balances = {"XLM": 0, SPORE_ASSET_CODE: 0}
if "cultivated_networks" not in st.session_state:
    st.session_state.cultivated_networks = []
if "tx_in_progress" not in st.session_state:
    st.session_state.tx_in_progress = False
if "latest_tx_hash" not in st.session_state:
    st.session_state.latest_tx_hash = None
if "transaction_type" not in st.session_state:
    st.session_state.transaction_type = None

# --- 3. Secret Key Handling (Mandate 11) ---
ISSUER_KEY: Keypair
if "ISSUER_KEY" in st.secrets:
    ISSUER_KEY = Keypair.from_secret(st.secrets["ISSUER_KEY"])
else:
    if "demo_issuer_key" not in st.session_state:
        st.session_state.demo_issuer_key = Keypair.random().secret
    ISSUER_KEY = Keypair.from_secret(st.session_state.demo_issuer_key)
    st.warning("Using Ephemeral Demo Keys for App's Issuer. Transactions requiring the issuer's signature will use this key. Your demo session will reset if you close the browser.")

ISSUER_PUBLIC_KEY = ISSUER_KEY.public_key
SPORE_ASSET = Asset(SPORE_ASSET_CODE, ISSUER_PUBLIC_KEY)


# --- 4. Helper Functions ---
def fetch_account_details(public_key: str):
    """Fetches account details and updates session state balances."""
    if not public_key:
        st.session_state.balances = {"XLM": 0, SPORE_ASSET_CODE: 0}
        return

    try:
        account = server.load_account(public_key)
        xlm_balance = 0
        spore_balance = 0
        for balance in account.balances:
            if balance.asset_type == "native":
                xlm_balance = float(balance.balance)
            elif balance.asset_code == SPORE_ASSET_CODE and balance.asset_issuer == ISSUER_PUBLIC_KEY:
                spore_balance = float(balance.balance)
        st.session_state.balances = {"XLM": xlm_balance, SPORE_ASSET_CODE: spore_balance}
    except NotFoundError:
        st.session_state.balances = {"XLM": 0, SPORE_ASSET_CODE: 0}
    except Exception as e:
        st.error(f"Error fetching account details: {e}")
        st.session_state.balances = {"XLM": 0, SPORE_ASSET_CODE: 0}

def clear_query_params():
    """Clears transaction-related query parameters."""
    for param in ["signed_xdr", "freighter_error", "tx_type"]:
        if param in st.query_params:
            del st.query_params[param]

def submit_signed_transaction(signed_xdr: str):
    """Submits a signed XDR to the Stellar network."""
    try:
        response = server.submit_transaction(signed_xdr)
        st.session_state.latest_tx_hash = response["hash"]
        st.success(f"Transaction submitted successfully! Hash: {st.session_state.latest_tx_hash}")
        st.session_state.tx_in_progress = False
        fetch_account_details(st.session_state.public_key)
        st.rerun() # Rerun to clear query params and update UI
    except BadRequestError as e:
        error_msg = e.response.text
        st.error(f"Transaction submission failed (Horizon): {error_msg}")
        st.session_state.tx_in_progress = False
        st.session_state.latest_tx_hash = None
    except Exception as e:
        st.error(f"An unexpected error occurred during submission: {e}")
        st.session_state.tx_in_progress = False
        st.session_state.latest_tx_hash = None


# --- 5. Freighter Integration (HTML Component) ---
FREIGHTER_JS = f"""
<script>
    async function connectFreighter() {{
        const currentUrl = new URL(window.location.href);
        try {{
            if (!window.freighter) {{
                currentUrl.searchParams.set("freighter_error", "Freighter not detected. Please install and connect.");
                window.location.href = currentUrl.toString();
                return;
            }}
            const publicKey = await window.freighter.getPublicKey();
            currentUrl.searchParams.set("public_key", publicKey);
            currentUrl.searchParams.delete("freighter_error");
        }} catch (error) {{
            currentUrl.searchParams.set("freighter_error", error.message || "Failed to connect Freighter.");
            currentUrl.searchParams.delete("public_key");
        }}
        window.location.href = currentUrl.toString();
    }}

    async function signAndSubmit(xdr, transactionType) {{
        const currentUrl = new URL(window.location.href);
        try {{
            if (!window.freighter) {{
                currentUrl.searchParams.set("freighter_error", "Freighter not detected. Please install and connect.");
                currentUrl.searchParams.set("tx_type", transactionType);
                window.location.href = currentUrl.toString();
                return;
            }}
            const signedXDR = await window.freighter.signTransaction(xdr, "{NETWORK_PASSPHRASE}");
            currentUrl.searchParams.set("signed_xdr", signedXDR);
            currentUrl.searchParams.set("tx_type", transactionType);
            currentUrl.searchParams.delete("freighter_error");
        }} catch (error) {{
            currentUrl.searchParams.set("freighter_error", error.message || "An unknown error occurred with Freighter.");
            currentUrl.searchParams.set("tx_type", transactionType);
            currentUrl.searchParams.delete("signed_xdr");
        }}
        window.location.href = currentUrl.toString();
    }}
</script>
"""

# Render the Freighter JS in a hidden component, or trigger actions based on buttons
components.html(FREIGHTER_JS, height=0, width=0)

# --- 6. Query Params Handling (Mandate 4) ---
# Check for incoming data from Freighter (after redirect)
if "public_key" in st.query_params and not st.session_state.public_key:
    st.session_state.public_key = st.query_params["public_key"]
    st.success(f"Connected with Freighter: {st.session_state.public_key[:8]}...")
    fetch_account_details(st.session_state.public_key)
    clear_query_params()
    st.rerun()
elif "freighter_error" in st.query_params:
    st.error(f"Freighter Error: {st.query_params['freighter_error']}")
    st.session_state.tx_in_progress = False
    clear_query_params()
    st.rerun()
elif "signed_xdr" in st.query_params and st.session_state.tx_in_progress:
    st.session_state.tx_in_progress = False # Mark as no longer in progress after receiving XDR
    signed_xdr = st.query_params["signed_xdr"]
    submit_signed_transaction(signed_xdr) # This will rerender and clear query params


# --- 7. Sidebar (Mandate 10) ---
with st.sidebar:
    st.info(f"### {APP_NAME}\n"
            f"**Concept:** A decentralized ecosystem where users cultivate unique digital mycelial networks, "
            f"sponsoring their growth to generate tradable 'spores' (assets) and participating in a "
            f"self-sustaining cycle of network expansion and resource decomposition.")
    st.caption("✨ Visual Style: Organic/Nature-Inspired")

    st.markdown("---")
    st.subheader("Freighter Connection")
    if st.session_state.public_key:
        st.success(f"Connected: `{st.session_state.public_key[:10]}...`")
        st.button("Disconnect", on_click=lambda: st.session_state.update(public_key=None, balances={"XLM":0, SPORE_ASSET_CODE:0}), key="disconnect_freighter")
    else:
        st.button("Connect with Freighter 🚀", on_click=lambda: components.html("<script>connectFreighter();</script>", height=0, width=0), key="connect_freighter")
    st.markdown("---")

    if st.session_state.public_key:
        st.subheader("Your Balances")
        st.metric(label="XLM Balance", value=f"{st.session_state.balances['XLM']:.2f} XLM 🌟")
        st.metric(label=f"{SPORE_ASSET_CODE} Balance", value=f"{st.session_state.balances[SPORE_ASSET_CODE]:.2f} {SPORE_ASSET_CODE} 🧬")
        st.markdown("---")
        st.subheader("App Issuer Details")
        st.write(f"Issuer Public Key: `{ISSUER_PUBLIC_KEY[:10]}...`")
        st.write(f"Asset Code: `{SPORE_ASSET_CODE}`")

    st.markdown("---")
    if st.session_state.latest_tx_hash:
        st.info(f"Latest Transaction: [{st.session_state.latest_tx_hash[:10]}...](https://testnet.stellar.expert/tx/{st.session_state.latest_tx_hash})")


# --- 8. Main App Logic ---
st.title(APP_NAME)
st.write("---")

if not st.session_state.public_key:
    st.info("👆 Please connect your Freighter wallet in the sidebar to begin.")
else:
    # --- Check for Trustline ---
    has_spore_trustline = False
    for balance in server.load_account(st.session_state.public_key).balances:
        if balance.asset_code == SPORE_ASSET_CODE and balance.asset_issuer == ISSUER_PUBLIC_KEY and balance.asset_type != "native":
            has_spore_trustline = True
            break

    if not has_spore_trustline:
        st.warning(f"You need to establish a trustline for the `{SPORE_ASSET_CODE}` asset to cultivate networks and receive spores.")
        if st.button(f"Establish Trustline for {SPORE_ASSET_CODE} 🤝"):
            if not st.session_state.tx_in_progress:
                try:
                    source_account = server.load_account(st.session_state.public_key)
                    transaction = (
                        TransactionBuilder(
                            source_account=source_account,
                            network_passphrase=NETWORK_PASSPHRASE,
                        )
                        .add_operation(stellar_sdk.ChangeTrust(asset=SPORE_ASSET, limit="9223372036854775807"))
                        .set_timeout(100)
                        .build()
                    )
                    xdr = transaction.to_xdr()
                    st.session_state.tx_in_progress = True
                    st.session_state.transaction_type = "change_trust"
                    components.html(f"<script>signAndSubmit('{xdr}', '{st.session_state.transaction_type}');</script>", height=0, width=0)
                    st.info("Awaiting Freighter signature for trustline...")
                except Exception as e:
                    st.error(f"Error building trustline transaction: {e}")
                    st.session_state.tx_in_progress = False
            else:
                st.info("A transaction is already in progress. Please wait.")
        st.markdown("---")


    # --- Mycelial Network Overview ---
    st.subheader("Mycelial Network Overview 🌍")
    col1, col2 = st.columns(2)
    col1.metric(label="Total Cultivated Networks", value=len(st.session_state.cultivated_networks))
    col2.metric(label=f"Total {SPORE_ASSET_CODE} in Wallet", value=f"{st.session_state.balances[SPORE_ASSET_CODE]:.2f}")
    st.write("---")

    # --- Cultivate New Network ---
    with st.expander("🌱 Cultivate a New Mycelial Network"):
        network_name = st.text_input("Name your new network (e.g., 'Forest Whisper', 'Deep Roots')", max_chars=50)
        if st.button("Cultivate Network", key="cultivate_btn"):
            if network_name:
                if network_name in st.session_state.cultivated_networks:
                    st.warning("You already have a network with this name.")
                else:
                    st.session_state.cultivated_networks.append(network_name)
                    st.success(f"Network '{network_name}' cultivated! Now you can sponsor its growth to generate {SPORE_ASSET_CODE}s.")
                    st.rerun()
            else:
                st.error("Please provide a name for your network.")
    st.write("---")

    # --- Sponsor Growth & Generate Spores ---
    with st.expander("💧 Sponsor Network Growth & Generate Spores"):
        if not st.session_state.cultivated_networks:
            st.info("Cultivate a network first to sponsor its growth!")
        else:
            selected_network = st.selectbox("Select a network to sponsor:", st.session_state.cultivated_networks, key="select_sponsor_network")
            xlm_amount = st.number_input(f"XLM amount to sponsor (1 XLM = {XLM_TO_SPORE_RATE} {SPORE_ASSET_CODE})", min_value=1.0, value=10.0, step=1.0, key="sponsor_amount")
            
            if xlm_amount > 0:
                potential_spores = xlm_amount * XLM_TO_SPORE_RATE
                st.info(f"Sponsoring with {xlm_amount} XLM will conceptually generate {potential_spores:.2f} {SPORE_ASSET_CODE} for you.")
            
            if st.button(f"Sponsor {selected_network or 'Network'} Growth", key="sponsor_btn"):
                if not st.session_state.tx_in_progress:
                    if st.session_state.balances["XLM"] < xlm_amount + 0.5: # +0.5 for tx fees
                        st.error("Insufficient XLM balance to cover the sponsorship and transaction fees.")
                    elif not has_spore_trustline:
                        st.error(f"You need a trustline for {SPORE_ASSET_CODE} to receive spores (even conceptually). Please establish it first.")
                    else:
                        try:
                            source_account = server.load_account(st.session_state.public_key)
                            transaction = (
                                TransactionBuilder(
                                    source_account=source_account,
                                    network_passphrase=NETWORK_PASSPHRASE,
                                )
                                .add_operation(
                                    stellar_sdk.Payment(
                                        destination=ISSUER_PUBLIC_KEY, # Payment to the app's issuer for sponsorship
                                        asset=Asset.native(),
                                        amount=str(xlm_amount),
                                    )
                                )
                                .set_timeout(100)
                                .build()
                            )
                            xdr = transaction.to_xdr()
                            st.session_state.tx_in_progress = True
                            st.session_state.transaction_type = "sponsor_payment"
                            components.html(f"<script>signAndSubmit('{xdr}', '{st.session_state.transaction_type}');</script>", height=0, width=0)
                            st.info("Awaiting Freighter signature for sponsorship payment...")
                            # In a real dApp, the ISSUER_KEY (server-side) would now send SPOREs back.
                            # For this demo, we assume the SPOREs are earned and available.
                        except Exception as e:
                            st.error(f"Error building sponsorship transaction: {e}")
                            st.session_state.tx_in_progress = False
                else:
                    st.info("A transaction is already in progress. Please wait.")
    st.write("---")

    # --- Harvest Spores (Send SPOREs to another account) ---
    with st.expander("🌰 Harvest & Transfer Spores"):
        if st.session_state.balances[SPORE_ASSET_CODE] == 0:
            st.info(f"You need to have {SPORE_ASSET_CODE} balance to harvest (transfer).")
            st.warning("To enable 'Harvest' functionality for testing, use the 'Get Demo Spores' button below 👇")

        recipient_pk = st.text_input("Recipient Public Key", key="recipient_pk")
        spore_amount_to_send = st.number_input(f"Amount of {SPORE_ASSET_CODE} to send", min_value=0.01, value=1.0, step=0.01, key="send_spore_amount")

        if st.button(f"Transfer {SPORE_ASSET_CODE}s", key="transfer_spore_btn"):
            if not st.session_state.tx_in_progress:
                try:
                    # Validate recipient public key
                    Keypair.from_public_key(recipient_pk)
                except ValueError:
                    st.error("Invalid Stellar recipient public key.")
                    st.stop()

                if st.session_state.balances[SPORE_ASSET_CODE] < spore_amount_to_send:
                    st.error(f"Insufficient {SPORE_ASSET_CODE} balance.")
                else:
                    try:
                        source_account = server.load_account(st.session_state.public_key)
                        transaction = (
                            TransactionBuilder(
                                source_account=source_account,
                                network_passphrase=NETWORK_PASSPHRASE,
                            )
                            .add_operation(
                                stellar_sdk.Payment(
                                    destination=recipient_pk,
                                    asset=SPORE_ASSET,
                                    amount=str(spore_amount_to_send),
                                )
                            )
                            .set_timeout(100)
                            .build()
                        )
                        xdr = transaction.to_xdr()
                        st.session_state.tx_in_progress = True
                        st.session_state.transaction_type = "spore_payment"
                        components.html(f"<script>signAndSubmit('{xdr}', '{st.session_state.transaction_type}');</script>", height=0, width=0)
                        st.info(f"Awaiting Freighter signature to transfer {spore_amount_to_send} {SPORE_ASSET_CODE}...")
                    except Exception as e:
                        st.error(f"Error building {SPORE_ASSET_CODE} transfer transaction: {e}")
                        st.session_state.tx_in_progress = False
            else:
                st.info("A transaction is already in progress. Please wait.")
    st.write("---")

    # --- Get Demo Spores (for testing Harvest functionality) ---
    with st.expander("🧪 Developer / Demo Tools"):
        st.info(f"This section allows the app's Issuer Key to send demo {SPORE_ASSET_CODE} to your connected account for testing purposes. "
                f"**This transaction is signed by the App's Issuer Key, not your Freighter wallet.**")
        demo_spore_amount = st.number_input(f"Amount of demo {SPORE_ASSET_CODE} to receive", min_value=1.0, value=100.0, step=1.0, key="demo_spore_amount")

        if st.button(f"Get {demo_spore_amount} Demo {SPORE_ASSET_CODE} from Issuer", key="get_demo_spore_btn"):
            if not has_spore_trustline:
                st.error(f"You need a trustline for {SPORE_ASSET_CODE} to receive spores. Please establish it first.")
            else:
                try:
                    # Fund issuer if necessary (only for ephemeral demo key)
                    if "demo_issuer_key" in st.session_state:
                        try:
                            server.load_account(ISSUER_PUBLIC_KEY)
                        except NotFoundError:
                            st.warning("Funding demo issuer account...")
                            server.friendbot(ISSUER_PUBLIC_KEY)
                            time.sleep(5) # Wait for friendbot

                    issuer_account = server.load_account(ISSUER_PUBLIC_KEY)
                    tx_builder = (
                        TransactionBuilder(
                            source_account=issuer_account,
                            network_passphrase=NETWORK_PASSPHRASE,
                        )
                    )
                    # Add ChangeTrust operation for the Issuer itself if it doesn't trust its own asset (only needed if SPORE is issued by *another* account)
                    # For a single issuer, this isn't typically needed for its own asset.
                    # Instead, we just make sure it has enough XLM to pay fees, and enough of the asset.
                    
                    # Ensure the issuer has the asset. For demo, we assume the issuer has infinite supply.
                    # If this were a real scenario with limited supply, we'd need to create it.
                    
                    tx_builder.add_operation(
                        stellar_sdk.Payment(
                            destination=st.session_state.public_key,
                            asset=SPORE_ASSET,
                            amount=str(demo_spore_amount),
                        )
                    )
                    transaction = tx_builder.set_timeout(100).build()
                    transaction.sign(ISSUER_KEY)
                    submit_signed_transaction(transaction.to_xdr())
                except Exception as e:
                    st.error(f"Error sending demo {SPORE_ASSET_CODE}: {e}")