import streamlit as st
import stellar_sdk
from stellar_sdk import Server, Keypair, TransactionBuilder, Network, Asset
from stellar_sdk.exceptions import BadRequestError, NotFoundError
import streamlit.components.v1 as components
import asyncio
import json

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
# Flag to ensure the JS message listener for components is registered only once
if "freighter_callback_registered" not in st.session_state:
    st.session_state.freighter_callback_registered = False

# --- Helper Functions ---
async def fetch_account_details(public_key):
    """Fetches account details from Horizon server."""
    try:
        account = await SERVER.load_account(public_key)
        return account
    except NotFoundError:
        return None
    except Exception as e:
        st.error(f"Error loading account {public_key}: {e}")
        return None

def submit_transaction_to_horizon(xdr_signed):
    """Submits a signed XDR transaction to Horizon."""
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
# This inline JS creates a hidden iframe that allows communication between Streamlit and Freighter.
# It listens for messages from Streamlit to trigger Freighter actions (connect, sign)
# And posts messages back to Streamlit using `streamlit.send()`, which updates `st.query_params`.
FREIGHTER_JS_COMPONENT = """
<script src="https://unpkg.com/@stellar/freighter-api@latest/build/index.js"></script>
<script>
    const streamlit = window.parent.streamlit; // Access Streamlit's send method

    async function connectFreighter() {
        try {
            if (!(await window.freighterApi.isConnected())) {
                await window.freighterApi.connect();
            }
            const publicKey = await window.freighterApi.getPublicKey();
            streamlit.send({ type: 'freighter_connected', publicKey: publicKey });
        } catch (error) {
            console.error("Freighter connection failed:", error);
            streamlit.send({ type: 'freighter_error', message: error.message });
        }
    }

    async function signTransaction(xdr, networkPassphrase) {
        try {
            const signedXDR = await window.freighterApi.signTransaction(xdr, { networkPassphrase });
            streamlit.send({ type: 'transaction_signed', signedXDR: signedXDR });
        } catch (error) {
            console.error("Transaction signing failed:", error);
            streamlit.send({ type: 'freighter_error', message: error.message });
        }
    }

    // Listen for messages from Streamlit to trigger Freighter actions
    window.addEventListener('message', async (event) => {
        // Ensure the message is from the expected source (Streamlit)
        if (event.source === window.parent && event.data && event.data.streamlitMessage) {
            const message = event.data.streamlitMessage;
            if (message.type === 'connect') {
                await connectFreighter();
            } else if (message.type === 'sign') {
                await signTransaction(message.xdr, message.networkPassphrase);
            }
        }
    });

    // Initial check if Freighter is already connected on page load
    window.freighterApi.isConnected().then(connected => {
        if (connected) {
            window.freighterApi.getPublicKey().then(publicKey => {
                streamlit.send({ type: 'freighter_connected', publicKey: publicKey });
            });
        }
    });

</script>
"""

# --- Custom CSS (Abstract/Mathematical Style) ---
CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700&family=Roboto+Mono:wght@400;700&display=swap');

    body {
        background-color: #0d1117; /* Dark GitHub-like background */
        color: #c9d1d9; /* Light gray text */
        font-family: 'Roboto Mono', monospace; /* Monospaced for mathematical feel */
        line-height: 1.6;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #58a6ff; /* A bright blue for headings */
        font-family: 'Montserrat', sans-serif; /* A more structured font for titles */
        text-shadow: 0px 0px 5px rgba(88, 166, 255, 0.4); /* Subtle glow */
    }
    .stApp {
        background-color: #0d1117;
    }
    .stMarkdown {
        color: #c9d1d9;
    }
    .stButton>button {
        background-color: #21262d; /* Darker button background */
        border: 1px solid #30363d; /* Darker border */
        color: #58a6ff; /* Blue text for buttons */
        border-radius: 5px;
        padding: 0.5em 1em;
        transition: all 0.2s ease-in-out;
        font-family: 'Roboto Mono', monospace;
        cursor: pointer;
    }
    .stButton>button:hover {
        background-color: #30363d; /* Slightly lighter on hover */
        border-color: #58a6ff; /* Blue border on hover */
        box-shadow: 0px 0px 8px rgba(88, 166, 255, 0.6); /* More prominent glow */
    }
    .stTextInput>div>div>input,
    .stSelectbox>div>div>select,
    .stTextArea>div>div>textarea {
        background-color: #161b22; /* Even darker input fields */
        border: 1px solid #30363d;
        color: #c9d1d9;
        border-radius: 5px;
        padding: 0.5em;
        font-family: 'Roboto Mono', monospace;
    }
    .stAlert {
        background-color: #161b22;
        border-left: 5px solid #58a6ff; /* Blue accent bar */
        color: #c9d1d9;
        border-radius: 5px;
    }
    .stInfo {
        background-color: #161b22;
        border-left: 5px solid #8b949e; /* Gray accent bar */
        color: #c9d1d9;
        border-radius: 5px;
    }
    .stWarning {
        background-color: #161b22;
        border-left: 5px solid #d29922; /* Orange accent bar */
        color: #c9d1d9;
        border-radius: 5px;
    }
    .stError {
        background-color: #161b22;
        border-left: 5px solid #f85149; /* Red accent bar */
        color: #c9d1d9;
        border-radius: 5px;
    }
    .stExpander>div>div {
        background-color: #161b22; /* Expander background */
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 10px;
        margin-bottom: 10px;
    }
    /* Metric styling */
    div[data-testid="stMetricLabel"] {
        color: #8b949e; /* Gray label */
        font-family: 'Montserrat', sans-serif;
        font-size: 0.9em;
    }
    div[data-testid="stMetricValue"] {
        color: #58a6ff; /* Blue value */
        font-family: 'Roboto Mono', monospace;
        font-size: 2.5em;
        text-shadow: 0px 0px 10px rgba(88, 166, 255, 0.8);
    }
    div[data-testid="stMetricDelta"] {
        color: #58a6ff; /* Blue delta */
    }
    /* Sidebar styling */
    .stSidebar {
        background-color: #161b22; /* Darker sidebar */
        border-right: 1px solid #30363d;
    }
    /* Specific target for the visual style badge/caption */
    .stSidebar .st-emotion-cache-16txt4v { /* This targets the caption container in sidebar, adjust if Streamlit's internal class names change */
        background-color: #30363d;
        border-radius: 5px;
        padding: 5px 10px;
        font-size: 0.8em;
        color: #58a6ff;
        border: 1px solid #58a6ff;
        display: inline-block;
        margin-top: 10px;
    }
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# --- Freighter Bridge Setup ---
# Render the HTML component with the JS. It's a hidden iframe for communication.
components.html(FREIGHTER_JS_COMPONENT, height=0, width=0)

# Function to send messages from Streamlit to the JS component
def send_to_freighter_component(message):
    """Sends a message to the hidden Streamlit HTML component containing Freighter JS."""
    components.html(
        f"""
        <script>
            // Find the iframe dynamically by its title or data-testid if available
            // Streamlit's components.html creates an iframe with title "st.html" by default
            const iframe = document.querySelector('iframe[title="st.html"]');
            if (iframe && iframe.contentWindow) {{
                iframe.contentWindow.postMessage({{ streamlitMessage: {json.dumps(message)} }}, '*');
            }} else {{
                console.error("Could not find the Freighter iframe to send message.");
            }}
        </script>
        """,
        height=0, width=0
    )

# Process messages from the JS component received via st.query_params
# The JS component uses `streamlit.send()` which adds data to 'streamlit_msg' query param.
if "streamlit_msg" in st.query_params:
    try:
        message_str = st.query_params["streamlit_msg"]
        message_data = json.loads(message_str)

        if message_data.get("type") == "freighter_connected":
            st.session_state.freighter_public_key = message_data["publicKey"]
            st.success(f"Freighter Connected! Public Key: `{message_data['publicKey'][:10]}...`")
            st.session_state.tx_in_progress = False # Clear pending state
            st.query_params.pop("streamlit_msg") # Clear the query param to avoid re-processing
            st.experimental_rerun()

        elif message_data.get("type") == "transaction_signed":
            st.session_state.signed_xdr = message_data["signedXDR"]
            # Do NOT immediately set tx_in_progress to False here. It will be set to false AFTER submission.
            # This allows the subsequent submit logic to execute.
            st.success("Transaction signed by Freighter!")
            st.query_params.pop("streamlit_msg") # Clear the query param
            st.experimental_rerun()

        elif message_data.get("type") == "freighter_error":
            st.session_state.tx_in_progress = False # Transaction failed or cancelled
            st.error(f"Freighter Error: {message_data['message']}")
            st.query_params.pop("streamlit_msg") # Clear the query param
            st.experimental_rerun()

    except json.JSONDecodeError:
        st.error("Error decoding message from Freighter component.")
    except Exception as e:
        st.error(f"An unexpected error occurred while processing Freighter message: {e}")

# --- Secret Key Handling (Mandate 11) ---
if "ISSUER_KEY" in st.secrets:
    ISSUER_SECRET = st.secrets["ISSUER_KEY"]
else:
    if "demo_key" not in st.session_state:
        # Generate a random keypair for demo mode, store its secret
        st.session_state.demo_key = Keypair.random().secret
    ISSUER_SECRET = st.session_state.demo_key
    st.sidebar.warning("Using Ephemeral Demo Keys for Issuer.")

try:
    ISSUER_KEYPAIR = Keypair.from_secret(ISSUER_SECRET)
    ISSUER_PUBLIC_KEY = ISSUER_KEYPAIR.public_key
except ValueError: # Using ValueError as per mandate 7
    st.error("Invalid ISSUER_KEY. Please check your Streamlit secrets or ensure a valid key is generated for demo mode.")
    st.stop() # Stop execution if issuer key is invalid

# Define Solution Fragment Assets
FRAGMENT_A = Asset("FRAG_A", ISSUER_PUBLIC_KEY)
FRAGMENT_B = Asset("FRAG_B", ISSUER_PUBLIC_KEY)

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
# Entropic state: 0.5 is optimal. Delta shows movement away from or towards 0.5
delta_val = f"{abs(st.session_state.current_entropic_state - 0.5):.4f}"
delta_color = "off" # Neutral by default
delta_label = "Balanced"

if st.session_state.current_entropic_state < 0.45:
    delta_color = "inverse" # Indicates 'bad' change if moving away from 0.5, or 'good' if moving towards it
    delta_label = "Low Entropy (Cooling)"
elif st.session_state.current_entropic_state > 0.55:
    delta_color = "inverse"
    delta_label = "High Entropy (Heating)"
else:
    delta_label = "Balanced"

st.sidebar.metric(label="Entropic State", value=f"{st.session_state.current_entropic_state:.4f}", delta=delta_label, delta_color=delta_color)
st.sidebar.caption("Optimal entropic state is 0.5. Deviations indicate instability. Values below 0.5 (low entropy) are 'cooling' while values above 0.5 (high entropy) are 'heating'.")
st.sidebar.markdown("---")

# --- Main App ---
st.title("The Entropic Equation Engine 🧬")
st.subheader("Orchestrating Solution Fragments for System Stabilization")

# --- 1. Connect Freighter (Your Equation Account) ---
st.header("1. Connect Your Equation Account (Freighter) 🔗")
st.markdown("Your connected Freighter wallet will serve as your 'Equation Account' for deploying offers.")

if not st.session_state.freighter_public_key:
    if st.button("Connect Freighter Wallet"):
        send_to_freighter_component({"type": "connect"})
        st.session_state.tx_in_progress = True # Indicate a pending action
        st.info("Awaiting Freighter connection...")
else:
    st.success(f"Connected to Freighter Public Key: `{st.session_state.freighter_public_key}`")
    account_details = asyncio.run(fetch_account_details(st.session_state.freighter_public_key))
    if account_details:
        xlm_balance = next((b.balance for b in account_details.balances if b.asset_type == 'native'), '0.0000000')
        st.write(f"Balance: **{xlm_balance} XLM**")
    else:
        st.warning("Freighter account not found on Testnet. Fund it below!")

# --- 2. Initialize Network State (Testnet Only) ---
if st.session_state.freighter_public_key:
    st.header("2. Initialize Network State (Testnet) 🧪")
    st.markdown("Use this to fund your connected Freighter account on the Stellar Testnet if it's new, and to verify the issuer.")
    
    col1, col2 = st.columns([1,2])
    with col1:
        if st.button("Fund Equation Account (XLM via Friendbot)"):
            try:
                # This is a direct server call, not via Freighter, for convenience on Testnet
                response = SERVER.friendbot(st.session_state.freighter_public_key)
                st.success("Equation Account funded by Friendbot! Transaction: " + response['hash'])
                st.experimental_rerun()
            except BadRequestError as e:
                st.error(f"Friendbot funding failed: {e.extras.get('result_codes')}")
            except Exception as e:
                st.error(f"An error occurred: {e}")
    with col2:
        st.write("System Issuer Public Key (for FRAG_A, FRAG_B):")
        st.code(ISSUER_PUBLIC_KEY)
        st.caption("This system account manages the supply of solution fragments.")

# --- 3. Manage Solution Fragments ---
st.header("3. Orchestrate Solution Fragments ⚛️")
st.markdown("Solution fragments (FRAG_A, FRAG_B) are essential for your equation. "
            "You need to establish trustlines for them, and then the system issuer can provide them.")

if not st.session_state.freighter_public_key:
    st.warning("Please connect your Freighter wallet first to manage fragments.")
else:
    equation_pk = st.session_state.freighter_public_key
    equation_account_details = asyncio.run(fetch_account_details(equation_pk))

    if not equation_account_details:
        st.warning(f"Equation account `{equation_pk[:10]}...` is not active. Please fund it via Friendbot.")
    else:
        st.subheader("Establish Trustlines (from your Equation Account)")
        st.markdown(f"Your equation account `{equation_pk[:10]}...` needs to trust the issuer for FRAG_A and FRAG_B before it can hold them.")

        has_trust_a = any(b.asset == FRAGMENT_A for b in equation_account_details.balances)
        has_trust_b = any(b.asset == FRAGMENT_B for b in equation_account_details.balances)

        col1, col2 = st.columns(2)
        with col1:
            if not has_trust_a:
                if st.button(f"Trust FRAG_A ({FRAGMENT_A.code})"):
                    try:
                        source_account = asyncio.run(fetch_account_details(equation_pk))
                        if not source_account: st.error("Equation account not found. Fund it first."); st.stop()

                        transaction = TransactionBuilder(
                            source_account=source_account,
                            network_passphrase=NETWORK_PASSPHRASE,
                        ).append_change_trust_op(
                            asset=FRAGMENT_A,
                            limit="100000000000" # High limit
                        ).set_timeout(300).build()

                        xdr = transaction.to_xdr()
                        st.session_state.tx_in_progress = True
                        send_to_freighter_component({"type": "sign", "xdr": xdr, "networkPassphrase": NETWORK_PASSPHRASE})
                        st.info("Awaiting Freighter signature to establish trustline for FRAG_A...")

                    except Exception as e:
                        st.error(f"Error building transaction: {e}")
            else:
                frag_a_balance = next((b.balance for b in equation_account_details.balances if b.asset == FRAGMENT_A), '0.0000000')
                st.success(f"✅ Trustline for FRAG_A established. Balance: `{frag_a_balance}` FRAG_A")

        with col2:
            if not has_trust_b:
                if st.button(f"Trust FRAG_B ({FRAGMENT_B.code})"):
                    try:
                        source_account = asyncio.run(fetch_account_details(equation_pk))
                        if not source_account: st.error("Equation account not found. Fund it first."); st.stop()

                        transaction = TransactionBuilder(
                            source_account=source_account,
                            network_passphrase=NETWORK_PASSPHRASE,
                        ).append_change_trust_op(
                            asset=FRAGMENT_B,
                            limit="100000000000" # High limit
                        ).set_timeout(300).build()

                        xdr = transaction.to_xdr()
                        st.session_state.tx_in_progress = True
                        send_to_freighter_component({"type": "sign", "xdr": xdr, "networkPassphrase": NETWORK_PASSPHRASE})
                        st.info("Awaiting Freighter signature to establish trustline for FRAG_B...")
                    except Exception as e:
                        st.error(f"Error building transaction: {e}")
            else:
                frag_b_balance = next((b.balance for b in equation_account_details.balances if b.asset == FRAGMENT_B), '0.0000000')
                st.success(f"✅ Trustline for FRAG_B established. Balance: `{frag_b_balance}` FRAG_B")

        # Process signed trustline transaction (after Freighter has signed)
        if st.session_state.tx_in_progress and st.session_state.signed_xdr:
            st.info("Submitting trustline transaction...")
            response = submit_transaction_to_horizon(st.session_state.signed_xdr)
            if response:
                st.success(f"Trustline established! Transaction: `{response['hash']}`")
                st.session_state.signed_xdr = None # Clear signed XDR
                st.experimental_rerun()
            else:
                st.error("Failed to establish trustline. Check horizon for details.")
            st.session_state.tx_in_progress = False


        st.subheader("Acquire Fragments (Issuer Provides)")
        st.markdown("The system's issuer provides initial solution fragments to your equation account once trustlines are established.")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"Request 10 FRAG_A from Issuer"):
                try:
                    # Fetch issuer account for sequence number
                    issuer_account = asyncio.run(fetch_account_details(ISSUER_PUBLIC_KEY))
                    if not issuer_account:
                        st.error("Issuer account not found. Please ensure it's funded on Testnet and its secret is correctly set.")
                        st.stop()
                    if not has_trust_a:
                        st.error("Equation account must first establish a trustline for FRAG_A.")
                        st.stop()

                    transaction = TransactionBuilder(
                        source_account=issuer_account,
                        network_passphrase=NETWORK_PASSPHRASE,
                    ).append_payment_op(
                        destination=equation_pk,
                        asset=FRAGMENT_A,
                        amount="10"
                    ).set_timeout(300).build()

                    transaction.sign(ISSUER_KEYPAIR) # Issuer signs directly

                    response = submit_transaction_to_horizon(transaction.to_xdr())
                    if response:
                        st.success(f"10 FRAG_A received! Transaction: `{response['hash']}`")
                        st.experimental_rerun()
                    else:
                        st.error("Failed to receive FRAG_A.")
                except Exception as e:
                    st.error(f"Error requesting FRAG_A: {e}")
        with col2:
            if st.button(f"Request 10 FRAG_B from Issuer"):
                try:
                    issuer_account = asyncio.run(fetch_account_details(ISSUER_PUBLIC_KEY))
                    if not issuer_account:
                        st.error("Issuer account not found. Please ensure it's funded on Testnet and its secret is correctly set.")
                        st.stop()
                    if not has_trust_b:
                        st.error("Equation account must first establish a trustline for FRAG_B.")
                        st.stop()

                    transaction = TransactionBuilder(
                        source_account=issuer_account,
                        network_passphrase=NETWORK_PASSPHRASE,
                    ).append_payment_op(
                        destination=equation_pk,
                        asset=FRAGMENT_B,
                        amount="10"
                    ).set_timeout(300).build()

                    transaction.sign(ISSUER_KEYPAIR)

                    response = submit_transaction_to_horizon(transaction.to_xdr())
                    if response:
                        st.success(f"10 FRAG_B received! Transaction: `{response['hash']}`")
                        st.experimental_rerun()
                    else:
                        st.error("Failed to receive FRAG_B.")
                except Exception as e:
                    st.error(f"Error requesting FRAG_B: {e}")


# --- 4. Create Entropic Offers (Passive Offers) ---
st.header("4. Create Entropic Offers 🔄")
st.markdown("Deploy passive offers from your equation account to exchange solution fragments, influencing the system's entropic state.")

if not st.session_state.freighter_public_key:
    st.warning("Please connect your Freighter wallet (your equation account) first.")
else:
    equation_pk = st.session_state.freighter_public_key
    equation_account_details = asyncio.run(fetch_account_details(equation_pk))

    if not equation_account_details:
        st.warning(f"Equation account `{equation_pk[:10]}...` not active. Please fund it and establish trustlines.")
    else:
        st.write(f"Equation Account: `{equation_pk}`")
        st.subheader("Define Your Passive Offer")

        col1, col2 = st.columns(2)
        with col1:
            selling_asset_options = [FRAGMENT_A.code, FRAGMENT_B.code, "XLM"]
            # Filter options to only include assets for which trustlines exist or XLM
            current_balances = {b.asset.code if b.asset_type != 'native' else 'XLM': b.balance for b in equation_account_details.balances}
            available_selling_assets = [opt for opt in selling_asset_options if opt in current_balances and float(current_balances[opt]) > 0]
            if not available_selling_assets:
                available_selling_assets = selling_asset_options # Fallback if no balances, let user choose anyway

            selling_asset_choice = st.selectbox("Selling Asset:", options=available_selling_assets)
            amount = st.text_input("Amount (to sell):", value="1.0")

        with col2:
            buying_asset_options = [FRAGMENT_A.code, FRAGMENT_B.code, "XLM"]
            # Ensure the buying asset is not the same as selling.
            buying_asset_options_filtered = [opt for opt in buying_asset_options if opt != selling_asset_choice]
            
            # Default to FRAG_B if available, otherwise first option
            default_buying_index = 0
            if FRAGMENT_B.code in buying_asset_options_filtered:
                default_buying_index = buying_asset_options_filtered.index(FRAGMENT_B.code)
            
            buying_asset_choice = st.selectbox("Buying Asset:", options=buying_asset_options_filtered, index=default_buying_index)

            price = st.text_input("Price (units of buying asset per unit of selling asset):", value="1.0")

        def get_asset_from_choice(choice):
            if choice == "XLM":
                return stellar_sdk.Asset.native()
            elif choice == FRAGMENT_A.code:
                return FRAGMENT_A
            elif choice == FRAGMENT_B.code:
                return FRAGMENT_B
            return None

        selling_asset = get_asset_from_choice(selling_asset_choice)
        buying_asset = get_asset_from_choice(buying_asset_choice)

        if st.button("Deploy Passive Offer"):
            if not selling_asset or not buying_asset:
                st.error("Invalid assets selected.")
            elif selling_asset == buying_asset:
                st.error("Cannot sell and buy the same asset. This should be prevented by the UI.")
            else:
                try:
                    amount_float = float(amount)
                    price_float = float(price)
                    if amount_float <= 0 or price_float <= 0:
                        st.error("Amount and Price must be positive numbers.")
                        st.stop()

                    source_account = equation_account_details # Use the current account details from Freighter
                    
                    transaction = TransactionBuilder(
                        source_account=source_account,
                        network_passphrase=NETWORK_PASSPHRASE,
                    ).append_manage_buy_offer_op( # Passive offer is a buy offer with offer_id=0
                        selling=selling_asset,
                        buying=buying_asset,
                        amount=str(amount_float),
                        price=str(price_float),
                        offer_id=0 # Create a new passive offer
                    ).set_timeout(300).build()

                    xdr = transaction.to_xdr()
                    st.session_state.tx_in_progress = True
                    send_to_freighter_component({"type": "sign", "xdr": xdr, "networkPassphrase": NETWORK_PASSPHRASE})
                    st.info("Awaiting Freighter signature for passive offer...")

                except ValueError:
                    st.error("Amount and Price must be valid numbers.")
                except Exception as e:
                    st.error(f"Error building transaction: {e}")

        # Process signed passive offer transaction (after Freighter has signed)
        if st.session_state.tx_in_progress and st.session_state.signed_xdr:
            st.info("Submitting passive offer transaction...")
            response = submit_transaction_to_horizon(st.session_state.signed_xdr)
            if response:
                st.success(f"Passive offer deployed! Transaction: `{response['hash']}`")
                
                # Simulate entropic state change based on offer
                # A simplistic simulation:
                # Trading FRAG_A for FRAG_B reduces entropy (stabilizes towards 0)
                # Trading FRAG_B for FRAG_A increases entropy (destabilizes towards 1)
                # Other trades have a tendency to move towards the optimal 0.5
                if selling_asset == FRAGMENT_A and buying_asset == FRAGMENT_B:
                    st.session_state.current_entropic_state = max(0.01, st.session_state.current_entropic_state - 0.05)
                elif selling_asset == FRAGMENT_B and buying_asset == FRAGMENT_A:
                    st.session_state.current_entropic_state = min(0.99, st.session_state.current_entropic_state + 0.05)
                else: # Any other trade, drift gently towards 0.5
                     st.session_state.current_entropic_state = max(0.01, min(0.99, st.session_state.current_entropic_state + (0.5 - st.session_state.current_entropic_state) * 0.1))
                
                st.session_state.signed_xdr = None # Clear signed XDR
                st.experimental_rerun()
            else:
                st.error("Failed to deploy passive offer. Check horizon for details.")
            st.session_state.tx_in_progress = False

        st.subheader("Your Active Offers")
        with st.expander("View your current offers 📊"):
            if equation_account_details:
                offers = []
                try:
                    # Fetch offers directly from Horizon for the connected account
                    offers_response = SERVER.offers().for_account(equation_pk).call()
                    offers = offers_response['_embedded']['records']
                except Exception as e:
                    st.warning(f"Could not fetch offers for this account: {e}")
                
                if offers:
                    # st.json(offers) # Optional: Show raw JSON for detail, useful for debugging
                    # st.markdown("---")
                    for i, offer in enumerate(offers):
                        st.markdown(f"**Offer {i+1} (ID: `{offer['id']}`):**")
                        
                        # Determine selling asset string
                        selling_asset_str = "XLM" if offer['selling']['asset_type'] == 'native' else offer['selling']['asset_code']
                        # Determine buying asset string
                        buying_asset_str = "XLM" if offer['buying']['asset_type'] == 'native' else offer['buying']['asset_code']

                        st.write(f"  - Selling: `{offer['amount']}` units of `{selling_asset_str}`")
                        st.write(f"  - Buying: `{buying_asset_str}` (at a price of `{offer['price']}` per unit of selling asset)")
                        # Price is 'buying units per selling unit'
                        st.markdown("---")
                else:
                    st.info("No active offers found for this equation account.")
            else:
                st.info("Connect your Freighter wallet to view offers.")

st.markdown("---")
st.caption("Conceptual dApp - Testnet Only. Clawback logic is not implemented in this MVP but would be based on the Entropic State metric.")