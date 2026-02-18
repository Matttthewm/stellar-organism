import streamlit as st
import streamlit.components.v1 as components

import stellar_sdk
from stellar_sdk import Server, Keypair, TransactionBuilder, Network, Asset
from stellar_sdk.exceptions import BadRequestError, NotFoundError

# --- CRITICAL IMPORTS MANDATE CHECK ---
# import stellar_sdk (DONE)
# from stellar_sdk import Server, Keypair, TransactionBuilder, Network, Asset (DONE)
# from stellar_sdk.exceptions import BadRequestError, NotFoundError (DONE)
# NEVER import 'Ed25519PublicKeyInvalidError'. Use 'ValueError'. (NOT USED, good)
# NEVER import 'AssetType'. (NOT USED, good)
# --- END MANDATE CHECK ---

# --- CONFIGURATION ---
HORIZON_URL = "https://horizon-testnet.stellar.org"
NETWORK_PASSPHRASE = Network.TESTNET_NETWORK_PASSPHRASE

APP_NAME = "Cosmic_Terrarium 🌌"
APP_CONCEPT = "Cultivate unique, evolving digital flora (NFT-like assets) using Payments to 'nourish' growth, ChangeTrust to 'transplant' rare 'Spores,' and SetOptions to 'terraform' your environment."
# --- END CONFIGURATION ---

# --- STELLAR SERVER RULES MANDATE CHECK ---
# Use 'Server(HORIZON_URL)' only. NEVER pass 'timeout' to Server(). (DONE)
server = Server(HORIZON_URL)
# Access operations via module: 'stellar_sdk.ChangeTrust(...)'. (WILL DO IN OPERATIONS)
# --- END MANDATE CHECK ---

# --- CSS STYLING (Organic/Nature-Inspired) ---
custom_css = """
<style>
    /* General Body Styles */
    body {
        font-family: 'Georgia', serif; /* Organic feel */
        color: #333;
        background-color: #F8F8F0; /* Earthy background */
    }

    /* Streamlit Container Styling */
    .stApp {
        background-color: #F8F8F0;
        padding: 1rem;
    }

    /* Header & Title Styles */
    h1, h2, h3, h4, h5, h6 {
        color: #2F4F4F; /* Dark Slate Grey - deep forest */
        font-family: 'Montserrat', sans-serif; /* Modern but natural */
    }

    /* Info/Warning/Success Boxes */
    div[data-testid="stInfo"], div[data-testid="stWarning"], div[data-testid="stSuccess"] {
        border-radius: 10px;
        border-left: 6px solid;
        padding: 10px;
        margin-bottom: 10px;
    }
    div[data-testid="stInfo"] { border-color: #6B8E23; background-color: #F0FFF0; } /* Olive Drab, Honeydew */
    div[data-testid="stWarning"] { border-color: #DAA520; background-color: #FFFACD; } /* Goldenrod, Lemon Chiffon */
    div[data-testid="stSuccess"] { border-color: #3CB371; background-color: #F0FFF0; } /* Medium Sea Green, Honeydew */

    /* Buttons */
    button[data-testid="stButton"] > div > span {
        background-color: #6B8E23; /* Olive Drab */
        color: white;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: bold;
        transition: all 0.2s ease-in-out;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.2);
    }
    button[data-testid="stButton"] > div > span:hover {
        background-color: #556B2F; /* Darker Olive Green */
        box-shadow: 3px 3px 8px rgba(0,0,0,0.3);
        transform: translateY(-2px);
    }

    /* Text Inputs & Select Boxes */
    input[data-testid="stTextInput"], div[data-testid="stSelectbox"] div.st-bx, div[data-testid="stNumberInput"] {
        border-radius: 8px;
        border: 1px solid #A9A9A9; /* Dark Gray */
        padding: 0.5rem;
        background-color: white;
    }

    /* Expander */
    div[data-testid="stExpander"] {
        border: 1px solid #D2B48C; /* Tan */
        border-radius: 10px;
        background-color: #FDF5E6; /* Old Lace */
        margin-bottom: 15px;
        box-shadow: 1px 1px 3px rgba(0,0,0,0.1);
    }
    div[data-testid="stExpander"] details summary div div p {
        color: #2F4F4F; /* Dark Slate Grey */
        font-weight: bold;
    }

    /* Metric */
    div[data-testid="stMetric"] {
        background-color: #E0FFE0; /* Light green for metrics */
        border: 1px solid #90EE90; /* Light Green */
        border-radius: 10px;
        padding: 10px;
        margin-bottom: 10px;
        text-align: center;
    }
    div[data-testid="stMetric"] label div {
        color: #333;
        font-size: 0.9em;
    }
    div[data-testid="stMetric"] div[data-testid="stMarkdownContainer"] h1 {
        color: #2E8B57; /* Sea Green */
    }

    /* Sidebar */
    .css-1d391kg { /* Target sidebar background */
        background-color: #E6EAD0; /* Lighter earthy tone */
    }
    .css-1d391kg .css-1aumxm2 { /* Sidebar header/title */
        color: #2F4F4F;
    }
    .css-1d391kg .css-1dp5yyh { /* Sidebar info box */
        background-color: #E0FFE0;
        border-color: #6B8E23;
    }
    .css-1d391kg .css-1dp5yyh p {
        color: #2F4F4F;
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# --- SESSION STATE INITIALIZATION ---
if "freighter_connected" not in st.session_state:
    st.session_state.freighter_connected = False
if "user_public_key" not in st.session_state:
    st.session_state.user_public_key = None
if "demo_key" not in st.session_state:
    st.session_state.demo_key = None
if "current_terrarium_status" not in st.session_state:
    st.session_state.current_terrarium_status = "A freshly tilled patch of cosmic soil awaits your touch... 🌱"

# --- SECRET KEY HANDLING MANDATE CHECK ---
# NEVER assume 'st.secrets' exists or has keys.
# ALWAYS implement a 'Demo Mode' fallback:
if "ISSUER_KEY" in st.secrets:
    flora_secret_key = st.secrets["ISSUER_KEY"]
else:
    if "demo_key" not in st.session_state or st.session_state.demo_key is None:
        st.session_state.demo_key = Keypair.random().secret
    flora_secret_key = st.session_state.demo_key
    st.warning("Demo Mode: Using Ephemeral Demo Keys for the Terrarium's 'Flora Issuer'. Your terrarium assets will disappear on refresh if you don't save the key!")
try:
    flora_keypair = Keypair.from_secret(flora_secret_key)
except ValueError:
    st.error("Invalid Flora Issuer Secret Key. Please check st.secrets or the demo key generation.")
    st.stop()
# --- END MANDATE CHECK ---

# --- SIDEBAR MANDATE CHECK ---
# At the very top of the sidebar, display the App Name and Concept
st.sidebar.info(f"### {APP_NAME}\n\n{APP_CONCEPT}")
# Show the 'Visual Style' in the sidebar as a badge/caption.
st.sidebar.markdown("Visual Style: Organic/Nature-Inspired 🌿")
# --- END MANDATE CHECK ---

st.sidebar.header("Connection Status")
if st.session_state.freighter_connected:
    st.sidebar.success(f"Freighter Connected ✅")
    st.sidebar.markdown(f"**Your Public Key:** `{st.session_state.user_public_key[:8]}...{st.session_state.user_public_key[-8:]}`")
else:
    st.sidebar.warning("Freighter Disconnected ❌")

st.sidebar.header("Terrarium Details")
st.sidebar.markdown(f"**Flora Issuer Key:** `{flora_keypair.public_key[:8]}...{flora_keypair.public_key[-8:]}`")
st.sidebar.markdown(f"**Current Terrarium Status:**\n_{st.session_state.current_terrarium_status}_")

# --- HELPER FUNCTIONS ---
def update_terrarium_status(message):
    st.session_state.current_terrarium_status = message
    st.experimental_rerun() # Rerun to update sidebar display

def fetch_account_details(public_key):
    try:
        account = server.load_account(public_key)
        return account
    except NotFoundError:
        st.error(f"Account {public_key} not found on the network. Please fund it first (e.g., using the Stellar Laboratory Friendbot for Testnet).")
        return None
    except Exception as e:
        st.error(f"Error fetching account details: {e}")
        return None

def submit_stellar_transaction(signed_xdr):
    try:
        tx_result = server.submit_transaction(signed_xdr)
        st.success(f"Transaction successful! Hash: `{tx_result['hash']}`")
        st.balloons()
        return True
    except BadRequestError as e:
        st.error(f"Transaction failed (Bad Request): {e.extras.get('result_codes', 'No result codes available')}")
        st.exception(e)
        return False
    except Exception as e:
        st.error(f"An unexpected error occurred during transaction submission: {e}")
        st.exception(e)
        return False

# --- FREIGHTER INTEGRATION ---
# JS to interact with Freighter
freighter_js = f"""
<script src="https://unpkg.com/@stellar/freighter-api@latest/build/freighter.min.js"></script>
<script>
    async function connectFreighter() {{
        if (window.freighterApi) {{
            try {{
                const publicKey = await window.freighterApi.getPublicKey();
                window.parent.postMessage({{
                    type: "streamlit:setComponentValue",
                    args: {{ publicKey: publicKey }}
                }}, "*");
            }} catch (error) {{
                console.error("Freighter connection error:", error);
                window.parent.postMessage({{
                    type: "streamlit:setComponentValue",
                    args: {{ publicKeyError: error.message }}
                }}, "*");
            }}
        }} else {{
            window.parent.postMessage({{
                type: "streamlit:setComponentValue",
                args: {{ publicKeyError: "Freighter not detected. Please install it." }}
            }}, "*");
        }}
    }}

    async function signTransaction(xdr, network, public_key) {{
        if (window.freighterApi) {{
            try {{
                const signedXDR = await window.freighterApi.signTransaction(xdr, {{ network, accountToSign: public_key }});
                window.parent.postMessage({{
                    type: "streamlit:setComponentValue",
                    args: {{ signedXDR: signedXDR }}
                }}, "*");
            }} catch (error) {{
                console.error("Freighter signing error:", error);
                window.parent.postMessage({{
                    type: "streamlit:setComponentValue",
                    args: {{ signedXDRError: error.message }}
                }}, "*");
            }}
        }} else {{
            window.parent.postMessage({{
                type: "streamlit:setComponentValue",
                args: {{ signedXDRError: "Freighter not detected." }}
            }}, "*");
        }}
    }}
</script>
"""
# --- HTML COMPONENT RULES MANDATE CHECK ---
# ALWAYS use: 'import streamlit.components.v1 as components' (DONE)
# ALWAYS call: 'components.html(...)'.
# NEVER call 'html(...)' directly from 'streamlit'. (DONE)
components.html(freighter_js, height=0)
# --- END MANDATE CHECK ---

# --- MAIN APP LAYOUT ---
st.title(f"{APP_NAME} 🪴")
st.markdown("---")

# --- Freighter Connection UI ---
st.header("Connect Your Gardener's Wallet 👛")
st.write("Connect your Stellar wallet via Freighter to interact with your Cosmic Terrarium.")

col1_conn, col2_conn = st.columns([1, 2])
with col1_conn:
    if st.button("Connect Freighter Wallet"):
        components.html("<script>connectFreighter();</script>", height=0)

# --- STRICTLY USE 'st.query_params' MANDATE CHECK ---
# NO 'st.experimental_get_query_params' (DONE, using st.query_params directly)
query_params = st.query_params
# --- END MANDATE CHECK ---

if "publicKey" in query_params:
    st.session_state.user_public_key = query_params["publicKey"]
    st.session_state.freighter_connected = True
    st.success(f"Connected with Public Key: `{st.session_state.user_public_key}`")
    # Clear the query param to avoid re-processing on refresh
    del query_params["publicKey"]
    st.experimental_set_query_params(**query_params) # Clear from URL
    st.experimental_rerun() # Rerun to update the session state and UI

if "publicKeyError" in query_params:
    st.error(f"Freighter Connection Error: {query_params['publicKeyError']}")
    del query_params["publicKeyError"]
    st.experimental_set_query_params(**query_params) # Clear from URL

st.markdown("---")

if st.session_state.freighter_connected and st.session_state.user_public_key:
    user_account = fetch_account_details(st.session_state.user_public_key)

    if user_account:
        st.header("Your Cosmic Terrarium 🏡")
        
        # Display user's XLM balance using st.metric
        xlm_balance = next((balance['balance'] for balance in user_account.balances if balance['asset_type'] == 'native'), '0')
        st.metric(label="Your Current Lumens (XLM) 🌟", value=f"{float(xlm_balance):.2f}")

        # --- NOURISH FLORA (Payment Operation) ---
        with st.expander("Nourish Your Flora 💧", expanded=True):
            st.write("Provide sustenance to your digital flora using Lumens. This helps them grow and evolve!")
            nourish_amount = st.number_input("Amount of XLM to nourish:", min_value=0.01, value=0.1, step=0.01, format="%.2f")
            
            if st.button("Nourish Flora ☀️"):
                if nourish_amount > 0:
                    try:
                        transaction = (
                            TransactionBuilder(
                                source_account=user_account,
                                network_passphrase=NETWORK_PASSPHRASE,
                            )
                            .add_operation(
                                stellar_sdk.Payment(
                                    destination=flora_keypair.public_key,
                                    asset=Asset.native(),
                                    amount=str(nourish_amount),
                                    source=st.session_state.user_public_key # Ensure the user is the source
                                )
                            )
                            .set_timeout(100)
                            .build()
                        )
                        xdr = transaction.to_xdr()
                        components.html(f"<script>signTransaction('{xdr}', '{Network.TESTNET_NETWORK_PASSPHRASE}', '{st.session_state.user_public_key}');</script>", height=0)
                        st.session_state.tx_in_progress = "nourish"
                        st.info("Awaiting Freighter signature for nourishment...")
                    except Exception as e:
                        st.error(f"Failed to build nourishment transaction: {e}")
                else:
                    st.warning("Please enter a valid amount to nourish.")
        
        # --- TRANSPLANT RARE SPORES (ChangeTrust Operation) ---
        with st.expander("Transplant Rare Spores 🍄"):
            st.write("Adopt a new species of cosmic flora by establishing a trustline to its unique 'Spore' asset.")
            
            # For simplicity, define a few sample spores issued by the flora_keypair
            sample_spores = {
                "Solar Bloom": Asset("SOLARBLOOM", flora_keypair.public_key),
                "Lunar Moss": Asset("LUNARMOSS", flora_keypair.public_key),
                "Nebula Fern": Asset("NEBULAFRN", flora_keypair.public_key),
            }
            
            selected_spore_name = st.selectbox("Select a Spore to Transplant:", list(sample_spores.keys()))
            selected_spore_asset = sample_spores[selected_spore_name]
            
            trust_limit = st.text_input(f"Trustline Limit (e.g., 100000000000 or a specific amount for {selected_spore_name})", value="100000000000") # Max limit
            
            if st.button(f"Transplant {selected_spore_name} Spore 🔬"):
                try:
                    transaction = (
                        TransactionBuilder(
                            source_account=user_account,
                            network_passphrase=NETWORK_PASSPHRASE,
                        )
                        .add_operation(
                            stellar_sdk.ChangeTrust(
                                asset=selected_spore_asset,
                                limit=trust_limit,
                                source=st.session_state.user_public_key
                            )
                        )
                        .set_timeout(100)
                        .build()
                    )
                    xdr = transaction.to_xdr()
                    components.html(f"<script>signTransaction('{xdr}', '{Network.TESTNET_NETWORK_PASSPHRASE}', '{st.session_state.user_public_key}');</script>", height=0)
                    st.session_state.tx_in_progress = "changetrust"
                    st.info(f"Awaiting Freighter signature to transplant {selected_spore_name}...")
                except Exception as e:
                    st.error(f"Failed to build ChangeTrust transaction: {e}")
        
        # --- TERRAFORM ENVIRONMENT (SetOptions Operation) ---
        with st.expander("Terraform Your Terrarium 🏞️"):
            st.write("Customize your personal terrarium by setting its home domain or adding unique data entries.")
            
            terraform_option = st.radio(
                "Choose a Terraform action:",
                ("Set Home Domain", "Add/Update Data Entry")
            )

            if terraform_option == "Set Home Domain":
                new_home_domain = st.text_input("New Home Domain (e.g., myterrarium.com):", value="cosmic.terrarium.test")
                if st.button("Set Home Domain 🌐"):
                    try:
                        transaction = (
                            TransactionBuilder(
                                source_account=user_account,
                                network_passphrase=NETWORK_PASSPHRASE,
                            )
                            .add_operation(
                                stellar_sdk.SetOptions(
                                    home_domain=new_home_domain if new_home_domain else None,
                                    source=st.session_state.user_public_key
                                )
                            )
                            .set_timeout(100)
                            .build()
                        )
                        xdr = transaction.to_xdr()
                        components.html(f"<script>signTransaction('{xdr}', '{Network.TESTNET_NETWORK_PASSPHRASE}', '{st.session_state.user_public_key}');</script>", height=0)
                        st.session_state.tx_in_progress = "setoptions_home_domain"
                        st.info("Awaiting Freighter signature to set home domain...")
                    except Exception as e:
                        st.error(f"Failed to build Set Home Domain transaction: {e}")
            
            elif terraform_option == "Add/Update Data Entry":
                data_name = st.text_input("Data Entry Name (Key, e.g., 'terrarium_color'):")
                data_value = st.text_input("Data Entry Value (e.g., 'emerald_green'):")
                
                if st.button("Add/Update Data Entry 📝"):
                    if data_name and data_value:
                        try:
                            transaction = (
                                TransactionBuilder(
                                    source_account=user_account,
                                    network_passphrase=NETWORK_PASSPHRASE,
                                )
                                .add_operation(
                                    stellar_sdk.ManageData(
                                        data_name=data_name,
                                        data_value=data_value.encode('utf-8'), # Data value must be bytes
                                        source=st.session_state.user_public_key
                                    )
                                )
                                .set_timeout(100)
                                .build()
                            )
                            xdr = transaction.to_xdr()
                            components.html(f"<script>signTransaction('{xdr}', '{Network.TESTNET_NETWORK_PASSPHRASE}', '{st.session_state.user_public_key}');</script>", height=0)
                            st.session_state.tx_in_progress = "setoptions_data_entry"
                            st.info(f"Awaiting Freighter signature to add data entry '{data_name}'...")
                        except Exception as e:
                            st.error(f"Failed to build Manage Data transaction: {e}")
                    else:
                        st.warning("Please provide both data entry name and value.")

        # --- Process Signed Transaction Results from Freighter ---
        if "signedXDR" in query_params and st.session_state.tx_in_progress:
            signed_xdr = query_params["signedXDR"]
            operation_type = st.session_state.tx_in_progress

            st.write(f"Freighter signed the transaction! Submitting {operation_type}...")
            if submit_stellar_transaction(signed_xdr):
                if operation_type == "nourish":
                    update_terrarium_status(f"Your flora received {nourish_amount} XLM! It's thriving! 📈")
                elif operation_type == "changetrust":
                    update_terrarium_status(f"New {selected_spore_name} spores successfully transplanted! Watch them grow! ✨")
                elif operation_type.startswith("setoptions"):
                    update_terrarium_status(f"Terrarium environment successfully terraformed! 🏗️")
            
            # Clear query params and state
            del query_params["signedXDR"]
            st.session_state.tx_in_progress = None
            st.experimental_set_query_params(**query_params)
            st.experimental_rerun() # Rerun to update the terrarium status and clear info message

        if "signedXDRError" in query_params:
            st.error(f"Freighter Signing Error: {query_params['signedXDRError']}")
            st.session_state.tx_in_progress = None # Clear any pending tx state
            del query_params["signedXDRError"]
            st.experimental_set_query_params(**query_params)

        st.markdown("---")
        st.subheader("Your Flora's Current Balances 🌿")
        # Display all non-native asset balances for the user
        asset_balances_exist = False
        for balance in user_account.balances:
            if balance['asset_type'] != 'native':
                asset_balances_exist = True
                st.metric(label=f"{balance['asset_code']} (Issuer: {balance['asset_issuer'][:8]}...)", value=f"{float(balance['balance']):.2f}")
        
        if not asset_balances_exist:
            st.info("You haven't transplanted any spores yet! Explore the 'Transplant Rare Spores' section to begin your collection. 🔍")

    else:
        st.warning("Please connect Freighter and ensure your account is funded to interact with the Terrarium.")
else:
    st.info("Please connect your Freighter wallet to start cultivating your Cosmic Terrarium.")

st.markdown("---")
st.caption(f"Powered by Stellar & Streamlit. Developed for educational purposes. All transactions on Testnet.")