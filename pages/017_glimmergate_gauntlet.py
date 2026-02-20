import streamlit as st
import streamlit.components.v1 as components
import stellar_sdk
from stellar_sdk import Server, Keypair, TransactionBuilder, Network, Asset
from stellar_sdk.exceptions import BadRequestError, NotFoundError

HORIZON_URL = "[https://horizon-testnet.stellar.org/](https://horizon-testnet.stellar.org/)"
NETWORK_PASSPHRASE = Network.TESTNET_NETWORK_PASSPHRASE
SERVER = Server(HORIZON_URL)

if 'player_public_key' not in st.session_state: st.session_state.player_public_key = None
if "demo_key" not in st.session_state: st.session_state.demo_key = Keypair.random().secret
ISSUER_KEYPAIR = Keypair.from_secret(st.session_state.demo_key)

ASSET_GLIM = Asset("GLIM", ISSUER_KEYPAIR.public_key)

FREIGHTER_CONNECT_HTML = """
<script src="[https://unpkg.com/@stellar/freighter-api@latest/build/index.js](https://unpkg.com/@stellar/freighter-api@latest/build/index.js)"></script>
<script>
    async function connectFreighter() {
        const pk = await window.freighterApi.getPublicKey();
        window.location.search = `?publicKey=${pk}`;
    }
</script>
<button onclick="connectFreighter()">Connect with Freighter 🚀</button>
"""

pk_query = st.query_params.get("publicKey") 
if pk_query:
    st.session_state.player_public_key = pk_query
    st.query_params.clear()
    st.rerun()

st.title("Glimmergate Gauntlet ⚔️")
if not st.session_state.player_public_key:
    components.html(FREIGHTER_CONNECT_HTML, height=50)
else:
    st.success(f"Connected: {st.session_state.player_public_key}")
    import requests
    if st.button("Fund"):
        requests.get(f"[https://friendbot.stellar.org/?addr=](https://friendbot.stellar.org/?addr=){st.session_state.player_public_key}")
        st.success("Funded!")
