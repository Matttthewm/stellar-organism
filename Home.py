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
        
        /* The icon container - FIXED SQUISHING */
        .app-icon {
            width: 80px;
            min-width: 80px;
            height: 80px;
            border-radius: 18px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 40px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.15);
            flex-shrink: 0; 
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
            margin-bottom: 8px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        /* Style the Streamlit native link to look like an App Store button */
        div[data-testid="stPageLink-NavLink"] {
            background-color: #f0f0f5; 
            border-radius: 20px;
            padding: 4px 18px;
            width: fit-content;
            display: flex;
            justify-content: center;
            transition: all 0.2s;
        }
        div[data-testid="stPageLink-NavLink"] p {
            color: #007aff !important;
            margin: 0 !important;
            font-weight: 700 !important;
            font-size: 13px !important;
        }
        div[data-testid="stPageLink-NavLink"]:hover {
            background-color: #e0e0e5;
            transform: scale(1.03);
        }

        /* Dark Mode Adjustments */
        @media (prefers-color-scheme: dark) {
            div[data-testid="stPageLink-NavLink"] {
                background-color: #3A3A3C;
            }
            div[data-testid="stPageLink-NavLink"] p {
                color: #0A84FF !important;
            }
            div[data-testid="stPageLink-NavLink"]:hover {
                background-color: #4A4A4C;
            }
            .app-icon {
                box-shadow: 0 4px 10px rgba(0,0,0,0.4);
            }
        }
        
        /* Adjust column padding to tighten the grid */
        [data-testid="column"] {
            padding: 10px;
            margin-bottom: 15px;
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
                # Clean up the name
                name = file.replace('.py', '')
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

                # Build the layout for each app card
                with cols[j]:
                    icon_col, text_col = st.columns([1, 2.5], gap="small")
                    
                    with icon_col:
                        # Draw the large custom icon
                        st.markdown(f'<div class="app-icon" style="background: {grad};">{emoji}</div>', unsafe_allow_html=True)
                    
                    with text_col:
                        # Draw the Title, Subtitle, and Native OPEN Button safely
                        st.markdown(f'''
                            <div class="app-title" title="{title}">{title}</div>
                            <div class="app-subtitle">Stellar dApp</div>
                        ''', unsafe_allow_html=True)
                        st.page_link(f"pages/{file}", label="OPEN", icon=None)
                
            st.write("") # Vertical spacer between rows
