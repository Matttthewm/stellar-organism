import streamlit as st
import streamlit.components.v1 as components
import stellar_sdk
from stellar_sdk import Server, Keypair, TransactionBuilder, Network, Asset
from stellar_sdk.exceptions import BadRequestError, NotFoundError
import requests # FIXED: Imported requests

HORIZON_URL = "[https://horizon-testnet.stellar.org](https://horizon-testnet.stellar.org)"
NETWORK_PASSPHRASE = Network.TESTNET_NETWORK_PASSPHRASE
server = Server(HORIZON_URL)

if "demo_key" not in st.session_state: st.session_state.demo_key = Keypair.random().secret
ISSUER_KEYPAIR = Keypair.from_secret(st.session_state.demo_key)
ISSUER_PUBLIC_KEY = ISSUER_KEYPAIR.public_key

LUMINA_DUST_ASSET = Asset("LUMINA", ISSUER_PUBLIC_KEY)
if 'public_key' not in st.session_state: st.session_state.public_key = None

def setup_issuer_account():
    try:
        server.load_account(ISSUER_PUBLIC_KEY)
    except NotFoundError:
        requests.get(f"[https://friendbot.stellar.org/?addr=](https://friendbot.stellar.org/?addr=){ISSUER_PUBLIC_KEY}") # FIXED
        st.success("Sanctuary core funded via Friendbot!")

st.title("The Whispering Wisp Sanctuary 🌬️")
components.html("""
<script src="[https://unpkg.com/@stellar/freighter-api@latest/build/index.js](https://unpkg.com/@stellar/freighter-api@latest/build/index.js)"></script>
<script>
    async function connectFreighter() {
        const pk = await window.freighterApi.getPublicKey();
        window.location.search = `?pk=${pk}`;
    }
</script>
""", height=0, width=0)

if "pk" in st.query_params:
    st.session_state.public_key = st.query_params["pk"]
    st.query_params.clear()
    st.rerun()

if not st.session_state.public_key:
    if st.button("Connect"): components.html("<script>connectFreighter()</script>", height=0, width=0)
else:
    st.success(f"Connected: {st.session_state.public_key}")
    if st.button("Fund Me"):
        requests.get(f"[https://friendbot.stellar.org/?addr=](https://friendbot.stellar.org/?addr=){st.session_state.public_key}")
        st.success("Funded!")

setup_issuer_account()
