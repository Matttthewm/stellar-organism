import os
import random
import json
import re
import google.generativeai as genai
import time

# --- CONFIGURATION ---
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

API_KEY = os.getenv("GEMINI_API_KEY") 
PAGES_DIR = "pages"

if not API_KEY:
    print("❌ CRITICAL ERROR: API Key missing.")
    exit(1)

# --- STANDARD LIBRARY SETUP ---
genai.configure(api_key=API_KEY)
MODEL_NAME = 'gemini-2.5-flash'

STELLAR_OPS = [
    "ManageData", "Payment", "PathPaymentStrictReceive", "ManageBuyOffer",
    "CreatePassiveSellOffer", "SetOptions", "ChangeTrust", "AccountMerge",
    "BumpSequence", "ClaimClaimableBalance", "Clawback", "SetTrustLineFlags",
    "BeginSponsoringFutureReserves", "RevokeSponsorship"
]

# --- 1. THE ARCHITECT (Variety Engine) ---
def conceive_holistic_system(history_summary):
    print(f"\n🧠 Conceiving System (Focus: Variety)...")
    num_ops = random.randint(3, 5) 
    ingredients = random.sample(STELLAR_OPS, num_ops)
    
    vibes = [
        "Cyberpunk/High-Tech", "Organic/Nature-Inspired", "Retro/Pixel-Art", 
        "Minimalist/Swiss-Design", "Mystical/Arcane", "Industrial/Blueprint",
        "Playful/Gamified", "Abstract/Mathematical"
    ]
    selected_vibe = random.choice(vibes)

    prompt = f"""
    You are the 'Stellar Organism'. An avant-garde software creator.
    
    YOUR INGREDIENTS: {ingredients}
    RECENT HISTORY: {history_summary}
    
    OBJECTIVE: 
    Invent a 'Stellar dApp' that uses these primitives in a weird, specific, or creative way.
    
    CREATIVE RULES:
    1. Look at the HISTORY. Do NOT repeat themes. If the last app was serious, make this one fun.
    2. NAMING: Avoid generic fintech names (Flow, Link, Pay). Use metaphorical names (e.g., "Glass_Ledger", "Time_Vortex", "Pixel_Bank").
    3. STYLE: Must be "{selected_vibe}".
    
    OUTPUT JSON:
    {{
        "human_name": "The Name", 
        "system_concept": "1-sentence pitch.",
        "visual_style": "{selected_vibe}",
        "ingredients": {json.dumps(ingredients)}
    }}
    """
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"   -> Brain Fog: {e}")
        return None

# --- 2. THE ENGINEER (Strict Builder) ---
def build_polished_dapp(spec, cycle):
    print(f"⚡ Engineering App {cycle}: {spec['human_name']} ({spec['visual_style']})...")
    
    prompt = f"""
    You are a Senior Streamlit Developer.
    
    TASK: Build a functional dApp based on this concept.
    
    APP NAME: {spec['human_name']}
    CONCEPT: {spec['system_concept']}
    STYLE: {spec['visual_style']} (Reflect this in the CSS!)
    
    MANDATES (DO NOT BREAK THESE):
    1. Freighter Integration (st.components.v1.html + signTransaction).
    2. Stellar SDK for XDR.
    3. Custom CSS for style "{spec['visual_style']}".
    4. STRICTLY use 'st.query_params' instead of 'st.experimental_get_query_params'.
    5. NO external images. Use Emojis 🧬 only.
    6. Keep the UI clean: Use st.columns, st.expander, and st.metric.
    
    7. CRITICAL IMPORT RULES:
       - Always include 'import stellar_sdk' at the top.
       - Then: 'from stellar_sdk import Server, Keypair, TransactionBuilder, Network, Asset'
       - Then: 'from stellar_sdk.exceptions import BadRequestError, NotFoundError'
       - NEVER import 'Ed22519PublicKeyInvalidError'. Use 'ValueError'.
       - NEVER import 'AssetType'.
    
    8. STELLAR SERVER RULES:
       - Use 'Server(HORIZON_URL)' only. NEVER pass 'timeout' to Server().
       - Access operations via module: 'stellar_sdk.ChangeTrust(...)'.
    
    9. HTML COMPONENT RULES:
       - ALWAYS use: 'import streamlit.components.v1 as components'
       - ALWAYS call: 'components.html(...)'. 
       - NEVER call 'html(...)' directly from 'streamlit'.
    
    10. SIDEBAR MANDATE:
        - At the very top of the sidebar, display the App Name and Concept using 'st.sidebar.info()' or 'st.sidebar.markdown()'.
        - Show the 'Visual Style' in the sidebar as a badge/caption.

    11. SECRET KEY HANDLING:
        - NEVER assume 'st.secrets' exists or has keys.
        - ALWAYS implement a 'Demo Mode' fallback:
          if "ISSUER_KEY" in st.secrets:
              key = st.secrets["ISSUER_KEY"]
          else:
              if "demo_key" not in st.session_state: st.session_state.demo_key = Keypair.random().secret
              key = st.session_state.demo_key
              st.warning("Using Ephemeral Demo Keys")
    
    OUTPUT: Raw Python code only.
    """
    
    model = genai.GenerativeModel(MODEL_NAME)
    response = model.generate_content(prompt)
    
    code = response.text
    if "```python" in code:
        code = code.split("```python")[1].split("```")[0]
    elif "```" in code:
        code = code.replace("```", "")
    return code.strip()

# --- 3. INFRASTRUCTURE & MAIN ---
def ensure_structure():
    if not os.path.exists(PAGES_DIR):
        os.makedirs(PAGES_DIR)
    
    home_path = "Home.py"
    if not os.path.exists(home_path):
        with open(home_path, "w") as f:
            f.write("""
import streamlit as st
st.set_page_config(page_title="Stellar Organism", page_icon="🧬", layout="wide")
st.title("🧬 The Stellar Organism")
st.info("⚠️ Use Freighter Wallet (Testnet)")
st.write("A Living Library of Evolutionary dApps.")
""")

def clean_filename(name):
    clean = re.sub(r'[^a-zA-Z0-9 ]', '', name)
    return clean.strip().replace(" ", "_").lower()

def main():
    ensure_structure()
    existing_files = [f for f in os.listdir(PAGES_DIR) if f.endswith(".py")]
    cycle = len(existing_files) + 1
    
    print(f"=== 🧬 CYCLE {cycle} INITIATED ===")
    
    spec = conceive_holistic_system(existing_files[-10:])
    
    if spec:
        code = build_polished_dapp(spec, cycle)
        
        safe_name = clean_filename(spec['human_name'])
        if len(safe_name) > 30:
            safe_name = safe_name[:30]
            
        filename = f"{cycle:03d}_{safe_name}.py"
        filepath = os.path.join(PAGES_DIR, filename)
        
        with open(filepath, "w") as f:
            f.write(code) 
        print(f"✅ Created: {filename}")
    else:
        print("❌ Conception Failed.")

if __name__ == "__main__":
    main()
