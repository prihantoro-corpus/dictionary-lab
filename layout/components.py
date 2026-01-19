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

import matplotlib.pyplot as plt

import numpy as np

def render_collocate_chart(collocates, node_word=""):
    """
    Renders a radial network graph (LancsBox style).
    Center: Node word
    Surrounding: Collocates
    Distance: Inversely proportional to Score (Closer = Stronger)
    Size: Proportional to Score
    Position: Left vs Right dominant
    """
    if not collocates:
        return

    # Extract Data & Limit
    data = collocates[:20]
    words = [c['collocate'] for c in data]
    scores = [float(c.get('score', c.get('LL', 0))) for c in data]
    
    if not scores: return
    
    min_s, max_s = min(scores), max(scores)
    # Norm function
    def get_norm(s):
        if max_s == min_s: return 1.0
        return (s - min_s) / (max_s - min_s)

    # Create Figure
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # 1. Center Node
    ax.scatter(0, 0, s=2500, c="#d32f2f", edgecolors="white", linewidth=2, zorder=20)
    ax.text(0, 0, node_word, ha='center', va='center', color='white', weight='bold', fontsize=12, zorder=21)
    
    # 2. Assign Directions
    # We split into Left-Leaning and Right-Leaning groups to distribute them
    left_side = []
    right_side = []
    
    for i, c in enumerate(data):
        l_cnt = c.get('left', 0)
        r_cnt = c.get('right', 0)
        total = l_cnt + r_cnt
        if total == 0:
            ratio = 0.5 # Neutral
        else:
            ratio = l_cnt / total
            
        item = {
            'word': words[i], 
            'score': scores[i], 
            'norm': get_norm(scores[i]),
            'ratio': ratio
        }
        
        if ratio >= 0.5:
            left_side.append(item)
        else:
            right_side.append(item)
            
    # Sort by ratio (most left to neutral)
    left_side.sort(key=lambda x: x['ratio'], reverse=True) 
    # Sort by ratio (neutral to most right)
    right_side.sort(key=lambda x: x['ratio'], reverse=True)

    # Distribute Angles
    # Left: 100 degrees to 260 degrees (avoid top/bottom exact overlap)
    # Right: -80 degrees to 80 degrees
    
    def assign_coords(group, start_angle, end_angle):
        if not group: return
        count = len(group)
        # linear space
        angles = np.linspace(np.radians(start_angle), np.radians(end_angle), count)
        
        min_dist = 0.3
        max_dist = 0.85
        min_size = 400
        max_size = 1800
        
        for idx, item in enumerate(group):
            angle = angles[idx]
            norm = item['norm']
            
            # Distance (Inverse to score)
            r = max_dist - (norm * (max_dist - min_dist))
            
            # Size (Proportional to score)
            s = min_size + (norm * (max_size - min_size))
            
            x = r * np.cos(angle)
            y = r * np.sin(angle)
            
            # Draw Line
            ax.plot([0, x], [0, y], c="#b0bec5", linewidth=1.0, zorder=1)
            
            # Draw Bubble
            # Lighter blue for better contrast with black text? 
            # Or standard material blue #42a5f5
            ax.scatter(x, y, s=s, c="#64b5f6", edgecolors="white", linewidth=1, zorder=10)
            
            # Label
            # Black text for visibility
            ax.text(x, y, item['word'], ha='center', va='center', color='black', weight='normal', fontsize=10, zorder=15)

    # Assign Left (Left side of circle)
    assign_coords(left_side, 100, 260)
    
    # Assign Right (Right side of circle)
    assign_coords(right_side, 80, -80)

    # Clean up
    ax.set_xlim(-1, 1)
    ax.set_ylim(-1, 1)
    ax.axis('off')
    ax.set_aspect('equal')
    # ax.set_title(f"Collocation Graph: {node_word}", fontsize=14, color="#555")
    
    st.pyplot(fig, use_container_width=True)
