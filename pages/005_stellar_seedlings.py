import streamlit as st
import stellar_sdk
from stellar_sdk import Server, Keypair, TransactionBuilder, Network, Asset
from stellar_sdk.exceptions import BadRequestError, NotFoundError
import json
import time

# --- Configuration ---
HORIZON_URL = "https://horizon-testnet.stellar.org"
NETWORK_PASSPHRASE = Network.TESTNET_NETWORK_PASSPHRASE

# --- Stellar Account Details (Testnet) ---
# DANGER: NEVER EXPOSE PRIVATE KEYS IN PRODUCTION APPS
# These keys are for demonstration on Testnet. In a real app, manage securely via a backend.
# For local testing, create a .streamlit/secrets.toml file with:
# SEEDLING_ISSUER_SEED="SA...your_stellar_secret_key_for_issuer...A"
# GROW_FUND_SEED="SC...your_stellar_secret_key_for_grow_fund...C"
# Make sure these accounts are funded on Testnet via Friendbot:
# https://friendbot.stellar.org/?addr=YOUR_PUBLIC_KEY

try:
    SEEDLING_ISSUER_SEED = st.secrets["SEEDLING_ISSUER_SEED"]
    SEEDLING_ISSUER_KEYPAIR = Keypair.from_secret(SEEDLING_ISSUER_SEED)
    SEEDLING_ISSUER_PUBLIC_KEY = SEEDLING_ISSUER_KEYPAIR.public_key
    st.session_state["SEEDLING_ISSUER_PUBLIC_KEY"] = SEEDLING_ISSUER_PUBLIC_KEY
except (KeyError, ValueError) as e:
    st.error(f"Configuration Error: SEEDLING_ISSUER_SEED not found in st.secrets or is invalid. Please ensure it's set correctly. Error: {e}")
    st.stop()

try:
    GROW_FUND_SEED = st.secrets["GROW_FUND_SEED"]
    GROW_FUND_KEYPAIR = Keypair.from_secret(GROW_FUND_SEED)
    GROW_FUND_PUBLIC_KEY = GROW_FUND_KEYPAIR.public_key
    st.session_state["GROW_FUND_PUBLIC_KEY"] = GROW_FUND_PUBLIC_KEY
except (KeyError, ValueError) as e:
    st.error(f"Configuration Error: GROW_FUND_SEED not found in st.secrets or is invalid. Please ensure it's set correctly. Error: {e}")
    st.stop()

# --- Custom Asset ---
SEEDLING_ASSET = Asset("SEEDLING", SEEDLING_ISSUER_PUBLIC_KEY)


# --- Helper Functions ---
@st.cache_resource
def get_server():
    """Returns a Stellar Horizon Server instance."""
    return Server(HORIZON_URL)

def get_account_details(public_key):
    """Fetches account details from Horizon."""
    server = get_server()
    try:
        return server.load_account(public_key)
    except NotFoundError:
        return None
    except BadRequestError as e:
        st.error(f"Error loading account {public_key}: {e}")
        return None

def submit_transaction(signed_xdr: str):
    """Submits a signed transaction XDR to Horizon."""
    server = get_server()
    try:
        response = server.submit_transaction(signed_xdr)
        st.success(f"Transaction successful! Hash: `{response['hash']}`")
        st.balloons()
        st.write(f"See on Explorer: [StellarExpert](https://testnet.stellarexpert.io/tx/{response['hash']})")
        return response
    except BadRequestError as e:
        error_msg = f"Transaction failed! Error: `{e.extras.get('result_codes', {}).get('transaction', 'Unknown error')}`"
        op_errors = e.extras.get('result_codes', {}).get('operations', [])
        if op_errors:
            error_msg += f" Operations: {', '.join(op_errors)}"
        st.error(error_msg)
        st.exception(e)
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred during transaction submission: {e}")
        return None

def refresh_account_data():
    """Refreshes connected wallet's account data."""
    if st.session_state.get("public_key"):
        st.session_state["account_details"] = get_account_details(st.session_state["public_key"])
    st.rerun()

# --- Streamlit UI ---

# Custom CSS for Playful/Gamified Style
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Fredoka+One&family=Open+Sans:wght@400;700&display=swap');
    
    body {
        font-family: 'Open Sans', sans-serif;
        background-color: #f0f8ff; /* Alice Blue */
        color: #333;
    }
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Fredoka One', cursive;
        color: #4CAF50; /* Green */
        text-shadow: 2px 2px #98FB98; /* Pale Green */
    }
    .stApp {
        background: linear-gradient(135deg, #e0ffe0, #c0f0c0); /* Light green gradient */
    }
    .stButton>button {
        background-color: #FFD700; /* Gold */
        color: #8B4513; /* Saddle Brown */
        border-radius: 25px;
        border: 2px solid #DAA520; /* Goldenrod */
        padding: 10px 20px;
        font-weight: bold;
        font-size: 16px;
        box-shadow: 3px 3px 5px rgba(0,0,0,0.2);
        transition: all 0.2s ease-in-out;
        cursor: pointer;
    }
    .stButton>button:hover {
        background-color: #DAA520; /* Goldenrod */
        color: #fff;
        transform: translateY(-2px);
        box-shadow: 5px 5px 8px rgba(0,0,0,0.3);
    }
    .stTextInput>div>div>input {
        border-radius: 15px;
        border: 1px solid #98FB98;
        padding: 8px 12px;
        background-color: #FFFACD; /* Lemon Chiffon */
    }
    .stMetric {
        background-color: #fff;
        border-radius: 15px;
        padding: 15px;
        margin-bottom: 10px;
        box-shadow: 2px 2px 8px rgba(0,0,0,0.1);
        text-align: center;
        border: 1px solid #add8e6; /* Light Blue */
    }
    .stExpander {
        border: 1px solid #add8e6;
        border-radius: 10px;
        padding: 10px;
        background-color: #e0f2f7; /* Light Cyan */
    }
    .stAlert {
        border-radius: 10px;
    }
    .header-style {
        font-size: 2.5em;
        text-align: center;
        margin-bottom: 20px;
        color: #2e8b57; /* Sea Green */
        text-shadow: 3px 3px #8fbc8f; /* Dark Sea Green */
    }
    .subheader-style {
        font-size: 1.8em;
        color: #6b8e23; /* Olive Drab */
        margin-top: 20px;
        margin-bottom: 15px;
    }
    .footer-text {
        text-align: center;
        margin-top: 50px;
        font-size: 0.8em;
        color: #666;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("<h1 class='header-style'>✨ Stellar Seedlings 🚀</h1>", unsafe_allow_html=True)
st.write("Nurture unique digital flora, trade in the intergalactic market, and contribute to the communal Grow-Fund!")

# --- Freighter Integration (JavaScript Component) ---
# This JS snippet handles connecting to Freighter and signing transactions.
# It uses window.location.href to communicate results back to Streamlit via query_params.
FREIGHTER_JS = """
<script>
    async function connectFreighter() {
        if (!window.freighter) {
            alert("Freighter wallet not detected! Please install Freighter browser extension.");
            return;
        }
        try {
            const publicKey = await window.freighter.getPublicKey();
            window.location.href = `?public_key=${publicKey}`;
        } catch (error) {
            console.error("Freighter connection failed:", error);
            alert("Failed to connect to Freighter. " + error.message);
        }
    }

    async function signTransaction(xdr) {
        if (!window.freighter) {
            alert("Freighter wallet not detected! Please install Freighter browser extension.");
            return;
        }
        try {
            const signedXDR = await window.freighter.signTransaction(xdr);
            window.location.href = `?signed_xdr=${encodeURIComponent(signedXDR)}`;
        } catch (error) {
            console.error("Freighter signing failed:", error);
            alert("Failed to sign transaction. " + error.message);
            window.location.href = `?signed_xdr_error=${encodeURIComponent(error.message)}`;
        }
    }
</script>
"""
st.components.v1.html(FREIGHTER_JS, height=0) # Embed the JS, keep it hidden

# --- Session State Initialization ---
if "public_key" not in st.session_state:
    st.session_state["public_key"] = None
if "account_details" not in st.session_state:
    st.session_state["account_details"] = None

# --- Process Query Params for Freighter ---
query_params = st.query_params

if "public_key" in query_params:
    pk = query_params["public_key"]
    if pk and pk != st.session_state["public_key"]: # Only update if new public key
        st.session_state["public_key"] = pk
        st.session_state["account_details"] = get_account_details(st.session_state["public_key"])
        st.success(f"Connected to Freighter with public key: `{st.session_state['public_key']}`")
        st.query_params.clear() 
        st.rerun() 
    elif not st.session_state["public_key"]: # If no public key in session but exists in query (e.g. initial load)
         st.session_state["public_key"] = pk
         st.session_state["account_details"] = get_account_details(st.session_state["public_key"])
         st.success(f"Connected to Freighter with public key: `{st.session_state['public_key']}`")
         st.query_params.clear()
         st.rerun()


if "signed_xdr" in query_params:
    signed_xdr = query_params["signed_xdr"]
    st.query_params.clear() # Clear the signed_xdr param immediately
    st.info("Submitting transaction...")
    response = submit_transaction(signed_xdr)
    if response:
        refresh_account_data() # Refresh account data after a successful transaction
    else:
        st.error("Transaction submission failed.")
    st.rerun() # Rerun to clear query params and update UI

if "signed_xdr_error" in query_params:
    error_message = query_params["signed_xdr_error"]
    st.error(f"Transaction signing cancelled or failed in Freighter: {error_message}")
    st.query_params.clear()
    st.rerun()

# --- Wallet Connection Section ---
st.markdown("<h2 class='subheader-style'>Connect Your Stellar Sprout 🌱 Wallet</h2>", unsafe_allow_html=True)
if not st.session_state["public_key"]:
    st.button("Connect Freighter Wallet 🚀", on_click=lambda: st.components.v1.html('<script>connectFreighter();</script>', height=0), use_container_width=True)
else:
    st.info(f"Connected Public Key: `{st.session_state['public_key']}`")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Refresh Account Data 🔄", use_container_width=True):
            refresh_account_data()
    with col2:
        if st.button("Disconnect Wallet 🔌", use_container_width=True):
            st.session_state["public_key"] = None
            st.session_state["account_details"] = None
            st.query_params.clear() # Clear all query params on disconnect
            st.rerun()

# Display account details if connected
if st.session_state["account_details"]:
    account = st.session_state["account_details"]
    st.markdown("<h3 class='subheader-style'>Your Cosmic Garden 🏡</h3>", unsafe_allow_html=True)

    # Display balances
    col1, col2, col3 = st.columns(3)
    xlm_balance = next((b["balance"] for b in account.balances if b["asset_type"] == "native"), "0")
    seedling_balance = next((b["balance"] for b in account.balances if b["asset_code"] == SEEDLING_ASSET.code and b["asset_issuer"] == SEEDLING_ASSET.issuer), "0")
    
    with col1:
        st.metric(label="XLM Balance 💰", value=f"{float(xlm_balance):,.2f}")
    with col2:
        st.metric(label="SEEDLINGs Planted 🪴", value=f"{float(seedling_balance):,.0f}")
    with col3:
        st.metric(label="Seq. Number #️⃣", value=account.sequence)

    # Check for trustline
    has_trustline = any(b["asset_code"] == SEEDLING_ASSET.code and b["asset_issuer"] == SEEDLING_ASSET.issuer for b in account.balances)
    if not has_trustline:
        st.warning(f"You don't have a trustline for {SEEDLING_ASSET.code}. You need one to receive SEEDLINGs.")
        if st.button(f"Create Trustline for {SEEDLING_ASSET.code} 🌱", use_container_width=True, key="create_trustline_btn"):
            try:
                # Get the latest account sequence for transaction building
                source_account = get_server().load_account(st.session_state["public_key"])
                transaction = (
                    TransactionBuilder(
                        source_account=source_account,
                        network_passphrase=NETWORK_PASSPHRASE,
                    )
                    .append_change_trust_op(asset=SEEDLING_ASSET)
                    .set_timeout(100)
                    .build()
                )
                xdr = transaction.to_envelope().to_xdr()
                st.info("Awaiting Freighter signature for Trustline creation...")
                st.components.v1.html(f"<script>signTransaction('{xdr}');</script>", height=0)
            except Exception as e:
                st.error(f"Failed to build trustline transaction: {e}")
                st.exception(e)
    else:
        st.success(f"You have a trustline for {SEEDLING_ASSET.code}. Ready to grow!")

    st.markdown("---")

    # --- Actions: Plant, Contribute, Market ---
    tab1, tab2, tab3 = st.tabs(["🌱 Plant Seedling", "💰 Grow-Fund", "🛍️ Seedling Market"])

    with tab1:
        st.markdown("<h3 class='subheader-style'>Plant a New Stellar Seedling 🧬</h3>", unsafe_allow_html=True)
        st.write("Receive a fresh `SEEDLING` from the Cosmos Nursery (our issuer account).")
        st.caption(f"Issuer Public Key: `{SEEDLING_ISSUER_PUBLIC_KEY}`")
        if not has_trustline:
            st.info("You need a trustline for SEEDLING before you can plant one.")
        elif st.button("Plant My Seedling! 🌿", use_container_width=True, key="plant_seedling_btn"):
            try:
                # Get the latest account sequence for transaction building
                issuer_account = get_server().load_account(SEEDLING_ISSUER_PUBLIC_KEY)
                transaction = (
                    TransactionBuilder(
                        source_account=issuer_account,
                        network_passphrase=NETWORK_PASSPHRASE,
                    )
                    .append_payment_op(
                        destination=st.session_state["public_key"],
                        asset=SEEDLING_ASSET,
                        amount="1", # Each plant gives 1 SEEDLING
                    )
                    .set_timeout(100)
                    .build()
                )
                # Issuer signs this transaction
                transaction.sign(SEEDLING_ISSUER_KEYPAIR)
                signed_xdr = transaction.to_envelope().to_xdr()
                st.info("Submitting transaction (issuer signed)...")
                response = submit_transaction(signed_xdr)
                if response:
                    refresh_account_data() # Refresh user's balance
            except Exception as e:
                st.error(f"Failed to plant seedling: {e}")
                st.exception(e)

    with tab2:
        st.markdown("<h3 class='subheader-style'>Contribute to the Galactic Grow-Fund 💸</h3>", unsafe_allow_html=True)
        st.write("Help expand our cosmic garden by contributing XLM. All contributions fuel future innovations!")
        st.caption(f"Grow-Fund Public Key: `{GROW_FUND_PUBLIC_KEY}`")

        grow_fund_details = get_account_details(GROW_FUND_PUBLIC_KEY)
        if grow_fund_details:
            grow_fund_balance = next((b["balance"] for b in grow_fund_details.balances if b["asset_type"] == "native"), "0")
            st.metric(label="Current Grow-Fund 🌟", value=f"{float(grow_fund_balance):,.2f} XLM")
        else:
            st.warning("Grow-Fund account not found on network. Please ensure it's funded via Friendbot.")
            st.markdown(f"[Fund Grow-Fund Account via Friendbot](https://friendbot.stellar.org/?addr={GROW_FUND_PUBLIC_KEY})")

        amount_to_contribute = st.number_input("Amount of XLM to Contribute:", min_value=0.01, value=1.0, step=0.1, key="growfund_amount")
        if st.button("Contribute XLM to Grow-Fund 🎉", use_container_width=True, key="contribute_growfund_btn"):
            try:
                source_account = get_server().load_account(st.session_state["public_key"])
                transaction = (
                    TransactionBuilder(
                        source_account=source_account,
                        network_passphrase=NETWORK_PASSPHRASE,
                    )
                    .append_payment_op(
                        destination=GROW_FUND_PUBLIC_KEY,
                        asset=Asset.native(),
                        amount=f"{amount_to_contribute:.7f}",
                    )
                    .set_timeout(100)
                    .build()
                )
                xdr = transaction.to_envelope().to_xdr()
                st.info("Awaiting Freighter signature for Grow-Fund contribution...")
                st.components.v1.html(f"<script>signTransaction('{xdr}');</script>", height=0)
            except Exception as e:
                st.error(f"Failed to build contribution transaction: {e}")
                st.exception(e)

    with tab3:
        st.markdown("<h3 class='subheader-style'>Intergalactic Seedling Market 🛒</h3>", unsafe_allow_html=True)
        st.write("Buy or sell `SEEDLING` assets in the open market.")
        st.caption("You can create offers to trade your `SEEDLING` for XLM, or vice-versa.")

        st.markdown("#### Your Active Offers 📈")
        server = get_server()
        try:
            offers_response = server.offers().for_account(st.session_state["public_key"]).call()
            offers = offers_response["_embedded"]["records"]
            
            seedling_offers = [
                o for o in offers
                if (o["selling"]["asset_type"] == "credit_alphanum4" and o["selling"]["asset_code"] == SEEDLING_ASSET.code and o["selling"]["asset_issuer"] == SEEDLING_ASSET.issuer) or
                   (o["buying"]["asset_type"] == "credit_alphanum4" and o["buying"]["asset_code"] == SEEDLING_ASSET.code and o["buying"]["asset_issuer"] == SEEDLING_ASSET.issuer)
            ]
            if seedling_offers:
                for i, offer in enumerate(seedling_offers):
                    offer_id = offer["id"]
                    amount = float(offer["amount"])
                    price = float(offer["price"]) # price is buying_asset/selling_asset
                    
                    if offer["selling"]["asset_type"] == "native" and \
                       offer["buying"]["asset_code"] == SEEDLING_ASSET.code: # Buying SEEDLING with XLM (selling XLM)
                        total_xlm_committed = amount # Amount is the selling asset amount (XLM)
                        seedlings_to_receive = total_xlm_committed * price # price is SEEDLING/XLM
                        display_text = f"**Offer {i+1} (ID: `{offer_id}`):** Buying `{seedlings_to_receive:,.2f} {SEEDLING_ASSET.code}` with `{total_xlm_committed:,.2f} XLM` (Price: `{price:,.2f} {SEEDLING_ASSET.code}/XLM`)"
                        selling_asset_obj = Asset.native()
                        buying_asset_obj = SEEDLING_ASSET
                    elif offer["selling"]["asset_code"] == SEEDLING_ASSET.code and \
                         offer["buying"]["asset_type"] == "native": # Selling SEEDLING for XLM
                        seedlings_to_sell = amount # Amount is the selling asset amount (SEEDLING)
                        xlm_to_receive = seedlings_to_sell * price # price is XLM/SEEDLING
                        display_text = f"**Offer {i+1} (ID: `{offer_id}`):** Selling `{seedlings_to_sell:,.0f} {SEEDLING_ASSET.code}` for `{xlm_to_receive:,.2f} XLM` (Price: `{price:,.2f} XLM/{SEEDLING_ASSET.code}`)"
                        selling_asset_obj = SEEDLING_ASSET
                        buying_asset_obj = Asset.native()
                    else:
                        continue # Skip other asset offers

                    st.markdown(display_text)
                    col_offer_cancel, _ = st.columns([0.3, 0.7])
                    with col_offer_cancel:
                        if st.button(f"Cancel Offer {offer_id} ❌", key=f"cancel_offer_{offer_id}"):
                            try:
                                source_account = get_server().load_account(st.session_state["public_key"])
                                transaction = (
                                    TransactionBuilder(
                                        source_account=source_account,
                                        network_passphrase=NETWORK_PASSPHRASE,
                                    )
                                    .append_manage_sell_offer_op(
                                        selling=selling_asset_obj,
                                        buying=buying_asset_obj,
                                        amount="0", # Amount 0 cancels the offer
                                        price=offer["price"], # Original price must be provided
                                        offer_id=int(offer_id),
                                    )
                                    .set_timeout(100)
                                    .build()
                                )
                                xdr = transaction.to_envelope().to_xdr()
                                st.info(f"Awaiting Freighter signature to cancel offer {offer_id}...")
                                st.components.v1.html(f"<script>signTransaction('{xdr}');</script>", height=0)
                            except Exception as e:
                                st.error(f"Failed to build cancel offer transaction: {e}")
                                st.exception(e)
                    st.markdown("---")
            else:
                st.info("You have no active Seedling offers.")
        except Exception as e:
            st.error(f"Failed to load offers: {e}")
            st.exception(e)
            
        st.markdown("#### Create New Offer 📝")
        market_mode = st.radio("What do you want to do?", ["Sell SEEDLINGs for XLM", "Buy SEEDLINGs with XLM"], key="market_mode")

        if market_mode == "Sell SEEDLINGs for XLM":
            st.write("Set an offer to sell your SEEDLINGs.")
            sell_seedlings_amount = st.number_input("Amount of SEEDLINGs to Sell:", min_value=1.0, value=1.0, step=1.0, key="sell_seedlings_amt")
            sell_seedlings_price_xlm = st.number_input("Price per SEEDLING (in XLM):", min_value=0.01, value=10.0, step=0.1, key="sell_seedlings_price")
            
            if st.button("Create Sell Offer 🚀", use_container_width=True, disabled=not has_trustline, key="create_sell_offer_btn"):
                if not has_trustline:
                    st.warning("You need a trustline for SEEDLING to sell them.")
                elif float(seedling_balance) < sell_seedlings_amount:
                    st.error(f"You only have {float(seedling_balance):.0f} SEEDLINGs. You cannot sell more than you own.")
                else:
                    try:
                        source_account = get_server().load_account(st.session_state["public_key"])
                        transaction = (
                            TransactionBuilder(
                                source_account=source_account,
                                network_passphrase=NETWORK_PASSPHRASE,
                            )
                            .append_manage_sell_offer_op(
                                selling=SEEDLING_ASSET,
                                buying=Asset.native(),
                                amount=f"{sell_seedlings_amount:.7f}",
                                price=f"{sell_seedlings_price_xlm:.7f}", # Price is XLM/SEEDLING
                            )
                            .set_timeout(100)
                            .build()
                        )
                        xdr = transaction.to_envelope().to_xdr()
                        st.info("Awaiting Freighter signature for creating sell offer...")
                        st.components.v1.html(f"<script>signTransaction('{xdr}');</script>", height=0)
                    except Exception as e:
                        st.error(f"Failed to build sell offer transaction: {e}")
                        st.exception(e)

        elif market_mode == "Buy SEEDLINGs with XLM":
            st.write("Set an offer to buy SEEDLINGs.")
            buy_seedlings_amount = st.number_input("Amount of SEEDLINGs to Buy:", min_value=1.0, value=1.0, step=1.0, key="buy_seedlings_amt")
            buy_seedlings_price_xlm = st.number_input("Max price per SEEDLING (in XLM):", min_value=0.01, value=10.0, step=0.1, key="buy_seedlings_price")
            
            if st.button("Create Buy Offer 🛒", use_container_width=True, disabled=not has_trustline, key="create_buy_offer_btn"):
                if not has_trustline:
                    st.warning("You need a trustline for SEEDLING to buy them.")
                elif float(xlm_balance) < (buy_seedlings_amount * buy_seedlings_price_xlm):
                    st.error(f"You need at least {buy_seedlings_amount * buy_seedlings_price_xlm:.2f} XLM to cover this buy offer. You have {float(xlm_balance):.2f} XLM.")
                else:
                    try:
                        source_account = get_server().load_account(st.session_state["public_key"])
                        # ManageSellOffer where selling XLM to buy SEEDLING
                        transaction = (
                            TransactionBuilder(
                                source_account=source_account,
                                network_passphrase=NETWORK_PASSPHRASE,
                            )
                            .append_manage_sell_offer_op(
                                selling=Asset.native(), # Selling XLM
                                buying=SEEDLING_ASSET, # To buy SEEDLING
                                amount=f"{buy_seedlings_amount * buy_seedlings_price_xlm:.7f}", # Total XLM amount to spend
                                price=f"{1/buy_seedlings_price_xlm:.7f}", # Price is (buying_asset / selling_asset) = (SEEDLING / XLM)
                            )
                            .set_timeout(100)
                            .build()
                        )
                        xdr = transaction.to_envelope().to_xdr()
                        st.info("Awaiting Freighter signature for creating buy offer...")
                        st.components.v1.html(f"<script>signTransaction('{xdr}');</script>", height=0)
                    except Exception as e:
                        st.error(f"Failed to build buy offer transaction: {e}")
                        st.exception(e)

else:
    st.info("Connect your wallet to begin your Stellar Seedlings adventure! 🚀")
    st.markdown("""
        <div style="text-align: center; margin-top: 30px;">
            <p>Don't have a Stellar Testnet account?</p>
            <p>Get some test XLM from the <a href="https://friendbot.stellar.org/" target="_blank">Friendbot!</a></p>
        </div>
    """, unsafe_allow_html=True)


# --- Footer ---
st.markdown("<p class='footer-text'>🌌 Stellar Seedlings dApp by Your Friendly Dev 🌟</p>", unsafe_allow_html=True)

# Add an expander for debugging or showing static info
with st.expander("🛠️ Debug Info & Static Accounts"):
    st.write(f"Stellar Horizon: `{HORIZON_URL}`")
    st.write(f"Network Passphrase: `{NETWORK_PASSPHRASE}`")
    st.write(f"SEEDLING Asset Code: `{SEEDLING_ASSET.code}`")
    
    issuer_pk = st.session_state.get('SEEDLING_ISSUER_PUBLIC_KEY', 'Not Set')
    growfund_pk = st.session_state.get('GROW_FUND_PUBLIC_KEY', 'Not Set')
    st.write(f"SEEDLING Issuer Public Key: `{issuer_pk}`")
    if issuer_pk != 'Not Set':
        st.markdown(f"Fund Issuer via Friendbot if needed: [Link](https://friendbot.stellar.org/?addr={issuer_pk})")
    
    st.write(f"Galactic Grow-Fund Public Key: `{growfund_pk}`")
    if growfund_pk != 'Not Set':
        st.markdown(f"Fund Grow-Fund via Friendbot if needed: [Link](https://friendbot.stellar.org/?addr={growfund_pk})")

    if st.session_state.get("public_key"):
        st.write("Current `st.session_state['public_key']`: ", st.session_state["public_key"])
        if st.session_state.get("account_details"):
            st.json(st.session_state["account_details"]._as_dict())
    st.write("Current `st.query_params`: ", st.query_params)
    st.write("Session State:", st.session_state)