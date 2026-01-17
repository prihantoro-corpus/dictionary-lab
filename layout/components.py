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

def render_collocate_example(left_list, node, right_list, col_token):
    """
    Renders a sentence with search word and collocate highlighted.
    """
    def highlight(t):
        if t.lower() == node.lower():
            return f"<span style='color: #ff4b4b; font-weight: bold;'>{t}</span>"
        if t.lower() == col_token.lower():
            return f"<span style='color: #29b5e8; font-weight: bold;'>{t}</span>"
        return t
        
    l_str = " ".join([highlight(t) for t in left_list])
    r_str = " ".join([highlight(t) for t in right_list])
    n_str = highlight(node)
    
    st.markdown(f"{l_str} {n_str} {r_str}", unsafe_allow_html=True)
