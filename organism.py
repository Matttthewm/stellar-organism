import os
import random
import json
import re
from google import genai
from google.genai import types

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

# Initialize the NEW Google GenAI Client
client = genai.Client(api_key=API_KEY)

ARCHITECT_MODEL = 'gemini-2.0-flash' 
ENGINEER_MODEL = 'gemini-2.0-pro-exp-02-05' 

STELLAR_OPS = [
    "ManageData", "Payment", "PathPaymentStrictReceive", "ManageBuyOffer",
    "CreatePassiveSellOffer", "SetOptions", "ChangeTrust", "AccountMerge",
    "BumpSequence", "ClaimClaimableBalance", "Clawback", "SetTrustLineFlags"
]

def conceive_holistic_system(history_summary):
    print(f"\n🧠 Conceiving System (Model: {ARCHITECT_MODEL})...")
    num_ops = random.randint(3, 5) 
    ingredients = random.sample(STELLAR_OPS, num_ops)
    
    vibes = ["Cyberpunk/High-Tech", "Organic/Nature-Inspired", "Retro/Pixel-Art", "Minimalist/Swiss-Design", "Mystical/Arcane"]
    selected_vibe = random.choice(vibes)

    prompt = f"""
    You are the 'Stellar Organism'. An avant-garde software creator.
    YOUR INGREDIENTS: {ingredients}
    RECENT HISTORY: {history_summary}
    
    OBJECTIVE: Invent a 'Stellar dApp' that uses these primitives.
    
    CREATIVE RULES:
    1. Do NOT repeat themes from HISTORY.
    2. NAMING: Avoid generic fintech names. Use metaphorical names.
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
        response = client.models.generate_content(
            model=ARCHITECT_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"   -> Brain Fog: {e}")
        if "429" in str(e):
            print("   🛑 QUOTA EXCEEDED: You have hit the Gemini Free Tier limits. The Organism must rest until the quota resets.")
        return None

def build_polished_dapp(spec, cycle):
    prompt = f"""
    You are a Senior Streamlit Developer.
    TASK: Build a functional dApp based on this concept.
    
    APP NAME: {spec['human_name']}
    CONCEPT: {spec['system_concept']}
    STYLE: {spec['visual_style']}
    
    MANDATES (DO NOT BREAK THESE):
    1. Freighter Integration (st.components.v1.html + signTransaction).
    2. Custom CSS for style "{spec['visual_style']}".
    3. STRICTLY use 'st.query_params' (No experimental_get_query_params).
    4. NO external images. Use Emojis only.
    
    5. CRITICAL IMPORT RULES:
       - 'import stellar_sdk'
       - 'from stellar_sdk import Server, Keypair, TransactionBuilder, Network, Asset'
       - 'from stellar_sdk.exceptions import BadRequestError, NotFoundError'
       - 'import requests' (Required for friendbot)
    
    6. STRICT SYNTAX & ANTI-HALLUCINATION RULES:
       - URLS: NEVER wrap URLs in Markdown. Use pure strings. Example: HORIZON_URL = "https://horizon-testnet.stellar.org" (No brackets or parenthesis).
       - PASSPHRASE: MUST use `Network.TESTNET_NETWORK_PASSPHRASE`. Never `TESTNET_PASSPHRASE`.
       - ASSET CODES: 1-12 Alphanumeric characters ONLY. NO UNDERSCORES (e.g., Use "FRAGA", never "FRAG_A").
       - FRIENDBOT: The python SDK `Server` does NOT have a `.friendbot()` method. You MUST use: `requests.get(f"https://friendbot.stellar.org/?addr={{public_key}}")`
       - HTML COMPONENTS: `components.html()` does NOT accept a `key` argument. NEVER pass `key=...` to it.
       - JS FORMATTING: NEVER use `.format()` on HTML/JS strings (it breaks curly braces). Use f-strings and double curly braces `{{}}` for JS logic.
    
    OUTPUT: Raw Python code only.
    """
    
    response = None
    try:
        print(f"⚡ Engineering App {cycle} (Model: {ENGINEER_MODEL})...")
        response = client.models.generate_content(
            model=ENGINEER_MODEL,
            contents=prompt
        )
    except Exception as e:
        print(f"⚠️ Pro Limit Hit? ({e}). Falling back to {ARCHITECT_MODEL}...")
        try:
            response = client.models.generate_content(
                model=ARCHITECT_MODEL,
                contents=prompt
            )
        except Exception as fallback_e:
            print(f"   -> Engineering Collapse: {fallback_e}")
            if "429" in str(fallback_e):
                print("   🛑 QUOTA EXCEEDED on fallback model. The Organism is forced to sleep.")
            return None
    
    if response and response.text:
        code = response.text
        if "```python" in code:
            code = code.split("```python")[1].split("```")[0]
        elif "```" in code:
            code = code.replace("```", "")
        return code.strip()
    return None

def ensure_structure():
    if not os.path.exists(PAGES_DIR): os.makedirs(PAGES_DIR)

def clean_filename(name):
    # Aggressively strip colons and special characters that break Streamlit routing
    clean = re.sub(r'[^a-zA-Z0-9 ]', '', name)
    # Replaces any multiple spaces with a single underscore safely
    clean = re.sub(r'\s+', '_', clean.strip())
    return clean.lower()

def main():
    ensure_structure()
    existing_files = [f for f in os.listdir(PAGES_DIR) if f.endswith(".py")]
    cycle = len(existing_files) + 1
    
    print(f"=== 🧬 CYCLE {cycle} INITIATED ===")
    spec = conceive_holistic_system(existing_files[-10:])
    
    if spec:
        code = build_polished_dapp(spec, cycle)
        if code:
            filename = f"{PAGES_DIR}/{cycle:03d}_{clean_filename(spec['human_name'])[:30]}.py"
            with open(filename, "w") as f: f.write(code) 
            print(f"✅ Created: {filename}")
        else: print("❌ Engineering Failed.")

if __name__ == "__main__":
    main()
