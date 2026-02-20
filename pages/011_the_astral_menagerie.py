import streamlit as st
import stellar_sdk
from stellar_sdk import Server, Keypair, TransactionBuilder, Network, Asset
from stellar_sdk.exceptions import BadRequestError, NotFoundError
import streamlit.components.v1 as components
import json
import time
import requests

# --- Configuration ---
HORIZON_URL = "https://horizon-testnet.stellar.org"
# FIXED: Network Passphrase Typo
NETWORK_PASSPHRASE = Network.TESTNET_NETWORK_PASSPHRASE 
INITIAL_ISSUER_BALANCE = "10000"
ADOPTION_FEE_SDU = 5
SDU_INITIAL_SUPPLY = 1_000_000

server = Server(HORIZON_URL)

# --- Session State Initialization ---
if "public_key" not in st.session_state: st.session_state.public_key = None
if "signed_xdr" not in st.session_state: st.session_state.signed_xdr = None
if "transaction_hash" not in st.session_state: st.session_state.transaction_hash = None
if "current_xdr" not in st.session_state: st.session_state.current_xdr = None
if "tx_in_progress" not in st.session_state: st.session_state.tx_in_progress = False
if "freighter_public_key" not in st.session_state: st.session_state.freighter_public_key = None
if "freighter_status" not in st.session_state: st.session_state.freighter_status = None 
if "freighter_tx_signed_xdr" not in st.session_state: st.session_state.freighter_tx_signed_xdr = None
if "freighter_tx_error" not in st.session_state: st.session_state.freighter_tx_error = None
if "last_adoption_payment_tx_info" not in st.session_state: st.session_state.last_adoption_payment_tx_info = None 
if "current_adoption_target_creature_code" not in st.session_state: st.session_state.current_adoption_target_creature_code = None

if "ISSUER_KEY" in st.secrets:
    issuer_secret = st.secrets["ISSUER_KEY"]
    st.session_state.issuer_key_source = "secrets"
else:
    if "demo_key" not in st.session_state:
        st.session_state.demo_key = Keypair.random().secret
    issuer_secret = st.session_state.demo_key
    st.session_state.issuer_key_source = "demo"

try:
    issuer_keypair = Keypair.from_secret(issuer_secret)
    issuer_public_key = issuer_keypair.public_key
except ValueError:
    st.error("Invalid ISSUER_KEY provided. Please check your secrets or demo key.")
    st.stop()

STARDUST_ASSET = Asset("STARDUST", issuer_public_key)

CREATURE_ASSETS_CONFIG = [
    {"code": "AURORA", "name": "Aurora Spryte 🌌", "description": "A shimmering sprite, born from nebulae dust."},
    {"code": "LUMINA", "name": "Lumina Beast 🌠", "description": "A majestic creature, its gaze illuminates the darkest void."},
    {"code": "COSMO", "name": "Cosmo Gazer 💫", "description": "Observes the cosmos, a silent guardian of celestial paths."},
    {"code": "NEBULA", "name": "Nebula Weaver 🔮", "description": "Spins threads of starlight into intricate patterns."}
]
CREATURE_ASSETS = [Asset(c["code"], issuer_public_key) for c in CREATURE_ASSETS_CONFIG]

# --- Custom CSS ---
def apply_custom_css():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Cinzel+Decorative:wght@400;700&family=Orbitron:wght@400;700&display=swap');
        body { background-color: #0d0d1e; color: #e0e0f0; font-family: 'Cinzel Decorative', serif; }
        .stApp { background-color: #0d0d1e; background-image: radial-gradient(at 0% 0%, hsla(240,100%,70%,0.1) 0, transparent 50%), radial-gradient(at 100% 0%, hsla(280,100%,70%,0.1) 0, transparent 50%), radial-gradient(at 50% 100%, hsla(200,100%,70%,0.1) 0, transparent 50%), linear-gradient(to bottom, #1a0a2a, #0d0d1e); }
        h1, h2, h3, h4, h5, h6 { font-family: 'Orbitron', sans-serif; color: #d8b4fe; text-shadow: 0 0 5px #a78bfa, 0 0 10px #a78bfa; }
        .stButton>button { background-color: #3b0060; color: #e0e0f0; border: 1px solid #a78bfa; border-radius: 8px; padding: 10px 20px; font-family: 'Cinzel Decorative', serif; box-shadow: 0 0 8px rgba(167, 139, 250, 0.5); }
        .stButton>button:hover:not(:disabled) { background-color: #5d00a0; color: #ffffff; border-color: #c4b5fd; box-shadow: 0 0 15px rgba(196, 181, 253, 0.7); }
        .stMetric { background-color: #2a1a3a; border-radius: 10px; padding: 15px; border: 1px solid #5d00a0; box-shadow: 0 0 10px rgba(167, 139, 250, 0.3); }
        .stMetric div[data-testid="stMetricValue"] { color: #c4b5fd !important; font-family: 'Orbitron', sans-serif; font-size: 1.8em; }
        .stSidebar .st-emotion-cache-1pxx9r9 { background-color: #1a0a2a; }
        </style>
        """, unsafe_allow_html=True
    )

# --- Freighter HTML Component ---
def freighter_integration_html(action, xdr_to_sign=None):
    script_content = f"""
    <script src="https://unpkg.com/@stellar/freighter-api@latest/build/index.js"></script>
    <script>
        const ACTION = "{action}";
        const XDR_TO_SIGN = "{xdr_to_sign if xdr_to_sign else ''}";
        const NETWORK_PASSPHRASE = "{NETWORK_PASSPHRASE}";

        async function initFreighterAction() {{
            if (!window.freighterApi) return;
            if (ACTION === 'connect') {{
                const {{"publicKey"}} = await window.freighterApi.getPublicKey();
                window.parent.streamlit.setComponentValue('freighter_public_key', publicKey);
                window.parent.streamlit.setComponentValue('freighter_status', 'CONNECTED');
            }} else if (ACTION === 'sign' && XDR_TO_SIGN) {{
                const signedXdr = await window.freighterApi.signTransaction(XDR_TO_SIGN, {{networkPassphrase: NETWORK_PASSPHRASE}});
                window.parent.streamlit.setComponentValue('freighter_tx_signed_xdr', signedXdr);
            }}
        }}
        initFreighterAction(); 
    </script>
    """
    # FIXED: Removed `key` from components.html
    components.html(script_content, height=0, width=0)

def create_change_trust_op(asset, limit=None):
    return stellar_sdk.ChangeTrust(asset=asset, limit=str(limit) if limit is not None else None)

def create_payment_op(destination, asset, amount):
    return stellar_sdk.Payment(destination=destination, asset=asset, amount=str(amount))

def create_raw_tx(source_public_key, operations):
    try:
        source_account = server.load_account(source_public_key)
        transaction = TransactionBuilder(source_account=source_account, network_passphrase=NETWORK_PASSPHRASE).add_sequence_number()
        for op in operations: transaction.add_operation(op)
        return transaction.build().to_xdr()
    except: return None

def submit_signed_xdr(signed_xdr):
    try:
        response = server.submit_transaction(signed_xdr)
        st.success("Transaction successful!")
        return response
    except Exception as e:
        st.error("Failed.")
        return None

def get_account_data(public_key):
    try: return server.load_account(public_key)
    except: return None

def fund_account_with_friendbot(public_key):
    try:
        # FIXED: Use requests for Friendbot
        requests.get(f"https://friendbot.stellar.org/?addr={public_key}")
        st.success(f"Account funded successfully by Friendbot!")
        return True
    except Exception as e:
        st.error(f"Friendbot funding failed.")
        return False

def main():
    apply_custom_css()
    st.sidebar.info("**The Astral Menagerie** 🧬\nA celestial sanctuary where users adopt and nurture unique digital companions.")
    st.sidebar.caption("Visual Style: Mystical/Arcane ✨🔮🌌")

    st.markdown("<h1>The Astral Menagerie ✨🔮</h1>", unsafe_allow_html=True)
    st.markdown("### A celestial sanctuary for unique digital companions.")
    st.markdown("---")

    if not st.session_state.public_key:
        if st.button("Connect Freighter Wallet ✨", disabled=st.session_state.tx_in_progress):
            st.session_state.tx_in_progress = True 
            freighter_integration_html("connect")
            time.sleep(1)
            st.rerun()
        if st.session_state.get('freighter_status') == 'CONNECTED':
            st.session_state.public_key = st.session_state.freighter_public_key
            st.session_state.tx_in_progress = False
            st.rerun()
    else: 
        st.success(f"Connected Wallet: `{st.session_state.public_key}`")
        if st.button("Disconnect Wallet"):
            st.session_state.public_key = None
            st.rerun()

    if st.session_state.public_key:
        user_account = get_account_data(st.session_state.public_key)
        if not user_account:
            if st.button("Fund Account with Friendbot 🤖"):
                if fund_account_with_friendbot(st.session_state.public_key): st.rerun()
        else:
            col1, col2 = st.columns(2)
            xlm_balance = next((b.balance for b in user_account.balances if b.asset_type == 'native'), '0')
            stardust_balance = next((b.balance for b in user_account.balances if b.asset_code == STARDUST_ASSET.code), '0')
            col1.metric("Lumens (XLM) Balance 💰", f"{float(xlm_balance):,.2f} XLM")
            col2.metric(f"Stardust ({STARDUST_ASSET.code}) Balance ✨", f"{float(stardust_balance):,.2f} SDU")

            has_stardust_trustline = any(b.asset_code == STARDUST_ASSET.code for b in user_account.balances)
            if not has_stardust_trustline:
                if st.button(f"Establish Trustline for {STARDUST_ASSET.code}"):
                    xdr = create_raw_tx(st.session_state.public_key, [create_change_trust_op(STARDUST_ASSET)])
                    if xdr:
                        st.session_state.tx_in_progress = True
                        freighter_integration_html("sign", xdr_to_sign=xdr)
            
            if st.session_state.tx_in_progress and st.session_state.get('freighter_tx_signed_xdr'):
                submit_signed_xdr(st.session_state.freighter_tx_signed_xdr)
                st.session_state.tx_in_progress = False
                st.session_state.freighter_tx_signed_xdr = None
                st.rerun()

            st.markdown("---")
            st.subheader("The Astral Menagerie 🧬")
            for creature_conf in CREATURE_ASSETS_CONFIG:
                creature_asset = Asset(creature_conf["code"], issuer_public_key)
                holds_creature = any(b.asset_code == creature_asset.code and float(b.balance) >= 1 for b in user_account.balances)
                st.markdown(f"#### {creature_conf['name']}")
                st.markdown(f"*{creature_conf['description']}*")
                col_btn, _ = st.columns([1,3])
                with col_btn:
                    if holds_creature:
                        st.success("Adopted! 🎉")
                    elif has_stardust_trustline:
                        if st.button(f"Adopt {creature_asset.code}", key=f"adopt_{creature_asset.code}"):
                            xdr = create_raw_tx(st.session_state.public_key, [create_change_trust_op(creature_asset), create_payment_op(issuer_public_key, STARDUST_ASSET, ADOPTION_FEE_SDU)])
                            if xdr: freighter_integration_html("sign", xdr_to_sign=xdr)
                st.markdown("---")

if __name__ == "__main__":
    main()
