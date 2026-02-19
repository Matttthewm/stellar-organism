import streamlit as st
import streamlit.components.v1 as components

import stellar_sdk
from stellar_sdk import Server, Keypair, TransactionBuilder, Network, Asset
from stellar_sdk.exceptions import BadRequestError, NotFoundError

import json
import asyncio
import random
import time

# --- Global Configuration ---
HORIZON_URL = "https://horizon-testnet.stellar.org/"
NETWORK_PASSPHRASE = Network.TESTNET_NETWORK_PASSPHRASE
SWIRL_ASSET_CODE = "SWIRL"
COSMIC_ASSET_CODE = "COSMIC"

# --- Custom CSS for Playful/Gamified Style ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Pacifico&family=Orbitron&display=swap');

    :root {
        --primary-color: #6C5CE7; /* Amethyst */
        --secondary-color: #A08BE7; /* Lighter Amethyst */
        --accent-color-1: #FFD700; /* Gold */
        --accent-color-2: #FF69B4; /* Hot Pink */
        --text-color: #FFFFFF;
        --background-color: #1A0033; /* Dark Purple */
        --card-background: #2C0059; /* Slightly lighter dark purple */
        --border-color: #4A0080; /* Medium Purple */
        --font-primary: 'Orbitron', sans-serif;
        --font-secondary: 'Pacifico', cursive;
    }

    body {
        font-family: var(--font-primary);
        color: var(--text-color);
        background-color: var(--background-color);
        background-image: linear-gradient(135deg, var(--background-color) 0%, #0D001A 100%);
        animation: gradient-shift 10s ease infinite;
    }
    
    @keyframes gradient-shift {
        0% {background-position: 0% 50%;}
        50% {background-position: 100% 50%;}
        100% {background-position: 0% 50%;}
    }

    h1, h2, h3, h4, h5, h6 {
        font-family: var(--font-secondary);
        color: var(--accent-color-1);
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
    }

    .stApp {
        background-color: transparent;
    }

    .stTextInput>div>div>input, .stSelectbox>div>div>select, .stNumberInput>div>div>input {
        background-color: var(--card-background);
        color: var(--text-color);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 10px;
        font-family: var(--font-primary);
    }

    .stButton>button {
        background-color: var(--primary-color);
        color: var(--text-color);
        border: none;
        padding: 12px 24px;
        border-radius: 25px;
        font-family: var(--font-primary);
        font-size: 1.1em;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.4);
        margin-top: 10px;
    }

    .stButton>button:hover {
        background-color: var(--secondary-color);
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.5);
    }

    .stMetric {
        background-color: var(--card-background);
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 15px;
        border: 1px solid var(--border-color);
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
    }

    .stMetric > div > div:first-child { /* Label */
        color: var(--accent-color-2) !important;
        font-size: 0.9em;
        font-family: var(--font-primary);
        text-transform: uppercase;
    }
    .stMetric > div > div:nth-child(2) > div { /* Value */
        color: var(--accent-color-1) !important;
        font-size: 2em;
        font-family: var(--font-secondary);
        margin-top: 5px;
    }
    .stMetric > div > div:nth-child(3) > div { /* Delta */
        color: #90EE90 !important;
        font-size: 0.9em;
    }

    .stExpander {
        background-color: var(--card-background);
        border-radius: 12px;
        border: 1px solid var(--border-color);
        margin-bottom: 15px;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
    }
    .stExpander button {
        color: var(--text-color);
        font-family: var(--font-secondary);
        font-size: 1.2em;
    }

    .stAlert {
        border-radius: 8px;
        background-color: var(--card-background);
        border: 1px solid var(--border-color);
        color: var(--text-color);
        font-family: var(--font-primary);
    }
    .stAlert > div > div {
        color: var(--text-color) !important;
    }

    .stRadio > label {
        color: var(--text-color);
        font-family: var(--font-primary);
    }

    div.stSpinner > div {
        color: var(--accent-color-1);
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- Freighter Integration (JS component) ---
FREIGHTER_JS = """
<script src="https://unpkg.com/@stellar/freighter-api@latest/dist/freighter-api.js"></script>
<script>
    window.stellarFreighter = {
        async getPublicKey() {
            try {
                const publicKey = await StellarFreighterApi.getPublicKey();
                return { success: true, publicKey: publicKey };
            } catch (error) {
                return { success: false, error: error.message };
            }
        },
        async signTransaction(xdr, networkPassphrase) {
            try {
                const signedXdr = await StellarFreighterApi.signTransaction(xdr, { network: networkPassphrase });
                return { success: true, signedXdr: signedXdr };
            } catch (error) {
                return { success: false, error: error.message };
            }
        },
        async isConnected() {
            const isConnected = await StellarFreighterApi.isConnected();
            return { success: true, isConnected: isConnected };
        },
        async getNetwork() {
            try {
                const network = await StellarFreighterApi.getNetwork();
                return { success: true, network: network };
            } catch (error) {
                return { success: false, error: error.message };
            }
        }
    };
</script>
"""
components.html(FREIGHTER_JS, height=0, width=0)

# --- Stellar Server & Issuer Setup ---
server = Server(HORIZON_URL)

# Initialize session state for issuer key and counter
if "ISSUER_KEY" in st.secrets:
    ISSUER_KEYPAIR = Keypair.from_secret(st.secrets["ISSUER_KEY"])
else:
    if "demo_key" not in st.session_state:
        st.session_state.demo_key = Keypair.random().secret
    ISSUER_KEYPAIR = Keypair.from_secret(st.session_state.demo_key)
    st.sidebar.warning("Using Ephemeral Demo Keys for Asset Issuer ⚠️")
    st.sidebar.caption(f"Demo Issuer Public Key: `{ISSUER_KEYPAIR.public_key[:8]}...`")

ISSUER_ACCOUNT_ID = ISSUER_KEYPAIR.public_key
SWIRL_ASSET = Asset(SWIRL_ASSET_CODE, ISSUER_ACCOUNT_ID)
COSMIC_ASSET = Asset(COSMIC_ASSET_CODE, ISSUER_ACCOUNT_ID)

# --- Helper Functions ---
@st.cache_resource
def get_server_instance():
    return Server(HORIZON_URL)

def get_freighter_public_key():
    return components.html(
        f"""
        <script>
            window.stellarFreighter.getPublicKey().then(result => {{
                if (result.success) {{
                    window.parent.postMessage({{"type": "freighter_pk", "publicKey": result.publicKey}}, "*");
                }} else {{
                    window.parent.postMessage({{"type": "freighter_error", "error": result.error}}, "*");
                }}
            }});
        </script>
        """,
        height=0, width=0,
        key="get_pk_script"
    )

def sign_and_submit_with_freighter(xdr_b64):
    return components.html(
        f"""
        <script>
            window.stellarFreighter.signTransaction('{xdr_b64}', '{NETWORK_PASSPHRASE}').then(result => {{
                if (result.success) {{
                    window.parent.postMessage({{"type": "freighter_signed_xdr", "signedXdr": result.signedXdr}}, "*");
                }} else {{
                    window.parent.postMessage({{"type": "freighter_error", "error": result.error}}, "*");
                }}
            }});
        </script>
        """,
        height=0, width=0,
        key=f"sign_tx_{time.time()}" # Unique key for each call
    )

def load_account_data(public_key):
    try:
        account = server.load_account(public_key=public_key)
        return account
    except NotFoundError:
        st.error(f"Account {public_key} not found on Testnet. Please fund it using a Testnet Lumen Faucet (e.g., friendbot for new accounts).")
        return None
    except BadRequestError as e:
        st.error(f"Bad request to Horizon: {e}")
        return None
    except Exception as e:
        st.error(f"Error loading account data: {e}")
        return None

def get_asset_balance(account_balances, asset_code, issuer_id=None):
    for balance in account_balances:
        if balance['asset_type'] == 'native' and asset_code == 'XLM':
            return float(balance['balance'])
        elif balance['asset_code'] == asset_code and balance['asset_issuer'] == issuer_id:
            return float(balance['balance'])
    return 0.0

def listen_for_freighter_response():
    query_params = st.query_params
    if "freighter_pk" in query_params:
        pk = query_params["freighter_pk"]
        st.session_state.public_key = pk
        st.session_state.freighter_connected = True
        del st.query_params["freighter_pk"] # Clear it to avoid re-processing
        st.rerun()
    elif "freighter_error" in query_params:
        error_msg = query_params["freighter_error"]
        st.error(f"Freighter Error: {error_msg}")
        del st.query_params["freighter_error"]
        st.rerun()
    elif "freighter_signed_xdr" in query_params:
        signed_xdr = query_params["freighter_signed_xdr"]
        st.session_state.signed_xdr_to_submit = signed_xdr
        del st.query_params["freighter_signed_xdr"]
        st.rerun()

def generate_swirl_traits():
    colors = ["Crimson", "Azure", "Emerald", "Golden", "Amethyst", "Sapphire", "Ruby"]
    patterns = ["Swirling Nebula", "Stardust Sparkle", "Cosmic Dust Trail", "Galactic Bloom", "Quantum Ripple"]
    shimmers = ["Faintly Pulsing", "Radiant", "Glimmering", "Ethereal", "Vibrant"]
    rarities = ["Common", "Uncommon", "Rare", "Epic", "Legendary"]

    color = random.choice(colors)
    pattern = random.choice(patterns)
    shimmer = random.choice(shimmers)
    rarity = random.choice(rarities)

    return {
        "color": color,
        "pattern": pattern,
        "shimmer": shimmer,
        "rarity": rarity
    }

# --- Session State Initialization ---
if "freighter_connected" not in st.session_state:
    st.session_state.freighter_connected = False
if "public_key" not in st.session_state:
    st.session_state.public_key = ""
if "signed_xdr_to_submit" not in st.session_state:
    st.session_state.signed_xdr_to_submit = None
if "swirl_id_counter" not in st.session_state:
    st.session_state.swirl_id_counter = 0

# --- Sidebar ---
st.sidebar.info("🌌 Stardust Swirl Emporium 🌠\n\n**Concept:** Cultivate unique 'Stardust Swirl' tokens, trade them in a vibrant marketplace, or purchase rare cosmic essences instantly!")
st.sidebar.caption("✨ **Visual Style:** Playful & Gamified")
st.sidebar.markdown("---")
st.sidebar.header("Connection Status")

if st.session_state.freighter_connected:
    st.sidebar.success("Freighter Connected! 🎉")
    st.sidebar.markdown(f"**Wallet:** `{st.session_state.public_key[:8]}...`")
else:
    st.sidebar.warning("Freighter Not Connected")
    if st.sidebar.button("🔗 Connect Freighter Wallet", key="sidebar_connect"):
        get_freighter_public_key()
        st.toast("Connecting to Freighter...", icon="⏳")

# Listen for Freighter responses
listen_for_freighter_response()

# --- Main App ---
st.title("🌌 Stardust Swirl Emporium 🌠")

if not st.session_state.freighter_connected:
    st.info("Please connect your Freighter wallet to begin your cosmic adventure! ✨")
    st.stop()

# Load user account data
user_account = load_account_data(st.session_state.public_key)
if user_account is None:
    st.stop()

# Display User Account Balances
st.subheader("Your Cosmic Wallet 🪐")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="XLM Balance", value=f"{get_asset_balance(user_account.balances, 'XLM'):.2f} XLM 🚀")
with col2:
    st.metric(label=f"{SWIRL_ASSET_CODE} Balance", value=f"{get_asset_balance(user_account.balances, SWIRL_ASSET_CODE, ISSUER_ACCOUNT_ID):.2f} SWIRL ✨")
with col3:
    st.metric(label=f"{COSMIC_ASSET_CODE} Balance", value=f"{get_asset_balance(user_account.balances, COSMIC_ASSET_CODE, ISSUER_ACCOUNT_ID):.2f} COSMIC 🌟")

# Check if issuer account is funded (only for demo mode)
if "demo_key" in st.session_state:
    try:
        issuer_account = server.load_account(ISSUER_ACCOUNT_ID)
        if get_asset_balance(issuer_account.balances, 'XLM') < 10:
            st.warning(f"Demo Issuer account has low XLM balance ({get_asset_balance(issuer_account.balances, 'XLM'):.2f} XLM). Assets might not be distributed. Please fund `{ISSUER_ACCOUNT_ID}` via friendbot.")
    except NotFoundError:
        st.error(f"Demo Issuer account `{ISSUER_ACCOUNT_ID}` not found. Cannot issue assets. Please fund it via friendbot.")
        st.stop()
    except Exception as e:
        st.error(f"Error checking demo issuer account: {e}")
        st.stop()

# --- Handle signed_xdr_to_submit ---
if st.session_state.signed_xdr_to_submit:
    st.subheader("Submitting Transaction... 🚀")
    signed_xdr = st.session_state.signed_xdr_to_submit
    try:
        with st.spinner("Broadcasting transaction to Stellar Network..."):
            response = server.submit_transaction(signed_xdr)
            st.success(f"Transaction successful! 🎉 [View on StellarExpert](https://testnet.stellarexpert.io/tx/{response['hash']})")
            st.balloons()
            st.session_state.signed_xdr_to_submit = None # Clear after submission
            st.rerun() # Refresh account data
    except BadRequestError as e:
        st.error(f"Transaction failed: {e.extras.get('result_codes', {}).get('transaction', 'Unknown error')}")
        st.exception(e)
        st.session_state.signed_xdr_to_submit = None
    except Exception as e:
        st.error(f"An unexpected error occurred during transaction submission: {e}")
        st.session_state.signed_xdr_to_submit = None


# --- 1. Cultivate Stardust Swirls (ChangeTrust + ManageData) ---
with st.expander("✨ Cultivate Your Own Stardust Swirls ✨", expanded=True):
    st.markdown("Embark on a journey to claim your unique Stardust Swirl tokens and embed their cosmic traits! ")

    has_swirl_trustline = get_asset_balance(user_account.balances, SWIRL_ASSET_CODE, ISSUER_ACCOUNT_ID) >= 0.0

    if not has_swirl_trustline:
        st.warning(f"You don't have a trustline for {SWIRL_ASSET_CODE}. Establish one to start cultivating!")
        if st.button("🌌 Establish SWIRL Trustline", key="create_trustline_swirl"):
            try:
                source_account = server.load_account(st.session_state.public_key)
                transaction = TransactionBuilder(
                    source_account=source_account,
                    network_passphrase=NETWORK_PASSPHRASE,
                    base_fee=100
                ).append_change_trust_op(
                    asset=SWIRL_ASSET,
                    limit="100000000000" # High limit for demo
                ).set_timeout(30).build()
                transaction_xdr = transaction.to_xdr()
                sign_and_submit_with_freighter(transaction_xdr)
                st.info("Awaiting Freighter signature for ChangeTrust operation...")
            except Exception as e:
                st.error(f"Error preparing ChangeTrust transaction: {e}")
    else:
        st.success(f"Trustline for {SWIRL_ASSET_CODE} already established. You're ready to cultivate! 🎉")

        st.markdown("---")
        st.subheader("Receive a Stardust Swirl")
        st.markdown("Once you have a trustline, you can receive a *sample* Stardust Swirl from the Emporium!")
        if st.button("🌠 Receive a Stardust Swirl (1 SWIRL)", key="receive_swirl"):
            try:
                source_account = server.load_account(ISSUER_ACCOUNT_ID) # Issuer is sending
                transaction = TransactionBuilder(
                    source_account=source_account,
                    network_passphrase=NETWORK_PASSPHRASE,
                    base_fee=100
                ).append_payment_op(
                    destination=st.session_state.public_key,
                    asset=SWIRL_ASSET,
                    amount="1"
                ).set_timeout(30).build()
                transaction.sign(ISSUER_KEYPAIR) # Issuer signs directly
                
                with st.spinner("Sending Stardust Swirl..."):
                    response = server.submit_transaction(transaction.to_xdr())
                    st.success(f"You've received a Stardust Swirl! ✨ [Tx](https://testnet.stellarexpert.io/tx/{response['hash']})")
                    st.rerun()
            except Exception as e:
                st.error(f"Error sending Stardust Swirl: {e}")

        st.markdown("---")
        st.subheader("Record Your Swirl's Unique Traits")
        st.markdown("Generate and store a custom trait description for your Swirl directly on your account! Each trait entry will be unique.")

        current_swirl_balance = get_asset_balance(user_account.balances, SWIRL_ASSET_CODE, ISSUER_ACCOUNT_ID)
        if current_swirl_balance > 0:
            traits = generate_swirl_traits()
            st.json(traits)
            trait_name = st.text_input("Give your Swirl Trait a Name (e.g., 'MyFirstSwirl')", value=f"CosmicSwirl-{st.session_state.swirl_id_counter + 1}")

            if st.button("💾 Record Swirl Traits (ManageData)", key="record_swirl_data"):
                try:
                    source_account = server.load_account(st.session_state.public_key)
                    swirl_data_key = f"SWIRL_ID_{st.session_state.swirl_id_counter + 1}_{trait_name}"
                    swirl_data_value = json.dumps(traits)

                    if len(swirl_data_key) > 64:
                        st.error("Trait Name is too long. Please keep it under 64 characters combined with 'SWIRL_ID_X_'.")
                    elif len(swirl_data_value) > 64:
                         st.error("Generated trait value is too long. Try again or simplify traits.") # Should not happen with current traits
                    else:
                        transaction = TransactionBuilder(
                            source_account=source_account,
                            network_passphrase=NETWORK_PASSPHRASE,
                            base_fee=100
                        ).append_manage_data_op(
                            data_name=swirl_data_key,
                            data_value=swirl_data_value.encode('utf-8')
                        ).set_timeout(30).build()
                        transaction_xdr = transaction.to_xdr()
                        sign_and_submit_with_freighter(transaction_xdr)
                        st.session_state.swirl_id_counter += 1
                        st.info("Awaiting Freighter signature for ManageData operation...")
                except Exception as e:
                    st.error(f"Error preparing ManageData transaction: {e}")
        else:
            st.info("Receive at least one Stardust Swirl to record its traits! ✨")

# --- 2. Stardust Swirl Marketplace (ManageBuyOffer & CreatePassiveSellOffer) ---
with st.expander("🛒 Stardust Swirl Marketplace 💫"):
    st.markdown("Buy and sell your unique Stardust Swirls here! Trade with others using XLM.")

    sell_col, buy_col = st.columns(2)

    with sell_col:
        st.subheader("Sell Your Swirls 🌠")
        st.markdown("List your Stardust Swirls for sale using a passive offer.")

        sell_swirl_amount = st.number_input(f"Amount of {SWIRL_ASSET_CODE} to sell:", min_value=0.01, value=1.0, step=0.1, format="%.2f", key="sell_swirl_amt")
        sell_swirl_price_xlm = st.number_input(f"Price per {SWIRL_ASSET_CODE} (in XLM):", min_value=0.01, value=10.0, step=0.1, format="%.2f", key="sell_swirl_price")

        if st.button("🚀 Create Passive Sell Offer", key="create_sell_offer"):
            if sell_swirl_amount > get_asset_balance(user_account.balances, SWIRL_ASSET_CODE, ISSUER_ACCOUNT_ID):
                st.error(f"You only have {get_asset_balance(user_account.balances, SWIRL_ASSET_CODE, ISSUER_ACCOUNT_ID):.2f} {SWIRL_ASSET_CODE} to sell.")
            else:
                try:
                    source_account = server.load_account(st.session_state.public_key)
                    transaction = TransactionBuilder(
                        source_account=source_account,
                        network_passphrase=NETWORK_PASSPHRASE,
                        base_fee=100
                    ).append_create_passive_sell_offer_op(
                        selling=SWIRL_ASSET,
                        buying=Asset.native(),
                        amount=str(sell_swirl_amount),
                        price=str(sell_swirl_price_xlm)
                    ).set_timeout(30).build()
                    transaction_xdr = transaction.to_xdr()
                    sign_and_submit_with_freighter(transaction_xdr)
                    st.info("Awaiting Freighter signature for CreatePassiveSellOffer operation...")
                except Exception as e:
                    st.error(f"Error preparing CreatePassiveSellOffer transaction: {e}")

    with buy_col:
        st.subheader("Buy Swirls 💰")
        st.markdown("Make an offer to buy Stardust Swirls from others.")

        buy_swirl_amount = st.number_input(f"Amount of {SWIRL_ASSET_CODE} to buy:", min_value=0.01, value=1.0, step=0.1, format="%.2f", key="buy_swirl_amt")
        buy_swirl_price_xlm = st.number_input(f"Max XLM to pay per {SWIRL_ASSET_CODE}:", min_value=0.01, value=10.0, step=0.1, format="%.2f", key="buy_swirl_price")
        total_xlm_cost = buy_swirl_amount * buy_swirl_price_xlm

        st.caption(f"Total XLM cost for this offer: {total_xlm_cost:.2f} XLM")

        if st.button("✨ Create Buy Offer", key="create_buy_offer"):
            if total_xlm_cost > get_asset_balance(user_account.balances, 'XLM'):
                st.error(f"You only have {get_asset_balance(user_account.balances, 'XLM'):.2f} XLM. You need {total_xlm_cost:.2f} XLM for this offer.")
            else:
                try:
                    source_account = server.load_account(st.session_state.public_key)
                    
                    # Ensure trustline for SWIRL exists before creating buy offer
                    if not has_swirl_trustline:
                        st.warning(f"You need a trustline for {SWIRL_ASSET_CODE} to receive them when your buy offer is met.")
                        st.stop()

                    transaction = TransactionBuilder(
                        source_account=source_account,
                        network_passphrase=NETWORK_PASSPHRASE,
                        base_fee=100
                    ).append_manage_buy_offer_op(
                        selling=Asset.native(), # Selling XLM
                        buying=SWIRL_ASSET,    # Buying SWIRL
                        buy_amount=str(buy_swirl_amount),
                        price=str(1/buy_swirl_price_xlm) # Price is Selling/Buying, so XLM/SWIRL. Here we want SWIRL/XLM for ManageBuyOffer.
                                                        # It's amount of buying asset / amount of selling asset.
                                                        # If buying 1 SWIRL for 10 XLM, price is 1/10 = 0.1
                    ).set_timeout(30).build()
                    transaction_xdr = transaction.to_xdr()
                    sign_and_submit_with_freighter(transaction_xdr)
                    st.info("Awaiting Freighter signature for ManageBuyOffer operation...")
                except Exception as e:
                    st.error(f"Error preparing ManageBuyOffer transaction: {e}")


# --- 3. Cosmic Essence Emporium (PathPaymentStrictReceive) ---
with st.expander("🌟 Cosmic Essence Emporium 🌟"):
    st.markdown("Instantly purchase rare Cosmic Essence (COSMIC) using your XLM! No offers, just direct cosmic exchange.")

    has_cosmic_trustline = get_asset_balance(user_account.balances, COSMIC_ASSET_CODE, ISSUER_ACCOUNT_ID) >= 0.0

    if not has_cosmic_trustline:
        st.warning(f"You don't have a trustline for {COSMIC_ASSET_CODE}. Establish one to receive Cosmic Essence!")
        if st.button("✨ Establish COSMIC Trustline", key="create_trustline_cosmic"):
            try:
                source_account = server.load_account(st.session_state.public_key)
                transaction = TransactionBuilder(
                    source_account=source_account,
                    network_passphrase=NETWORK_PASSPHRASE,
                    base_fee=100
                ).append_change_trust_op(
                    asset=COSMIC_ASSET,
                    limit="100000000000" # High limit for demo
                ).set_timeout(30).build()
                transaction_xdr = transaction.to_xdr()
                sign_and_submit_with_freighter(transaction_xdr)
                st.info("Awaiting Freighter signature for ChangeTrust operation...")
            except Exception as e:
                st.error(f"Error preparing ChangeTrust transaction: {e}")
    else:
        st.success(f"Trustline for {COSMIC_ASSET_CODE} already established. You can buy Cosmic Essence! 🎉")

        st.markdown("---")
        cosmic_amount = st.number_input(f"Amount of {COSMIC_ASSET_CODE} to purchase:", min_value=0.01, value=1.0, step=0.1, format="%.2f", key="buy_cosmic_amt")
        max_xlm_to_spend = st.number_input("Max XLM to spend:", min_value=0.01, value=50.0, step=0.1, format="%.2f", key="max_xlm_spend")
        
        # In a real scenario, the issuer might have a fixed price. For demo, we assume a simple exchange.
        # Let's say 1 COSMIC costs 20 XLM for this demo
        estimated_xlm_cost = cosmic_amount * 20
        st.caption(f"Estimated XLM cost for {cosmic_amount} {COSMIC_ASSET_CODE}: ~{estimated_xlm_cost:.2f} XLM")
        if estimated_xlm_cost > max_xlm_to_spend:
            st.warning(f"Your 'Max XLM to spend' ({max_xlm_to_spend:.2f} XLM) might be too low to receive {cosmic_amount} {COSMIC_ASSET_CODE} at a rate of 20 XLM/COSMIC.")


        if st.button("🛒 Purchase Cosmic Essence", key="purchase_cosmic"):
            if max_xlm_to_spend > get_asset_balance(user_account.balances, 'XLM'):
                st.error(f"You only have {get_asset_balance(user_account.balances, 'XLM'):.2f} XLM. You need at least {max_xlm_to_spend:.2f} XLM for this purchase.")
            else:
                try:
                    source_account = server.load_account(st.session_state.public_key)
                    # For PathPaymentStrictReceive, the issuer (seller) needs to provide the path
                    # For simplicity, we assume the user directly pays XLM to the issuer, and the issuer sends COSMIC.
                    # This means the destination is the user, and the sender is the user. The issuer is effectively a middleman
                    # whose account balances are checked implicitly during pathfinding.
                    # The issuer has to have a trustline for COSMIC and enough COSMIC to sell.
                    
                    transaction = TransactionBuilder(
                        source_account=source_account,
                        network_passphrase=NETWORK_PASSPHRASE,
                        base_fee=100
                    ).append_path_payment_strict_receive_op(
                        send_asset=Asset.native(), # User sends XLM
                        send_max=str(max_xlm_to_spend),
                        destination=st.session_state.public_key, # User receives COSMIC
                        dest_asset=COSMIC_ASSET,
                        dest_amount=str(cosmic_amount),
                        path=[Asset.native(), COSMIC_ASSET] # Path from XLM to COSMIC, potentially through the issuer.
                                                          # Simplest path is direct if issuer is the source/destination of assets
                                                          # For this setup, we simulate buying directly from the issuer.
                                                          # Path is needed if there are other intermediaries.
                                                          # A simple path `[Asset.native(), COSMIC_ASSET]` implies Stellar's DEX
                                                          # will find a way from native to COSMIC.
                                                          # For direct payment from A (XLM) to B (COSMIC), where B is the ultimate recipient
                                                          # and also the *seller* of COSMIC, it implies an existing offer from B.
                                                          # More straightforward for a demo: User sends XLM, receives COSMIC.
                                                          # The 'path' here is not for an intermediary account but for a general DEX path.
                    ).set_timeout(30).build()
                    transaction_xdr = transaction.to_xdr()
                    sign_and_submit_with_freighter(transaction_xdr)
                    st.info("Awaiting Freighter signature for PathPaymentStrictReceive operation...")
                except Exception as e:
                    st.error(f"Error preparing PathPaymentStrictReceive transaction: {e}")

st.markdown("---")
st.caption("Powered by Stellar & Streamlit ✨")