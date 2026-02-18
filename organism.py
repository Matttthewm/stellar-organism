import os
import random
import json
from datetime import datetime
from google import genai

# --- CONFIGURATION ---
# Works for both Local (.env) and Cloud (Secrets)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

API_KEY = os.getenv("GEMINI_API_KEY") 
REPO_PATH = "." # Current directory in Cloud
PAGES_DIR = "pages"

if not API_KEY:
    print("❌ CRITICAL ERROR: API Key missing.")
    exit(1)

client = genai.Client(api_key=API_KEY)

# The Palette of Physics
STELLAR_OPS = [
    "ManageData", "Payment", "PathPaymentStrictReceive", "ManageBuyOffer",
    "CreatePassiveSellOffer", "SetOptions", "ChangeTrust", "AccountMerge",
    "BumpSequence", "ClaimClaimableBalance", "Clawback", "SetTrustLineFlags",
    "BeginSponsoringFutureReserves", "RevokeSponsorship"
]

# --- 1. THE ARCHITECT ---
def conceive_holistic_system(history_summary):
    print(f"\n🧠 Conceiving Holistic System...")
    num_ops = random.randint(3, 5) 
    ingredients = random.sample(STELLAR_OPS, num_ops)
    
    prompt = f"""
    You are the 'Stellar Organism'. A visionary software architect.
    
    YOUR RAW MATERIALS: {ingredients}
    
    OBJECTIVE: 
    Invent a 'Holistic System' (dApp) that combines these primitives into a coherent product.
    
    EXAMPLES:
    - 'ManageData' + 'TimeBounds' + 'MultiSig' = A Dead Man's Switch Vault.
    - 'Payment' + 'ManageOffer' + 'PathPayment' = An Auto-Balancing Portfolio Tool.
    
    REQUIREMENTS:
    1. **Novelty**: Must be unlike anything in history.
    2. **Utility**: Something a human wants to use.
    3. **Visuals**: Define a specific aesthetic (e.g. "Cyberpunk", "Swiss Minimalist").
    
    HISTORY: {history_summary}
    
    OUTPUT JSON:
    {{
        "human_name": "The Public Name",
        "system_concept": "The interaction of primitives.",
        "visual_style": "The aesthetic vibe.",
        "ingredients": {json.dumps(ingredients)}
    }}
    """
    try:
        response = client.models.generate_content(
            model="gemini-1.5-pro", 
            contents=prompt,
            config={'response_mime_type': 'application/json'}
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"   -> Brain Fog: {e}")
        return None

# --- 2. THE ENGINEER (Freighter + UI) ---
def build_polished_dapp(spec, cycle):
    print(f"⚡ Engineering App {cycle}: {spec['human_name']}...")
    
    prompt = f"""
    You are a Senior Streamlit Developer focusing on UI/UX.
    
    TASK: Build a production-ready dApp with a BEAUTIFUL, CUSTOM INTERFACE.
    
    APP: {spec['human_name']}
    CONCEPT: {spec['system_concept']}
    STYLE: {spec['visual_style']}
    
    TECHNICAL MANDATES:
    1.  **Freighter Integration**: Use `st.components.v1.html` to inject JavaScript that calls `signTransaction` from `@stellar/freighter-api`.
    2.  **Stellar Logic**: Use `stellar_sdk` to build the XDR (Transaction Envelope) in Python, then pass it to the JS bridge for signing.
    3.  **Network**: Use `https://horizon-testnet.stellar.org`.
    
    DESIGN MANDATES:
    1.  **Custom CSS**: Inject a `<style>` block to match the "{spec['visual_style']}" vibe.
    2.  **Layout**: Use `st.columns`, `st.expander` for a clean dashboard.
    3.  **Polish**: Add a custom footer and clean header.
    
    OUTPUT: Raw Python code only.
    """
    
    response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
    
    code = response.text
    if "```python" in code:
        code = code.split("```python")[1].split("```")[0]
    elif "```" in code:
        code = code.replace("```", "")
    return code.strip()

# --- 3. THE INFRASTRUCTURE ---
def ensure_structure():
    if not os.path.exists(PAGES_DIR):
        os.makedirs(PAGES_DIR)
    
    home_path = "Home.py"
    if not os.path.exists(home_path):
        with open(home_path, "w") as f:
            f.write(f"""
import streamlit as st

st.set_page_config(
    page_title="Stellar Organism",
    page_icon="🧬",
    layout="wide"
)

st.title("🧬 The Stellar Organism")
st.subheader("A Living Library of Evolutionary dApps")
st.info("⚠️ You need the [Freighter Wallet](https://www.freighter.app/) (Testnet) to use these apps.")

st.markdown(\"\"\"
### The Archive
This repository is maintained by an AI that lives in the cloud.
Every hour, it invents a new dApp and pushes it here.
\"\"\")
            """)

# --- MAIN (Run Once) ---
def main():
    ensure_structure()
    
    # Check History
    existing_files = [f for f in os.listdir(PAGES_DIR) if f.endswith(".py")]
    cycle = len(existing_files) + 1
    
    print(f"=== 🧬 CYCLE {cycle} INITIATED ===")
    
    # 1. Conceive
    spec = conceive_holistic_system(existing_files[-10:])
    
    if spec:
        # 2. Build
        code = build_polished_dapp(spec, cycle)
        
        safe_name = spec['human_name'].replace(" ", "_").replace("'", "").lower()
        filename = f"{cycle:03d}_{safe_name}.py"
        filepath = os.path.join(PAGES_DIR, filename)
        
        with open(filepath, "w") as f:
            f.write(code)
            
        print(f"✅ Created: {filename}")
    else:
        print("❌ Conception Failed.")

if __name__ == "__main__":
    main()