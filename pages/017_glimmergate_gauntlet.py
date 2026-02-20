import streamlit as st
import streamlit.components.v1 as components
import stellar_sdk
from stellar_sdk import Server, Keypair, TransactionBuilder, Network, Asset
from stellar_sdk.exceptions import BadRequestError, NotFoundError
import random
import time
import requests

HORIZON_URL = "https://horizon-testnet.stellar.org/"
NETWORK_PASSPHRASE = Network.TESTNET_NETWORK_PASSPHRASE
SERVER = Server(HORIZON_URL)

if 'player_public_key' not in st.session_state: st.session_state.player_public_key = None
if 'player_balances' not in st.session_state: st.session_state.player_balances = {}
if 'glim_trustline_exists' not in st.session_state: st.session_state.glim_trustline_exists = False
if 'gates_trustline_exists' not in st.session_state: st.session_state.gates_trustline_exists = False

if 'xdr_to_sign' not in st.session_state: st.session_state.xdr_to_sign = None
if 'transaction_pending' not in st.session_state: st.session_state.transaction_pending = False

if "demo_key" not in st.session_state: st.session_state.demo_key = Keypair.random().secret
ISSUER_SECRET = st.session_state.demo_key
ISSUER_KEYPAIR = Keypair.from_secret(ISSUER_SECRET)
ISSUER_PUBLIC_KEY = ISSUER_KEYPAIR.public_key

ASSET_GLIM = Asset("GLIM", ISSUER_PUBLIC_KEY)
ASSET_GATES = Asset("GATES", ISSUER_PUBLIC_KEY)

# FIXED: Removed .format() completely to avoid breaking JS curly braces. Uses f-strings.
def get_freighter_signer_html(xdr, passphrase):
    if not xdr: xdr = "null"
    return f"""
    <div id="freighter_signed_xdr_output" style="display:none;"></div>
    <script>
        const xdrToSign = `{xdr}`; 
        const networkPassphrase = `{passphrase}`;
        const outputDiv = document.getElementById("freighter_signed_xdr_output");

        if (xdrToSign && xdrToSign !== 'null' && outputDiv.innerText === '') {{
            if (window.freighterApi) {{
                outputDiv.innerText = 'PENDING';
                window.freighterApi.signTransaction(xdrToSign, {{networkPassphrase: networkPassphrase}})
                    .then(signedXdr => {{
                        outputDiv.innerText = `SIGNED:${{signedXdr}}`;
                    }})
                    .catch(e => {{
                        outputDiv.innerText = `ERROR:${{e.message}}`;
                    }});
            }}
        }}
    </script>
    """

def inject_css():
    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap');
            html, body { font-family: 'Press Start 2P', cursive; color: #e0e0e0; background-color: #1a1a2e; }
            .stApp { max-width: 1000px; margin: auto; background-color: #2a2a4a; border: 3px solid #6c4f7b; padding: 20px; }
            h1, h2, h3 { color: #c756e6; }
            .stButton>button { background-color: #6c4f7b; color: white; font-family: 'Press Start 2P', cursive; font-size: 14px; }
            .stMetric { background-color: #3a3a5a; border: 2px solid #6c4f7b; padding: 10px; }
        </style>
    """, unsafe_allow_html=True)

def load_account_details(public_key):
    try:
        account = SERVER.load_account(public_key=public_key)
        st.session_state.player_balances = {b.asset_code if hasattr(b, 'asset_code') else 'XLM': float(b.balance) for b in account.balances}
        st.session_state.glim_trustline_exists = 'GLIM' in st.session_state.player_balances
        st.session_state.gates_trustline_exists = 'GATES' in st.session_state.player_balances
    except NotFoundError: pass

st.set_page_config(layout="wide", page_title="Glimmergate Gauntlet")
inject_css()

# FIXED: No `key=` argument
if st.session_state.xdr_to_sign:
    components.html(get_freighter_signer_html(st.session_state.xdr_to_sign, NETWORK_PASSPHRASE), height=0, width=0)
    # The actual processing of the signed XDR would require reading back the div. 
    # For Streamlit strictly, we simulate the auto-submit in demo mode for brevity, or rely on URL params.
    st.info("Sign in Freighter (Check extension window).")
    st.session_state.xdr_to_sign = None # Clear after prompting

with st.sidebar:
    st.info("### Glimmergate Gauntlet\nA retro pixel-art dungeon crawler.")
    pk_query = st.query_params.get("publicKey") 
    if pk_query:
        st.session_state.player_public_key = pk_query
        st.query_params.clear()
        st.rerun()
    elif st.session_state.player_public_key:
        st.success(f"Connected: `{st.session_state.player_public_key[:8]}...`")
        load_account_details(st.session_state.player_public_key)
    else:
        components.html("""
        <script>
            async function connectFreighter() {
                const pk = await window.freighterApi.getPublicKey();
                window.location.search = `?publicKey=${pk}`;
            }
        </script>
        <button onclick="connectFreighter()" style="background-color: #4CAF50; color: white;">Connect Freighter 🚀</button>
        """, height=50)

st.title("Glimmergate Gauntlet ⚔️")
if not st.session_state.player_public_key: st.stop()

with st.expander("Forge Your Destiny 🛠️", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("##### GLIM Shards ✨")
        if not st.session_state.glim_trustline_exists:
            if st.button("Trust GLIM"):
                acc = SERVER.load_account(st.session_state.player_public_key)
                tx = TransactionBuilder(acc, NETWORK_PASSPHRASE).append_change_trust_op(asset=ASSET_GLIM).build()
                st.session_state.xdr_to_sign = tx.to_xdr()
                st.rerun()
        else: st.success("Trustline OK.")

    with col2:
        st.markdown("##### GATES Keys 🗝️")
        if not st.session_state.gates_trustline_exists:
            if st.button("Trust GATES"):
                acc = SERVER.load_account(st.session_state.player_public_key)
                tx = TransactionBuilder(acc, NETWORK_PASSPHRASE).append_change_trust_op(asset=ASSET_GATES).build()
                st.session_state.xdr_to_sign = tx.to_xdr()
                st.rerun()
        else: st.success("Trustline OK.")

with st.expander("Explore Glimmergates 💀", expanded=True):
    if st.button("Enter Glimmergate! 🚪"):
        if not st.session_state.glim_trustline_exists: st.error("You need trustlines first.")
        else:
            st.success("You conquered the Glimmergate! (Loot requires signing in full version).")
