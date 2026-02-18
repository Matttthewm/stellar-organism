import streamlit as st
from streamlit.components.v1 import html
from stellar_sdk import Server, Keypair, TransactionBuilder, Network, Asset, ManageData, ChangeTrust, Payment, Clawback, CreateClaimableBalance, ClaimClaimableBalance, PathPaymentStrictReceive, Claimant, ClaimPredicate
from stellar_sdk.exceptions import BadRequestError, NotFoundError
import json
import time 

# --- Configuration ---
# Set to 'TESTNET' or 'PUBLIC'
CURRENT_NETWORK = "TESTNET" 
HORIZON_URL = "https://horizon-testnet.stellar.org" if CURRENT_NETWORK == "TESTNET" else "https://horizon.stellar.org"
NETWORK_PASSPHRASE = Network.TESTNET_NETWORK_PASSPHRASE if CURRENT_NETWORK == "TESTNET" else Network.PUBLIC_NETWORK_PASSPHRASE

# Pre-defined issuer for demonstration purposes
if 'ISSUER_KEYPAIR' not in st.session_state:
    st.session_state.ISSUER_KEYPAIR = Keypair.random()
ISSUER_PUBLIC_KEY = st.session_state.ISSUER_KEYPAIR.public_key
ISSUER_SECRET_KEY = st.session_state.ISSUER_KEYPAIR.secret

# Initialize Stellar server
server = Server(horizon_url=HORIZON_URL)

# --- Custom CSS for Futuristic, High-Contrast, Minimalist Style ---
def apply_custom_css():
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Fira+Code:wght@400;700&display=swap');

            :root {
                --primary-bg: #0a0a1a;
                --secondary-bg: #1a1a2e;
                --text-color: #e0e0e0;
                --accent-color-1: #00ffff; /* Cyan */
                --accent-color-2: #7fff00; /* Chartreuse */
                --accent-color-3: #ff00ff; /* Magenta */
                --border-color: #3a3a5e;
                --button-bg: #2a2a4e;
                --button-hover-bg: #3a3a5e;
            }

            body {
                font-family: 'Fira Code', monospace;
                color: var(--text-color);
                background-color: var(--primary-bg);
            }

            .stApp {
                background-color: var(--primary-bg);
                color: var(--text-color);
            }

            /* Main content padding */
            .st-emotion-cache-z5fcl4 { 
                padding-top: 2rem;
                padding-right: 2rem;
                padding-left: 2rem;
                padding-bottom: 2rem;
            }

            /* Title/Header */
            h1, h2, h3, h4, h5, h6 {
                font-family: 'Orbitron', sans-serif;
                color: var(--accent-color-1);
                text-shadow: 0 0 5px rgba(0, 255, 255, 0.4), 0 0 10px rgba(0, 255, 255, 0.2);
            }
            h1 { font-size: 2.5em; text-align: center; margin-bottom: 1.5em; }
            h2 { font-size: 1.8em; border-bottom: 1px solid var(--border-color); padding-bottom: 0.5em; margin-top: 1.5em; color: var(--accent-color-2); }

            /* Containers & Cards */
            .st-emotion-cache-1eqfpmc, .st-emotion-cache-1gh274 { 
                 background-color: var(--secondary-bg);
                 border: 1px solid var(--border-color);
                 border-radius: 8px;
                 padding: 1.5em;
                 box-shadow: 0 0 15px rgba(0, 255, 255, 0.1);
                 margin-bottom: 1em;
            }
            
            /* Expander */
            .streamlit-expanderHeader {
                background-color: var(--secondary-bg);
                color: var(--accent-color-1);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                padding: 0.8em;
                margin-bottom: 0.5em;
                font-family: 'Orbitron', sans-serif;
                font-weight: bold;
                transition: background-color 0.3s, border-color 0.3s;
            }
            .streamlit-expanderHeader:hover {
                background-color: var(--button-hover-bg);
                border-color: var(--accent-color-1);
            }
            .streamlit-expanderContent {
                background-color: var(--primary-bg);
                border-left: 3px solid var(--accent-color-2);
                padding: 1em;
                margin-left: 0.5em;
                margin-top: -0.5em;
                border-bottom-right-radius: 8px;
                border-top-right-radius: 8px;
            }

            /* Buttons */
            .stButton > button {
                background-color: var(--button-bg);
                color: var(--accent-color-1);
                border: 1px solid var(--accent-color-1);
                border-radius: 5px;
                padding: 0.6em 1.2em;
                font-family: 'Orbitron', sans-serif;
                font-weight: bold;
                transition: all 0.2s ease-in-out;
                box-shadow: 0 0 5px rgba(0, 255, 255, 0.5);
            }
            .stButton > button:hover {
                background-color: var(--accent-color-1);
                color: var(--primary-bg);
                border-color: var(--accent-color-1);
                box-shadow: 0 0 15px var(--accent-color-1);
            }
            .stButton > button:active {
                transform: translateY(1px);
            }

            /* Inputs */
            .stTextInput > div > div > input,
            .stSelectbox > div > div > select,
            .stNumberInput > div > div > input,
            .stTextArea > div > div > textarea {
                background-color: var(--primary-bg);
                color: var(--text-color);
                border: 1px solid var(--border-color);
                border-radius: 5px;
                padding: 0.5em;
                font-family: 'Fira Code', monospace;
            }
            .stTextInput > div > div > input:focus,
            .stSelectbox > div > div > select:focus,
            .stNumberInput > div > div > input:focus,
            .stTextArea > div > div > textarea:focus {
                border-color: var(--accent-color-2);
                box-shadow: 0 0 8px rgba(127, 255, 0, 0.5);
                outline: none;
            }
            .stTextInput > div > div > input:disabled {
                background-color: #0d0d1a;
                color: #888888;
                cursor: not-allowed;
            }

            /* Metrics */
            .st-metric {
                background-color: var(--secondary-bg);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                padding: 1em;
                text-align: center;
                box-shadow: 0 0 10px rgba(0, 255, 255, 0.1);
            }
            .st-metric > div > div:first-child { 
                color: var(--accent-color-2);
                font-family: 'Orbitron', sans-serif;
                font-size: 0.9em;
            }
            .st-metric > div > div:nth-child(2) { 
                color: var(--accent-color-1);
                font-family: 'Fira Code', monospace;
                font-size: 1.5em;
                font-weight: bold;
            }
            .st-metric > div > div:nth-child(3) { 
                color: var(--text-color);
                font-size: 0.8em;
            }

            /* Info, Warning, Error boxes */
            .stAlert {
                background-color: var(--secondary-bg) !important;
                border: 1px solid var(--border-color) !important;
                border-left: 5px solid var(--accent-color-1) !important;
                color: var(--text-color) !important;
                border-radius: 8px !important;
            }
            .stAlert button { 
                color: var(--text-color) !important;
            }

            code {
                background-color: var(--button-bg);
                border: 1px solid var(--border-color);
                border-radius: 4px;
                padding: 0.2em 0.4em;
                font-family: 'Fira Code', monospace;
                color: var(--accent-color-3);
            }
            pre {
                background-color: var(--primary-bg);
                border: 1px solid var(--border-color);
                border-radius: 5px;
                padding: 1em;
                overflow-x: auto;
            }
        </style>
        """,
        unsafe_allow_html=True
    )

# --- Freighter JavaScript Component ---
FREIGHTER_JS_COMPONENT = f"""
<script>
    function getQueryParam(name) {{
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get(name);
    }}

    function setQueryParam(name, value) {{
        const urlParams = new URLSearchParams(window.location.search);
        urlParams.delete('freighter_pk');
        urlParams.delete('freighter_error');
        urlParams.delete('tx_hash');
        urlParams.delete('tx_result');
        urlParams.delete('tx_error');
        urlParams.delete('signed_xdr');

        urlParams.set(name, value);
        window.location.search = urlParams.toString();
    }}

    async function connectFreighter() {{
        if (window.freighterApi) {{
            try {{
                const publicKey = await window.freighterApi.getPublicKey();
                setQueryParam('freighter_pk', publicKey);
            }} catch (error) {{
                console.error("Freighter connection error:", error);
                setQueryParam('freighter_error', error.message || "Unknown Freighter error");
            }}
        }} else {{
            alert("Freighter wallet not detected. Please install it.");
            setQueryParam('freighter_error', 'Freighter not detected');
        }}
    }}

    async function signAndSubmitTx(xdr, networkPassphrase) {{
        if (window.freighterApi) {{
            try {{
                const signedXDR = await window.freighterApi.signTransaction(xdr, {{ network: networkPassphrase }});
                const HORIZON_URL = "{HORIZON_URL}";
                const response = await fetch(`${{HORIZON_URL}}/transactions`, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/x-www-form-urlencoded' }},
                    body: `tx=${{signedXDR}}`
                }});
                const data = await response.json();
                if (data.hash) {{
                    setQueryParam('tx_hash', data.hash);
                    setQueryParam('tx_result', 'success');
                    setQueryParam('signed_xdr', encodeURIComponent(signedXDR));
                }} else {{
                    setQueryParam('tx_result', 'error');
                    setQueryParam('tx_error', encodeURIComponent(JSON.stringify(data)));
                }}
            }} catch (error) {{
                console.error("Freighter transaction error:", error);
                setQueryParam('tx_result', 'error');
                setQueryParam('tx_error', error.message || "Unknown transaction error");
            }}
        }} else {{
            alert("Freighter wallet not detected.");
            setQueryParam('freighter_error', 'Freighter not detected for signing');
        }}
    }}
    window.connectFreighter = connectFreighter;
    window.signAndSubmitTx = signAndSubmitTx;
</script>
"""

# --- Helper Functions ---
def get_account_details(public_key):
    try:
        account = server.load_account(public_key)
        return account
    except NotFoundError:
        st.error(f"Account `{public_key}` not found on the {CURRENT_NETWORK} network. Please fund it.", icon="🚨")
        if CURRENT_NETWORK == "TESTNET":
            st.code(f"Fund your account here for Testnet: https://laboratory.stellar.org/#account-creator?network=test", language="url")
        return None
    except BadRequestError as e:
        st.error(f"Bad request for account `{public_key}`: {e}", icon="🚫")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred loading account `{public_key}`: {e}", icon="🚫")
        return None

def display_transaction_result():
    tx_hash = st.query_params.get("tx_hash")
    tx_result = st.query_params.get("tx_result")
    signed_xdr = st.query_params.get("signed_xdr")
    tx_error = st.query_params.get("tx_error")

    if tx_result == "success" and tx_hash:
        st.success(f"Transaction submitted successfully! Hash: `{tx_hash}` ✅", icon="✅")
        if signed_xdr:
            with st.expander("Signed Transaction XDR 📄"):
                st.code(signed_xdr, language="plaintext")
        st.link_button("View on Stellar Explorer ↗️", f"https://testnet.stellarexpert.io/tx/{tx_hash}", help="Opens in a new tab")
        clear_transaction_query_params()
        st.rerun() 
    elif tx_result == "error":
        st.error(f"Transaction failed: {tx_error} ❌", icon="❌")
        clear_transaction_query_params()
        st.rerun()

def clear_transaction_query_params():
    for param in ["tx_hash", "tx_result", "signed_xdr", "tx_error"]:
        if param in st.query_params:
            st.query_params.pop(param)
    
def get_asset_object(code, issuer):
    if code.upper() == "XLM":
        return Asset.native()
    try:
        if not issuer:
            st.error("Issuer is required for non-native assets.", icon="⚠️")
            return None
        Keypair.from_public_key(issuer) # Validate issuer format
        return Asset(code, issuer)
    except ValueError:
        st.error(f"Invalid issuer public key format: `{issuer}`", icon="⚠️")
        return None
    except Exception as e:
        st.error(f"Error creating asset object for {code}:{issuer}: {e}", icon="🚫")
        return None

def generate_tx_xdr(source_account, operations):
    try:
        base_fee = server.fetch_base_fee()
        transaction_builder = (
            TransactionBuilder(
                source_account=source_account,
                network_passphrase=NETWORK_PASSPHRASE,
                base_fee=base_fee,
            )
        )
        for op in operations:
            transaction_builder.add_operation(op)
        
        transaction = transaction_builder.build()
        return transaction.to_xdr()
    except Exception as e:
        st.error(f"Error building transaction: {e}", icon="⚠️")
        return None

# --- Main Application ---
def main():
    apply_custom_css()

    st.title("🛡️ AegisFlow: Compliant Digital Assets on Stellar 🌐")
    st.markdown(f"**Network:** `{CURRENT_NETWORK}` | **Horizon:** `{HORIZON_URL}`")

    st.write("---")

    # --- Freighter Connection ---
    st.header("🔗 Connect Freighter Wallet")
    st.write("Connect your Stellar wallet (Freighter) to interact with AegisFlow.")

    freighter_pk = st.query_params.get("freighter_pk", None)
    freighter_error = st.query_params.get("freighter_error", None)

    if freighter_pk:
        st.session_state.freighter_public_key = freighter_pk
        st.success(f"Connected to Freighter with Public Key: `{freighter_pk}` ✅")
        if "freighter_pk" in st.query_params:
            st.query_params.pop("freighter_pk")
            st.rerun()
    elif freighter_error:
        st.error(f"Freighter connection error: {freighter_error} ❌")
        if "freighter_error" in st.query_params:
            st.query_params.pop("freighter_error")
            st.rerun()
    else:
        html(FREIGHTER_JS_COMPONENT, height=0, width=0)
        if st.button("Connect Freighter Wallet 🚀"):
            html("<script>window.connectFreighter();</script>", height=0, width=0)
            st.info("Connecting to Freighter... Please approve in your wallet.", icon="💡")

    user_pk = st.session_state.get("freighter_public_key")
    if user_pk:
        st.subheader(f"User Public Key: `{user_pk}` ✨")
    else:
        st.warning("Please connect your Freighter wallet to use the dApp functionalities.", icon="⚠️")
        return

    # --- Account Dashboard ---
    st.header("📊 Account Dashboard")
    account_info = get_account_details(user_pk)

    if account_info:
        col1, col2, col3 = st.columns(3)
        native_balance = "0 XLM"
        funded_assets_count = 0
        data_entry_count = 0

        for balance in account_info.balances:
            if balance.asset_type == "native":
                native_balance = f"{float(balance.balance):,.2f} XLM"
            else:
                funded_assets_count += 1
        
        data_entry_count = len(account_info.data)

        with col1:
            st.metric("XLM Balance 💰", native_balance)
        with col2:
            st.metric("Funded Assets 💎", funded_assets_count)
        with col3:
            st.metric("Data Entries 📜", data_entry_count)

        with st.expander("Full Account Details (JSON) 📝"):
            st.json(account_info._response)

        st.info(f"**Demonstration Issuer Account:** `{ISSUER_PUBLIC_KEY}` (Funded on {CURRENT_NETWORK})", icon="ℹ️")
        st.code(f"Secret Key (for Clawback/CB creation): `{ISSUER_SECRET_KEY}`", language="plaintext")
        st.warning("Ensure the Issuer Account has some XLM and the AEGISTOKEN asset funded and set for clawback if testing clawback and token issuance.", icon="⚠️")

    # --- Transaction Operations ---
    st.header("⚙️ Stellar Operations")

    display_transaction_result()

    def sign_and_submit_tx_to_freighter(tx_xdr: str):
        st.session_state.last_tx_xdr = tx_xdr 
        st.markdown(f"<script>window.signAndSubmitTx('{tx_xdr}', '{NETWORK_PASSPHRASE}');</script>", unsafe_allow_html=True)
        st.info("Transaction sent to Freighter for signing... Please approve in your wallet.", icon="💡")

    # --- ChangeTrust Operation ---
    with st.expander("🤝 Adopt New Asset (ChangeTrust)"):
        st.write("Establish a trustline to hold a regulated asset from a specific issuer.")
        asset_code = st.text_input("Asset Code (e.g., USD, EURC)", value="AEGISTOKEN", max_chars=12, key="ct_code")
        asset_issuer = st.text_input("Asset Issuer Public Key", value=ISSUER_PUBLIC_KEY, key="ct_issuer")
        limit = st.text_input("Trustline Limit", value="", key="ct_limit", help="Leave empty for maximum.")

        if st.button("Create Trustline ✨", key="change_trust_btn"):
            if not asset_code or not asset_issuer:
                st.error("Asset Code and Issuer are required.", icon="🚫")
            else:
                asset = get_asset_object(asset_code, asset_issuer)
                if asset:
                    source_account = get_account_details(user_pk)
                    if source_account:
                        try:
                            operations = [
                                ChangeTrust(
                                    asset=asset,
                                    limit=limit if limit else None 
                                )
                            ]
                            tx_xdr = generate_tx_xdr(source_account, operations)
                            if tx_xdr:
                                sign_and_submit_tx_to_freighter(tx_xdr)
                        except Exception as e:
                            st.error(f"Error creating ChangeTrust operation: {e}", icon="🚫")

    # --- ManageData Operation ---
    with st.expander("✍️ Attach Compliance Attestation (ManageData)"):
        st.write("Attach compliance metadata to your account or an asset.")
        data_name = st.text_input("Data Name", key="md_name", max_chars=64)
        data_value = st.text_input("Data Value", key="md_value", max_chars=64)
        clear_data = st.checkbox("Clear this data entry", key="md_clear")

        if st.button("Add/Update Data Entry 📝", key="manage_data_btn"):
            if not data_name:
                st.error("Data Name is required.", icon="🚫")
            else:
                source_account = get_account_details(user_pk)
                if source_account:
                    try:
                        operations = [
                            ManageData(
                                data_name=data_name,
                                data_value=data_value.encode('utf-8') if data_value and not clear_data else None 
                            )
                        ]
                        tx_xdr = generate_tx_xdr(source_account, operations)
                        if tx_xdr:
                            sign_and_submit_tx_to_freighter(tx_xdr)
                    except Exception as e:
                        st.error(f"Error creating ManageData operation: {e}", icon="🚫")

    # --- Clawback Operation ---
    with st.expander("🚨 Clawback Asset (Issuer Demo)"):
        st.write("Demonstrates an issuer's ability to clawback funds.")
        st.warning(f"Signed by Issuer: `{ISSUER_PUBLIC_KEY}`", icon="⚠️")
        
        clawback_asset_code = st.text_input("Asset Code to Clawback", value="AEGISTOKEN", max_chars=12, key="cb_code")
        clawback_asset_issuer = st.text_input("Asset Issuer Public Key", value=ISSUER_PUBLIC_KEY, key="cb_issuer", disabled=True)
        clawback_from_account = st.text_input("Account to Clawback From", value=user_pk, key="cb_from")
        clawback_amount = st.number_input("Amount to Clawback", min_value=0.0000001, format="%.7f", value=10.0, key="cb_amount")

        if st.button("Initiate Clawback 🛑", key="clawback_btn"):
            if not clawback_asset_code or not clawback_asset_issuer or not clawback_from_account or clawback_amount <= 0:
                st.error("All clawback fields are required.", icon="🚫")
            else:
                asset = get_asset_object(clawback_asset_code, clawback_asset_issuer)
                if asset:
                    issuer_account = get_account_details(ISSUER_PUBLIC_KEY)
                    if issuer_account:
                        try:
                            operations = [
                                Clawback(
                                    asset=asset,
                                    from_=clawback_from_account,
                                    amount=str(clawback_amount)
                                )
                            ]
                            base_fee = server.fetch_base_fee()
                            transaction = (
                                TransactionBuilder(
                                    source_account=issuer_account,
                                    network_passphrase=NETWORK_PASSPHRASE,
                                    base_fee=base_fee,
                                )
                                .add_sequence_bump()
                                .add_operation(operations[0])
                                .build()
                            )
                            transaction.sign(ISSUER_SECRET_KEY)
                            
                            st.info("Submitting Clawback transaction...", icon="⏳")
                            response = server.submit_transaction(transaction)
                            st.success(f"Clawback successful! Hash: `{response['hash']}` ✅", icon="✅")
                            st.link_button("View on Stellar Explorer ↗️", f"https://testnet.stellarexpert.io/tx/{response['hash']}")

                        except BadRequestError as e:
                            st.error(f"Clawback failed: {e.extras.result_codes}", icon="❌")
                        except Exception as e:
                            st.error(f"Error initiating Clawback: {e}", icon="🚫")

    # --- ClaimClaimableBalance Operation ---
    with st.expander("🔒 Claim Conditional Funds"):
        st.write("Claim a claimable balance that was previously set up for your account.")
        
        create_cb_asset_code = st.text_input("Asset Code for CB", value="AEGISTOKEN", max_chars=12, key="cb_create_code")
        create_cb_amount = st.number_input("Amount for CB", min_value=0.0000001, format="%.7f", value=5.0, key="cb_create_amount")
        create_cb_sponsor_issuer = st.text_input("Issuer for CB Asset", value=ISSUER_PUBLIC_KEY, key="cb_create_issuer", disabled=True)

        if st.button("Create Claimable Balance (Issuer) 🎁", key="create_claimable_balance_btn"):
            if not create_cb_asset_code or not create_cb_amount:
                st.error("Asset code and amount are required.", icon="🚫")
            else:
                asset_for_cb = get_asset_object(create_cb_asset_code, create_cb_sponsor_issuer)
                if asset_for_cb:
                    issuer_account = get_account_details(ISSUER_PUBLIC_KEY)
                    if issuer_account:
                        try:
                            claimant = Claimant(user_pk, ClaimPredicate.unconditional())
                            operations = [
                                CreateClaimableBalance(
                                    asset=asset_for_cb,
                                    amount=str(create_cb_amount),
                                    claimants=[claimant]
                                )
                            ]
                            base_fee = server.fetch_base_fee()
                            transaction = (
                                TransactionBuilder(
                                    source_account=issuer_account,
                                    network_passphrase=NETWORK_PASSPHRASE,
                                    base_fee=base_fee,
                                )
                                .add_sequence_bump()
                                .add_operation(operations[0])
                                .build()
                            )
                            transaction.sign(ISSUER_SECRET_KEY)
                            
                            st.info("Submitting CreateClaimableBalance transaction...", icon="⏳")
                            response = server.submit_transaction(transaction)
                            st.success(f"Claimable Balance created! Hash: `{response['hash']}` ✅", icon="✅")
                            st.link_button("View on Stellar Explorer ↗️", f"https://testnet.stellarexpert.io/tx/{response['hash']}")

                        except BadRequestError as e:
                            st.error(f"Create Claimable Balance failed: {e.extras.result_codes}", icon="❌")
                        except Exception as e:
                            st.error(f"Error creating Claimable Balance: {e}", icon="🚫")

        st.write("---")
        claimable_balance_id = st.text_input("Claimable Balance ID", key="ccb_id")

        if st.button("Claim Balance 💰", key="claim_balance_btn"):
            if not claimable_balance_id or len(claimable_balance_id) != 64:
                st.error("Valid 64-char Claimable Balance ID is required.", icon="🚫")
            else:
                source_account = get_account_details(user_pk)
                if source_account:
                    try:
                        operations = [
                            ClaimClaimableBalance(
                                balance_id=claimable_balance_id
                            )
                        ]
                        tx_xdr = generate_tx_xdr(source_account, operations)
                        if tx_xdr:
                            sign_and_submit_tx_to_freighter(tx_xdr)
                    except Exception as e:
                        st.error(f"Error creating ClaimClaimableBalance operation: {e}", icon="🚫")

    # --- PathPaymentStrictReceive Operation ---
    with st.expander("🔄 Trade/Convert Assets"):
        st.write("Seamlessly convert one regulated asset to another.")
        destination_public_key = st.text_input("Destination Account", value=user_pk, key="ppsr_dest")
        send_asset_code = st.text_input("Asset to Send Code", value="XLM", max_chars=12, key="ppsr_send_code")
        send_asset_issuer = st.text_input("Asset to Send Issuer", value="", key="ppsr_send_issuer", help="Leave empty for native XLM.")
        send_max = st.number_input("Max Amount to Send", min_value=0.0000001, format="%.7f", value=1.0, key="ppsr_send_max")
        dest_asset_code = st.text_input("Asset to Receive Code", value="AEGISTOKEN", max_chars=12, key="ppsr_dest_code")
        dest_asset_issuer = st.text_input("Asset to Receive Issuer", value=ISSUER_PUBLIC_KEY, key="ppsr_dest_issuer")
        dest_amount = st.number_input("Min Amount to Receive", min_value=0.0000001, format="%.7f", value=0.5, key="ppsr_dest_amount")
        
        path_assets_raw = st.text_area("Path Assets (Code,Issuer pairs)", "AEGISTOKEN,YOUR_ISSUER_PK_IF_NEEDED", key="ppsr_path")

        if st.button("Execute Path Payment 🚀", key="path_payment_btn"):
            if not all([destination_public_key, send_asset_code, send_max, dest_asset_code, dest_amount]):
                st.error("All required path payment fields must be filled.", icon="🚫")
            else:
                source_account = get_account_details(user_pk)
                if source_account:
                    try:
                        send_asset = get_asset_object(send_asset_code, send_asset_issuer)
                        dest_asset = get_asset_object(dest_asset_code, dest_asset_issuer)
                        
                        if not send_asset or not dest_asset: return

                        path = []
                        if path_assets_raw.strip():
                            for line in path_assets_raw.strip().split('\n'):
                                if line.strip():
                                    parts = line.strip().split(',', 1)
                                    if len(parts) == 2:
                                        p_code = parts[0].strip()
                                        p_issuer = parts[1].strip()
                                        path_asset = get_asset_object(p_code, p_issuer)
                                        if path_asset: path.append(path_asset)

                        operations = [
                            PathPaymentStrictReceive(
                                destination=destination_public_key,
                                send_asset=send_asset,
                                send_max=str(send_max),
                                dest_asset=dest_asset,
                                dest_amount=str(dest_amount),
                                path=path
                            )
                        ]
                        tx_xdr = generate_tx_xdr(source_account, operations)
                        if tx_xdr:
                            sign_and_submit_tx_to_freighter(tx_xdr)
                    except Exception as e:
                        st.error(f"Error creating PathPaymentStrictReceive operation: {e}", icon="🚫")

if __name__ == "__main__":
    if "freighter_public_key" not in st.session_state:
        st.session_state.freighter_public_key = None
    if "last_tx_xdr" not in st.session_state:
        st.session_state.last_tx_xdr = None
    
    main()
