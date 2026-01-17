import streamlit as st

def render_pmw_bar(pmw, max_pmw=5000):
    """
    Renders a progress bar for PMW.
    max_pmw acts as the 100% mark.
    """
    if max_pmw == 0:
        progress = 0
    else:
        progress = min(pmw / max_pmw, 1.0)
    
    st.write(f"**PMW**: {pmw}")
    st.progress(progress)

def render_zipf_band(band):
    """
    Renders Zipf band as a visual indicator (1-5).
    """
    # 5 bars. "Filled" vs "Empty".
    # filled = "█"
    # empty = "░"
    filled = "🟦" # Or some other icon
    empty = "⬜"
    
    visual = (filled * band) + (empty * (5 - band))
    st.write(f"**Zipf Band**: {visual} ({band}/5)")

def render_badge(text, type="corpus"):
    color = "blue" if type == "corpus" else "green"
    st.markdown(f":{color}[{text}]")
