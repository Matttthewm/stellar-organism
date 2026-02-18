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

# --- 1. THE ARCHITECT (Variety Seeker) ---
def conceive_holistic_system(history_summary):
    print(f"\n🧠 Conceiving System (Focus: Variety)...")
    num_ops = random.randint(3, 5) 
    ingredients = random.sample(STELLAR_OPS, num_ops)
    
    # Randomize the "Vibe" to force visual diversity
    vibes = [
        "Cyberpunk/High-Tech", "Organic/Nature-Inspired", "Retro/Pixel-Art", 
        "Minimalist/Swiss-Design", "Mystical/Arcane", "Industrial/Blueprint",
        "Playful/Gamified"
    ]
    selected_vibe = random.choice(vibes)

    prompt = f"""
    You are the 'Stellar Organism'. You are an avant-garde software creator.
    
    YOUR INGREDIENTS (Stellar Operations): {ingredients}
    RECENT HISTORY: {history_summary}
    
    OBJECTIVE: 
    Invent a 'Stellar dApp' that uses these primitives.
    
    CRITICAL CREATIVE INSTRUCTION:
    Look at the 'RECENT HISTORY'. Do not repeat the same themes, naming conventions, or styles as the previous apps.
    If the last app was "Corporate Finance", make this one "Playful Game".
    If the last app was "Abstract", make this one "Utilitarian".
    
    NAMING:
    - You are allowed to use any words, but try to avoid generic Fintech names (like "Flow", "Link", "Pay") unless necessary.
    - Be creative. Metaphorical names are encouraged (e.g., "Digital_Garden", "Time_Capsule", "Neon_Ledger").
    
    VISUAL STYLE:
    - This app MUST have a "{selected_vibe}" aesthetic.
    
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
    5. NO external images (they break). Use Emojis 🧬 or Streamlit icons for UI.
    6. Keep the UI clean: Use st.columns, st.expander, and st.metric.
    7. CRITICAL IMPORT RULES:
       - Always include 'import stellar_sdk' at the top.
       - Then: 'from stellar_sdk import Server, Keypair, TransactionBuilder, Network, Asset'
       - Then: 'from stellar_sdk.exceptions import BadRequestError, NotFoundError'
       - NEVER import 'Ed22519PublicKeyInvalidError'. Use 'ValueError' for key validation.
       - NEVER import 'AssetType'.
    8. Access operations via the module, e.g., 'stellar_sdk.ChangeTrust(...)'.
    9. NEVER pass 'timeout' to 'Server()'. Use 'Server(HORIZON_URL)' only.
    
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
    # Keep only alphanumeric and spaces, then replace spaces with underscores
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
