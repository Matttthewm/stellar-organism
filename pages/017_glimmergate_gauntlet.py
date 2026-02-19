import streamlit as st
import streamlit.components.v1 as components
import stellar_sdk
from stellar_sdk import Server, Keypair, TransactionBuilder, Network, Asset
from stellar_sdk.exceptions import BadRequestError, NotFoundError
import random
import time
import json # For passing network_config to Freighter HTML

# --- MANDATE 7: CRITICAL IMPORT RULES ---
# Always include 'import stellar_sdk' at the top.
# Then: 'from stellar_sdk import Server, Keypair, TransactionBuilder, Network, Asset'
# Then: 'from stellar_sdk.exceptions import BadRequestError, NotFoundError'
# NEVER import 'Ed25519PublicKeyInvalidError'. Use 'ValueError'.
# NEVER import 'AssetType'.

# --- CONFIGURATION ---
HORIZON_URL = "https://horizon-testnet.stellar.org/"
NETWORK_PASSPHRASE = Network.TESTNET_NETWORK_PASSPHRASE
SERVER = Server(HORIZON_URL) # MANDATE 8: Use 'Server(HORIZON_URL)' only. NEVER pass 'timeout' to Server().

# --- SESSION STATE INITIALIZATION ---
if 'player_public_key' not in st.session_state:
    st.session_state.player_public_key = None
if 'player_account' not in st.session_state:
    st.session_state.player_account = None
if 'player_balances' not in st.session_state:
    st.session_state.player_balances = {}
if 'player_account_needs_refresh' not in st.session_state:
    st.session_state.player_account_needs_refresh = True
if 'glim_trustline_exists' not in st.session_state:
    st.session_state.glim_trustline_exists = False
if 'gates_trustline_exists' not in st.session_state:
    st.session_state.gates_trustline_exists = False

# For Freighter Transaction Signing Flow
if 'xdr_to_sign' not in st.session_state:
    st.session_state.xdr_to_sign = None
if 'transaction_message' not in st.session_state:
    st.session_state.transaction_message = ""
if 'transaction_pending' not in st.session_state:
    st.session_state.transaction_pending = False
if 'last_transaction_key' not in st.session_state:
    st.session_state.last_transaction_key = None # To prevent re-processing same signed XDR


# --- MANDATE 11: SECRET KEY HANDLING ---
if "ISSUER_KEY" in st.secrets:
    ISSUER_SECRET = st.secrets["ISSUER_KEY"]
else:
    if "demo_key" not in st.session_state:
        st.session_state.demo_key = Keypair.random().secret
    ISSUER_SECRET = st.session_state.demo_key
    st.warning("🚨 Using Ephemeral Demo Issuer Keys. Your issuer key will reset on app restart. Please configure `st.secrets` for persistence.")

try:
    ISSUER_KEYPAIR = Keypair.from_secret(ISSUER_SECRET)
    ISSUER_PUBLIC_KEY = ISSUER_KEYPAIR.public_key
except ValueError: # MANDATE 7: Use ValueError
    st.error("Invalid ISSUER_KEY. Please check your secrets or ensure the demo key is valid.")
    st.stop()


# --- ASSET DEFINITIONS ---
ASSET_GLIM = Asset("GLIM", ISSUER_PUBLIC_KEY)
ASSET_GATES = Asset("GATES", ISSUER_PUBLIC_KEY)

# --- FREIGHTER HTML COMPONENTS (MANDATE 9: ALWAYS use components.html) ---
FREIGHTER_CONNECT_HTML = """
<script>
    async function connectFreighter() {
        if (window.freighterApi) {
            try {
                const publicKey = await window.freighterApi.getPublicKey();
                window.location.search = `?publicKey=${publicKey}`;
            } catch (e) {
                alert("Freighter connection failed: " + e.message);
                console.error("Freighter connection error:", e);
            }
        } else {
            alert("Freighter extension not found. Please install it.");
        }
    }
</script>
<button onclick="connectFreighter()" style="background-color: #4CAF50; color: white; padding: 10px 20px; border: none; cursor: pointer; font-size: 16px; border-radius: 5px; font-family: 'Press Start 2P', cursive;">
    Connect with Freighter 🚀
</button>
"""

# This component handles signing and returns a prefixed string (SIGNED:xdr or ERROR:message)
FREIGHTER_SIGNER_HTML = """
<div id="freighter_signed_xdr_output" style="display:none;"></div>
<script>
    const xdrToSign = `{xdr_to_sign}`; // XDR passed from Streamlit Python
    const networkPassphrase = `{network_passphrase}`;
    const transactionKey = `{transaction_key}`; // Unique key to identify transaction request

    const outputDiv = document.getElementById("freighter_signed_xdr_output");

    // Clear output if no XDR is provided or if transactionKey has changed (new request)
    if (!xdrToSign || xdrToSign === 'null' || outputDiv.dataset.transactionKey !== transactionKey) {
        outputDiv.innerText = '';
        outputDiv.dataset.transactionKey = transactionKey; // Store the key for next render
    }

    // Only attempt to sign if there's a new XDR and it hasn't been signed for this key before (output is empty)
    if (xdrToSign && xdrToSign !== 'null' && outputDiv.innerText === '' && outputDiv.dataset.transactionKey === transactionKey) {
        if (window.freighterApi) {
            outputDiv.innerText = 'PENDING'; // Indicate signing attempt

            const networkConfig = {
                network: networkPassphrase === 'Test SDF Network ; September 2015' ? 'testnet' : 'public',
                networkPassphrase: networkPassphrase
            };

            window.freighterApi.signTransaction(xdrToSign, networkConfig)
                .then(signedXdr => {
                    outputDiv.innerText = `SIGNED:${signedXdr}`;
                    outputDiv.dataset.transactionKey = transactionKey; // Confirm key on success
                })
                .catch(e => {
                    console.error("Freighter signing failed:", e);
                    outputDiv.innerText = `ERROR:${e.message}`;
                    outputDiv.dataset.transactionKey = transactionKey; // Confirm key on error
                });
        } else {
            outputDiv.innerText = 'ERROR:Freighter not found';
        }
    }
</script>
"""

# --- Custom CSS (MANDATE 3: Retro/Pixel-Art Style) ---
def inject_css():
    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap');
            html, body, [class*="st-emotion-cache"] {
                font-family: 'Press Start 2P', cursive;
                color: #e0e0e0; /* Light gray for pixel art feel */
                background-color: #1a1a2e; /* Dark blue/purple background */
                background-image: linear-gradient(to bottom, #1a1a2e, #0f0f1c);
                padding: 10px;
            }
            .stApp {
                max-width: 1000px;
                margin: auto;
                background-color: #2a2a4a; /* Slightly lighter inner background */
                border: 3px solid #6c4f7b; /* Purple border */
                box-shadow: 8px 8px 0px 0px #4a3a5a; /* Pixel art shadow */
                padding: 20px;
                border-radius: 5px;
            }
            h1, h2, h3, h4, h5, h6 {
                color: #c756e6; /* Vibrant purple for titles */
                text-shadow: 2px 2px #8b36a1; /* Shadow for pixel art text */
            }
            .stButton>button {
                background-color: #6c4f7b; /* Button background */
                color: white;
                border: 2px solid #a37bc7; /* Button border */
                padding: 10px 15px;
                border-radius: 3px;
                font-family: 'Press Start 2P', cursive;
                font-size: 14px;
                cursor: pointer;
                transition: all 0.1s ease-in-out;
                box-shadow: 3px 3px 0px 0px #4a3a5a; /* Button shadow */
            }
            .stButton>button:hover {
                background-color: #a37bc7;
                box-shadow: 1px 1px 0px 0px #4a3a5a; /* Smaller shadow on hover */
                transform: translate(2px, 2px);
            }
            .stTextInput>div>div>input {
                background-color: #3a3a5a;
                color: #e0e0e0;
                border: 1px solid #6c4f7b;
                border-radius: 3px;
                padding: 8px;
                font-family: monospace;
            }
            .stMetric {
                background-color: #3a3a5a;
                border: 2px solid #6c4f7b;
                padding: 10px;
                border-radius: 5px;
                box-shadow: 5px 5px 0px 0px #2a2a4a;
            }
            .stMetric .css-1cpxqw2, .stMetric .css-1cpxqw2.e16zpvmf3 { /* Metric label */
                color: #a37bc7;
                font-size: 1em;
            }
            .stMetric .css-1q9fgt5, .stMetric .css-1q9fgt5.e16zpvmf2 { /* Metric value */
                color: #f0f0f0;
                font-size: 1.5em;
            }
            .stExpander {
                background-color: #2a2a4a;
                border: 2px solid #6c4f7b;
                border-radius: 5px;
                margin-bottom: 15px;
                box-shadow: 5px 5px 0px 0px #1a1a2e;
            }
            .stExpander > div > div > div { /* Expander header */
                background-color: #4a3a5a;
                padding: 10px;
                border-bottom: 2px solid #6c4f7b;
                border-radius: 3px 3px 0 0;
            }
            .stAlert {
                background-color: #4a3a5a;
                border-left: 5px solid #a37bc7;
                color: #e0e0e0;
                padding: 10px;
                border-radius: 3px;
                font-size: 0.9em;
            }
            .stAlert.error { border-left-color: #e74c3c; }
            .stAlert.warning { border-left-color: #f39c12; }
            .stAlert.info { border-left-color: #3498db; }
            .stAlert.success { border-left-color: #2ecc71; }

            /* Sidebar specific styles */
            .st-emotion-cache-1q1n0j9, .st-emotion-cache-1q1n0j9.ezrtsby2 { /* Sidebar container */
                background-color: #1a1a2e;
                color: #e0e0e0;
                border-right: 3px solid #6c4f7b;
                box-shadow: 8px 8px 0px 0px #0f0f1c;
            }
            .st-emotion-cache-1q1n0j9 h1, .st-emotion-cache-1q1n0j9 h2, .st-emotion-cache-1q1n0j9 h3,
            .st-emotion-cache-1q1n0j9 h4, .st-emotion-cache-1q1n0j9 h5, .st-emotion-cache-1q1n0j9 h6 {
                color: #c756e6;
                text-shadow: 1px 1px #8b36a1;
            }
            .st-emotion-cache-1q1n0j9 .st-emotion-cache-zt5igz, .st-emotion-cache-1q1n0j9 .st-emotion-cache-zt5igz.e1f1d6z90 { /* st.sidebar.info content */
                background-color: #3a3a5a;
                border: 1px solid #6c4f7b;
                color: #f0f0f0;
                padding: 10px;
                border-radius: 3px;
            }
        </style>
    """, unsafe_allow_html=True)

# --- Helper Functions ---
def load_account_details(public_key):
    try:
        account = SERVER.load_account(public_key=public_key)
        balances = {balance.asset_code if hasattr(balance, 'asset_code') else 'XLM': float(balance.balance) for balance in account.balances}
        st.session_state.glim_trustline_exists = 'GLIM' in balances
        st.session_state.gates_trustline_exists = 'GATES' in balances
        st.session_state.player_account = account
        st.session_state.player_balances = balances
        st.session_state.player_account_needs_refresh = False
    except NotFoundError:
        st.error(f"Account {public_key} not found on the network. Please fund it (e.g., using the Stellar Laboratory Friendbot for Testnet).")
        st.session_state.player_account = None
        st.session_state.player_balances = {}
        st.session_state.player_account_needs_refresh = False
    except Exception as e:
        st.error(f"Error loading account details: {e}")
        st.session_state.player_account = None
        st.session_state.player_balances = {}
        st.session_state.player_account_needs_refresh = False

def initiate_freighter_transaction(transaction_xdr: str, message: str):
    """Initiates a transaction signing request via Freighter, updating session state."""
    st.session_state.xdr_to_sign = transaction_xdr
    st.session_state.transaction_message = message
    st.session_state.transaction_pending = True
    st.session_state.last_transaction_key = time.time() # Unique key for this transaction request
    # Trigger a rerun so the Freighter component re-renders with the new XDR
    st.rerun()

def make_payment(source_keypair: Keypair, destination_public_key: str, asset: Asset, amount: str, memo: str = None):
    """Submits a payment transaction, signed by the Issuer Keypair."""
    try:
        source_account = SERVER.load_account(source_keypair.public_key)
        tx_builder = TransactionBuilder(
            source_account=source_account,
            network_passphrase=NETWORK_PASSPHRASE,
            base_fee=100
        )
        # MANDATE 8: Access operations via module
        tx_builder.append_payment_op(
            destination=destination_public_key,
            asset=asset,
            amount=amount
        )
        if memo:
            tx_builder.add_text_memo(memo)

        transaction = tx_builder.build()
        transaction.sign(source_keypair) # Issuer signs this
        SERVER.submit_transaction(transaction)
        return True
    except BadRequestError as e:
        st.error(f"Issuer payment failed: {e.extras.get('result_codes', 'No result codes available')}")
    except Exception as e:
        st.error(f"An error occurred during issuer payment: {e}")
    return False

# --- UI Setup ---
st.set_page_config(layout="wide", page_title="Glimmergate Gauntlet")
inject_css()

# --- MANDATE 9: HTML COMPONENT RULES ---
# This component is rendered once and its state (innerText) is continuously checked.
# It's hidden but its JS interacts with Freighter based on st.session_state.xdr_to_sign
signed_xdr_from_component_html = components.html(
    FREIGHTER_SIGNER_HTML.format(
        xdr_to_sign=json.dumps(st.session_state.xdr_to_sign) if st.session_state.xdr_to_sign else 'null',
        network_passphrase=NETWORK_PASSPHRASE,
        transaction_key=str(st.session_state.last_transaction_key) # Pass as string
    ),
    key="freighter_signer_main", # Single key
    height=0, width=0 # Hidden
)

# Process the signed XDR result if a transaction is pending and the component returned a result
if st.session_state.transaction_pending and signed_xdr_from_component_html and signed_xdr_from_component_html != 'PENDING':
    if signed_xdr_from_component_html.startswith('SIGNED:'):
        signed_xdr = signed_xdr_from_component_html[7:]
        try:
            signed_tx = TransactionBuilder.from_xdr(signed_xdr, network_passphrase=NETWORK_PASSPHRASE)
            SERVER.submit_transaction(signed_tx)
            st.success(st.session_state.transaction_message)
            st.session_state.player_account_needs_refresh = True
        except BadRequestError as e:
            st.error(f"Transaction failed: {e.extras.get('result_codes', 'No result codes available')}")
        except Exception as e:
            st.error(f"An unexpected error occurred during submission: {e}")
        finally:
            # Clear all signing state after processing
            st.session_state.xdr_to_sign = None
            st.session_state.transaction_message = ""
            st.session_state.transaction_pending = False
            st.session_state.last_transaction_key = None
            st.rerun() # Rerun to clear component state and refresh UI
    elif signed_xdr_from_component_html.startswith('ERROR:'):
        st.error(f"Transaction failed: {signed_xdr_from_component_html[6:]}")
        # Clear all signing state
        st.session_state.xdr_to_sign = None
        st.session_state.transaction_message = ""
        st.session_state.transaction_pending = False
        st.session_state.last_transaction_key = None
        st.rerun() # Rerun to clear component state and refresh UI

# --- MANDATE 10: SIDEBAR MANDATE ---
with st.sidebar:
    st.info("### Glimmergate Gauntlet\n\nA retro pixel-art dungeon crawler where players delve into procedurally generated 'Glimmergates', fighting pixelated foes, collecting loot, and eventually forging their hero's legacy through strategic Stellar operations.")
    st.caption("Visual Style: 👾 **Retro/Pixel-Art** 👾")
    st.markdown("---")
    st.subheader("Player Status")
    
    # MANDATE 4: STRICTLY use 'st.query_params'
    player_public_key_from_query = st.query_params.get("publicKey") 

    if player_public_key_from_query and st.session_state.player_public_key != player_public_key_from_query:
        st.session_state.player_public_key = player_public_key_from_query
        st.session_state.player_account_needs_refresh = True # Force refresh for new player
        st.experimental_rerun() # Rerun to update state and UI
    elif st.session_state.player_public_key:
        st.success(f"Connected: `{st.session_state.player_public_key[:8]}...`")
    else:
        st.warning("Not connected to Freighter.")
        components.html(FREIGHTER_CONNECT_HTML, height=50)

    st.markdown("---")
    if st.session_state.player_public_key:
        if st.session_state.player_account_needs_refresh:
            load_account_details(st.session_state.player_public_key)

        if st.session_state.player_account:
            col_xlm, col_glim, col_gates = st.columns(3)
            with col_xlm:
                st.metric(label="XLM Balance 💰", value=f"{st.session_state.player_balances.get('XLM', 0):.2f}")
            with col_glim:
                st.metric(label="GLIM Shards ✨", value=f"{st.session_state.player_balances.get('GLIM', 0):.2f}")
            with col_gates:
                st.metric(label="GATES Keys 🗝️", value=f"{st.session_state.player_balances.get('GATES', 0):.2f}")
        else:
            st.error("Could not load player account details.")
    else:
        st.info("Connect Freighter to see player status.")

    st.markdown("---")
    st.subheader("Game Info")
    st.markdown(f"**Issuer Account**: `{ISSUER_PUBLIC_KEY[:8]}...`")
    st.markdown(f"**GLIM Asset**: `GLIM:{ISSUER_PUBLIC_KEY[:8]}...`")
    st.markdown(f"**GATES Asset**: `GATES:{ISSUER_PUBLIC_KEY[:8]}...`")

# --- Main App Content ---
st.title("Glimmergate Gauntlet ⚔️")
st.markdown("Delve into the Glimmergates, collect ancient loot, and forge your legend on the Stellar blockchain!")

if not st.session_state.player_public_key:
    st.info("Connect your Freighter wallet to begin your adventure!")
    st.stop() # Stop further execution if not connected

# --- Mandate 6: Use st.columns, st.expander, st.metric ---

# The Forge
with st.expander("forge your destiny 🛠️ (Stellar Operations)", expanded=True):
    st.subheader("The Ancient Forge")
    st.markdown("Here, you can establish trust with the Glimmergate assets and prepare for your adventures.")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### GLIM Shards ✨")
        if not st.session_state.glim_trustline_exists:
            st.warning(f"You need a trustline for GLIM.")
            if st.button(f"Establish Trustline for GLIM {ASSET_GLIM.code}", key="trust_glim", disabled=st.session_state.transaction_pending):
                try:
                    player_account = SERVER.load_account(st.session_state.player_public_key)
                    tx_builder = TransactionBuilder(
                        source_account=player_account,
                        network_passphrase=NETWORK_PASSPHRASE,
                        base_fee=100
                    )
                    # MANDATE 8: Access operations via module
                    tx_builder.append_change_trust_op(asset=ASSET_GLIM)
                    transaction = tx_builder.build()
                    initiate_freighter_transaction(transaction.to_xdr(), f"Trustline for {ASSET_GLIM.code} established successfully!")
                except Exception as e:
                    st.error(f"Error preparing GLIM trustline transaction: {e}")
        else:
            st.success(f"Trustline for GLIM already established.")

    with col2:
        st.markdown("##### GATES Keys 🗝️")
        if not st.session_state.gates_trustline_exists:
            st.warning(f"You need a trustline for GATES.")
            if st.button(f"Establish Trustline for GATES {ASSET_GATES.code}", key="trust_gates", disabled=st.session_state.transaction_pending):
                try:
                    player_account = SERVER.load_account(st.session_state.player_public_key)
                    tx_builder = TransactionBuilder(
                        source_account=player_account,
                        network_passphrase=NETWORK_PASSPHRASE,
                        base_fee=100
                    )
                    # MANDATE 8: Access operations via module
                    tx_builder.append_change_trust_op(asset=ASSET_GATES)
                    transaction = tx_builder.build()
                    initiate_freighter_transaction(transaction.to_xdr(), f"Trustline for {ASSET_GATES.code} established successfully!")
                except Exception as e:
                    st.error(f"Error preparing GATES trustline transaction: {e}")
        else:
            st.success(f"Trustline for GATES already established.")

    st.markdown("---")
    st.markdown("##### Upgrade Your Hero 🌟")
    st.write("Exchange your GLIM Shards for more GATES Keys, preparing for deeper delves!")
    glim_to_burn = st.number_input("GLIM to Burn (10 GLIM = 1 GATES)", min_value=10.0, step=10.0, format="%.2f", key="glim_burn_input", disabled=st.session_state.transaction_pending)
    
    if st.button("Trade GLIM for GATES", key="trade_glim_gates", disabled=st.session_state.transaction_pending):
        if not st.session_state.glim_trustline_exists or not st.session_state.gates_trustline_exists:
            st.error("You need trustlines for both GLIM and GATES to trade.")
        elif st.session_state.player_balances.get('GLIM', 0) < glim_to_burn:
            st.error(f"Insufficient GLIM shards. You have {st.session_state.player_balances.get('GLIM', 0):.2f}, but need {glim_to_burn:.2f}.")
        else:
            try:
                # Player sends GLIM to Issuer (burn)
                player_account = SERVER.load_account(st.session_state.player_public_key)
                tx_builder = TransactionBuilder(
                    source_account=player_account,
                    network_passphrase=NETWORK_PASSPHRASE,
                    base_fee=100
                )
                tx_builder.append_payment_op(
                    destination=ISSUER_PUBLIC_KEY,
                    asset=ASSET_GLIM,
                    amount=f"{glim_to_burn:.7f}"
                )
                transaction = tx_builder.build()
                initiate_freighter_transaction(transaction.to_xdr(), f"Successfully sent {glim_to_burn:.2f} GLIM to the Forge.")
                
                # Issuer sends GATES to Player (reward) happens automatically IF player's GLIM burn succeeds
                # This cannot be part of the same transaction easily when one op is player signed, other is issuer signed.
                # For demo purposes, we will assume success and send GATES immediately after player's transaction.
                # A more robust system would involve checking the payment transaction from the player.
                st.session_state.glim_burn_amount = glim_to_burn # Store to process after player tx
                st.session_state.gates_reward_amount = glim_to_burn / 10.0

            except Exception as e:
                st.error(f"Error during trade preparation: {e}")

# If player's GLIM burn was successful, issue GATES
if not st.session_state.transaction_pending and st.session_state.get('glim_burn_amount') is not None:
    glim_burned = st.session_state.glim_burn_amount
    gates_reward = st.session_state.gates_reward_amount
    st.session_state.glim_burn_amount = None # Clear
    st.session_state.gates_reward_amount = None # Clear

    # Give time for the ledger to close from the previous transaction
    time.sleep(2)
    
    if make_payment(ISSUER_KEYPAIR, st.session_state.player_public_key, ASSET_GATES, f"{gates_reward:.7f}", f"Forge Trade: {glim_burned} GLIM for {gates_reward} GATES"):
        st.success(f"You received {gates_reward:.2f} GATES Keys from the Forge! 🎉")
        st.session_state.player_account_needs_refresh = True
    else:
        st.error("Failed to issue GATES after GLIM burn. Please try again.")
    st.rerun() # Rerun to update balances

# Explore Glimmergates
with st.expander("explore glimmergates 💀 (Dungeon Crawler)", expanded=True):
    st.subheader("Delve into the Unknown")
    st.write("Each Glimmergate offers unique challenges and treasures. Prepare for battle!")

    col_diff, col_loot, col_monsters = st.columns(3)
    with col_diff:
        st.metric("Difficulty 📈", random.choice(["Easy", "Normal", "Hard", "Deadly"]))
    with col_loot:
        st.metric("Loot Chances 💎", random.choice(["Low", "Medium", "High", "Epic"]))
    with col_monsters:
        st.metric("Monsters Encountered 👹", random.randint(3, 15))

    st.markdown("---")

    if st.button("Enter Glimmergate! 🚪", key="enter_dungeon_button", disabled=st.session_state.transaction_pending):
        if not st.session_state.glim_trustline_exists or not st.session_state.gates_trustline_exists:
            st.error("You need trustlines for both GLIM and GATES to collect loot from Glimmergates. Visit 'The Forge' first.")
        else:
            st.info("You bravely enter the Glimmergate...")
            time.sleep(1) # Simulate dungeon crawl

            outcome = random.choice(["win", "lose"])

            if outcome == "win":
                glim_reward = round(random.uniform(5, 20), 2)
                gates_reward = round(random.uniform(0.1, 1), 2)
                st.success(f"You conquered the Glimmergate! You found {glim_reward} GLIM ✨ and {gates_reward} GATES 🗝️!")

                # Issuer issues GLIM and GATES to player
                if make_payment(ISSUER_KEYPAIR, st.session_state.player_public_key, ASSET_GLIM, f"{glim_reward:.7f}", "Glimmergate Loot: GLIM"):
                    if make_payment(ISSUER_KEYPAIR, st.session_state.player_public_key, ASSET_GATES, f"{gates_reward:.7f}", "Glimmergate Loot: GATES"):
                        st.session_state.player_account_needs_refresh = True
                        st.success("Loot successfully transferred to your wallet!")
                    else:
                        st.error("Failed to issue GATES. Please try again.")
                else:
                    st.error("Failed to issue GLIM. Please try again.")
                st.rerun() # Rerun to update balances and clear messages
            else:
                st.error("You were overwhelmed by the dungeon's guardians... Retreat and try again! 🤕")

# MANDATE 5: NO external images. Use Emojis 🧬 only.
st.markdown("---")
st.markdown("Brought to you by 🧬 Glimmergate Studios 🧬")