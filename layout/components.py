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

import plotly.graph_objects as go
import numpy as np

def render_collocate_chart(collocates, node_word="", chart_size=1.0, examples_dict=None):
    """
    Renders a radial network graph (LancsBox style).
    Center: Node word
    Surrounding: Collocates
    Distance: Inversely proportional to Score (Closer = Stronger)
    Size: Proportional to Score
    Position: Left vs Right dominant
    chart_size: Multiplier for figsize
    """
    if not collocates:
        return
        
    if examples_dict is None:
        examples_dict = {}

    # POS Color Mapping
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

    # Extract Data & Limit (Top 20 from whatever was passed in)
    data = collocates[:20]
    words = [c['collocate'] for c in data]
    scores = [float(c.get('score', c.get('LL', 0))) for c in data]
    
    if not scores: return
    
    min_s, max_s = min(scores), max(scores)
    def get_norm(s):
        if max_s == min_s: return 1.0
        return (s - min_s) / (max_s - min_s)

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
        bubble_color = pos_colors.get(tag)
        if not bubble_color:
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
            
    # Sort by ratio
    left_side.sort(key=lambda x: x['ratio'], reverse=True) 
    right_side.sort(key=lambda x: x['ratio'], reverse=True)

    nodes_list = []
    def assign_coords(group, start_angle, end_angle):
        if not group: return
        count = len(group)
        angles = np.linspace(np.radians(start_angle), np.radians(end_angle), count)
        
        min_dist = 0.3
        max_dist = 0.85
        
        for idx, item in enumerate(group):
            angle = angles[idx]
            norm = item['norm']
            
            # Distance (Inverse to score)
            r = max_dist - (norm * (max_dist - min_dist))
            
            x = r * np.cos(angle)
            y = r * np.sin(angle)
            
            item['x'] = x
            item['y'] = y
            nodes_list.append(item)

    # Assign coordinates
    assign_coords(left_side, 100, 260)
    assign_coords(right_side, 80, -80)

    # Build Plotly Figure
    fig = go.Figure()
    
    # 1. Lines trace
    edge_x = []
    edge_y = []
    for node in nodes_list:
        edge_x.extend([0, node['x'], None])
        edge_y.extend([0, node['y'], None])
        
    fig.add_trace(go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=1, color='#b0bec5'),
        hoverinfo='none',
        mode='lines'
    ))
    
    # 2. Nodes trace
    node_x = [0]
    node_y = [0]
    node_text = [node_word]
    node_color = ['#fdd835']
    node_size = [60]
    hover_texts = [f"<b>{node_word}</b>"]
    
    for item in nodes_list:
        node_x.append(item['x'])
        node_y.append(item['y'])
        node_text.append(item['word'])
        node_color.append(item['color'])
        
        # Calculate bubble size (diameter)
        d = 30 + item['norm'] * 40
        node_size.append(d)
        
        kwic_ex = examples_dict.get(item['word'])
        if not kwic_ex:
            kwic_ex = "No example available."
        else:
            kwic_ex = str(kwic_ex).replace("&lt;s&gt;", "").replace("&lt;/s&gt;", "").strip()
            import html, re, textwrap
            kwic_ex = html.escape(kwic_ex)
            
            # Wrap text BEFORE highlighting so we don't break HTML tags in half
            kwic_ex = "<br>".join(textwrap.wrap(kwic_ex, width=60))
            
            def highlight_word(text, word, color):
                if not word: return text
                pattern = re.compile(rf"\b({re.escape(word)})\b", flags=re.IGNORECASE)
                return pattern.sub(rf'<span style="color:{color}"><b>\1</b></span>', text)
                
            kwic_ex = highlight_word(kwic_ex, node_word, "#d32f2f")
            kwic_ex = highlight_word(kwic_ex, item['word'], "#1976d2")
            
        hover_texts.append(f"<span style='font-size: 14px;'><b>{item['word']}</b><br>Score: {item['score']:.2f}<br><br><i>{kwic_ex}</i></span>")
        
    fig.add_trace(go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        text=node_text,
        textposition="middle center",
        hoverinfo='text',
        hovertext=hover_texts,
        marker=dict(
            color=node_color,
            size=node_size,
            line=dict(width=1, color='black')
        ),
        textfont=dict(color='black', size=12)
    ))
    
    fig.update_layout(
        showlegend=False,
        hovermode='closest',
        margin=dict(b=0,l=0,r=0,t=0),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-1.1, 1.1]),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-1.1, 1.1]),
        plot_bgcolor="white",
        width=800 * chart_size,
        height=640 * chart_size
    )
    
    st.plotly_chart(fig, use_container_width=True)
