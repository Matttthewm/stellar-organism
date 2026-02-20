import streamlit as st
import streamlit.components.v1 as components
import stellar_sdk
from stellar_sdk import Server, Keypair, TransactionBuilder, Network, Asset
from stellar_sdk.exceptions import BadRequestError, NotFoundError
import json
import time
import hashlib
import urllib.parse

HORIZON_URL = "[https://horizon-testnet.stellar.org](https://horizon-testnet.stellar.org)"
NETWORK_PASSPHRASE = Network.TESTNET_NETWORK_PASSPHRASE
SERVER = Server(HORIZON_URL)

if "ISSUER_SECRET_KEY" in st.secrets:
    ISSUER_SECRET_KEY = st.secrets["ISSUER_SECRET_KEY"]
else:
    if "demo_issuer_key_secret" not in st.session_state:
        st.session_state.demo_issuer_key_secret = Keypair.random().secret
    ISSUER_SECRET_KEY = st.session_state.demo_issuer_key_secret

ISSUER_KEYPAIR = Keypair.from_secret(ISSUER_SECRET_KEY)
ISSUER_PUBLIC_KEY = ISSUER_KEYPAIR.public_key
WHISPER_ASSET_CODE = "WHISPER"
WHISPER_ASSET = Asset(WHISPER_ASSET_CODE, ISSUER_PUBLIC_KEY)

if 'freighter_connected' not in st.session_state: st.session_state.freighter_connected = False
if 'freighter_public_key' not in st.session_state: st.session_state.freighter_public_key = None
if 'whispers' not in st.session_state: st.session_state.whispers = {}
if 'account_balances' not in st.session_state: st.session_state.account_balances = {}
if 'pending_tx_purpose' not in st.session_state: st.session_state.pending_tx_purpose = None
if 'pending_whisper_content' not in st.session_state: st.session_state.pending_whisper_content = None

st.markdown("""<style> body { background-color: #0d0d0d; color: #00ff00; } </style>""", unsafe_allow_html=True)

FREIGHTER_HTML = f"""
<script src="[https://unpkg.com/@stellar/freighter-api@1.2.0/build/freighter.min.js](https://unpkg.com/@stellar/freighter-api@1.2.0/build/freighter.min.js)"></script>
<script>
    function updateParentQueryParam(key, value) {{
        const url = new URL(window.parent.location.href);
        url.searchParams.set(key, value);
        window.parent.location.href = url.toString();
    }}
    async function connectFreighter() {{
        try {{
            const publicKey = await window.freighterApi.getPublicKey();
            updateParentQueryParam('freighter_response', encodeURIComponent(JSON.stringify({{ type: 'freighter_connected', data: {{ publicKey: publicKey }} }})));
        }} catch (error) {{
            updateParentQueryParam('freighter_response', encodeURIComponent(JSON.stringify({{ type: 'freighter_error', data: error.message }})));
        }}
    }}
    async function signTransaction(xdr, networkPassphrase) {{
        try {{
            const signedXDR = await window.freighterApi.signTransaction(xdr, {{ networkPassphrase: networkPassphrase }});
            updateParentQueryParam('freighter_response', encodeURIComponent(JSON.stringify({{ type: 'transaction_signed', data: {{ signedXDR: signedXDR }} }})));
        }} catch (error) {{
            updateParentQueryParam('freighter_response', encodeURIComponent(JSON.stringify({{ type: 'freighter_error', data: error.message }})));
        }}
    }}
    window.addEventListener('message', async (event) => {{
        if (event.data && event.data.type) {{
            if (event.data.type === 'connectFreighter') connectFreighter();
            else if (event.data.type === 'signTransaction') signTransaction(event.data.data.xdr, event.data.data.networkPassphrase);
        }}
    }});
</script>
"""
components.html(FREIGHTER_HTML, height=0, width=0)

def send_message_to_freighter_iframe(message_type, data=None):
    js_code = f"""
    <script>
        const freighterIframe = window.parent.document.querySelector('iframe');
        if (freighterIframe && freighterIframe.contentWindow) {{
            freighterIframe.contentWindow.postMessage({{ type: '{message_type}', data: {json.dumps(data)} }}, '*');
        }}
    </script>
    """
    components.html(js_code, height=0, width=0)

def handle_freighter_response():
    response_encoded = st.query_params.get("freighter_response")
    if response_encoded:
        response_str = urllib.parse.unquote(response_encoded)
        try:
            response = json.loads(response_str)
            if response['type'] == 'freighter_connected':
                st.session_state.freighter_connected = True
                st.session_state.freighter_public_key = response['data']['publicKey']
            elif response['type'] == 'transaction_signed':
                st.session_state.signed_xdr = response['data']['signedXDR']
            elif response['type'] == 'freighter_error':
                st.error(f"Freighter Error: {response['data']}")
            st.query_params.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Error processing response: {e}")

def get_account_details(public_key):
    try:
        account = SERVER.load_account(public_key=public_key)
        st.session_state.account_balances[public_key] = {b.asset_code if hasattr(b, 'asset_code') else 'XLM': b.balance for b in account.balances}
        return account
    except NotFoundError:
        st.session_state.account_balances[public_key] = {}
        return None

def create_whisper_asset_and_account():
    try:
        SERVER.load_account(ISSUER_PUBLIC_KEY)
    except NotFoundError:
        import requests
        requests.get(f"[https://friendbot.stellar.org/?addr=](https://friendbot.stellar.org/?addr=){ISSUER_PUBLIC_KEY}")

def submit_signed_xdr(signed_xdr):
    try:
        tx_result = SERVER.submit_transaction(signed_xdr)
        st.success("Transaction successful!")
        return tx_result
    except Exception as e:
        st.error(f"Transaction failed: {e}")
        return None

with st.sidebar:
    st.info("The Spectral Radiogram 📻")
    if not st.session_state.freighter_connected:
        if st.button("Connect Freighter 🚀"): send_message_to_freighter_iframe('connectFreighter')
    else:
        st.success(f"Connected: {st.session_state.freighter_public_key[:8]}...")
        if st.button("Disconnect"):
            st.session_state.freighter_connected = False
            st.rerun()

handle_freighter_response()

if 'signed_xdr' in st.session_state and st.session_state.signed_xdr:
    if st.session_state.pending_tx_purpose == 'create_trustline':
        submit_signed_xdr(st.session_state.signed_xdr)
    elif st.session_state.pending_tx_purpose == 'transmit_whisper':
        tx_result = submit_signed_xdr(st.session_state.signed_xdr)
        if tx_result:
            wid = hashlib.sha256(st.session_state.pending_whisper_content.encode()).hexdigest()
            st.session_state.whispers[wid] = {'sender': st.session_state.freighter_public_key, 'message': st.session_state.pending_whisper_content, 'timestamp': time.time(), 'tx_hash': tx_result['hash']}
    st.session_state.signed_xdr = None
    st.session_state.pending_tx_purpose = None
    st.rerun()

st.title("The Spectral Radiogram 📻")
if st.session_state.freighter_connected:
    acc = get_account_details(st.session_state.freighter_public_key)
    if not acc:
        import requests
        if st.button("Fund Testnet Account"): 
            requests.get(f"[https://friendbot.stellar.org/?addr=](https://friendbot.stellar.org/?addr=){st.session_state.freighter_public_key}")
            st.rerun()
    else:
        st.write("Balances:", st.session_state.account_balances.get(st.session_state.freighter_public_key, {}))
        msg = st.text_input("Whisper:")
        if st.button("Transmit"):
            source = SERVER.load_account(st.session_state.freighter_public_key)
            tx = TransactionBuilder(source, NETWORK_PASSPHRASE, 100).append_payment_op(ISSUER_PUBLIC_KEY, Asset.native(), "0.1").add_memo(stellar_sdk.MemoText(msg[:28])).build()
            st.session_state.pending_tx_purpose = 'transmit_whisper'
            st.session_state.pending_whisper_content = msg
            send_message_to_freighter_iframe('signTransaction', {'xdr': tx.to_xdr(), 'networkPassphrase': NETWORK_PASSPHRASE})

create_whisper_asset_and_account()
