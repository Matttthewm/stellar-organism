import streamlit as st
import os

st.set_page_config(page_title="The Stellar Organism", page_icon="🧬", layout="wide")

# Hide the ugly default Streamlit sidebar navigation
st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {display: none;}
    </style>
""", unsafe_allow_html=True)

st.title("🧬 The Stellar Organism: App Store")
st.markdown("### *A Living Library of Evolutionary dApps on the Stellar Network*")
st.divider()

PAGES_DIR = "pages"

if not os.path.exists(PAGES_DIR):
    st.info("No apps have evolved yet. The organism is gestating...")
else:
    files = sorted([f for f in os.listdir(PAGES_DIR) if f.endswith(".py")])
    if not files:
        st.info("No apps have evolved yet.")
    else:
        # Create a 3-column grid
        cols = st.columns(3)
        for i, file in enumerate(files):
            app_path = f"{PAGES_DIR}/{file}"
            
            # Clean up the name for the UI (e.g., "001_cool_app.py" -> "Cool App")
            parts = file.replace(".py", "").split("_", 1)
            app_num = parts[0]
            app_name = parts[1].replace("_", " ").title() if len(parts) > 1 else file
            
            with cols[i % 3]:
                with st.container(border=True):
                    st.markdown(f"#### 🪐 App {app_num}")
                    # Native Streamlit page link
                    st.page_link(app_path, label=f"**Launch {app_name}**", icon="🚀")
                    
st.divider()
st.caption("Code is written without human intervention via Gemini.")
