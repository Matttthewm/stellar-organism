import streamlit as st
import streamlit.components.v1 as components
import json
import base64
import time
import secrets
from stellar_sdk import Server, Keypair, TransactionBuilder, Network, Price, asset
from stellar_sdk.exceptions import BadRequestError, NotFoundError

# --- Configuration ---
# Set to 'testnet' for development, 'public' for production
NETWORK_PASSPHRASE_TESTNET = Network.TESTNET_NETWORK_PASSPHRASE
HORIZON_URL_TESTNET = "https://horizon-testnet.stellar.org/"

# --- Streamlit Session State Initialization ---
if "is_connected" not in st.session_state:
    st.session_state.is_connected = False
if "public_key" not in st.session_state:
    st.session_state.public_key = None
if "network" not in st.session_state:
    st.session_state.network = "testnet" # Default network
if "horizon_server" not in st.session_state:
    st.session_state.horizon_server = Server(HORIZON_URL_TESTNET)
if "projects" not in st.session_state:
    st.session_state.projects = []
if "balances" not in st.session_state:
    st.session_state.balances = {}
if "selected_project_id" not in st.session_state:
    st.session_state.selected_project_id = None

# --- Custom CSS for UI/UX ---
CUSTOM_CSS = """
<style>
    :root {
        --primary-blue: #007bff;
        --secondary-blue: #6c757d;
        --accent-green: #28a745;
        --accent-orange: #ffc107;
        --text-color: #343a40;
        --bg-color: #f8f9fa;
        --card-bg: #ffffff;
        --border-color: #e9ecef;
        --shadow-light: rgba(0, 0, 0, 0.05);
        --font-family: 'Inter', sans-serif;
    }

    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    body {
        font-family: var(--font-family);
        color: var(--text-color);
        background-color: var(--bg-color);
    }

    /* General Streamlit Overrides */
    .stApp {
        padding-top: 2rem;
        background-color: var(--bg-color);
    }

    .stApp > header {
        display: none; /* Hide default Streamlit header */
    }

    .css-1d391kg { /* Main content padding */
        padding: 1rem 2rem 10rem;
    }

    .st-emotion-cache-18ni7mt, .st-emotion-cache-r42i3o { /* Sidebar padding */
        padding: 2rem 1rem;
        background-color: var(--card-bg);
        border-right: 1px solid var(--border-color);
    }

    /* Header & Title */
    h1, h2, h3, h4, h5, h6 {
        color: var(--primary-blue);
        font-weight: 600;
        margin-bottom: 1rem;
    }
    h1 {
        font-size: 2.5rem;
        border-bottom: 2px solid var(--primary-blue);
        padding-bottom: 0.5rem;
        margin-bottom: 2rem;
    }
    h2 {
        font-size: 1.8rem;
        margin-top: 2rem;
    }

    /* Buttons */
    .stButton > button {
        background-color: var(--primary-blue);
        color: white;
        border-radius: 8px;
        padding: 0.75rem 1.25rem;
        font-weight: 500;
        border: none;
        transition: all 0.2s ease-in-out;
        box-shadow: 0 4px 6px var(--shadow-light);
    }
    .stButton > button:hover {
        background-color: #0056b3;
        transform: translateY(-2px);
        box-shadow: 0 6px 8px var(--shadow-light);
    }
    .stButton > button:active {
        transform: translateY(0);
        box-shadow: 0 2px 3px var(--shadow-light);
    }
    .stButton > button[kind="secondary"] {
        background-color: var(--secondary-blue);
    }
    .stButton > button[kind="secondary"]:hover {
        background-color: #5a6268;
    }
    .stButton > button[kind="tertiary"] {
        background-color: var(--accent-green);
    }
    .stButton > button[kind="tertiary"]:hover {
        background-color: #218838;
    }

    /* Text Inputs */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > select,
    .stTextArea > div > div > textarea {
        border-radius: 8px;
        border: 1px solid var(--border-color);
        padding: 0.75rem 1rem;
        box-shadow: inset 0 1px 2px var(--shadow-light);
    }

    /* Cards & Containers */
    .st-emotion-cache-1r4qj8m { /* specific for some containers */
        background-color: var(--card-bg);
        border-radius: 12px;
        box-shadow: 0 6px 12px var(--shadow-light);
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        border: 1px solid var(--border-color);
        transition: all 0.2s ease-in-out;
    }
    .st-emotion-cache-1r4qj8m:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 16px rgba(0,0,0,0.1);
    }

    .project-card {
        background-color: var(--card-bg);
        border-radius: 12px;
        box-shadow: 0 6px 12px var(--shadow-light);
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        border: 1px solid var(--border-color);
        transition: all 0.2s ease-in-out;
        cursor: pointer;
    }
    .project-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 16px rgba(0,0,0,0.1);
    }
    .project-card h3 {
        color: var(--primary-blue);
        margin-top: 0;
        margin-bottom: 0.5rem;
    }
    .project-card .project-status {
        display: inline-block;
        padding: 0.3em 0.7em;
        border-radius: 5px;
        font-size: 0.8em;
        font-weight: 500;
        color: white;
        margin-left: 0.5rem;
    }
    .status-open { background-color: var(--primary-blue); }
    .status-in_progress { background-color: var(--accent-green); }
    .status-completed { background-color: #6c757d; } /* Grey for completed */
    .status-archived { background-color: #343a40; } /* Dark grey for archived */
    .milestone-status-pending { background-color: var(--accent-orange); }
    .milestone-status-funded { background-color: var(--primary-blue); }
    .milestone-status-claimed { background-color: var(--accent-green); }

    /* Progress bars / status indicators */
    .progress-bar-container {
        width: 100%;
        background-color: var(--border-color);
        border-radius: 5px;
        margin-top: 1rem;
        overflow: hidden;
    }
    .progress-bar {
        height: 10px;
        background-color: var(--accent-green);
        border-radius: 5px;
        width: 0%; /* controlled by JS/Python */
        transition: width 0.5s ease-in-out; /* Organic animation */
    }

    /* Connect Wallet button */
    #connect-freighter-button {
        background-color: #f7921a; /* Freighter orange */
        color: white;
        border-radius: 8px;
        padding: 0.75rem 1.25rem;
        font-weight: 500;
        border: none;
        transition: all 0.2s ease-in-out;
        box-shadow: 0 4px 6px rgba(247, 146, 26, 0.2);
    }
    #connect-freighter-button:hover {
        background-color: #d17b12;
        transform: translateY(-2px);
        box-shadow: 0 6px 8px rgba(247, 146, 26, 0.3);
    }

    /* Info/Warning/Success messages */
    .stAlert {
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    .stAlert > div { /* Specific targeting for the content within alerts */
        padding: 1rem 1.5rem;
    }

    /* Links for transaction hashes */
    .tx-hash-link {
        font-family: monospace;
        font-size: 0.9em;
        color: var(--primary-blue);
        text-decoration: none;
    }
    .tx-hash-link:hover {
        text-decoration: underline;
    }

    .footer {
        text-align: center;
        margin-top: 3rem;
        padding-top: 1.5rem;
        border-top: 1px solid var(--border-color);
        color: var(--secondary-blue);
        font-size: 0.9em;
    }
    .disclaimer {
        color: #dc3545; /* Red for warning */
        font-weight: bold;
        margin-top: 1rem;
        padding: 1rem;
        border: 1px solid #dc3545;
        border-radius: 8px;
        background-color: rgba(220, 53, 69, 0.05);
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# --- Freighter Integration JavaScript ---
# This script is injected into the Streamlit app to interact with Freighter.
# It handles connecting, getting public key, and signing transactions.
FREIGHTER_JS = """
<script>
    async function connectFreighter() {
        if (window.freighter) {
            try {
                const publicKey = await window.freighter.getPublicKey();
                window.parent.postMessage({ type: 'FREIGHTER_CONNECTED', publicKey: publicKey }, '*');
            } catch (error) {
                console.error("Freighter connection error:", error);
                window.parent.postMessage({ type: 'FREIGHTER_ERROR', message: error.message }, '*');
            }
        } else {
            window.parent.postMessage({ type: 'FREIGHTER_ERROR', message: 'Freighter wallet not found. Please install it.' }, '*');
        }
    }

    async function signTransaction(xdr, networkPassphrase) {
        if (window.freighter) {
            try {
                const signedXDR = await window.freighter.signTransaction(xdr, { networkPassphrase });
                window.parent.postMessage({ type: 'TX_SIGNED', signedXDR: signedXDR }, '*');
            } catch (error) {
                console.error("Transaction signing error:", error);
                window.parent.postMessage({ type: 'TX_SIGN_ERROR', message: error.message }, '*');
            }
        } else {
            window.parent.postMessage({ type: 'FREIGHTER_ERROR', message: 'Freighter wallet not found.' }, '*');
        }
    }

    // Listen for messages from Streamlit
    window.addEventListener('message', event => {
        if (event.data.type === 'CONNECT_FREIGHTER') {
            connectFreighter();
        } else if (event.data.type === 'SIGN_TX') {
            signTransaction(event.data.xdr, event.data.networkPassphrase);
        }
    });
</script>
"""
components.html(FREIGHTER_JS, height=0, width=0)

# --- Helper Functions ---
def get_horizon_server():
    """Returns the Stellar Horizon server instance based on the selected network."""
    if st.session_state.network == "testnet":
        return Server(HORIZON_URL_TESTNET)
    # Add public network logic if needed later
    # elif st.session_state.network == "public":
    #     return Server(HORIZON_URL_PUBLIC)
    return Server(HORIZON_URL_TESTNET) # Default to testnet

def get_network_passphrase():
    """Returns the Stellar network passphrase based on the selected network."""
    if st.session_state.network == "testnet":
        return NETWORK_PASSPHRASE_TESTNET
    # Add public network logic if needed later
    # elif st.session_state.network == "public":
    #     return NETWORK_PASSPHRASE_PUBLIC
    return NETWORK_PASSPHRASE_TESTNET # Default

def fetch_account_balances(public_key):
    """Fetches and updates account balances for a given public key."""
    if not public_key:
        return {}
    try:
        account = st.session_state.horizon_server.load_account(public_key)
        st.session_state.balances[public_key] = {
            bal.asset_code if hasattr(bal, 'asset_code') else 'XLM': float(bal.balance)
            for bal in account.balances
        }
        return st.session_state.balances[public_key]
    except NotFoundError:
        st.error(f"Account {public_key} not found on the network. Please fund it (e.g., using Friendbot for Testnet).")
        return {}
    except Exception as e:
        st.error(f"Error fetching account balances for {public_key}: {e}")
        return {}

def send_message_to_js(message_type, **kwargs):
    """Sends a message to the JavaScript component."""
    message = {"type": message_type, **kwargs}
    st.components.v1.html(
        f"""
        <script>
            window.postMessage({json.dumps(message)}, '*');
        </script>
        """,
        height=0, width=0
    )

def handle_freighter_response():
    """Listens for and processes messages from the JavaScript component."""
    if st.session_state.get("freighter_response"):
        response = st.session_state.freighter_response
        response_type = response.get("type")

        if response_type == "FREIGHTER_CONNECTED":
            st.session_state.public_key = response.get("publicKey")
            st.session_state.is_connected = True
            st.session_state.freighter_response = None # Clear response
            st.success(f"Connected to Freighter: {st.session_state.public_key[:8]}...")
            st.rerun()
        elif response_type == "FREIGHTER_ERROR":
            st.error(f"Freighter Error: {response.get('message')}")
            st.session_state.freighter_response = None
        elif response_type == "TX_SIGNED":
            signed_xdr = response.get("signedXDR")
            try:
                # Submit the signed transaction to Horizon
                horizon = get_horizon_server()
                tx_result = horizon.submit_transaction(signed_xdr)
                st.success(f"Transaction successful! Hash: "
                           f"<a href='https://testnet.stellarexplorer.org/tx/{tx_result['hash']}' target='_blank' class='tx-hash-link'>"
                           f"{tx_result['hash'][:10]}...</a>", unsafe_allow_html=True)
                # Clear pending transaction data
                if "pending_tx_action" in st.session_state:
                    action_data = st.session_state.pending_tx_action
                    if action_data["action"] == "create_project_account":
                        project_id = action_data["project_id"]
                        for project in st.session_state.projects:
                            if project["id"] == project_id:
                                project["status"] = "open"
                                fetch_account_balances(project["project_account_pk"])
                                break
                    elif action_data["action"] == "fund_milestone":
                        project_id = action_data["project_id"]
                        milestone_index = action_data["milestone_index"]
                        for project in st.session_state.projects:
                            if project["id"] == project_id:
                                project["milestones"][milestone_index]["status"] = "funded"
                                project["milestones"][milestone_index]["claimable_balance_id"] = tx_result['hash'] # Use tx hash as simple ID for demo
                                fetch_account_balances(st.session_state.public_key)
                                break
                    elif action_data["action"] == "claim_milestone":
                        project_id = action_data["project_id"]
                        milestone_index = action_data["milestone_index"]
                        for project in st.session_state.projects:
                            if project["id"] == project_id:
                                project["milestones"][milestone_index]["status"] = "claimed"
                                fetch_account_balances(st.session_state.public_key)
                                fetch_account_balances(project["project_account_pk"]) # For the funder
                                break
                    elif action_data["action"] == "archive_project":
                        project_id = action_data["project_id"]
                        for project in st.session_state.projects:
                            if project["id"] == project_id:
                                project["status"] = "archived"
                                fetch_account_balances(st.session_state.public_key) # Funder's balance
                                break
                st.session_state.pending_tx_action = None
                st.session_state.freighter_response = None
                st.rerun() # Refresh UI to show updated status
            except BadRequestError as e:
                st.error(f"Transaction submission failed: {e.extras.get('result_codes', 'No result codes')}")
            except Exception as e:
                st.error(f"Error submitting transaction: {e}")
            finally:
                st.session_state.freighter_response = None
        elif response_type == "TX_SIGN_ERROR":
            st.error(f"Transaction signing cancelled or failed: {response.get('message')}")
            st.session_state.freighter_response = None

def listen_for_freighter_messages():
    """A component to listen for messages from the JavaScript."""
    # This component captures messages sent from the JavaScript and stores them in session state.
    # It needs to be placed *once* in the app.
    st.markdown(
        """
        <script>
            window.addEventListener('message', event => {
                if (event.source === window && event.data.type && 
                    (event.data.type.startsWith('FREIGHTER_') || event.data.type.startsWith('TX_'))) {
                    // Send to Streamlit
                    window.parent.postMessage({
                        streamlit: true,
                        type: 'freighter_callback',
                        payload: event.data
                    }, '*');
                }
            });
        </script>
        """,
        unsafe_allow_html=True
    )
    # Check for messages from the iframe (Streamlit's way to get JS output)
    if st.runtime.exists():
        query_params = query_params = st.query_params
        if "freighter_callback" in query_params:
            payload_str = query_params["freighter_callback"][0]
            st.session_state.freighter_response = json.loads(base64.b64decode(payload_str).decode())
            st.experimental_set_query_params(freighter_callback=None) # Clear to prevent re-processing

listen_for_freighter_messages()
handle_freighter_response() # Process any new response

# --- Streamlit UI Components ---

def sidebar():
    st.sidebar.image("https://www.stellar.org/img/logos/stellar-logo-white-mark.svg", width=50) # Placeholder logo
    st.sidebar.title("NexusFlow 🚀")
    st.sidebar.markdown("Collaborative Project Orchestration")

    st.sidebar.markdown("---")

    # Network Selection
    st.sidebar.subheader("Network")
    selected_network = st.sidebar.radio(
        "Select Stellar Network",
        ["Testnet"], # For this demo, only Testnet is active.
        index=0,
        key="network_selector"
    )
    if selected_network != st.session_state.network:
        st.session_state.network = selected_network
        st.session_state.horizon_server = get_horizon_server()
        st.session_state.balances = {} # Clear balances on network change
        st.info(f"Switched to {st.session_state.network.capitalize()}")
        st.rerun()

    st.sidebar.markdown("---")

    # Wallet Connection
    st.sidebar.subheader("Wallet Status")
    if not st.session_state.is_connected:
        if st.sidebar.button("Connect Freighter Wallet", key="connect_freighter_button"):
            send_message_to_js("CONNECT_FREIGHTER")
            st.sidebar.info("Awaiting Freighter connection...")
    else:
        st.sidebar.success(f"Connected: {st.session_state.public_key[:8]}...")
        # Fetch and display XLM balance
        current_balances = fetch_account_balances(st.session_state.public_key)
        xlm_balance = current_balances.get("XLM", 0)
        st.sidebar.metric("XLM Balance", f"{xlm_balance:,.2f} XLM")
        
        # Display other assets if any
        other_assets = {k: v for k, v in current_balances.items() if k != "XLM"}
        if other_assets:
            st.sidebar.markdown("Other Assets:")
            for asset_code, balance in other_assets.items():
                st.sidebar.write(f"- {balance:,.2f} {asset_code}")
        
        if st.sidebar.button("Disconnect", key="disconnect_button"):
            st.session_state.is_connected = False
            st.session_state.public_key = None
            st.session_state.balances = {}
            st.success("Disconnected from Freighter.")
            st.rerun()

    st.sidebar.markdown("---")

    # Navigation
    st.sidebar.subheader("Navigation")
    if st.sidebar.button("Dashboard", key="nav_dashboard"):
        st.session_state.selected_project_id = None
        st.rerun()
    if st.session_state.selected_project_id:
        if st.sidebar.button("View All Projects", key="nav_all_projects"):
            st.session_state.selected_project_id = None
            st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.markdown("""
        <div class="footer">
            Built with Streamlit & Stellar SDK<br>
            Powered by Freighter
        </div>
    """, unsafe_allow_html=True)
    st.sidebar.markdown("""
        <div class="disclaimer">
            ⚠️ <strong>Disclaimer:</strong> This is a demo dApp. Project account secret keys are stored in session state for demonstration purposes only. This is HIGHLY INSECURE and NOT SUITABLE for production environments. A real dApp would use multi-sig, a secure backend, or Soroban smart contracts.
        </div>
    """, unsafe_allow_html=True)

def dashboard_view():
    st.title("NexusFlow Dashboard")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Create a New Project")
        if not st.session_state.is_connected:
            st.warning("Please connect your Freighter wallet to create projects.")
        else:
            with st.form("create_project_form"):
                project_name = st.text_input("Project Name", max_chars=100)
                project_description = st.text_area("Project Description")
                contributor_pk = st.text_input("Contributor Public Key")
                submit_button = st.form_submit_button("Create Project")

                if submit_button:
                    if not project_name or not contributor_pk:
                        st.error("Project name and Contributor Public Key are required.")
                    else:
                        try:
                            Keypair.from_public_key(contributor_pk) # Validate PK
                            # Generate a new keypair for the project's dedicated account
                            project_keypair = Keypair.random()
                            project_pk = project_keypair.public_key
                            project_sk = project_keypair.secret_key # DANGER! For demo only.

                            new_project = {
                                "id": secrets.token_hex(8),
                                "name": project_name,
                                "description": project_description,
                                "funder_account_pk": st.session_state.public_key,
                                "contributor_account_pk": contributor_pk,
                                "project_account_pk": project_pk,
                                "project_account_sk": project_sk, # !!! SECURITY RISK - DEMO ONLY !!!
                                "status": "pending_creation", # Will be "open" after account funding
                                "milestones": [],
                            }
                            st.session_state.projects.append(new_project)

                            # Create the project account and fund it with min. balance (2 XLM on testnet)
                            # This needs to be signed by the Funder (connected wallet)
                            funder_account = get_horizon_server().load_account(st.session_state.public_key)
                            transaction = (
                                TransactionBuilder(
                                    source_account=funder_account,
                                    network_passphrase=get_network_passphrase(),
                                )
                                .add_operation(
                                    asset.create_account_op.CreateAccountOperation(
                                        destination=project_pk,
                                        starting_balance="2.0" # Minimum 1 XLM base + 1 XLM for CB reserve per op
                                    )
                                )
                                .set_timeout(100)
                                .build()
                            )
                            xdr = transaction.to_xdr()
                            send_message_to_js("SIGN_TX", xdr=xdr, networkPassphrase=get_network_passphrase())
                            st.session_state.pending_tx_action = {
                                "action": "create_project_account",
                                "project_id": new_project["id"]
                            }
                            st.spinner("Creating and funding project account... Please sign with Freighter.")
                            st.info("The project will appear as 'open' after the transaction is confirmed.")

                        except ValueError:
                            st.error("Invalid Contributor Public Key.")
                        except NotFoundError:
                            st.error(f"Funder account {st.session_state.public_key} not found on network. Please fund it.")
                        except Exception as e:
                            st.error(f"Error creating project: {e}")

    with col2:
        st.subheader("Your Active Projects")
        if not st.session_state.projects:
            st.info("No projects created yet. Start by creating one!")
        else:
            active_projects = [p for p in st.session_state.projects if p["status"] not in ["completed", "archived"]]
            if not active_projects:
                st.info("No active projects. All projects are either completed or archived.")
            for project in active_projects:
                status_class = project["status"].replace("_", "-")
                st.markdown(
                    f"""
                    <div class="project-card" onclick="window.parent.postMessage({{streamlit: true, type: 'streamlit_callback', payload: {{action: 'select_project', project_id: '{project['id']}'}}}}, '*')">
                        <h3>{project['name']} <span class="project-status status-{status_class}">{project['status'].replace('_', ' ').title()}</span></h3>
                        <p>{project['description'][:100]}...</p>
                        <small>Funder: {project['funder_account_pk'][:8]}...</small><br>
                        <small>Contributor: {project['contributor_account_pk'][:8]}...</small>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            # Handle project selection via custom JS message
            if st.runtime.exists():
                query_params = st.experimental_get_query_params()
                if "streamlit_callback" in query_params:
                    payload_str = query_params["streamlit_callback"][0]
                    callback_data = json.loads(base64.b64decode(payload_str).decode())
                    if callback_data.get("action") == "select_project":
                        st.session_state.selected_project_id = callback_data["project_id"]
                        st.experimental_set_query_params(streamlit_callback=None) # Clear
                        st.rerun()

    st.subheader("Archived Projects")
    archived_projects = [p for p in st.session_state.projects if p["status"] == "archived"]
    if not archived_projects:
        st.info("No projects have been archived yet.")
    else:
        for project in archived_projects:
            st.markdown(
                f"""
                <div class="project-card status-archived">
                    <h3>{project['name']} <span class="project-status status-archived">Archived</span></h3>
                    <p>{project['description'][:100]}...</p>
                </div>
                """,
                unsafe_allow_html=True
            )


def project_detail_view(project_id):
    project = next((p for p in st.session_state.projects if p["id"] == project_id), None)

    if not project:
        st.error("Project not found.")
        st.session_state.selected_project_id = None
        st.rerun()
        return

    st.title(f"Project: {project['name']}")
    status_class = project["status"].replace("_", "-")
    st.markdown(f"Status: <span class='project-status status-{status_class}'>{project['status'].replace('_', ' ').title()}</span>", unsafe_allow_html=True)
    st.write(f"**Description:** {project['description']}")
    st.write(f"**Funder:** `{project['funder_account_pk']}`")
    st.write(f"**Contributor:** `{project['contributor_account_pk']}`")
    st.write(f"**Project Account:** `{project['project_account_pk']}`")
    fetch_account_balances(project['project_account_pk'])
    project_xlm_balance = st.session_state.balances.get(project['project_account_pk'], {}).get("XLM", 0)
    st.write(f"**Project Account Balance:** {project_xlm_balance:,.2f} XLM")


    st.markdown("---")
    st.subheader("Milestones")

    col1, col2 = st.columns([2,1])

    with col1:
        if st.session_state.public_key == project['funder_account_pk'] and project["status"] != "archived":
            with st.expander("Add New Milestone"):
                with st.form("add_milestone_form"):
                    milestone_name = st.text_input("Milestone Name")
                    milestone_desc = st.text_area("Milestone Description")
                    milestone_amount = st.number_input("Amount (XLM)", min_value=0.1, format="%.2f")
                    add_milestone_button = st.form_submit_button("Add Milestone")
                    if add_milestone_button:
                        if not milestone_name or not milestone_amount:
                            st.error("Milestone name and amount are required.")
                        else:
                            project["milestones"].append({
                                "name": milestone_name,
                                "description": milestone_desc,
                                "amount": milestone_amount,
                                "status": "pending",
                                "claimable_balance_id": None
                            })
                            st.success("Milestone added to project.")
                            st.rerun()

        if not project["milestones"]:
            st.info("No milestones defined for this project yet.")
        else:
            for i, milestone in enumerate(project["milestones"]):
                milestone_status_class = milestone["status"].replace("_", "-")
                st.markdown(
                    f"""
                    <div class="project-card">
                        <h4>{milestone['name']} <span class="project-status milestone-status-{milestone_status_class}">{milestone['status'].title()}</span></h4>
                        <p>{milestone['description']}</p>
                        <p><strong>Amount:</strong> {milestone['amount']} XLM</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                if st.session_state.public_key == project['funder_account_pk'] and milestone["status"] == "pending":
                    if st.button(f"Fund Milestone: {milestone['name']}", key=f"fund_milestone_{i}"):
                        if not st.session_state.is_connected:
                            st.error("Please connect your Freighter wallet to fund milestones.")
                            continue
                        if st.session_state.public_key != project['funder_account_pk']:
                            st.error("Only the Funder can fund this milestone.")
                            continue

                        with st.spinner(f"Preparing funding for '{milestone['name']}'..."):
                            try:
                                # Funder's account is the source. It needs to have enough balance.
                                funder_account = get_horizon_server().load_account(st.session_state.public_key)
                                contributor_pk = project['contributor_account_pk']

                                # Funder creates a Claimable Balance for the Contributor
                                transaction = (
                                    TransactionBuilder(
                                        source_account=funder_account,
                                        network_passphrase=get_network_passphrase(),
                                    )
                                    .add_operation(
                                        asset.create_claimable_balance_op.CreateClaimableBalanceOperation(
                                            asset=asset.Asset.native(), # XLM
                                            amount=str(milestone['amount']),
                                            claimants=[
                                                asset.create_claimable_balance_op.Claimant(
                                                    destination=contributor_pk,
                                                    predicate=asset.create_claimable_balance_op.ClaimantPredicate.predicate_unconditional()
                                                )
                                            ]
                                        )
                                    )
                                    .set_timeout(100)
                                    .build()
                                )
                                xdr = transaction.to_xdr()
                                send_message_to_js("SIGN_TX", xdr=xdr, networkPassphrase=get_network_passphrase())
                                st.session_state.pending_tx_action = {
                                    "action": "fund_milestone",
                                    "project_id": project["id"],
                                    "milestone_index": i
                                }
                                st.info("Please sign the transaction with Freighter to fund this milestone.")
                            except NotFoundError:
                                st.error(f"Funder account {st.session_state.public_key} not found or insufficient balance.")
                            except Exception as e:
                                st.error(f"Error funding milestone: {e}")

                elif st.session_state.public_key == project['contributor_account_pk'] and milestone["status"] == "funded":
                    if st.button(f"Claim Milestone: {milestone['name']}", key=f"claim_milestone_{i}"):
                        if not st.session_state.is_connected:
                            st.error("Please connect your Freighter wallet to claim milestones.")
                            continue
                        if st.session_state.public_key != project['contributor_account_pk']:
                            st.error("Only the Contributor can claim this milestone.")
                            continue
                        if not milestone["claimable_balance_id"]:
                            st.error("Claimable Balance ID not found. Has the milestone been funded?")
                            continue

                        with st.spinner(f"Preparing claim for '{milestone['name']}'..."):
                            try:
                                # Contributor's account is the source for claiming
                                contributor_account = get_horizon_server().load_account(st.session_state.public_key)

                                # Fetch the actual Claimable Balance entry to get its ID
                                # For demo, we are using the transaction hash as a placeholder for CB ID.
                                # In a real scenario, you'd query Horizon for the actual CB ID.
                                # Example: https://horizon-testnet.stellar.org/claimable_balances?claimable_balance_id=...
                                # However, due to Streamlit stateless nature and the need for immediate feedback,
                                # we'll use a simplified approach by using the tx_hash as identifier.
                                # A more robust solution would involve storing the actual CB ID after creation.

                                # To make this work, let's assume milestone["claimable_balance_id"] stores the actual ID.
                                # For the `CreateClaimableBalanceOperation` earlier, the CB ID is not directly returned by `submit_transaction`
                                # Instead, it's typically derived from the transaction (e.g., hash + operation index) or queried via Horizon.
                                # For this demo, let's just assume `milestone["claimable_balance_id"]` holds the correct Stellar Claimable Balance ID.
                                # The `tx_result['hash']` used previously is NOT the CB ID. It's just a placeholder for demo.

                                # Let's fetch the actual claimable balance ID from Horizon based on some criteria
                                # This is a common challenge for `ClaimableBalance` with stateless UIs.
                                # A better approach for the demo: The funder can retrieve the actual Claimable Balance ID
                                # from the Horizon API after creation and update the project milestone.
                                # For now, let's try to query based on recipient and amount for simplicity.

                                # Simpler approach: List claimable balances for the contributor and pick the matching one.
                                claimable_balances = get_horizon_server().claimable_balances().for_claimant(project['contributor_account_pk']).call()
                                cb_id_to_claim = None
                                for cb in claimable_balances['_embedded']['records']:
                                    if float(cb['amount']) == milestone['amount'] and cb['asset'] == 'native' and cb['id'] not in [m['claimable_balance_id'] for m in project['milestones'] if m['claimable_balance_id'] is not None and m['status'] == 'claimed']:
                                        cb_id_to_claim = cb['id']
                                        break
                                
                                if not cb_id_to_claim:
                                    st.warning("No matching claimable balance found for this milestone. It might have been claimed already or not yet created correctly.")
                                    continue

                                transaction = (
                                    TransactionBuilder(
                                        source_account=contributor_account,
                                        network_passphrase=get_network_passphrase(),
                                    )
                                    .add_operation(
                                        asset.claim_claimable_balance_op.ClaimClaimableBalanceOperation(
                                            balance_id=cb_id_to_claim
                                        )
                                    )
                                    .set_timeout(100)
                                    .build()
                                )
                                xdr = transaction.to_xdr()
                                send_message_to_js("SIGN_TX", xdr=xdr, networkPassphrase=get_network_passphrase())
                                st.session_state.pending_tx_action = {
                                    "action": "claim_milestone",
                                    "project_id": project["id"],
                                    "milestone_index": i
                                }
                                st.info("Please sign the transaction with Freighter to claim this milestone.")
                            except NotFoundError:
                                st.error(f"Contributor account {st.session_state.public_key} not found.")
                            except Exception as e:
                                st.error(f"Error claiming milestone: {e}")

    with col2:
        st.subheader("Project Progress")
        total_milestones = len(project["milestones"])
        claimed_milestones = sum(1 for m in project["milestones"] if m["status"] == "claimed")
        progress_percentage = (claimed_milestones / total_milestones * 100) if total_milestones > 0 else 0

        st.markdown(f"""
            <div class="progress-bar-container">
                <div class="progress-bar" style="width: {progress_percentage:.0f}%;"></div>
            </div>
            <p style='text-align: center; margin-top: 0.5rem;'>{claimed_milestones} of {total_milestones} milestones completed ({progress_percentage:.0f}%)</p>
        """, unsafe_allow_html=True)

        if project["status"] != "archived":
            st.markdown("---")
            st.subheader("Project Actions")

            if st.session_state.public_key == project['funder_account_pk']:
                if claimed_milestones == total_milestones and total_milestones > 0 and project["status"] != "completed":
                    if st.button("Mark Project as Completed", key="mark_completed_btn"):
                        project["status"] = "completed"
                        st.success("Project marked as completed!")
                        st.rerun()

                if st.button("Archive Project (AccountMerge)", key="archive_project_btn"):
                    # This requires signing by the project_account
                    if not project.get("project_account_sk"):
                        st.error("Project account secret key not found. Cannot archive.")
                        return
                    
                    with st.spinner("Preparing project account merge..."):
                        try:
                            project_keypair_for_merge = Keypair.from_secret(project["project_account_sk"])
                            funder_pk = project['funder_account_pk']

                            project_acc_horizon = get_horizon_server().load_account(project_keypair_for_merge.public_key)

                            transaction = (
                                TransactionBuilder(
                                    source_account=project_acc_horizon,
                                    network_passphrase=get_network_passphrase(),
                                )
                                .add_operation(
                                    asset.account_merge_op.AccountMergeOperation(
                                        destination=funder_pk
                                    )
                                )
                                .set_timeout(100)
                                .build()
                            )
                            # Sign with the project's secret key (DANGER: demo only)
                            transaction.sign(project_keypair_for_merge)
                            signed_xdr = transaction.to_xdr()

                            horizon = get_horizon_server()
                            tx_result = horizon.submit_transaction(signed_xdr)
                            st.success(f"Project account merged successfully! Hash: "
                                       f"<a href='https://testnet.stellarexplorer.org/tx/{tx_result['hash']}' target='_blank' class='tx-hash-link'>"
                                       f"{tx_result['hash'][:10]}...</a>", unsafe_allow_html=True)
                            project["status"] = "archived"
                            fetch_account_balances(funder_pk) # Update funder's balance
                            fetch_account_balances(project['project_account_pk']) # Should be 0 after merge
                            st.rerun()

                        except NotFoundError:
                            st.error(f"Project account {project['project_account_pk']} not found or already merged.")
                        except Exception as e:
                            st.error(f"Error archiving project: {e}")
            else:
                st.info("Only the Funder can manage project actions (e.g., archive).")


# --- Main App Logic ---
def main():
    sidebar()

    if st.session_state.public_key:
        if st.session_state.selected_project_id:
            project_detail_view(st.session_state.selected_project_id)
        else:
            dashboard_view()
    else:
        st.info("Connect your Freighter wallet to get started with NexusFlow!")
        st.markdown(
            """
            <h2>Welcome to NexusFlow!</h2>
            <p>Empower your collaborative projects with transparent, trustless financial orchestration on Stellar.</p>
            <p>
                As a Funder, you can create projects, define milestones, and secure commitments using Claimable Balances. 
                Funds are locked until milestones are met.
            </p>
            <p>
                As a Contributor, once you deliver on your promises, you can seamlessly claim your remuneration.
            </p>
            <p>
                The system enables graceful consolidation and archiving of completed projects via Account Merge, ensuring perpetual financial fluidity.
            </p>
            <p>
                <strong>Get started by connecting your Freighter wallet in the sidebar.</strong>
            </p>
            """,
            unsafe_allow_html=True
        )

if __name__ == "__main__":
    main()
