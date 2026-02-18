import streamlit as st
from stellar_sdk import (
    Keypair,
    TransactionBuilder,
    Server,
    Network,
    Asset,
    AssetType,
    ChangeTrust,
    CreatePassiveSellOffer,
    PathPaymentStrictReceive,
    ClaimClaimableBalance,
    SetOptions,
    Account,
    Memo,
    MuxedAccount
)
from stellar_sdk.exceptions import NoMuxedAccountError, BadSignatureError
import json
import base64
import asyncio
import streamlit.components.v1 as components # Import components

# --- Configuration ---
HORIZON_TESTNET = "https://horizon-testnet.stellar.org"
HORIZON_PUBLIC = "https://horizon.stellar.org"
NETWORK_PASSPHRASE_TESTNET = Network.TESTNET_NETWORK_PASSPHRASE
NETWORK_PASSPHRASE_PUBLIC = Network.PUBLIC_NETWORK_PASSPHRASE

# Initialize session state for connection status and network
if 'public_key' not in st.session_state:
    st.session_state.public_key = None
if 'network' not in st.session_state:
    st.session_state.network = 'Testnet' # Default to Testnet
if 'streamlit_messages' not in st.session_state: # To store messages from JS
    st.session_state.streamlit_messages = []
if 'signed_xdr' not in st.session_state:
    st.session_state.signed_xdr = None
if 'show_signed_xdr' not in st.session_state:
    st.session_state.show_signed_xdr = False
if 'query_params_processed' not in st.session_state:
    st.session_state.query_params_processed = False

# --- Custom CSS for Minimalist, High-Contrast, Futuristic Style ---
def apply_custom_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Orbitron:wght@400;600&display=swap');

        :root {
            --primary-bg: #0A0A0F;
            --secondary-bg: #1A1A22;
            --accent-color: #00FFC0; /* Neon Green */
            --text-color: #E0E0E0;
            --secondary-text-color: #A0A0A0;
            --border-color: #333344;
            --warning-color: #FFD700;
            --error-color: #FF6347;
            --font-family-header: 'Orbitron', sans-serif;
            --font-family-body: 'IBM Plex Mono', monospace;
        }

        body {
            background-color: var(--primary-bg);
            color: var(--text-color);
            font-family: var(--font-family-body);
        }

        h1, h2, h3, h4, h5, h6 {
            font-family: var(--font-family-header);
            color: var(--accent-color);
            text-shadow: 0 0 5px rgba(0, 255, 192, 0.5);
        }

        .stApp {
            background-color: var(--primary-bg);
            color: var(--text-color);
        }

        .stMarkdown {
            color: var(--text-color);
        }

        /* --- Streamlit Elements Overrides --- */
        .stButton button {
            background-color: var(--accent-color);
            color: var(--primary-bg);
            border: 2px solid var(--accent-color);
            border-radius: 8px;
            padding: 10px 20px;
            font-size: 1rem;
            font-weight: 600;
            transition: all 0.2s ease-in-out;
            cursor: pointer;
            text-transform: uppercase;
            box-shadow: 0 0 5px rgba(0, 255, 192, 0.3);
        }
        .stButton button:hover {
            background-color: transparent;
            color: var(--accent-color);
            box-shadow: 0 0 15px var(--accent-color);
        }
        .stButton button:active {
            transform: translateY(1px);
        }

        .stTextInput label, .stSelectbox label, .stRadio label, .stCheckbox label, .stNumberInput label {
            color: var(--secondary-text-color);
            font-weight: 600;
            margin-bottom: 5px;
            display: block;
        }
        .stTextInput input, .stSelectbox div[data-baseweb="select"] button, .stNumberInput input, .stTextArea textarea {
            background-color: var(--secondary-bg);
            border: 1px solid var(--border-color);
            color: var(--text-color);
            border-radius: 5px;
            padding: 10px;
            font-family: var(--font-family-body);
            box-shadow: inset 0 1px 3px rgba(0,0,0,0.3);
        }
        .stTextInput input:focus, .stSelectbox div[data-baseweb="select"] button:focus, .stNumberInput input:focus, .stTextArea textarea:focus {
            border-color: var(--accent-color);
            box-shadow: 0 0 8px rgba(0, 255, 192, 0.3);
            outline: none;
        }

        .stSelectbox div[data-baseweb="popover"] div[role="listbox"] {
            background-color: var(--secondary-bg);
            border: 1px solid var(--border-color);
        }
        .stSelectbox div[data-baseweb="popover"] div[role="option"] {
            color: var(--text-color);
        }
        .stSelectbox div[data-baseweb="popover"] div[role="option"]:hover {
            background-color: rgba(0, 255, 192, 0.1);
            color: var(--accent-color);
        }

        .stAlert {
            background-color: var(--secondary-bg);
            color: var(--text-color);
            border-left: 5px solid var(--accent-color);
            border-radius: 5px;
            padding: 10px;
            margin-top: 10px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
        }
        .stAlert.st-emotion-cache-1f6e2sq { /* Target specific warning class for yellow */
            border-left-color: var(--warning-color);
        }
        .stAlert.st-emotion-cache-16qf4sw { /* Target specific error class for red */
             border-left-color: var(--error-color);
        }
        .stAlert.st-emotion-cache-km02q1 { /* Target specific success class for green */
             border-left-color: var(--accent-color);
        }


        .stExpander details {
            background-color: var(--secondary-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 10px 15px;
            margin-top: 15px;
            transition: all 0.2s ease;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
        }
        .stExpander details summary {
            color: var(--accent-color);
            font-weight: 600;
            font-family: var(--font-family-header);
            cursor: pointer;
            outline: none;
        }
        .stExpander details summary::marker, .stExpander details summary::-webkit-details-marker {
            color: var(--accent-color);
        }
        .stExpander details[open] {
            border-color: var(--accent-color);
            box-shadow: 0 0 10px rgba(0, 255, 192, 0.2);
        }

        .stMetric {
            background-color: var(--secondary-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
            text-align: center;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
        }
        .stMetric > div:first-child { /* Label */
            color: var(--secondary-text-color);
            font-family: var(--font-family-header);
            font-size: 0.9em;
            text-transform: uppercase;
            margin-bottom: 5px;
        }
        .stMetric > div:nth-child(2) { /* Value */
            color: var(--accent-color);
            font-family: var(--font-family-body);
            font-size: 1.8em;
            font-weight: 600;
        }
        .stMetric > div:nth-child(3) { /* Delta */
            color: var(--secondary-text-color);
            font-size: 0.8em;
        }

        code {
            background-color: rgba(0, 255, 192, 0.1);
            color: var(--accent-color);
            border-radius: 3px;
            padding: 2px 4px;
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.9em;
        }

        /* Tabs styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            background: transparent;
            border: none;
            border-bottom: 2px solid var(--border-color);
            border-radius: 0px;
            transition: all 0.2s ease;
            color: var(--secondary-text-color);
            font-family: var(--font-family-header);
            font-weight: 600;
            text-transform: uppercase;
        }
        .stTabs [data-baseweb="tab"]:hover {
            color: var(--accent-color);
        }
        .stTabs [data-baseweb="tab"][aria-selected="true"] {
            background: var(--secondary-bg);
            border-bottom: 2px solid var(--accent-color);
            color: var(--accent-color);
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
        }
        .stTabs [data-baseweb="tab-panel"] {
            background-color: var(--secondary-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 20px;
            margin-top: 15px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
        }

        /* Generic container styling */
        .st-emotion-cache-1r6dm7m { /* Target main block container */
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        .st-emotion-cache-z5fcl4 { /* Target Block container */
            padding: 0;
        }

    </style>
    """, unsafe_allow_html=True)

# --- Stellar Helper Functions ---
def get_horizon_server():
    if st.session_state.network == 'Testnet':
        return Server(HORIZON_TESTNET)
    else:
        return Server(HORIZON_PUBLIC)

def get_network_passphrase():
    if st.session_state.network == 'Testnet':
        return NETWORK_PASSPHRASE_TESTNET
    else:
        return NETWORK_PASSPHRASE_PUBLIC

def get_asset_object(asset_code, asset_issuer):
    if asset_code.upper() == 'XLM':
        return Asset.native()
    if not asset_issuer: # For non-XLM assets, issuer is mandatory
        raise ValueError(f"Asset '{asset_code}' requires an issuer.")
    return Asset(asset_code, asset_issuer)

async def fetch_account_balances(public_key):
    server = get_horizon_server()
    try:
        account_info = await server.load_account(public_key)
        balances = {}
        for balance in account_info.balances:
            asset_type = balance.asset_type
            asset_code = balance.asset_code if asset_type != 'native' else 'XLM'
            asset_issuer = balance.asset_issuer if asset_type != 'native' else None
            balances[asset_code] = {
                'balance': float(balance.balance),
                'limit': float(balance.limit) if balance.limit else None,
                'issuer': asset_issuer
            }
        return balances
    except Exception as e:
        st.error(f"⚠️ Error fetching account balances: {e}")
        return {}

# --- Freighter Integration (st.components.v1.html) ---
# This component uses window.streamlitReportMessage which is how JS communicates back to Streamlit.
# We embed the JS directly in the HTML component.
FREIGHTER_JS = """
<script>
    window.onload = function() {
        const connectButton = document.getElementById('connectFreighter');
        if (connectButton) {
            connectButton.onclick = async () => {
                try {
                    if (window.freighterApi) {
                        const publicKey = await window.freighterApi.getPublicKey();
                        window.streamlitReportMessage({ type: 'publicKey', data: publicKey });
                    } else {
                        window.streamlitReportMessage({ type: 'error', data: 'Freighter not detected! Please ensure Freighter wallet is installed and unlocked.' });
                    }
                } catch (error) {
                    window.streamlitReportMessage({ type: 'error', data: error.message });
                }
            };
        }

        window.signTransaction = async (xdr, network) => {
            try {
                if (window.freighterApi) {
                    const signedXdr = await window.freighterApi.signTransaction(xdr, { network: network });
                    window.streamlitReportMessage({ type: 'signedXdr', data: signedXdr });
                } else {
                    window.streamlitReportMessage({ type: 'error', data: 'Freighter not detected! Please ensure Freighter wallet is installed and unlocked.' });
                }
            } catch (error) {
                window.streamlitReportMessage({ type: 'error', data: error.message });
            }
        };

        // This is important: tell Streamlit the component is ready
        window.streamlitReportReady();
    };
</script>
<button id="connectFreighter" style="display: none;"></button>
"""

def freighter_component_embed():
    """
    Renders a hidden component that allows JavaScript to interact with Freighter
    and send messages back to Streamlit. This should be called once.
    """
    components.html(FREIGHTER_JS, height=0, width=0)

# Function to call JS from Python
def call_js_function(js_function_name, *args):
    """
    Injects JavaScript to call a function defined in the embedded component.
    """
    args_str = ', '.join(f"'{arg}'" if isinstance(arg, str) else str(arg) for arg in args)
    js_code = f"""
        <script>
            if (window.{js_function_name}) {{
                window.{js_function_name}({args_str});
            }} else {{
                console.error("JavaScript function {js_function_name} not found.");
            }}
        </script>
    """
    components.html(js_code, height=0, width=0)


# --- Streamlit UI ---
st.set_page_config(
    page_title="ApexStream dApp",
    page_icon="🧬",
    layout="centered",
    initial_sidebar_state="expanded"
)

apply_custom_css()

# Embed the Freighter component early to ensure its JS is loaded
freighter_component_embed()

# Process messages from JavaScript that might have come in previous reruns
rerun_needed = False
for message in st.session_state.streamlit_messages:
    if message['type'] == 'publicKey':
        st.session_state.public_key = message['data']
        st.success("Freighter connected successfully!")
        rerun_needed = True
    elif message['type'] == 'signedXdr':
        st.session_state.signed_xdr = message['data']
        st.session_state.show_signed_xdr = True
        st.success("Transaction signed successfully by Freighter!")
        rerun_needed = True # Rerun to display signed XDR
    elif message['type'] == 'error':
        st.error(f"Freighter Error: {message['data']}")
        st.session_state.public_key = None # Clear key on error
        st.session_state.signed_xdr = None
        st.session_state.show_signed_xdr = False
        rerun_needed = True
# Clear messages AFTER processing them for the current run
st.session_state.streamlit_messages = []

if rerun_needed:
    st.rerun()


# Sidebar for network selection and general info
with st.sidebar:
    st.markdown("## ⚙️ Settings")
    st.session_state.network = st.radio(
        "Select Network",
        ('Testnet', 'Public'),
        index=0 if st.session_state.network == 'Testnet' else 1,
        key='network_selector',
        help="Choose between Stellar Testnet and Public Network."
    )

    st.markdown("---")
    st.markdown("## 🛟 About ApexStream")
    st.markdown("""
        ApexStream is a decentralized financial automation platform.
        It orchestrates user-defined liquidity strategies through passive market making,
        automatically harvests rewards, and seamlessly converts diversified earnings
        into a consolidated target asset.
        
        **Note:** This dApp is for demonstration purposes. Use caution with real assets.
    """)
    st.markdown("""
        **Features:**
        - Create Passive Sell Offers
        - Claim Claimable Balances
        - Path Payments
        - Manage Trustlines & Account Options
    """)

# Main Title
st.markdown("<h1><span style='color:var(--accent-color);'>Apex</span>Stream 🧬</h1>", unsafe_allow_html=True)
st.markdown("### Decentralized Financial Automation for Stellar")

# --- Freighter Connection ---
col1, col2 = st.columns([2, 1])

with col1:
    if st.session_state.public_key:
        st.success(f"🔗 Connected: `{st.session_state.public_key[:8]}...{st.session_state.public_key[-8:]}`")
        st.markdown(f"**Network:** `{st.session_state.network}`")
        if st.button("🔌 Disconnect Freighter", key="disconnect_button"):
            st.session_state.public_key = None
            st.session_state.account_balances = {} # Clear balances too
            st.rerun()
    else:
        st.warning("⚠️ Not connected to Freighter.")
        if st.button("🚀 Connect Freighter", key="connect_button"):
            call_js_function('connectToFreighter')
            st.info("Awaiting Freighter connection...")
            # No rerun here, waiting for JS to report back will trigger one if successful.


# Function to encapsulate XDR signing and display
# This function no longer needs to poll, as the message handler above will set session_state.signed_xdr and trigger a rerun.
async def sign_and_display_xdr(transaction_xdr, network_name):
    # Clear previous signed XDR state
    st.session_state.signed_xdr = None
    st.session_state.show_signed_xdr = False

    st.info("Awaiting transaction signing by Freighter...")
    call_js_function('signTransaction', transaction_xdr, network_name.lower())
    # The next Streamlit rerun (triggered by JS message) will display the result

# --- Account Balances ---
if st.session_state.public_key:
    st.markdown("---")
    st.subheader("📊 Account Overview")
    account_balances = {}
    # Only fetch if not already in session state or if refresh button is clicked
    if 'account_balances' not in st.session_state or st.button("🔄 Refresh Balances", key="refresh_balances_button"):
        account_balances = asyncio.run(fetch_account_balances(st.session_state.public_key))
        st.session_state.account_balances = account_balances
    else:
        account_balances = st.session_state.account_balances

    if account_balances:
        balance_cols = st.columns(3)
        i = 0
        for asset_code, data in account_balances.items():
            with balance_cols[i % 3]:
                st.metric(label=f"💰 {asset_code} Balance", value=f"{data['balance']:.2f}")
            i += 1
    else:
        st.info("No balances found. Ensure your account is funded or you have trustlines for other assets.")

    # Display signed XDR if available from a previous successful signing operation
    if st.session_state.show_signed_xdr and st.session_state.signed_xdr:
        st.markdown("---")
        st.subheader("✅ Signed Transaction XDR")
        st.code(st.session_state.signed_xdr, language="text")
        st.success("Transaction signed! You can now submit this XDR to the Stellar network.")
        # We keep it displayed until a new action is performed or page reloads,
        # providing persistent feedback for the last signed transaction.
        
    st.markdown("---")

    # --- dApp Operations Tabs ---
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "💰 Trustlines",
        "⚖️ Passive Offer",
        "🎁 Claim Rewards",
        "🔄 Path Payment",
        "⚙️ Set Options"
    ])

    # --- TAB 1: Change Trust (Trustlines) ---
    with tab1:
        st.subheader("Manage Asset Trustlines 💰")
        st.markdown("Create or remove trustlines for specific assets.")

        asset_code_ct = st.text_input("Asset Code (e.g., USD, EURT)", key="ct_asset_code", value="USD")
        asset_issuer_ct = st.text_input("Asset Issuer Public Key", key="ct_asset_issuer", value="GAXLYH63H47C62N7S5ZB2S6M66E6Y75BPTL525Y4N344R7Y6EELHHKLM") # Example issuer for Testnet

        limit_col1, limit_col2 = st.columns([1,2])
        with limit_col1:
            trust_limit = st.number_input(
                "Trust Limit (0 to remove)",
                min_value=0.0,
                max_value=1_000_000_000.0, # Large but reasonable max
                value=1000.0,
                key="ct_trust_limit",
                help="Set to 0 to remove an existing trustline."
            )
        with limit_col2:
            st.empty() # Placeholder for alignment

        if st.button("🏗️ Build ChangeTrust Transaction", key="build_changetrust"):
            if not asset_code_ct or not asset_issuer_ct:
                st.error("Asset Code and Issuer are required for trustline operations.")
                st.stop()
            elif asset_code_ct.upper() == 'XLM':
                st.error("Cannot create a trustline for native XLM asset.")
                st.stop()
            else:
                try:
                    asset = get_asset_object(asset_code_ct, asset_issuer_ct)
                    account = asyncio.run(get_horizon_server().load_account(st.session_state.public_key))

                    operation = ChangeTrust(
                        asset=asset,
                        limit=str(trust_limit)
                    )

                    transaction = (
                        TransactionBuilder(
                            source_account=account,
                            network_passphrase=get_network_passphrase(),
                            base_fee=100
                        )
                        .add_operation(operation)
                        .set_memo(Memo.text(f"ApexStream ChangeTrust {asset_code_ct}"))
                        .build()
                    )

                    xdr = transaction.to_xdr()
                    st.success("ChangeTrust Transaction XDR Built!")
                    st.code(xdr, language="text")

                    with st.expander("Transaction Details (Raw XDR)"):
                        st.code(xdr, language="text")

                    if st.button("✍️ Sign with Freighter", key="sign_ct_xdr"):
                        asyncio.run(sign_and_display_xdr(xdr, st.session_state.network))

                except Exception as e:
                    st.error(f"Error building ChangeTrust transaction: {e}")

    # --- TAB 2: Create Passive Sell Offer ---
    with tab2:
        st.subheader("Create Passive Sell Offer ⚖️")
        st.markdown("Automatically sell an asset at a specified price to provide liquidity.")

        col_selling, col_selling_issuer = st.columns(2)
        with col_selling:
            selling_asset_code = st.text_input("Selling Asset Code (e.g., USD)", key="offer_selling_code", value="USD")
        with col_selling_issuer:
            selling_asset_issuer = st.text_input("Selling Asset Issuer (or leave empty for XLM)", key="offer_selling_issuer", value="GAXLYH63H47C62N7S5ZB2S6M66E6Y75BPTL525Y4N344R7Y6EELHHKLM")

        col_buying, col_buying_issuer = st.columns(2)
        with col_buying:
            buying_asset_code = st.text_input("Buying Asset Code (e.g., XLM)", key="offer_buying_code", value="XLM")
        with col_buying_issuer:
            buying_asset_issuer = st.text_input("Buying Asset Issuer (or leave empty for XLM)", key="offer_buying_issuer", value="")

        amount = st.number_input("Amount to Sell", min_value=0.0000001, value=100.0, format="%.7f", key="offer_amount")
        price = st.number_input("Price (Selling per Buying unit, e.g., 1 USD for X XLM)", min_value=0.0000001, value=0.1, format="%.7f", key="offer_price")

        if st.button("🏗️ Build PassiveSellOffer Transaction", key="build_passive_offer"):
            # Validation for assets (XLM needs no issuer, others do)
            if selling_asset_code.upper() != 'XLM' and not selling_asset_issuer:
                st.error("Selling Asset Issuer is required for non-XLM assets.")
                st.stop()
            if buying_asset_code.upper() != 'XLM' and not buying_asset_issuer:
                st.error("Buying Asset Issuer is required for non-XLM assets.")
                st.stop()

            if not selling_asset_code or not buying_asset_code:
                st.error("Selling Asset Code and Buying Asset Code are required.")
                st.stop()
            elif selling_asset_code == buying_asset_code and selling_asset_issuer == buying_asset_issuer:
                st.error("Selling and Buying assets cannot be the same.")
                st.stop()
            else:
                try:
                    selling_asset = get_asset_object(selling_asset_code, selling_asset_issuer)
                    buying_asset = get_asset_object(buying_asset_code, buying_asset_issuer)
                    account = asyncio.run(get_horizon_server().load_account(st.session_state.public_key))

                    operation = CreatePassiveSellOffer(
                        selling=selling_asset,
                        buying=buying_asset,
                        amount=str(amount),
                        price=str(price)
                    )

                    transaction = (
                        TransactionBuilder(
                            source_account=account,
                            network_passphrase=get_network_passphrase(),
                            base_fee=100
                        )
                        .add_operation(operation)
                        .set_memo(Memo.text(f"ApexStream PassiveSell {selling_asset_code}/{buying_asset_code}"))
                        .build()
                    )

                    xdr = transaction.to_xdr()
                    st.success("CreatePassiveSellOffer Transaction XDR Built!")
                    st.code(xdr, language="text")

                    with st.expander("Transaction Details (Raw XDR)"):
                        st.code(xdr, language="text")

                    if st.button("✍️ Sign with Freighter", key="sign_passive_offer_xdr"):
                        asyncio.run(sign_and_display_xdr(xdr, st.session_state.network))

                except Exception as e:
                    st.error(f"Error building PassiveSellOffer transaction: {e}")

    # --- TAB 3: Claim Claimable Balance ---
    with tab3:
        st.subheader("Harvest Rewards: Claim Claimable Balance 🎁")
        st.markdown("Claim existing claimable balances that have been distributed to your account.")

        balance_id = st.text_input("Claimable Balance ID", key="claim_balance_id", value="0000000000000000000000000000000000000000000000000000000000000000")
        st.caption("You'll need to know the specific ID of the claimable balance to claim it.")
        st.caption("Finding claimable balances for an account can be done via Horizon API: `YOUR_HORIZON_URL/accounts/YOUR_PUBLIC_KEY/claimable_balances`")

        if st.button("🏗️ Build ClaimClaimableBalance Transaction", key="build_claim_balance"):
            if not balance_id or balance_id.strip('0') == '': # Basic check for empty or all-zero
                st.error("Claimable Balance ID is required.")
                st.stop()
            else:
                try:
                    account = asyncio.run(get_horizon_server().load_account(st.session_state.public_key))

                    operation = ClaimClaimableBalance(
                        balance_id=balance_id
                    )

                    transaction = (
                        TransactionBuilder(
                            source_account=account,
                            network_passphrase=get_network_passphrase(),
                            base_fee=100
                        )
                        .add_operation(operation)
                        .set_memo(Memo.text("ApexStream ClaimReward"))
                        .build()
                    )

                    xdr = transaction.to_xdr()
                    st.success("ClaimClaimableBalance Transaction XDR Built!")
                    st.code(xdr, language="text")

                    with st.expander("Transaction Details (Raw XDR)"):
                        st.code(xdr, language="text")

                    if st.button("✍️ Sign with Freighter", key="sign_claim_balance_xdr"):
                        asyncio.run(sign_and_display_xdr(xdr, st.session_state.network))

                except Exception as e:
                    st.error(f"Error building ClaimClaimableBalance transaction: {e}")

    # --- TAB 4: Path Payment Strict Receive ---
    with tab4:
        st.subheader("Consolidate Earnings: Path Payment Strict Receive 🔄")
        st.markdown("Convert diversified assets into a single target asset via a payment path.")

        col_send_code, col_send_issuer = st.columns(2)
        with col_send_code:
            send_asset_code = st.text_input("Send Asset Code (e.g., USD)", key="pp_send_code", value="USD")
        with col_send_issuer:
            send_asset_issuer = st.text_input("Send Asset Issuer (or leave empty for XLM)", key="pp_send_issuer", value="GAXLYH63H47C62N7S5ZB2S6M66E6Y75BPTL525Y4N344R7Y6EELHHKLM")

        send_max = st.number_input("Max Send Amount", min_value=0.0000001, value=100.0, format="%.7f", key="pp_send_max")

        col_dest_code, col_dest_issuer = st.columns(2)
        with col_dest_code:
            dest_asset_code = st.text_input("Destination Asset Code (e.g., EURT)", key="pp_dest_code", value="EURT")
        with col_dest_issuer:
            dest_asset_issuer = st.text_input("Destination Asset Issuer (or leave empty for XLM)", key="pp_dest_issuer", value="GAXLYH63H47C62N7S5ZB2S6M66E6Y75BPTL525Y4N344R7Y6EELHHKLM")

        dest_amount = st.number_input("Destination Amount (Exact Receive)", min_value=0.0000001, value=10.0, format="%.7f", key="pp_dest_amount")
        destination_account = st.text_input("Recipient Public Key", key="pp_destination_account", value=st.session_state.public_key)

        path_assets_str = st.text_input(
            "Path Assets (Optional, comma-separated 'CODE:ISSUER' or 'XLM')",
            key="pp_path_assets",
            value="XLM"
        )
        st.caption("Example: `USD:GAXLY...,XLM,EURT:GBABC...`")

        if st.button("🏗️ Build PathPaymentStrictReceive Transaction", key="build_path_payment"):
            # Validation for assets (XLM needs no issuer, others do)
            if send_asset_code.upper() != 'XLM' and not send_asset_issuer:
                st.error("Sending Asset Issuer is required for non-XLM assets.")
                st.stop()
            if dest_asset_code.upper() != 'XLM' and not dest_asset_issuer:
                st.error("Destination Asset Issuer is required for non-XLM assets.")
                st.stop()

            if not all([send_asset_code, dest_asset_code, destination_account]):
                st.error("All asset details, destination account, and amounts are required.")
                st.stop()
            else:
                try:
                    send_asset = get_asset_object(send_asset_code, send_asset_issuer)
                    dest_asset = get_asset_object(dest_asset_code, dest_asset_issuer)

                    path = []
                    if path_assets_str:
                        for p_asset_str in path_assets_str.split(','):
                            p_asset_str = p_asset_str.strip()
                            if p_asset_str.upper() == 'XLM':
                                path.append(Asset.native())
                            else:
                                parts = p_asset_str.split(':')
                                if len(parts) == 2:
                                    # Ensure issuer is not empty for non-XLM path assets
                                    if not parts[1].strip():
                                        st.error(f"Path asset '{parts[0]}' requires an issuer.")
                                        st.stop()
                                    path.append(Asset(parts[0].strip(), parts[1].strip()))
                                else:
                                    st.error(f"Invalid path asset format: {p_asset_str}. Use 'CODE:ISSUER' or 'XLM'.")
                                    st.stop()
                    account = asyncio.run(get_horizon_server().load_account(st.session_state.public_key))

                    operation = PathPaymentStrictReceive(
                        send_asset=send_asset,
                        send_max=str(send_max),
                        destination=destination_account,
                        dest_asset=dest_asset,
                        dest_amount=str(dest_amount),
                        path=path
                    )

                    transaction = (
                        TransactionBuilder(
                            source_account=account,
                            network_passphrase=get_network_passphrase(),
                            base_fee=100
                        )
                        .add_operation(operation)
                        .set_memo(Memo.text(f"ApexStream PathPayment"))
                        .build()
                    )

                    xdr = transaction.to_xdr()
                    st.success("PathPaymentStrictReceive Transaction XDR Built!")
                    st.code(xdr, language="text")

                    with st.expander("Transaction Details (Raw XDR)"):
                        st.code(xdr, language="text")

                    if st.button("✍️ Sign with Freighter", key="sign_path_payment_xdr"):
                        asyncio.run(sign_and_display_xdr(xdr, st.session_state.network))

                except Exception as e:
                    st.error(f"Error building PathPaymentStrictReceive transaction: {e}")


    # --- TAB 5: Set Options ---
    with tab5:
        st.subheader("Advanced Configurations: Set Options ⚙️")
        st.markdown("Configure advanced account settings like home domain, inflation destination, signers, and data entries.")

        st.info("💡 Only fill in the fields you wish to change. Leave others empty to ignore them.")

        master_weight = st.number_input("Master Key Weight (0-255)", min_value=0, max_value=255, value=None, help="New weight for the master key. Set 0 to disable if other signers exist.")
        low_threshold = st.number_input("Low Threshold (0-255)", min_value=0, max_value=255, value=None, help="Threshold for low security operations.")
        med_threshold = st.number_input("Medium Threshold (0-255)", min_value=0, max_value=255, value=None, help="Threshold for medium security operations.")
        high_threshold = st.number_input("High Threshold (0-255)", min_value=0, max_value=255, value=None, help="Threshold for high security operations.")
        inflation_dest = st.text_input("Inflation Destination Account (Public Key)", value="", help="Public key of the account to receive inflation.")
        home_domain = st.text_input("Home Domain", value="", help="Home domain for the account, e.g., 'example.com'.")
        clear_flags = st.multiselect(
            "Clear Account Flags (Optional)",
            options=["AUTH_REQUIRED", "AUTH_REVOCABLE", "AUTH_IMMUTABLE"],
            default=[],
            help="Select flags to clear from the account."
        )
        set_flags = st.multiselect(
            "Set Account Flags (Optional)",
            options=["AUTH_REQUIRED", "AUTH_REVOCABLE", "AUTH_IMMUTABLE"],
            default=[],
            help="Select flags to set on the account."
        )

        st.markdown("---")
        st.markdown("##### Add/Remove Signer")
        signer_key = st.text_input("Signer Public Key or Muxed Account ID", key="set_options_signer_key", value="")
        signer_weight = st.number_input("Signer Weight (0-255, 0 to remove)", min_value=0, max_value=255, value=None, key="set_options_signer_weight", help="Set to 0 to remove an existing signer.")

        st.markdown("---")
        st.markdown("##### Manage Data Entries")
        data_name = st.text_input("Data Entry Name", key="set_options_data_name", value="")
        data_value_input = st.text_area("Data Entry Value (will be Base64 encoded; leave empty to delete)", key="set_options_data_value_input", value="", height=80, help="Enter the raw string value here. It will be Base64 encoded for the transaction. Leave empty to delete.")

        if st.button("🏗️ Build SetOptions Transaction", key="build_set_options"):
            try:
                account = asyncio.run(get_horizon_server().load_account(st.session_state.public_key))

                # Prepare arguments for SetOptions, only include if provided
                kwargs = {}
                if master_weight is not None:
                    kwargs['master_key_weight'] = master_weight
                if low_threshold is not None:
                    kwargs['low_threshold'] = low_threshold
                if med_threshold is not None:
                    kwargs['med_threshold'] = med_threshold
                if high_threshold is not None:
                    kwargs['high_threshold'] = high_threshold
                if inflation_dest:
                    kwargs['inflation_dest'] = inflation_dest
                if home_domain:
                    kwargs['home_domain'] = home_domain

                # Handle flags
                _clear_flags = 0
                for flag in clear_flags:
                    if flag == "AUTH_REQUIRED": _clear_flags |= 1
                    elif flag == "AUTH_REVOCABLE": _clear_flags |= 2
                    elif flag == "AUTH_IMMUTABLE": _clear_flags |= 4
                if _clear_flags > 0:
                    kwargs['clear_flags'] = _clear_flags

                _set_flags = 0
                for flag in set_flags:
                    if flag == "AUTH_REQUIRED": _set_flags |= 1
                    elif flag == "AUTH_REVOCABLE": _set_flags |= 2
                    elif flag == "AUTH_IMMUTABLE": _set_flags |= 4
                if _set_flags > 0:
                    kwargs['set_flags'] = _set_flags

                # Handle signer
                if signer_key and signer_weight is not None:
                    try:
                        # Try to parse as MuxedAccount, fallback to Keypair.from_public_key
                        # Note: stellar-sdk's signer_key function handles both implicitly
                        kwargs['signer'] = Keypair.from_public_key(signer_key).signer_key(signer_weight)
                    except Exception as e:
                        st.error(f"Invalid signer key or format: {e}")
                        st.stop()
                elif signer_key and signer_weight is None:
                    st.warning("Please provide a signer weight (0-255) for the signer key.")
                    st.stop()


                # Handle data entry
                if data_name:
                    if data_value_input:
                        # Encode the input string to bytes, then base64 encode
                        encoded_bytes = data_value_input.encode('utf-8')
                        base64_value = base64.b64encode(encoded_bytes).decode('utf-8')
                        kwargs['set_data'] = {data_name: base64_value}
                    else: # If value is empty, delete the data entry
                        kwargs['set_data'] = {data_name: None} # Set to None to delete
                elif data_value_input: # If data_value_input is present but data_name is not
                    st.warning("Please provide a Data Entry Name if you are providing a Data Entry Value.")
                    st.stop()


                if not kwargs:
                    st.warning("No options selected to set. Please fill in at least one field.")
                    st.stop()

                operation = SetOptions(**kwargs)

                transaction = (
                    TransactionBuilder(
                        source_account=account,
                        network_passphrase=get_network_passphrase(),
                        base_fee=100
                    )
                    .add_operation(operation)
                    .set_memo(Memo.text("ApexStream SetOptions"))
                    .build()
                )

                xdr = transaction.to_xdr()
                st.success("SetOptions Transaction XDR Built!")
                st.code(xdr, language="text")

                with st.expander("Transaction Details (Raw XDR)"):
                    st.code(xdr, language="text")

                if st.button("✍️ Sign with Freighter", key="sign_set_options_xdr"):
                    asyncio.run(sign_and_display_xdr(xdr, st.session_state.network))

            except Exception as e:
                st.error(f"Error building SetOptions transaction: {e}")

# --- Query Params Integration (Example - required for mandate) ---
if not st.session_state.query_params_processed:
    if st.query_params.get("asset_code"):
        st.sidebar.info(f"Query parameter detected: Asset Code - `{st.query_params['asset_code']}`")
    if st.query_params.get("asset_issuer"):
         st.sidebar.info(f"Query parameter detected: Asset Issuer - `{st.query_params['asset_issuer']}`")
    # Mark as processed to avoid showing on every rerun
    st.session_state.query_params_processed = True


# --- Footer ---
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: var(--secondary-text-color); font-size: 0.8em;'>
        Built with ❤️ and Stellar. ApexStream © 2023.
    </div>
    """,
    unsafe_allow_html=True
)