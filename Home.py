import streamlit as st

# Page Config (Title & Icon)
st.set_page_config(
    page_title="The Stellar Organism",
    page_icon="🧬",
    layout="wide"
)

# Header Section
st.title("🧬 The Stellar Organism")
st.markdown("### *A Self-Evolving Autonomous Entity on the Stellar Network*")

# The Explanation
st.info("ℹ️ **How to Use:** Open the sidebar on the left to explore the dApps this organism has created.")

# Dynamic Stats (Optional, keeps it simple for now)
st.divider()

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    #### 🧠 The Brain
    - **Model:** Gemini 2.5 Flash
    - **Cycle:** Daily Evolution
    - **Mission:** Explore Stellar capabilities through code.
    """)

with col2:
    st.markdown("""
    #### 🏗️ The Body
    - **Host:** Streamlit Community Cloud
    - **Network:** Stellar Testnet (Soroban)
    - **Wallet:** [Freighter](https://www.freighter.app/) required.
    """)

st.divider()

# Footer
st.caption("This application evolves automatically via GitHub Actions. Code is written without human intervention.")
