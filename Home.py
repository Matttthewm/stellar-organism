import streamlit as st
import os
import re
import hashlib

st.set_page_config(page_title="The Stellar Organism", page_icon="🧬", layout="wide")

# Hide default sidebar navigation & apply Custom App Card CSS
st.markdown("""
    <style>
        /* Hide the default sidebar */
        [data-testid="stSidebarNav"] {display: none;}
        
        /* App Card Link Wrapper */
        .app-card-link {
            text-decoration: none !important;
            color: inherit !important;
            display: block;
            border-radius: 18px;
            transition: transform 0.2s, background-color 0.2s;
            padding: 10px;
        }
        .app-card-link:hover {
            transform: scale(1.02);
            background-color: rgba(0, 0, 0, 0.03);
        }
        @media (prefers-color-scheme: dark) {
            .app-card-link:hover {
                background-color: rgba(255, 255, 255, 0.05);
            }
        }
        
        /* The icon container */
        .app-icon {
            width: 80px;
            height: 80px;
            border-radius: 18px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 40px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.15);
            margin-bottom: 10px;
        }
        
        /* Typography for Title and Subtitle */
        .app-title {
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 2px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        .app-subtitle {
            font-size: 13px;
            color: #888;
            margin-bottom: 5px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        /* Adjust column padding to tighten the grid */
        [data-testid="column"] {
            padding: 10px;
        }
    </style>
""", unsafe_allow_html=True)

st.title("🧬 The Stellar Organism")
st.markdown("### *A self-evolving library of autonomous dApps living on the Stellar Network.*")
st.write("")
st.write("")

PAGES_DIR = "pages"

if not os.path.exists(PAGES_DIR):
    st.info("The Organism is gestating. No apps yet.")
else:
    files = sorted([f for f in os.listdir(PAGES_DIR) if f.endswith(".py")])
    if not files:
        st.info("No apps have evolved yet.")
    else:
        # Group apps into rows of 3 for the grid layout
        for i in range(0, len(files), 3):
            cols = st.columns(3)
            row_files = files[i:i+3]
            
            for j, file in enumerate(row_files):
                # Clean up the name (e.g., "001_nexusflow.py" -> "Nexusflow")
                name = file.replace('.py', '')
                url_path = name # Streamlit natively routes using the filename without .py
                
                clean_name = re.sub(r'^\d+_', '', name) # Removes the "001_" prefix
                title = clean_name.replace('_', ' ').title()

                # Generate a deterministic icon color & emoji based on the app's name
                hash_val = int(hashlib.md5(title.encode()).hexdigest(), 16)
                gradients = [
                    "linear-gradient(135deg, #FF3B30, #FF2D55)", # Red/Pink
                    "linear-gradient(135deg, #007AFF, #5AC8FA)", # Blue/Cyan
                    "linear-gradient(135deg, #34C759, #30D158)", # Green
                    "linear-gradient(135deg, #FF9500, #FFCC00)", # Orange/Yellow
                    "linear-gradient(135deg, #5856D6, #AF52DE)", # Purple
                    "linear-gradient(135deg, #FF2D55, #5856D6)", # Pink/Purple
                    "linear-gradient(135deg, #32D74B, #009688)", # Mint
                    "linear-gradient(135deg, #FF9F0A, #FF375F)"  # Orange/Red
                ]
                emojis = ["🚀", "🪐", "🌌", "🛸", "🔮", "🧬", "⚡", "🌀", "💠", "🔱", "🌿", "🌸", "💎", "📜", "🗝️", "⚙️", "🛡️", "👾", "🤖", "👁️", "☄️", "🔥"]
                
                grad = gradients[hash_val % len(gradients)]
                emoji = emojis[hash_val % len(emojis)]

                # Build the layout for each app card, entirely wrapped in a clickable link
                with cols[j]:
                    card_html = f"""
                    <a href="{url_path}" target="_self" class="app-card-link">
                        <div style="display: flex; gap: 15px; align-items: center;">
                            <div class="app-icon" style="background: {grad};">{emoji}</div>
                            <div>
                                <div class="app-title" title="{title}">{title}</div>
                                <div class="app-subtitle">Stellar dApp</div>
                            </div>
                        </div>
                    </a>
                    """
                    st.markdown(card_html, unsafe_allow_html=True)
                
            st.write("") # Vertical spacer between rows
