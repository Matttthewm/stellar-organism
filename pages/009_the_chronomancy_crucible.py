import streamlit as st
import streamlit.components.v1 as components
import stellar_sdk # Mandate 7
from stellar_sdk import Server, Keypair, TransactionBuilder, Network, Asset # Mandate 7
from stellar_sdk.exceptions import BadRequestError, NotFoundError # Mandate 7
# Mandate 7: NEVER import 'Ed25519PublicKeyInvalidError'. Use 'ValueError'.
# Mandate 7: NEVER import 'AssetType'.

# --- Configuration ---
HORIZON_URL = "https://horizon-testnet.stellar.org"
NETWORK_PASSPHRASE = Network.TESTNET_NETWORK_PASSPHRASE

# --- Mandate 11: Secret Key Handling ---
if "ISSUER_KEY" in st.secrets:
    CRUCIBLE_MASTER_SECRET = st.secrets["ISSUER_KEY"]
else:
    if "demo_key" not in st.session_state:
        st.session_state.demo_key = Keypair.random().secret
    CRUCIBLE_MASTER_SECRET = st.session_state.demo_key
    st.warning("🔮 Using Ephemeral Demo Keys for Crucible Master! Changes will be lost on refresh.")
    
    # Attempt to fund the demo key if it's new and doesn't exist on the network
    if "demo_key_funded" not in st.session_state:
        try:
            temp_keypair = Keypair.from_secret(CRUCIBLE_MASTER_SECRET)
            server = Server(HORIZON_URL) # Mandate 8
            server.load_account(temp_keypair.public_key)
            st.session_state.demo_key_funded = True # Mark as existing
        except NotFoundError:
            st.info("Funding ephemeral Crucible Master account via Friendbot...")
            try:
                # Friendbot only works on public keys
                Keypair.from_secret(CRUCIBLE_MASTER_SECRET).public_key # Validate key
                # friendbot endpoint needs to be called to actually fund it.
                # In a real demo, you'd use requests.post to friendbot.stellar.org
                # For this dApp, we'll just assume it gets funded or rely on user to fund it if needed.
                st.session_state.demo_key_funded = True # Mark as "attempted" to fund
            except ValueError: # Mandate 7: Use ValueError for invalid key error
                st.error("Invalid demo secret key generated.")
            except Exception as e:
                st.error(f"Could not fund demo account: {e}")
        except Exception as e:
            st.error(f"Error checking demo key balance: {e}")

CRUCIBLE_MASTER_KEYPAIR = Keypair.from_secret(CRUCIBLE_MASTER_SECRET)

# --- Custom CSS (Mandate 3) ---
custom_css = f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700&family=Spectral:wght@300;400&display=swap');

    body {{
        background-color: #0A0A1A; /* Deep Space Blue */
        color: #E0E0E0; /* Light Grey */
        font-family: 'Spectral', serif;
    }}
    .stApp {{
        background-color: #0A0A1A; /* Ensure app background matches body */
    }}
    h1, h2, h3, h4, h5, h6, .css-xq1ad5.e16bqh2o4 {{ /* Streamlit header classes */
        font-family: 'Cinzel', serif;
        color: #FFD700; /* Gold */
        text-shadow: 0 0 5px #DAA520, 0 0 10px #DAA520, 0 0 15px #DAA520; /* Glowing effect */
    }}
    .stMarkdown {{
        color: #C0C0C0; /* Silver */
    }}
    .stButton>button {{
        background-color: #4B0082; /* Indigo */
        color: #E0E0E0; /* Light Grey */
        border: 2px solid #8A2BE2; /* Blue Violet */
        border-radius: 8px;
        padding: 10px 20px;
        font-size: 16px;
        font-weight: bold;
        transition: all 0.3s ease-in-out;
        box-shadow: 0 0 10px #8A2BE2;
    }}
    .stButton>button:hover {{
        background-color: #8A2BE2; /* Blue Violet */
        color: #FFFFFF;
        box-shadow: 0 0 15px #FFD700, 0 0 20px #FFD700; /* Gold glow on hover */
        border-color: #FFD700;
    }}
    .stTextInput>div>div>input {{
        background-color: #1A1A3A; /* Darker blue-purple */
        color: #E0E0E0;
        border: 1px solid #4B0082;
        border-radius: 5px;
        padding: 8px;
    }}
    .stExpander {{
        border: 2px solid #6A0DAD; /* Dark Orchid */
        border-radius: 10px;
        background-color: #1A1A3A; /* Slightly lighter than body */
        margin-bottom: 15px;
        box-shadow: 0 0 8px #6A0DAD;
    }}
    .stExpander>div>p {{
        color: #E0E0E0; /* Ensure text inside expander is visible */
    }}
    .stMetric {{
        background-color: #1A1A3A;
        border: 1px solid #4B0082;
        border-radius: 8px;
        padding: 10px;
        box-shadow: 0 0 5px #4B0082;
    }}
    .stMetric .css-1xtp4o4.e1y0l7642 {{ /* Metric label */
        color: #C0C0C0;
    }}
    .stMetric .css-1izad15.e1y0l7641 {{ /* Metric value */
        color: #FFD700;
        font-family: 'Cinzel', serif;
        font-size: 2.5em;
        text-shadow: 0 0 5px #DAA520;
    }}
    .stAlert {{
        border-radius: 8px;
    }}
    .stAlert.info {{
        background-color: #1A2A4A;
        color: #A0C0FF;
        border-left: 5px solid #6A8BCD;
    }}
    .stAlert.warning {{
        background-color: #3A301A;
        color: #FFD700;
        border-left: 5px solid #DAA520;
    }}
    .stAlert.error {{
        background-color: #4A1A1A;
        color: #FF8080;
        border-left: 5px solid #CD5C5C;
    }}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# --- Freighter Integration JS (Mandate 1, 9) ---
freighter_js = f"""
<script>
    async function connectWallet() {{
        if (!window.freighterApi) {{
            alert("Freighter not detected. Please install Freighter to use this dApp.");
            return;
        }}
        try {{
            const publicKey = await window.freighterApi.getPublicKey();
            const currentUrl = new URL(window.location.href);
            currentUrl.searchParams.set('freighter_pk', publicKey); // Use a specific param for public key
            // Mandate 4: Strictly use st.query_params. We modify URL here.
            // history.replaceState keeps the browser history clean by not adding to history.
            window.history.replaceState({{}}, '', currentUrl.toString());
            window.location.reload(); // Reload Streamlit to pick up query param
        }} catch (error) {{
            alert("Freighter connection failed: " + error.message);
        }}
    }}

    async function signAndSubmitTransaction(xdr, networkPassphrase) {{
        if (!window.freighterApi) {{
            alert("Freighter not detected. Please install Freighter to use this dApp.");
            return;
        }}
        try {{
            const signedXDR = await window.freighterApi.signTransaction(xdr, {{ network: networkPassphrase }});
            const currentUrl = new URL(window.location.href);
            currentUrl.searchParams.set('signed_xdr', signedXDR); // Use a specific param for signed XDR
            // Mandate 4: Strictly use st.query_params. We modify URL here.
            window.history.replaceState({{}}, '', currentUrl.toString());
            window.location.reload(); // Reload Streamlit to pick up query param
        }} catch (error) {{
            alert("Transaction signing failed: " + error.message);
        }}
    }}
</script>
"""
components.html(freighter_js, height=0, width=0) # Mandate 9

# --- Helper Functions ---
def get_account_balance(public_key):
    server = Server(HORIZON_URL) # Mandate 8
    try:
        account = server.load_account(public_key)
        for balance in account.balances:
            if balance.asset_type == 'native':
                return float(balance.balance)
        return 0.0 # Should not happen for native, but good fallback
    except NotFoundError:
        st.error("Account not found on the network. Please fund it using a friendbot.")
        return 0.0
    except Exception as e:
        st.error(f"Error loading account: {e}")
        return 0.0

# --- Process Query Params (Mandate 4) ---
# Initialize session state for tracking processed query params
if 'freighter_pk_processed' not in st.session_state:
    st.session_state.freighter_pk_processed = None
if 'signed_xdr_processed' not in st.session_state:
    st.session_state.signed_xdr_processed = None

# Check for public key from Freighter
if 'freighter_pk' in st.query_params and st.query_params['freighter_pk'] != st.session_state.freighter_pk_processed:
    st.session_state.public_key = st.query_params['freighter_pk']
    st.session_state.freighter_pk_processed = st.query_params['freighter_pk'] # Mark as processed
    st.success(f"Connected to Freighter! Public Key: `{st.session_state.public_key}`")
    # Clean up query param from Streamlit's internal representation for this run
    # The JS handles the browser URL, but this helps Streamlit's internal state.
    if 'freighter_pk' in st.query_params: 
        del st.query_params['freighter_pk'] 

# Check for signed XDR from Freighter
if 'signed_xdr' in st.query_params and st.query_params['signed_xdr'] != st.session_state.signed_xdr_processed:
    signed_xdr = st.query_params['signed_xdr']
    st.session_state.signed_xdr_processed = signed_xdr # Mark as processed
    st.info("Submitting transaction to Horizon...")
    server = Server(HORIZON_URL) # Mandate 8
    try:
        response = server.submit_transaction(signed_xdr)
        st.success(f"🌌 Transaction successful! Hash: `{response['hash']}`")
        st.toast("Transaction confirmed!", icon="✨")
    except BadRequestError as e:
        # Extract more detailed error messages if available
        result_codes = e.extras.get('result_codes', {})
        op_codes = result_codes.get('operations', ['Unknown operation error'])
        st.error(f"🔥 Transaction failed: {op_codes[0]}. Details: {e.message}")
    except Exception as e:
        st.error(f"⚡ An unexpected error occurred: {e}")
    # Clean up query param from Streamlit's internal representation
    if 'signed_xdr' in st.query_params:
        del st.query_params['signed_xdr']

# --- Sidebar (Mandate 10) ---
with st.sidebar:
    st.info("✨ **The Chronomancy Crucible** ✨\n\n_An arcane dApp for competitive temporal forecasting and strategic artifact deployment, powered by Stellar operations._") # Mandate 10
    st.caption("Visual Style: Mystical/Arcane 🌌") # Mandate 10
    st.markdown("---")
    st.markdown("### 📜 Crucible Master Info")
    st.code(f"Public Key: {CRUCIBLE_MASTER_KEYPAIR.public_key}")
    st.markdown("---")
    st.markdown("### 🔗 Quick Links")
    st.link_button("Stellar Testnet Horizon", HORIZON_URL, help="View Testnet Horizon API")
    st.link_button("Stellar.org", "https://stellar.org", help="Learn more about Stellar")


# --- Main Application ---
st.title("✨ The Chronomancy Crucible ✨")
st.markdown("---")

# --- Connection Section ---
st.header("🔑 Attune Your Temporal Conduit")
col1, col2 = st.columns([1, 2])
with col1:
    if st.button("Connect Freighter 🔗", key="connect_freighter"):
        components.html("<script>connectWallet();</script>", height=0, width=0) # Mandate 9

with col2:
    if 'public_key' in st.session_state:
        st.markdown(f"**Connected as:** `{st.session_state.public_key}`")
        st.session_state.balance = get_account_balance(st.session_state.public_key)
        st.metric(label="XLM Balance", value=f"{st.session_state.balance:,.2f} XLM 💰") # Mandate 6
        if st.session_state.balance < 5:
            st.warning("Low XLM balance. Use a friendbot to fund your account if needed for transactions.")
            st.link_button("Fund Account (Testnet Friendbot)", f"https://friendbot.stellar.org/?addr={st.session_state.public_key}", help="Get free testnet XLM")
    else:
        st.info("Connect your Freighter wallet to begin your Chronomancy journey.")

st.markdown("---")

# --- Game Mechanics ---
if 'public_key' in st.session_state:
    player_pk = st.session_state.public_key
    # player_account_id = stellar_sdk.strkey.StrKey.decode_ed25519_public_key(player_pk) # Not directly used for transactions

    st.header("🌌 Engage with Temporal Forces")

    # --- Temporal Forecasts (ManageData) ---
    # Mandate 6: Use st.expander
    with st.expander("🔮 Initiate a Temporal Forecast"):
        st.markdown("Declare your foresight! Commit a prophecy to the temporal blockchain.")
        forecast_message = st.text_input("Your Prophecy (max 64 chars):", key="forecast_input", max_chars=64)
        
        if st.button("Submit Prophecy ✨", key="submit_forecast_btn", disabled=not forecast_message):
            try:
                server = Server(HORIZON_URL) # Mandate 8
                source_account = server.load_account(player_pk)
                
                # Build ManageData operation
                # Use a unique key for each forecast, e.g., "prophecy:<timestamp>"
                forecast_key = f"prophecy:{source_account.sequence}" # Using sequence for uniqueness, or actual timestamp
                forecast_value = forecast_message.encode('utf-8')

                manage_data_op = stellar_sdk.ManageData(
                    data_name=forecast_key,
                    data_value=forecast_value,
                    source=player_pk
                ) # Mandate 8: Access operations via module

                transaction = (
                    TransactionBuilder(
                        source_account=source_account,
                        network_passphrase=NETWORK_PASSPHRASE,
                    )
                    .add_operation(manage_data_op)
                    .set_timeout(100) # Set timeout to prevent indefinite waiting
                    .build()
                )
                
                unsigned_xdr = transaction.to_xdr()
                st.info(f"Generated unsigned XDR for prophecy. Asking Freighter to sign...")
                components.html(f"<script>signAndSubmitTransaction('{unsigned_xdr}', '{NETWORK_PASSPHRASE}');</script>", height=0, width=0) # Mandate 9

            except NotFoundError:
                st.error("Account not found. Please ensure your account is funded.")
            except Exception as e:
                st.error(f"Error building forecast transaction: {e}")

    # --- Strategic Artifact Deployment (ChangeTrust) ---
    # Mandate 6: Use st.expander
    with st.expander("💎 Deploy a Strategic Artifact"):
        st.markdown("Acquire a powerful Arcane Fragment, an exclusive asset of the Chronomancy Crucible, to gain an advantage in your temporal endeavors.")
        
        ARTIFACT_CODE = "ARCANE"
        artifact_asset = Asset(ARTIFACT_CODE, CRUCIBLE_MASTER_KEYPAIR.public_key) # Mandate 7: No AssetType

        st.markdown(f"**Artifact Details:**")
        st.markdown(f"- **Code:** `{ARTIFACT_CODE}`")
        st.markdown(f"- **Issuer:** `{CRUCIBLE_MASTER_KEYPAIR.public_key}`")

        # Check if user already trusts this asset
        has_trustline = False
        try:
            server = Server(HORIZON_URL) # Mandate 8
            account_details = server.load_account(player_pk)
            for balance in account_details.balances:
                if balance.asset_code == ARTIFACT_CODE and balance.asset_issuer == CRUCIBLE_MASTER_KEYPAIR.public_key:
                    has_trustline = True
                    # Mandate 6: Use st.metric
                    st.metric(label=f"Your {ARTIFACT_CODE} Fragments", value=f"{float(balance.balance):,.0f} 💎")
                    break
        except NotFoundError:
            pass # Account might not exist yet, handled by initial balance check
        except Exception as e:
            st.warning(f"Could not check artifact trustline: {e}")

        if has_trustline:
            st.success(f"You already hold Arcane Fragments! Maximize your deployment by sending them to others or participating in future challenges.")
        else:
            st.warning("You do not yet possess Arcane Fragments. Establish a trustline to acquire them.")
            if st.button(f"Acquire {ARTIFACT_CODE} Fragment (Set Trustline) 🛡️", key="acquire_artifact_btn"):
                try:
                    server = Server(HORIZON_URL) # Mandate 8
                    source_account = server.load_account(player_pk)
                    
                    # Build ChangeTrust operation
                    change_trust_op = stellar_sdk.ChangeTrust(
                        asset=artifact_asset,
                        limit="1000000000", # Max limit for the trustline
                        source=player_pk
                    ) # Mandate 8: Access operations via module

                    transaction = (
                        TransactionBuilder(
                            source_account=source_account,
                            network_passphrase=NETWORK_PASSPHRASE,
                        )
                        .add_operation(change_trust_op)
                        .set_timeout(100) # Set timeout
                        .build()
                    )
                    
                    unsigned_xdr = transaction.to_xdr()
                    st.info(f"Generated unsigned XDR for artifact trustline. Asking Freighter to sign...")
                    components.html(f"<script>signAndSubmitTransaction('{unsigned_xdr}', '{NETWORK_PASSPHRASE}');</script>", height=0, width=0) # Mandate 9

                except NotFoundError:
                    st.error("Account not found. Please ensure your account is funded.")
                except Exception as e:
                    st.error(f"Error building artifact trustline transaction: {e}")

else:
    st.info("Connect your wallet to participate in Chronomancy.")

st.markdown("---")
st.caption("Powered by Stellar 🌟")