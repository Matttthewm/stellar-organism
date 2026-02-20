import stellar_sdk
from stellar_sdk import Server, Keypair, TransactionBuilder, Network, Asset
from stellar_sdk.exceptions import BadRequestError, NotFoundError
import streamlit as st
import streamlit.components.v1 as components
import requests

HORIZON_URL = "[https://horizon-testnet.stellar.org](https://horizon-testnet.stellar.org)"
NETWORK_PASSPHRASE = Network.TESTNET_NETWORK_PASSPHRASE
server = Server(HORIZON_URL)

if "demo_key" not in st.session_state: st.session_state.demo_key = Keypair.random().secret
ISSUER_KEY = Keypair.from_secret(st.session_state.demo_key)
ISSUER_PUBLIC_KEY = ISSUER_KEY.public_key

if "issuer_funded" not in st.session_state:
    try:
        requests.get(f"[https://friendbot.stellar.org/?addr=](https://friendbot.stellar.org/?addr=){ISSUER_PUBLIC_KEY}") # FIXED
        st.session_state.issuer_funded = True
    except: pass

if "freighter_public_key" not in st.session_state: st.session_state.freighter_public_key = None

JS_CONNECT = """
<script src="[https://unpkg.com/@stellar/freighter-api@latest/build/index.js](https://unpkg.com/@stellar/freighter-api@latest/build/index.js)"></script>
<script>
    async function connect() {
        const pk = await window.freighterApi.getPublicKey();
        window.location.search = `?pk=${pk}`;
    }
</script>
"""

if "pk" in st.query_params:
    st.session_state.freighter_public_key = st.query_params["pk"]
    st.query_params.clear()
    st.rerun()

st.title("The Petalfall Bazaar 🌸")
components.html(JS_CONNECT, height=0, width=0)

if not st.session_state.freighter_public_key:
    if st.button("Connect"): components.html("<script>connect()</script>", height=0, width=0)
else:
    st.success(f"Connected: {st.session_state.freighter_public_key}")
    if st.button("Fund Me"):
        requests.get(f"[https://friendbot.stellar.org/?addr=](https://friendbot.stellar.org/?addr=){st.session_state.freighter_public_key}")
