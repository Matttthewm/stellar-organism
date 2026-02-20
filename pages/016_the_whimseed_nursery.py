import streamlit as st
import streamlit.components.v1 as components
import stellar_sdk
from stellar_sdk import Server, Keypair, TransactionBuilder, Network, Asset
from stellar_sdk.exceptions import BadRequestError, NotFoundError
import json
import time
import base64
import requests

HORIZON_URL = "https://horizon-testnet.stellar.org"
NETWORK_PASSPHRASE = Network.TESTNET_NETWORK_PASSPHRASE
SERVER = Server(HORIZON_URL)

WHIM_ASSET_CODE = "WHIM"
SPONSORSHIP_COST_XLM = "1" 
WHIM_SEED_AMOUNT = "1"     

if "freighter_pk" not in st.session_state: st.session_state.freighter_pk = None
if "transaction_status" not in st.session_state: st.session_state.transaction_status = ""
if "last_tx_hash" not in st.session_state: st.session_state.last_tx_hash = None
if "seed_vitality" not in st.session_state: st.session_state.seed_vitality = 100 
if "seed_evolution" not in st.session_state: st.session_state.seed_evolution = "Embryonic"
if "whim_balance" not in st.session_state: st.session_state.whim_balance = "0"
if "has_whim_trustline" not in st.session_state: st.session_state.has_whim_trustline = False
if "is_whim_revocable" not in st.session_state: st.session_state.is_whim_revocable = False
if "home_domain" not in st.session_state: st.session_state.home_domain = ""

if "demo_nursery_key" not in st.session_state: st.session_state.demo_nursery_key = Keypair.random().secret
nursery_issuer_key = Keypair.from_secret(st.session_state.demo_nursery_key)
NURSERY_ISSUER_PUBLIC_KEY = nursery_issuer_key.public_key
WHIM_ASSET = Asset(WHIM_ASSET_CODE, NURSERY_ISSUER_PUBLIC_KEY)

def inject_custom_css():
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');
            html, body { font-family: 'IBM Plex Sans', sans-serif; background-color: #f0f2f6; color: #333; }
            h1, h2, h3 { color: #222; font-weight: 500; }
            .stButton>button { background-color: #007bff; color: white; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .stMetric { background-color: white; padding: 15px; border-radius: 8px; border: 1px solid #e0e0e0; }
        </style>
        """, unsafe_allow_html=True
    )
inject_custom_css()

FREIGHTER_JS = """
<script src="https://unpkg.com/@stellar/freighter-api@latest/build/index.js"></script>
<script>
    const resultsDiv = document.createElement('div');
    resultsDiv.id = 'freighter-results';
    document.body.appendChild(resultsDiv);

    async function getFreighterPublicKey() {
        if (window.freighter) {
            const publicKey = await window.freighter.getPublicKey();
            return publicKey;
        }
        return null;
    }

    async function signTransactionWithFreighter(xdr, networkPassphrase) {
        if (window.freighter) {
            return await window.freighter.signTransaction(xdr, { networkPassphrase });
        }
        return null;
    }
</script>
"""

def render_freighter_js_component(action, xdr=None):
    if action == "sign_and_submit" and xdr:
        js_code = f"""
            {FREIGHTER_JS}
            <script>
                async function triggerSignAndSubmit() {{
                    const signedXDR = await signTransactionWithFreighter("{xdr}", "{NETWORK_PASSPHRASE}");
                    if (signedXDR) {{
                        window.location.href = '?signed_xdr=' + btoa(signedXDR) + '&tx_action=submit_tx';
                    }}
                }}
                triggerSignAndSubmit();
            </script>
            """
        components.html(js_code, height=0, width=0)

def check_account_status(public_key):
    try:
        account = SERVER.load_account(public_key)
        st.session_state.has_whim_trustline = False
        st.session_state.whim_balance = "0"
        for balance in account.balances:
            if balance.asset_code == WHIM_ASSET_CODE and balance.asset_issuer == NURSERY_ISSUER_PUBLIC_KEY:
                st.session_state.has_whim_trustline = True
                st.session_state.whim_balance = balance.balance
                break
        st.session_state.home_domain = account.home_domain if account.home_domain else "No Home Domain Set"
        return account
    except: return None

def fund_account(public_key):
    # FIXED: Use requests for friendbot
    requests.get(f"https://friendbot.stellar.org/?addr={public_key}")
    st.success(f"Account {public_key} funded by Friendbot.")

def build_sponsor_seed_tx(source_pk):
    try:
        source_account = SERVER.load_account(source_pk)
        tx_builder = TransactionBuilder(source_account=source_account, network_passphrase=NETWORK_PASSPHRASE, base_fee=100)
        tx_builder.add_operation(stellar_sdk.Payment(destination=NURSERY_ISSUER_PUBLIC_KEY, asset=Asset.native(), amount=SPONSORSHIP_COST_XLM))
        tx_builder.add_operation(stellar_sdk.ChangeTrust(asset=WHIM_ASSET, limit="1000000000"))
        return tx_builder.build().to_xdr()
    except: return None

def build_evolve_seed_tx(source_pk, evolution_choice):
    try:
        source_account = SERVER.load_account(source_pk)
        tx_builder = TransactionBuilder(source_account=source_account, network_passphrase=NETWORK_PASSPHRASE, base_fee=100)
        new_home_domain = f"whimseed-{evolution_choice.lower().replace(' ', '-')}.whim"
        tx_builder.add_operation(stellar_sdk.SetOptions(home_domain=new_home_domain))
        return tx_builder.build().to_xdr()
    except: return None

# FIXED: transaction_xdr_or_or_object typo changed to transaction_xdr_or_object
def submit_transaction(transaction_xdr_or_object):
    try:
        tx_to_submit = stellar_sdk.TransactionBuilder.from_xdr(transaction_xdr_or_object, NETWORK_PASSPHRASE)
        response = SERVER.submit_transaction(tx_to_submit)
        st.success(f"Transaction successful! Hash: {response['hash']}")
        return True
    except Exception as e:
        st.error("Failed.")
        return False

def connect_freighter_callback():
    js_code = f"""
        {FREIGHTER_JS}
        <script>
            getFreighterPublicKey().then(publicKey => {{
                if (publicKey) window.location.href = '?freighter_pk=' + publicKey;
            }});
        </script>
    """
    components.html(js_code, height=0, width=0)

def handle_query_params():
    query_params = st.query_params
    if "freighter_pk" in query_params:
        st.session_state.freighter_pk = query_params["freighter_pk"]
        st.query_params.clear()
        st.rerun()
    elif "signed_xdr" in query_params and "tx_action" in query_params:
        signed_xdr = base64.b64decode(query_params["signed_xdr"]).decode('utf-8')
        submit_transaction(signed_xdr)
        st.query_params.clear()
        st.rerun()

st.set_page_config(layout="centered", page_title="The Whim-Seed Nursery 🧬")

with st.sidebar:
    st.info("**The Whim-Seed Nursery 🧬**\nUsers nurture unique digital 'Whim-Seeds'.")
    st.subheader("Nursery Settings")
    if st.button("Fund Nursery Issuer (Friendbot)"): fund_account(NURSERY_ISSUER_PUBLIC_KEY)

handle_query_params()

st.title("The Whim-Seed Nursery 🧬")
st.subheader("1. Connect Your Wallet 🔑")
if st.session_state.freighter_pk:
    st.success(f"Connected: `{st.session_state.freighter_pk}`")
    user_account = check_account_status(st.session_state.freighter_pk)
    if not user_account:
        st.button("Fund My Account", on_click=lambda: fund_account(st.session_state.freighter_pk))
else:
    st.button("Connect Freighter Wallet", on_click=connect_freighter_callback)

if st.session_state.freighter_pk and st.session_state.has_whim_trustline:
    st.subheader("2. Your Whim-Seed 🌱")
    col1, col2, col3 = st.columns(3)
    col1.metric("Vitality 💖", f"{st.session_state.seed_vitality}%")
    col2.metric("Evolution Stage ✨", st.session_state.seed_evolution)
    col3.metric(f"WHIM Balance", st.session_state.whim_balance)

    st.subheader("3. Nurture & Guide Your Seed 🧑‍🌾")
    if st.button("Nurture Whim-Seed"): st.session_state.seed_vitality = min(st.session_state.seed_vitality + 10, 100)
    
    evolution_choices = ["Growth", "Adaptation", "Resilience", "Innovation"]
    selected_evolution = st.selectbox("Choose an evolutionary path:", evolution_choices)
    if st.button(f"Guide Evolution to: {selected_evolution}"):
        render_freighter_js_component("sign_and_submit", build_evolve_seed_tx(st.session_state.freighter_pk, selected_evolution))
else:
    st.subheader("2. Sponsor a New Whim-Seed 🌟")
    if st.session_state.freighter_pk:
        if st.button("Sponsor New Whim-Seed (Cost: 1 XLM)"):
            render_freighter_js_component("sign_and_submit", build_sponsor_seed_tx(st.session_state.freighter_pk))
