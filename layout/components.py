import streamlit as st
import urllib.parse

def get_google_links(query, language):
    """
    Returns tuple (def_url, img_url) for Google Search.
    """
    q_plus = urllib.parse.quote_plus(query)
    
    if language == 'Indonesian':
        def_url = f"https://www.google.com/search?q=apa+itu+%27{q_plus}%27"
    elif language == 'Chinese':
        def_url = f"https://www.google.com/search?q=什么是'{q_plus}'"
    elif language == 'Japanese':
         def_url = f"https://www.google.com/search?q='{q_plus}'+とは"
    elif language == 'Korean':
         def_url = f"https://www.google.com/search?q='{q_plus}'+이란"
    elif language == 'Arabic':
         def_url = f"https://www.google.com/search?q=ما+هو+'{q_plus}'"
    elif language == 'Javanese':
         def_url = f"https://www.google.com/search?q=apa+kuwi+'{q_plus}'"
    else:
        # Default/English
        def_url = f"https://www.google.com/search?q=what+is+%27{q_plus}%27"
        
    img_url = f"https://www.google.com/search?tbm=isch&q={q_plus}"
    
    return def_url, img_url

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

def render_collocate_example(left, node, right, col_token=None, translation=None):
    """
    Renders a sentence with search word and optionally collocate highlighted.
    Handles both lists and strings for left/right context.
    If translation is provided, it's rendered below with a distinct style.
    """
    def highlight_node(text):
        if not text: return text
        # If it's a single word
        if " " not in text and text.lower() == node.lower():
             return f"<span style='color: #ff4b4b; font-weight: bold;'>{text}</span>"
        # If it's a segment, use regex to highlight all occurrences of the node word
        import re
        # Escape node in case it has regex chars
        pattern = re.compile(f"\\b({re.escape(node)})\\b", re.IGNORECASE)
        text = pattern.sub(r"<span style='color: #ff4b4b; font-weight: bold;'>\1</span>", text)
        
        if col_token:
            col_pattern = re.compile(f"\\b({re.escape(col_token)})\\b", re.IGNORECASE)
            text = col_pattern.sub(r"<span style='color: #29b5e8; font-weight: bold;'>\1</span>", text)
        return text

    def get_str(ctx):
        if isinstance(ctx, list):
            return " ".join(ctx)
        return str(ctx)

    l_str = highlight_node(get_str(left))
    r_str = highlight_node(get_str(right))
    n_str = highlight_node(node)
    
    full_html = f"{l_str} {n_str} {r_str}"
    
    st.markdown(f"""
    <div style="border-left: 3px solid #ff4b4b; padding-left: 10px; margin-bottom: 15px;">
        <div style="font-size: 1.05em; line-height: 1.4;">{full_html}</div>
        {f'<div style="margin-top: 5px; color: #4e9a06; font-style: italic; font-size: 0.95em;">{translation}</div>' if translation else ''}
    </div>
    """, unsafe_allow_html=True)

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# Configure Matplotlib to use fonts that support CJK and other scripts
# Priority list for Windows/Standard fonts covering multiple languages
plt.rcParams['font.family'] = ['sans-serif']
plt.rcParams['font.sans-serif'] = [
    'Microsoft YaHei', 'SimHei', 'Malgun Gothic', 'Meiryo', 'Arial Unicode MS', 
    'Segoe UI', 'sans-serif'
]
# Ensure minus sign is rendered correctly
plt.rcParams['axes.unicode_minus'] = False

import numpy as np

def render_collocate_chart(collocates, node_word="", chart_size=1.0):
    """
    Renders a radial network graph (LancsBox style).
    Center: Node word
    Surrounding: Collocates
    Distance: Inversely proportional to Score (Closer = Stronger)
    Size: Proportional to Score
    Position: Left vs Right dominant
    chart_size: Multiplier for figsize (default 1.0 -> 10x8)
    """
    if not collocates:
        return

    # POS Color Mapping (more diverse as requested)
    pos_colors = {
        'NN': '#1f77b4', 'NNS': '#aec7e8', 'NP': '#ff7f0e', 'NPS': '#ffbb78', 'NNP': '#ff7f0e', 'NNPS': '#ffbb78', # Nouns
        'JJ': '#2ca02c', 'JJR': '#98df8a', 'JJS': '#bcbd22', # Adjectives
        'VV': '#d62728', 'VVP': '#ff9896', 'VVZ': '#d62728', 'VVD': '#ff9896', 'VVG': '#d62728', 'VVN': '#ff9896', # Verbs
        'VB': '#d62728', 'VH': '#d62728', # Verbs (Be/Have)
        'RB': '#9467bd', 'RBR': '#c5b0d5', 'RBS': '#9467bd', # Adverbs
        'IN': '#8c564b', # Preposition
        'DT': '#c49c94', # Determiner
        'PRP': '#e377c2', 'PP': '#e377c2', 'PP$': '#f7b6d2', # Pronouns
        'MD': '#dbdb8d', # Modal
        'CD': '#17becf', # Cardinal
        'FW': '#9edae5', # Foreign Word
    }

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

    # Create Figure with adjustable size
    # We use a base DPI of 100. figsize is in inches.
    width, height = 10 * chart_size, 8 * chart_size
    fig, ax = plt.subplots(figsize=(width, height), dpi=100)
    
    # Scale fonts and markers
    center_marker_size = 2500 * chart_size
    bubble_min_size = 400 * chart_size
    bubble_max_size = 1800 * chart_size
    font_center = 12 * chart_size
    font_label = 10 * chart_size
    
    # 1. Center Node
    ax.scatter(0, 0, s=center_marker_size, c="#fdd835", edgecolors="black", linewidth=1.5, zorder=20)
    ax.text(0, 0, node_word, ha='center', va='center', color='black', weight='bold', fontsize=font_center, zorder=21)
    
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
            
        # Determine Color based on POS tag
        tag = c.get('tag') or ''
        # Use exact match or prefix if not found
        bubble_color = pos_colors.get(tag)
        if not bubble_color:
             # Try first two letters
             bubble_color = pos_colors.get(tag[:2])
             
        if not bubble_color:
            bubble_color = "#b0bec5" # Fallback
            
        item = {
            'word': words[i], 
            'score': scores[i], 
            'norm': get_norm(scores[i]),
            'ratio': ratio,
            'color': bubble_color
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
        
        for idx, item in enumerate(group):
            angle = angles[idx]
            norm = item['norm']
            
            # Distance (Inverse to score)
            r = max_dist - (norm * (max_dist - min_dist))
            
            # Size (Proportional to score)
            s = bubble_min_size + (norm * (bubble_max_size - bubble_min_size))
            
            # Size (Proportional to score)
            s = bubble_min_size + (norm * (bubble_max_size - bubble_min_size))
            
            x = r * np.cos(angle)
            y = r * np.sin(angle)
            
            # Draw Line
            ax.plot([0, x], [0, y], c="#b0bec5", linewidth=1.0, zorder=1)
            
            # Draw Bubble
            ax.scatter(x, y, s=s, c=item['color'], edgecolors="black", linewidth=0.5, zorder=10)
            
            # Label - Black text for visibility as requested
            ax.text(x, y, item['word'], ha='center', va='center', color='black', weight='normal', fontsize=font_label, zorder=15)

    # Assign Left (Left side of circle)
    assign_coords(left_side, 100, 260)
    
    # Assign Right (Right side of circle)
    assign_coords(right_side, 80, -80)

    # Clean up
    ax.set_xlim(-1, 1)
    ax.set_ylim(-1, 1)
    ax.axis('off')
    ax.set_aspect('equal')
    
    st.pyplot(fig, use_container_width=False)
    plt.close(fig)
