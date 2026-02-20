import streamlit as st
import stellar_sdk
from stellar_sdk import Server, Keypair, TransactionBuilder, Network, Asset
from stellar_sdk.exceptions import BadRequestError, NotFoundError
import streamlit.components.v1 as components
import json

HORIZON_URL = "[https://horizon-testnet.stellar.org](https://horizon-testnet.stellar.org)"
NETWORK_PASSPHRASE = Network.TESTNET_NETWORK_PASSPHRASE # FIXED TYPO
server = Server(HORIZON_URL)

if "public_key" not in st.session_state: st.session_state.public_key = None
if "demo_key" not in st.session_state: st.session_state.demo_key = Keypair.random().secret

issuer_keypair = Keypair.from_secret(st.session_state.demo_key)
issuer_public_key = issuer_keypair.public_key
STARDUST_ASSET = Asset("STARDUST", issuer_public_key)

def freighter_integration_html(action, xdr_to_sign=None):
    script_content = f"""
    <script src="[https://unpkg.com/@stellar/freighter-api@latest/build/index.js](https://unpkg.com/@stellar/freighter-api@latest/build/index.js)"></script>
    <script>
        async function initFreighterAction() {{
            if ("{action}" === 'connect') {{
                const {{publicKey}} = await window.freighterApi.getPublicKey();
                window.parent.location.search = `?freighter_pk=${{publicKey}}`;
            }}
        }}
        initFreighterAction();
    </script>
    """
    components.html(script_content, height=0, width=0) # FIXED: Removed key

if "freighter_pk" in st.query_params:
    st.session_state.public_key = st.query_params["freighter_pk"]
    st.query_params.clear()
    st.rerun()

st.title("The Astral Menagerie ✨")
if not st.session_state.public_key:
    if st.button("Connect Wallet"): freighter_integration_html("connect")
else:
    st.success(f"Connected: {st.session_state.public_key}")
    if st.button("Fund (Friendbot)"):
        import requests
        requests.get(f"[https://friendbot.stellar.org/?addr=](https://friendbot.stellar.org/?addr=){st.session_state.public_key}")
        st.success("Funded!")
