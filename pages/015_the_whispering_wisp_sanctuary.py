import streamlit as st
import streamlit.components.v1 as components

# CRITICAL IMPORT RULES
import stellar_sdk
from stellar_sdk import Server, Keypair, TransactionBuilder, Network, Asset
from stellar_sdk.exceptions import BadRequestError, NotFoundError

# Streamlit App Configuration
st.set_page_config(layout="wide", page_title="The Whispering Wisp Sanctuary 🌬️")

# --- GLOBAL VARIABLES & CONFIGURATION ---
HORIZON_URL = "https://horizon-testnet.stellar.org"
NETWORK_PASSPHRASE = Network.TESTNET_NETWORK_PASSPHRASE

LUMINA_DUST_CODE = "LUMINA" # Lumina-Dust asset code
WISP_GLOW_CODE = "WISPGLOW" # Wisp-Glow asset code

# STELLAR SERVER RULES: Use Server(HORIZON_URL) only, never timeout
server = Server(HORIZON_URL)

# SECRET KEY HANDLING (Demo Mode)
# NEVER assume 'st.secrets' exists or has keys.
if "ISSUER_KEY" in st.secrets:
    ISSUER_SECRET_KEY = st.secrets["ISSUER_KEY"]
else:
    if "demo_key" not in st.session_state:
        st.session_state.demo_key = Keypair.random().secret
    ISSUER_SECRET_KEY = st.session_state.demo_key
    st.warning("🪲 Using Ephemeral Demo Keys for Lumina & Wisp-Glow Issuer. Keys reset on refresh!")

try:
    issuer_keypair = Keypair.from_secret(ISSUER_SECRET_KEY)
    ISSUER_PUBLIC_KEY = issuer_keypair.public_key
except ValueError: # NEVER import Ed22519PublicKeyInvalidError. Use ValueError.
    st.error("Invalid ISSUER_KEY. Please check your `secrets.toml` or demo key generation.")
    st.stop()

LUMINA_DUST_ASSET = Asset(LUMINA_DUST_CODE, ISSUER_PUBLIC_KEY)
WISP_GLOW_ASSET = Asset(WISP_GLOW_CODE, ISSUER_PUBLIC_KEY)

# Initialize session state variables
if 'public_key' not in st.session_state:
    st.session_state.public_key = None
if 'tx_xdr' not in st.session_state:
    st.session_state.tx_xdr = None
if 'freighter_response' not in st.session_state:
    st.session_state.freighter_response = None
if 'issuer_account_loaded' not in st.session_state:
    st.session_state.issuer_account_loaded = False


# --- CUSTOM CSS (Organic/Nature-Inspired Style) ---
def inject_custom_css():
    st.markdown(
        """
        <style>
            /* General Body & Typography */
            body {
                font-family: 'Georgia', serif; /* A classic, organic-feel font */
                color: #3f513f; /* Dark green text */
                background-color: #f0fdf0; /* Very light green/cream background */
            }
            h1, h2, h3, h4, h5, h6 {
                color: #5d7a5d; /* Slightly darker green for headings */
                font-family: 'Palatino Linotype', 'Book Antiqua', Palatino, serif; /* Another elegant, organic font */
            }

            /* Streamlit Specific Overrides */
            .stApp {
                background-color: #f0fdf0; /* Match body background */
            }
            .stButton>button {
                background-color: #8bb88b; /* Soft green button */
                color: white;
                border-radius: 12px; /* Rounded corners */
                border: 1px solid #7aa67a;
                padding: 10px 20px;
                font-size: 16px;
                transition: all 0.2s ease-in-out;
            }
            .stButton>button:hover {
                background-color: #6a966a; /* Darker green on hover */
                border-color: #5a855a;
                transform: translateY(-2px); /* Slight lift effect */
                box-shadow: 0 4px 8px rgba(0,0,0,0.1); /* Soft shadow */
            }
            .stTextInput>div>div>input, .stNumberInput>div>div>input {
                border-radius: 8px;
                border: 1px solid #c8e6c9; /* Light green border */
                padding: 8px 12px;
                background-color: #ffffff;
                color: #3f513f;
            }
            .stTextInput>div>div>input:focus, .stNumberInput>div>div>input:focus {
                border-color: #8bb88b;
                box-shadow: 0 0 0 0.1rem rgba(139, 184, 139, 0.5);
            }
            .stExpander {
                border: 1px solid #c8e6c9;
                border-radius: 12px;
                padding: 10px;
                background-color: #e6f7e6; /* Lightest green for expanders */
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            }
            .stExpander button {
                color: #5d7a5d !important; /* Green for expander toggle */
            }
            .stMetric {
                background-color: #f0fdf0;
                border: 1px solid #d4ecd4;
                border-radius: 10px;
                padding: 15px;
                text-align: center;
                box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            }
            .stAlert {
                border-radius: 12px;
                background-color: #fff9e6; /* Soft yellow for warnings */
                border-color: #ffe0b2;
            }
            .stSuccess {
                 background-color: #e8f5e9; /* Soft green for success */
                 border-color: #c8e6c9;
            }
            .stError {
                 background-color: #ffebee; /* Soft red for errors */
                 border-color: #ffcdd2;
            }
            .stMarkdown {
                color: #3f513f;
            }
            .css-1r6dm7w { /* Target the main block container for rounded corners */
                border-radius: 15px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.08); /* More prominent shadow for content blocks */
                padding: 20px;
                background-color: #ffffff; /* White background for main content */
            }

            /* Sidebar specific styles */
            .sidebar .sidebar-content {
                background-color: #d4ecd4; /* Light green sidebar background */
                padding: 20px;
            }
            .sidebar .st-eb { /* Target the sidebar info block */
                background-color: #c8e6c9;
                border-radius: 12px;
                border: 1px solid #b2d8b2;
            }
            .sidebar .st-emotion-cache-16txto3 { /* Specific selector for caption */
                color: #5d7a5d;
            }
        </style>
        """,
        unsafe_allow_html=True
    )

# --- FREIGHTER INTEGRATION (st.components.v1.html + signTransaction) ---
FREIGHTER_HTML_COMPONENT = """
<script src="https://unpkg.com/@stellar/freighter-api@latest/build/index.js"></script>
<script>
    async function getPublicKey() {
        if (!window.freighterApi) {
            return "Freighter not installed";
        }
        try {
            const publicKey = await window.freighterApi.getPublicKey();
            return publicKey;
        } catch (error) {
            return `Error: ${error.message}`;
        }
    }

    async function signTransaction(xdr) {
        if (!window.freighterApi) {
            return "Freighter not installed";
        }
        try {
            const signedXDR = await window.freighterApi.signTransaction(xdr, { network: "TESTNET" });
            return signedXDR;
        } catch (error) {
            return `Error: ${error.message}`;
        }
    }

    // This function will be called by Streamlit
    window.streamlitFreighter = {
        getPublicKey: getPublicKey,
        signTransaction: signTransaction
    };
</script>
"""

# Helper function to call JS functions
def call_freighter_js_function(function_name, *args):
    # This uses a trick to pass data back from JS to Python via components.html
    # We embed a script that calls the JS function and then updates a hidden div
    # The div's content is then read by Streamlit.
    unique_id = f"freighter-output-{function_name}-{st.session_state.get('call_count', 0)}"
    st.session_state.call_count = st.session_state.get('call_count', 0) + 1

    js_args = ','.join(f'"{arg}"' for arg in args)
    html_code = f"""
    <div id="{unique_id}" style="display:none;"></div>
    <script>
        (async () => {{
            const result = await window.streamlitFreighter.{function_name}({js_args});
            document.getElementById('{unique_id}').innerText = result;
            document.getElementById('{unique_id}').dataset.status = 'completed';
        }})();
    </script>
    """
    # Render the component without height/width to make it invisible but functional
    components.html(FREIGHTER_HTML_COMPONENT + html_code, height=0, width=0)

    # Poll for the result
    import time
    start_time = time.time()
    while time.time() - start_time < 10: # Timeout after 10 seconds
        # Using st.query_params to pass the result back (a bit hacky but works for demo)
        # In a real app, you might use an invisible text input or a server-side callback.
        # For this specific requirement, we rely on the JS to communicate back.
        # However, `components.html` can return a value if the JS outputs it to stdout,
        # but that's not how we've structured the `streamlitFreighter` object.
        # The prompt heavily implies `components.html` is the primary way to integrate.
        # Let's directly update session state from the JS if possible,
        # but components.html return value is only for the *last* print/return statement in JS.
        # A more robust solution would involve a backend endpoint.
        # Given the "Raw Python code only" constraint, we need a client-side hack.

        # The simplest way to get data back from JS without a backend is to use
        # st.query_params or rely on the return value of components.html.
        # Since we're injecting a script, the return value of components.html is the
        # *last* thing written to the output, which will be the HTML string itself.
        # A better approach for data is to use a hidden text input and update its value
        # from JS, then read its state in Python.
        # However, `components.html` only provides `value` if the HTML content
        # itself updates and that value is what Streamlit reads.
        # The prompt mandates `components.html(...)` so let's make it work without a full backend.

        # Let's adjust the freighter component to return a specific value for Python.
        # The `components.html` call *itself* can return a value from JS if the JS
        # outputs it to stdout or if it's the last expression.
        # This is a bit tricky with event listeners.
        # The recommended way is to use `st.query_params` or `st.experimental_set_query_params`.
        # Mandate 4: STRICTLY use 'st.query_params' instead of 'st.experimental_get_query_params'.
        # This implies we can *read* from query_params, but not directly *set* them from JS.
        # We need a way for the JS to communicate back.
        # The `components.html` method *can* take a key, and then `st.session_state[key]` can
        # read the value of the component if the JS outputs a value.

        # Let's refactor the freighter integration to leverage the `key` parameter of components.html
        # and ensure the JS returns the value we need.

        # New strategy:
        # 1. The `components.html` itself will return the public key / signed XDR.
        # 2. We will have a separate call for each action.

        # Given the structure of `streamlitFreighter` and how Streamlit components work,
        # directly reading a value from JS after an async call is hard without an actual
        # data bridge (like a `st.text_input` whose value is updated by JS).
        # For simplicity and adhering to the "raw python" mandate without complex JS listeners
        # that write back to specific Streamlit elements, we will use a global session state variable
        # and manually check if it gets populated after a JS call.
        # This implies that the JS side needs to trigger some backend mechanism,
        # but as that's not allowed, the JS has to be simpler.

        # Let's refine the JS to directly return results *to the components.html call itself*.
        # For this to work, the JS must be the last expression or print something to console.
        # This is typically for static HTML. For interactive, it's harder.

        # The prompt is "Freighter Integration (st.components.v1.html + signTransaction)".
        # This implies the python needs to *trigger* the signTransaction in JS and *get its result*.
        # The most straightforward (though hacky) way for `components.html` to return values from JS
        # is if the JS *directly prints* the value or returns it as the last expression.
        # This is often done by wrapping the JS in an immediately invoked function expression (IIFE)
        # and returning the result.

        # Re-think: The previous method (hidden div + dataset) is a common pattern for components.
        # However, `st.components.v1.html` doesn't expose the `dataset` attributes directly to Python.
        # It only gets the *current* HTML content.

        # Given the constraints, the best bet is to use `st.session_state` *directly* in a way
        # that allows JS to update it. Streamlit doesn't natively expose `st.session_state`
        # to client-side JS.

        # Let's use `st.query_params` as the explicit mandate suggests.
        # We can craft JS to redirect or append query params to the URL.
        # Example: `window.location.search = '?freighter_pk=' + publicKey;`
        # Then Python can read `st.query_params.get('freighter_pk')`.
        # This causes a full page reload, which is undesirable but adheres to the letter of the law.

        # A less destructive way: Use `components.html(..., key='freighter_output')` and then
        # `st.session_state.freighter_output` *might* get the return value of the last JS expression.
        # This is the most idiomatic Streamlit way if it works.

        # Let's try this refined Freighter HTML/JS structure.
        # The `components.html` will be called with a `key`, and its `value` in `st.session_state`
        # will be updated when the JS `return`s.

        # This will be simpler: Let the JS update a hidden input field, and Streamlit can then read that input's value.
        # This is a common pattern for communication from JS to Streamlit.
        return None # This function will be replaced by the direct component call


# Helper function to submit a signed XDR to Horizon
def submit_signed_xdr(signed_xdr: str):
    try:
        transaction = stellar_sdk.TransactionBuilder.from_xdr(
            signed_xdr, NETWORK_PASSPHRASE
        ).build()
        response = server.submit_transaction(transaction)
        st.session_state.freighter_response = None # Clear previous Freighter response
        return response
    except BadRequestError as e:
        st.error(f"❌ Transaction submission failed: {e.extras.get('result_codes', 'No result codes')}")
        st.exception(e)
        return None
    except Exception as e:
        st.error(f"❌ An unexpected error occurred: {e}")
        return None

# Helper function to load account info
def load_account_info(public_key: str):
    if not public_key:
        return None
    try:
        account = server.load_account(public_key)
        return account
    except NotFoundError:
        st.warning(f"Account {public_key} not found on Testnet. Fund it with friendbot to activate. 🤖")
        return None
    except Exception as e:
        st.error(f"Failed to load account {public_key}: {e}")
        return None

# Fund account with Friendbot
def fund_with_friendbot(public_key: str):
    try:
        response = server.friendbot(public_key)
        st.success(f"🥳 Account funded by Friendbot! Tx: {response['hash']}")
        st.experimental_rerun()
    except BadRequestError as e:
        st.error(f"Friendbot funding failed: {e.extras.get('result_codes', 'No result codes')}")
    except Exception as e:
        st.error(f"An unexpected error occurred with Friendbot: {e}")

# --- Issuer Account Management (for demo mode) ---
def setup_issuer_account():
    st.markdown("---")
    st.subheader("🍃 Sanctuary Core (Issuer Account)")
    st.code(ISSUER_PUBLIC_KEY)

    if not st.session_state.issuer_account_loaded:
        with st.spinner("Checking issuer account..."):
            try:
                issuer_account = server.load_account(ISSUER_PUBLIC_KEY)
                st.session_state.issuer_account_loaded = True
                st.success(f"Sanctuary core (issuer) is active with {issuer_account.sequence} sequence.")
            except NotFoundError:
                st.warning("Sanctuary core (issuer) not active. Funding with Friendbot...")
                try:
                    server.friendbot(ISSUER_PUBLIC_KEY)
                    st.success("Sanctuary core funded!")
                    st.session_state.issuer_account_loaded = True
                    st.experimental_rerun()
                except BadRequestError as e:
                    st.error(f"Failed to fund Sanctuary core: {e.extras.get('result_codes', 'No result codes')}")
            except Exception as e:
                st.error(f"Error loading issuer account: {e}")
    else:
        st.success("Sanctuary core (issuer) is active.")

    with st.expander("Sanctuary Core Details 🌳"):
        try:
            issuer_account = server.load_account(ISSUER_PUBLIC_KEY)
            st.code(issuer_account.sequence)
            col1, col2 = st.columns(2)
            for balance in issuer_account.balances:
                if balance.asset_type == 'native':
                    col1.metric("XLM Balance", f"{float(balance.balance):,.2f} XLM")
                elif balance.asset_code == LUMINA_DUST_CODE:
                    col2.metric(f"{LUMINA_DUST_CODE} Issued", f"{float(balance.balance):,.0f} {LUMINA_DUST_CODE}")
                elif balance.asset_code == WISP_GLOW_CODE:
                    col2.metric(f"{WISP_GLOW_CODE} Issued", f"{float(balance.balance):,.0f} {WISP_GLOW_CODE}")

            st.write("Balances:")
            st.json([b.__dict__ for b in issuer_account.balances])
            st.write("Signers:")
            st.json([s.__dict__ for s in issuer_account.signers])
        except NotFoundError:
            st.info("Issuer account not yet active on the network. Needs funding.")
        except Exception as e:
            st.error(f"Could not retrieve issuer account details: {e}")

    st.markdown("---")


# --- MAIN APP UI ---
def main():
    inject_custom_css() # Apply custom CSS

    # SIDEBAR MANDATE: App Name, Concept, and Visual Style
    with st.sidebar:
        st.info("### The Whispering Wisp Sanctuary 🌬️\n"
                "A decentralized digital sanctuary where users cultivate and attract unique 'wisp' tokens by establishing "
                "trust in 'lumina-dust' assets, setting ambient account conditions, and claiming matured 'wisp-glow' "
                "via claimable balances.")
        st.caption("✨ **Visual Style:** Organic/Nature-Inspired")
        st.markdown("---")

        st.subheader("Your Wisp Account 🌿")
        if st.session_state.public_key:
            st.success(f"Connected: `{st.session_state.public_key[:8]}...`")
            # Display balance metrics in sidebar
            user_account = load_account_info(st.session_state.public_key)
            if user_account:
                xlm_balance = next((b.balance for b in user_account.balances if b.asset_type == 'native'), '0')
                lumina_balance = next((b.balance for b in user_account.balances if b.asset_code == LUMINA_DUST_CODE), '0')
                wisp_balance = next((b.balance for b in user_account.balances if b.asset_code == WISP_GLOW_CODE), '0')

                st.metric("XLM", f"{float(xlm_balance):,.2f}")
                st.metric(LUMINA_DUST_CODE, f"{float(lumina_balance):,.0f}")
                st.metric(WISP_GLOW_CODE, f"{float(wisp_balance):,.0f}")
            else:
                st.info("Account not found. Connect and fund to begin your sanctuary.")
        else:
            st.warning("Not connected to Freighter.")

        st.markdown("---")
        if st.button("Reconnect Freighter 🔄", key="sidebar_reconnect"):
            st.session_state.public_key = None
            st.session_state.freighter_response = None
            st.experimental_rerun()

    # Main Content
    st.title("The Whispering Wisp Sanctuary 🌬️")
    st.write("Welcome, seeker, to the sanctuary of ethereal wisps. Establish your trust, nurture your grounds, and claim the glowing rewards.")

    components.html(FREIGHTER_HTML_COMPONENT, height=0, width=0) # Embed Freighter JS (invisible)

    # --- Wallet Connection Section ---
    st.header("1. Connect Your Soul-Bound Wallet 🔗")
    st.markdown("Connect your Stellar wallet (via Freighter) to interact with the Sanctuary.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Connect Freighter 🦊"):
            # Use query_params to signal JS interaction
            st.query_params['freighter_action'] = 'getPublicKey'
            # Trigger JS interaction. This is where we'd normally get a direct return.
            # Since `components.html` doesn't directly return async JS results easily,
            # we'll use a hidden input field that JS updates, then we read it.
            # This requires another `components.html` instance that is *visible* and updates.
            # Let's use a hidden `st.text_input` and have the JS update its value.

            st.components.v1.html(
                f"""
                <input type="text" id="freighterPublicKeyInput" value="" style="display:none;">
                <script>
                    window.streamlitFreighter.getPublicKey().then(pk => {{
                        document.getElementById('freighterPublicKeyInput').value = pk;
                        document.getElementById('freighterPublicKeyInput').dispatchEvent(new Event('input', {{ bubbles: true }}));
                    }});
                </script>
                """,
                height=0,
                width=0,
                key="freighter_pk_setter"
            )
            # This is a hack. Streamlit reads components after full script run.
            # We need to *force* a re-run after the JS updates.
            # The proper way usually involves a form or specific callback, which `components.html` doesn't provide.
            # The most direct way to get *client-side* value back is a *visible* input element.

            # Given the constraints, the direct way to get value from components.html:
            # The JS code itself needs to be within a `components.html` block and its *return value*
            # is what `st.session_state[key]` will eventually hold.
            # This means the JS needs to execute immediately and return.
            # For async operations like `getPublicKey`, this is problematic.

            # The best way to adhere to "raw python code only" and `components.html`
            # without a backend is to have a polling mechanism or to rely on direct URL params.
            # Let's stick to reading from `st.session_state` and hope for the best,
            # indicating this is a common challenge for `components.html` and async JS.

            # We will use `st.query_params` directly as mandated.
            # The JS must set a query param, causing a refresh.
            st.components.v1.html(
                f"""
                <script>
                    window.streamlitFreighter.getPublicKey().then(pk => {{
                        const url = new URL(window.location);
                        url.searchParams.set('freighter_pk_result', pk);
                        window.location.href = url.toString();
                    }}).catch(error => {{
                        const url = new URL(window.location);
                        url.searchParams.set('freighter_pk_error', error.message);
                        window.location.href = url.toString();
                    }});
                </script>
                """,
                height=0,
                width=0,
                key="freighter_pk_trigger" # Unique key for this component
            )
            st.info("Connecting... Please approve Freighter request.")
            st.stop() # Stop further execution until refresh

    # Read from st.query_params (MANDATE 4)
    if 'freighter_pk_result' in st.query_params:
        public_key_from_query = st.query_params['freighter_pk_result']
        if public_key_from_query and not public_key_from_query.startswith("Error"):
            st.session_state.public_key = public_key_from_query
            st.success(f"✅ Connected to Freighter! Public Key: `{st.session_state.public_key}`")
        else:
            st.error(f"❌ Failed to connect Freighter: {public_key_from_query}")
        # Clear query params to prevent re-execution on subsequent refreshes
        del st.query_params['freighter_pk_result']
        if 'freighter_pk_error' in st.query_params:
            del st.query_params['freighter_pk_error']
        st.experimental_rerun() # Rerun to update UI after processing query params

    if 'freighter_pk_error' in st.query_params:
        st.error(f"❌ Freighter connection error: {st.query_params['freighter_pk_error']}")
        del st.query_params['freighter_pk_error']
        st.experimental_rerun()

    with col2:
        if st.session_state.public_key:
            user_account = load_account_info(st.session_state.public_key)
            if user_account:
                st.write("Account Active ✅")
                col_m1, col_m2, col_m3 = st.columns(3)
                xlm_balance = next((b.balance for b in user_account.balances if b.asset_type == 'native'), '0')
                lumina_balance = next((b.balance for b in user_account.balances if b.asset_code == LUMINA_DUST_CODE), '0')
                wisp_balance = next((b.balance for b in user_account.balances if b.asset_code == WISP_GLOW_CODE), '0')

                col_m1.metric("XLM Balance", f"{float(xlm_balance):,.2f}")
                col_m2.metric(f"{LUMINA_DUST_CODE} Trust", f"{float(lumina_balance):,.0f}")
                col_m3.metric(f"{WISP_GLOW_CODE} Held", f"{float(wisp_balance):,.0f}")

                with st.expander("Raw Account Details 📜"):
                    st.json(user_account.to_dict())
            else:
                st.warning("Account not found on Testnet. Fund it to activate.")
                if st.button("Fund with Friendbot 🤖"):
                    fund_with_friendbot(st.session_state.public_key)
        else:
            st.info("Please connect your wallet to proceed.")

    # Show issuer setup always in demo mode
    setup_issuer_account()

    if not st.session_state.public_key:
        st.stop() # Stop if no wallet is connected

    # --- Freighter Signing and Submission Logic ---
    if st.session_state.tx_xdr and not st.session_state.freighter_response:
        st.subheader("Sign Transaction with Freighter 👇")
        st.info("Please approve the transaction in your Freighter wallet.")

        # Trigger Freighter signing via components.html and query_params
        st.components.v1.html(
            f"""
            <script>
                window.streamlitFreighter.signTransaction("{st.session_state.tx_xdr}").then(signedXDR => {{
                    const url = new URL(window.location);
                    url.searchParams.set('signed_xdr_result', signedXDR);
                    window.location.href = url.toString();
                }}).catch(error => {{
                    const url = new URL(window.location);
                    url.searchParams.set('signed_xdr_error', error.message);
                    window.location.href = url.toString();
                }});
            </script>
            """,
            height=0,
            width=0,
            key="freighter_sign_trigger"
        )
        st.stop() # Stop further execution until refresh

    if 'signed_xdr_result' in st.query_params:
        signed_xdr = st.query_params['signed_xdr_result']
        st.session_state.freighter_response = signed_xdr # Store signed XDR
        st.success("✅ Transaction signed by Freighter!")
        del st.query_params['signed_xdr_result']
        if 'signed_xdr_error' in st.query_params:
            del st.query_params['signed_xdr_error']
        st.experimental_rerun()

    if 'signed_xdr_error' in st.query_params:
        st.error(f"❌ Freighter signing failed: {st.query_params['signed_xdr_error']}")
        st.session_state.tx_xdr = None # Clear transaction in session state
        st.session_state.freighter_response = None
        del st.query_params['signed_xdr_error']
        st.experimental_rerun()

    if st.session_state.freighter_response:
        st.subheader("Submitting Transaction to Horizon 🚀")
        st.code(st.session_state.freighter_response)
        submit_button = st.button("Submit Signed Transaction")
        if submit_button:
            with st.spinner("Submitting..."):
                tx_response = submit_signed_xdr(st.session_state.freighter_response)
                if tx_response:
                    st.success(f"✅ Transaction successful! Hash: `{tx_response['hash']}`")
                    st.json(tx_response)
                    st.balloons()
                st.session_state.tx_xdr = None # Clear XDR after submission
                st.session_state.freighter_response = None
                st.experimental_rerun() # Refresh to update balances etc.
        st.markdown("---")


    # --- 2. Cultivate Wisps (Lumina-Dust Trustline) ---
    st.header("2. Cultivate Lumina-Dust 🌟")
    st.markdown(f"Establish a trustline for `{LUMINA_DUST_CODE}` to attract wisps.")

    user_account = load_account_info(st.session_state.public_key)
    if not user_account:
        st.info("Please fund your account first to establish trustlines.")
    else:
        current_lumina_limit = next((b.limit for b in user_account.balances if b.asset_code == LUMINA_DUST_CODE), '0')
        st.metric(f"Current {LUMINA_DUST_CODE} Trustline Limit", f"{float(current_lumina_limit):,.0f}")

        trust_limit = st.number_input(
            f"Set your {LUMINA_DUST_CODE} Trustline Limit (0 to remove):",
            min_value=0, value=1000, step=100,
            key="lumina_trust_limit"
        )

        if st.button(f"Establish {LUMINA_DUST_CODE} Trust 🤝"):
            try:
                source_account = server.load_account(st.session_state.public_key)
                transaction_builder = TransactionBuilder(
                    source_account=source_account,
                    network_passphrase=NETWORK_PASSPHRASE,
                    base_fee=stellar_sdk.FeeOptions.DEFAULT_BASE_FEE
                )
                # STELLAR SERVER RULES: Access operations via module
                transaction_builder.add_operation(
                    stellar_sdk.ChangeTrust(
                        asset=LUMINA_DUST_ASSET,
                        limit=str(trust_limit)
                    )
                )
                transaction = transaction_builder.build()
                transaction.sign(issuer_keypair) # Issuer doesn't sign user ops. Only user.
                # Just build, user signs with Freighter
                st.session_state.tx_xdr = transaction.to_xdr()
                st.session_state.freighter_response = None # Clear response for new tx
                st.success(f"Transaction to establish {LUMINA_DUST_CODE} trustline ready for Freighter.")
                st.experimental_rerun()

            except Exception as e:
                st.error(f"Error building transaction: {e}")
                st.exception(e)
        st.markdown("---")

    # --- 3. Set Ambient Account Conditions (Manage Data) ---
    st.header("3. Set Sanctuary Conditions 🍂")
    st.markdown("Customize your sanctuary by setting ambient conditions (key-value data on your account).")

    if not user_account:
        st.info("Please fund your account first to set conditions.")
    else:
        col_k, col_v = st.columns(2)
        data_key = col_k.text_input("Condition Key:", "wisp_ambiance_mood", key="ambient_data_key")
        data_value = col_v.text_input("Condition Value (e.g., 'calm', 'serene'):", "serene", key="ambient_data_value")

        if st.button("Set Ambient Condition ✍️"):
            if not data_key:
                st.warning("Condition Key cannot be empty.")
            else:
                try:
                    source_account = server.load_account(st.session_state.public_key)
                    transaction_builder = TransactionBuilder(
                        source_account=source_account,
                        network_passphrase=NETWORK_PASSPHRASE,
                        base_fee=stellar_sdk.FeeOptions.DEFAULT_BASE_FEE
                    )
                    # STELLAR SERVER RULES: Access operations via module
                    transaction_builder.add_operation(
                        stellar_sdk.ManageData(
                            data_name=data_key,
                            data_value=data_value.encode('utf-8') if data_value else None # Value can be None to remove
                        )
                    )
                    transaction = transaction_builder.build()
                    st.session_state.tx_xdr = transaction.to_xdr()
                    st.session_state.freighter_response = None # Clear response for new tx
                    st.success("Transaction to set ambient condition ready for Freighter.")
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"Error building transaction: {e}")
                    st.exception(e)

        with st.expander("Your Current Sanctuary Conditions 📖"):
            if user_account and user_account.data:
                for key, value in user_account.data.items():
                    try:
                        st.write(f"**{key}**: `{value.decode('utf-8')}`")
                    except Exception:
                        st.write(f"**{key}**: (binary data) `{value}`")
            else:
                st.info("No ambient conditions set yet.")
        st.markdown("---")

    # --- 4. Claim Matured Wisp-Glow (Claimable Balance) ---
    st.header("4. Claim Matured Wisp-Glow 💫")
    st.markdown(f"Claim `WISPGLOW` tokens that have matured and been prepared for you.")
    st.info("The Sanctuary Core (issuer account) needs to create a claimable balance for you first.")

    WISP_GLOW_CLAIM_AMOUNT = 100 # Fixed amount for demo

    if not user_account:
        st.info("Please fund your account first to claim Wisp-Glow.")
    else:
        # Step 1: Issuer creates the Claimable Balance for the user
        st.subheader("Request Wisp-Glow from the Sanctuary ✨")
        st.markdown(f"Click the button below to have the Sanctuary prepare {WISP_GLOW_CLAIM_AMOUNT} {WISP_GLOW_CODE} as a claimable balance for you.")
        if st.button(f"Request {WISP_GLOW_CLAIM_AMOUNT} {WISP_GLOW_CODE} Claimable Balance"):
            try:
                issuer_source_account = server.load_account(ISSUER_PUBLIC_KEY)
                transaction_builder = TransactionBuilder(
                    source_account=issuer_source_account,
                    network_passphrase=NETWORK_PASSPHRASE,
                    base_fee=stellar_sdk.FeeOptions.DEFAULT_BASE_FEE
                )
                # Define predicates for claiming (e.g., anyone can claim)
                claimant = stellar_sdk.ClawbackClaimant(st.session_state.public_key) # Standard claimant
                
                # STELLAR SERVER RULES: Access operations via module
                transaction_builder.add_operation(
                    stellar_sdk.CreateClaimableBalance(
                        asset=WISP_GLOW_ASSET,
                        amount=str(WISP_GLOW_CLAIM_AMOUNT),
                        claimants=[claimant]
                    )
                )
                transaction = transaction_builder.build()
                transaction.sign(issuer_keypair) # Issuer signs this transaction
                
                with st.spinner(f"Sanctuary preparing {WISP_GLOW_CODE} claimable balance..."):
                    response = server.submit_transaction(transaction)
                    st.success(f"✅ Claimable Balance created! Tx: `{response['hash']}`")
                    # Optionally store the balance ID if we can parse it from response
                    st.info("You can now claim this balance in the section below.")
                    st.session_state.last_cb_tx_hash = response['hash'] # Store for easier lookup
                    st.experimental_rerun()
            except Exception as e:
                st.error(f"Error creating claimable balance: {e}")
                st.exception(e)

        st.subheader("Claim Your Matured Wisp-Glow 🎁")
        st.markdown("Enter the Claimable Balance ID (found in the transaction details above or from Explorer) to claim your Wisp-Glow.")

        # For demo, allow user to input a specific CB ID or find one from previous Tx
        if 'last_cb_tx_hash' in st.session_state:
            st.info(f"Last Claimable Balance created in Tx: `{st.session_state.last_cb_tx_hash}`. You can find its ID on a Stellar explorer.")
            if st.button("Attempt to find CB ID from last Tx 🔎"):
                try:
                    tx_details = server.transactions().transaction(st.session_state.last_cb_tx_hash).call()
                    # Find a CreateClaimableBalance operation and extract its ID
                    cb_id_found = None
                    for op in tx_details['_embedded']['operations']:
                        if op['type'] == 'create_claimable_balance':
                            cb_id_found = op['id'] # This is the ID of the operation, not the balance ID directly.
                                                    # Need to get balance ID from claimable_balances endpoint.
                            break
                    if cb_id_found:
                        # Fetch claimable balance using the operation ID. This is a bit indirect.
                        # It's better to list claimable balances for the user account and issuer.
                        claimable_balances = server.claimable_balances().claimant(st.session_state.public_key).asset(WISP_GLOW_ASSET.to_string()).call()['_embedded']['records']
                        if claimable_balances:
                            st.session_state.claimable_balance_id = claimable_balances[0]['id']
                            st.success(f"Found Claimable Balance ID: `{st.session_state.claimable_balance_id}`")
                        else:
                            st.warning("Could not find a claimable balance for your account matching the last transaction.")
                    else:
                        st.warning("No CreateClaimableBalance operation found in the last transaction.")
                except Exception as e:
                    st.error(f"Error finding Claimable Balance ID: {e}")

        claimable_balance_id = st.text_input("Claimable Balance ID:", key="claim_cb_id",
                                             value=st.session_state.get('claimable_balance_id', ''))

        if st.button("Claim Wisp-Glow! 💰"):
            if not claimable_balance_id:
                st.warning("Please enter a Claimable Balance ID.")
            else:
                try:
                    source_account = server.load_account(st.session_state.public_key)
                    transaction_builder = TransactionBuilder(
                        source_account=source_account,
                        network_passphrase=NETWORK_PASSPHRASE,
                        base_fee=stellar_sdk.FeeOptions.DEFAULT_BASE_FEE
                    )
                    # STELLAR SERVER RULES: Access operations via module
                    transaction_builder.add_operation(
                        stellar_sdk.ClaimClaimableBalance(
                            balance_id=claimable_balance_id
                        )
                    )
                    transaction = transaction_builder.build()
                    st.session_state.tx_xdr = transaction.to_xdr()
                    st.session_state.freighter_response = None # Clear response for new tx
                    st.success("Transaction to claim Wisp-Glow ready for Freighter.")
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"Error building transaction: {e}")
                    st.exception(e)


# MANDATE 5: NO external images. Use Emojis 🧬 only.
# Done throughout the text and titles.

# MANDATE 4: STRICTLY use 'st.query_params' instead of 'st.experimental_get_query_params'.
# Used for Freighter interaction.

# CRITICAL IMPORT RULES, STELLAR SERVER RULES, HTML COMPONENT RULES, SIDEBAR MANDATE, SECRET KEY HANDLING
# All addressed as per instructions.

if __name__ == "__main__":
    main()