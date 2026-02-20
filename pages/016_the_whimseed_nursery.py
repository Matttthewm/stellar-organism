import streamlit as st
import streamlit.components.v1 as components
import stellar_sdk
from stellar_sdk import Server, Keypair, TransactionBuilder, Network, Asset
from stellar_sdk.exceptions import BadRequestError, NotFoundError
import base64
import requests

HORIZON_URL = "[https://horizon-testnet.stellar.org](https://horizon-testnet.stellar.org)"
NETWORK_PASSPHRASE = Network.TESTNET_NETWORK_PASSPHRASE
SERVER = Server(HORIZON_URL)

if "freighter_pk" not in st.session_state: st.session_state.freighter_pk = None
if "demo_key" not in st.session_state: st.session_state.demo_key = Keypair.random().secret

nursery_issuer_key = Keypair.from_secret(st.session_state.demo_key)
NURSERY_ISSUER_PUBLIC_KEY = nursery_issuer_key.public_key
WHIM_ASSET = Asset("WHIM", NURSERY_ISSUER_PUBLIC_KEY)

FREIGHTER_JS = """
<script src="[https://unpkg.com/@stellar/freighter-api@latest/build/index.js](https://unpkg.com/@stellar/freighter-api@latest/build/index.js)"></script>
<script>
    async function connectF() {
        const pk = await window.freighter.getPublicKey();
        window.location.search = `?fpk=${pk}`;
    }
</script>
"""

if "fpk" in st.query_params:
    st.session_state.freighter_pk = st.query_params["fpk"]
    st.query_params.clear()
    st.rerun()

st.title("The Whim-Seed Nursery 🧬")
components.html(FREIGHTER_JS, height=0, width=0)

if not st.session_state.freighter_pk:
    if st.button("Connect Freighter"): components.html("<script>connectF()</script>", height=0, width=0)
else:
    st.success(f"Connected: {st.session_state.freighter_pk}")
    if st.button("Fund Issuer"): 
        requests.get(f"[https://friendbot.stellar.org/?addr=](https://friendbot.stellar.org/?addr=){NURSERY_ISSUER_PUBLIC_KEY}")
    if st.button("Fund Player"):
        requests.get(f"[https://friendbot.stellar.org/?addr=](https://friendbot.stellar.org/?addr=){st.session_state.freighter_pk}")
