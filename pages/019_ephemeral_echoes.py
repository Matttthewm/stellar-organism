import streamlit as st
import streamlit.components.v1 as components
import stellar_sdk
from stellar_sdk import Server, Keypair, TransactionBuilder, Network, Asset
import requests

HORIZON_URL = "[https://horizon-testnet.stellar.org](https://horizon-testnet.stellar.org)"
NETWORK_PASSPHRASE = Network.TESTNET_NETWORK_PASSPHRASE # FIXED TYPO

if "demo_key" not in st.session_state: st.session_state.demo_key = Keypair.random().secret
ISSUER_KEYPAIR = Keypair.from_secret(st.session_state.demo_key)
server = Server(HORIZON_URL)

if 'freighter_public_key' not in st.session_state: st.session_state.freighter_public_key = None

def FreighterComponent():
    js_code = """
    <script src="[https://unpkg.com/@stellar/freighter-api@1.2.0/build/freighter.min.js](https://unpkg.com/@stellar/freighter-api@1.2.0/build/freighter.min.js)"></script>
    <script>
        async function connect() {
            const pk = await window.freighterApi.getPublicKey();
            window.location.search = `?fpk=${pk}`;
        }
    </script>
    """
    components.html(js_code, height=0, width=0)

if "fpk" in st.query_params:
    st.session_state.freighter_public_key = st.query_params["fpk"]
    st.query_params.clear()
    st.rerun()

st.title("🧬 Ephemeral Echoes")
FreighterComponent()

if not st.session_state.freighter_public_key:
    if st.button("Connect Freighter"): components.html("<script>connect()</script>", height=0, width=0)
else:
    st.success(f"Connected: {st.session_state.freighter_public_key}")
    if st.button("Fund Issuer"): requests.get(f"[https://friendbot.stellar.org/?addr=](https://friendbot.stellar.org/?addr=){ISSUER_KEYPAIR.public_key}")
    if st.button("Fund Me"): requests.get(f"[https://friendbot.stellar.org/?addr=](https://friendbot.stellar.org/?addr=){st.session_state.freighter_public_key}")
