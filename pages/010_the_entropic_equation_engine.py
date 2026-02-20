import streamlit as st
import stellar_sdk
from stellar_sdk import Server, Keypair, TransactionBuilder, Network, Asset
from stellar_sdk.exceptions import BadRequestError, NotFoundError
import streamlit.components.v1 as components
import asyncio
import json

HORIZON_URL = "[https://horizon-testnet.stellar.org](https://horizon-testnet.stellar.org)"
NETWORK_PASSPHRASE = Network.TESTNET_NETWORK_PASSPHRASE
SERVER = Server(HORIZON_URL)

if "freighter_public_key" not in st.session_state: st.session_state.freighter_public_key = None
if "signed_xdr" not in st.session_state: st.session_state.signed_xdr = None

async def fetch_account_details(public_key):
    try: return await SERVER.load_account(public_key)
    except: return None

FREIGHTER_JS_COMPONENT = """
<script src="[https://unpkg.com/@stellar/freighter-api@latest/build/index.js](https://unpkg.com/@stellar/freighter-api@latest/build/index.js)"></script>
<script>
    const streamlit = window.parent.streamlit;
    async function connectFreighter() {
        try {
            const publicKey = await window.freighterApi.getPublicKey();
            streamlit.send({ type: 'freighter_connected', publicKey: publicKey });
        } catch (error) {}
    }
    window.addEventListener('message', async (event) => {
        if (event.data && event.data.streamlitMessage) {
            if (event.data.streamlitMessage.type === 'connect') await connectFreighter();
        }
    });
</script>
"""
components.html(FREIGHTER_JS_COMPONENT, height=0, width=0)

def send_to_freighter_component(message):
    components.html(f"<script>window.parent.postMessage({{ streamlitMessage: {json.dumps(message)} }}, '*');</script>", height=0, width=0)

if "streamlit_msg" in st.query_params:
    try:
        msg = json.loads(st.query_params["streamlit_msg"])
        if msg.get("type") == "freighter_connected":
            st.session_state.freighter_public_key = msg["publicKey"]
        st.query_params.clear()
        st.rerun()
    except: pass

if "demo_key" not in st.session_state: st.session_state.demo_key = Keypair.random().secret
ISSUER_KEYPAIR = Keypair.from_secret(st.session_state.demo_key)
ISSUER_PUBLIC_KEY = ISSUER_KEYPAIR.public_key

# FIXED: Removed Underscores
FRAGMENT_A = Asset("FRAGA", ISSUER_PUBLIC_KEY)
FRAGMENT_B = Asset("FRAGB", ISSUER_PUBLIC_KEY)

st.title("The Entropic Equation Engine 🧬")

if not st.session_state.freighter_public_key:
    if st.button("Connect Freighter Wallet"): send_to_freighter_component({"type": "connect"})
else:
    st.success(f"Connected: {st.session_state.freighter_public_key}")
    if st.button("Fund Equation Account"):
        import requests
        requests.get(f"[https://friendbot.stellar.org/?addr=](https://friendbot.stellar.org/?addr=){st.session_state.freighter_public_key}")
        st.rerun()
