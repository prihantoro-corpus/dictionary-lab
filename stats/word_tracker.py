import math
import pandas as pd
from typing import Dict, List, Any, Optional
from pipeline.indexing import get_connection, safe_execute

CACHE_COLUMNS = ['id', 'token', 'tag', 'lemma', 'corpus', 'file_id', 'sentence_id', 'doc_id', 'sentence_num']

def get_available_time_attributes(where_clause="1=1", params=()) -> List[str]:
    """Returns list of metadata keys and token columns available for time tracking."""
    conn, is_shared = get_connection()
    try:
        query_meta = f"""
            SELECT DISTINCT unnest(json_keys(metadata)) as k 
            FROM tokens 
            WHERE metadata IS NOT NULL AND {where_clause}
        """
        res_meta = safe_execute(conn, query_meta, params).fetchall()
        meta_keys = [r[0] for r in res_meta if r[0]]
    except Exception:
        meta_keys = []
    finally:
        if not is_shared:
            conn.close()
            
    all_attrs = []
    time_candidates = ['year', 'date', 'month', 'time', 'period', 'decade', 'pub_year', 'year_published']
    
    for key in meta_keys:
        if key not in all_attrs:
            all_attrs.append(key)
            
    for col in ['corpus', 'doc_id', 'file_id']:
        if col not in all_attrs:
            all_attrs.append(col)
            
    def attr_priority(attr):
        attr_lower = attr.lower()
        if any(tc in attr_lower for tc in time_candidates):
            return (0, attr_lower)
        return (1, attr_lower)
        
    return sorted(all_attrs, key=attr_priority)

def calculate_word_volatility(token: str, time_attr: str, where_clause="1=1", params=(), pos_tag: Optional[str] = None) -> Dict[str, Any]:
    """
    Groups word occurrences by time_attr, computes time-series metrics (Frequency, PMW),
    and assigns a Volatility Label.
    """
    conn, is_shared = get_connection()
    try:
        if time_attr in CACHE_COLUMNS:
            time_expr = time_attr
        else:
            time_expr = f"json_extract_string(metadata, '$.{time_attr}')"
            
        # 1. Total tokens per time period
        query_totals = f"""
            SELECT {time_expr} as time_val, COUNT(*) as total_tokens
            FROM tokens
            WHERE {time_expr} IS NOT NULL AND {where_clause}
            GROUP BY time_val
            ORDER BY time_val
        """
        res_totals = safe_execute(conn, query_totals, params).fetchall()
        totals_map = {str(r[0]): r[1] for r in res_totals if r[0] is not None}
        
        if not totals_map:
            return {
                'success': False,
                'message': f"No data found for time attribute '{time_attr}'."
            }
            
        # 2. Token frequency per time period
        if pos_tag:
            query_token = f"""
                SELECT {time_expr} as time_val, COUNT(*) as word_count
                FROM tokens
                WHERE token ILIKE ? AND tag = ? AND {time_expr} IS NOT NULL AND {where_clause}
                GROUP BY time_val
            """
            token_params = (token, pos_tag, *params)
        else:
            query_token = f"""
                SELECT {time_expr} as time_val, COUNT(*) as word_count
                FROM tokens
                WHERE token ILIKE ? AND {time_expr} IS NOT NULL AND {where_clause}
                GROUP BY time_val
            """
            token_params = (token, *params)
            
        res_token = safe_execute(conn, query_token, token_params).fetchall()
        token_map = {str(r[0]): r[1] for r in res_token if r[0] is not None}
        
        # 3. Assemble time series dataframe
        time_series = []
        pmw_values = []
        
        for time_val in sorted(totals_map.keys()):
            total_count = totals_map[time_val]
            freq = token_map.get(time_val, 0)
            pmw = (freq / total_count * 1000000) if total_count > 0 else 0.0
            pmw_values.append(pmw)
            time_series.append({
                'time_period': time_val,
                'frequency': freq,
                'total_tokens': total_count,
                'pmw': round(pmw, 2)
            })
            
        # 4. Compute Statistical Volatility Metrics
        num_periods = len(pmw_values)
        if num_periods < 2:
            volatility_score = 0.0
            label = "⚪ Insufficient Time Bins"
            badge_color = "gray"
            description = "At least 2 distinct time periods are required to calculate volatility across time."
            std_dev = 0.0
            mean_pmw = 0.0
            cv_explanation = "CV (Coefficient of Variation) requires at least 2 distinct time periods."
            cv_tooltip = f"Volatility across {time_attr}: Insufficient data (at least 2 time periods required)."
        else:
            mean_pmw = sum(pmw_values) / num_periods
            variance = sum((x - mean_pmw) ** 2 for x in pmw_values) / num_periods
            std_dev = math.sqrt(variance)
            
            # Coefficient of Variation (CV = std_dev / mean)
            cv = (std_dev / mean_pmw) if mean_pmw > 0 else 0.0
            volatility_score = round(cv, 3)
            
            # Assign Volatility Label based on CV thresholds
            if cv >= 0.85:
                label = "🔴 Highly Volatile"
                badge_color = "red"
                description = f"High fluctuation across time periods (CV = {cv:.2f}). Usage spikes or drops significantly."
            elif cv >= 0.40:
                label = "🟡 Moderately Volatile"
                badge_color = "orange"
                description = f"Moderate variation across time periods (CV = {cv:.2f}). Usage changes noticeably across time."
            else:
                label = "🟢 Stable / Low Volatility"
                badge_color = "green"
                description = f"Consistent usage across time periods (CV = {cv:.2f}). Usage remains steady."

            cv_explanation = (
                f"CV Score = {cv:.3f} (StdDev {std_dev:.2f} / Mean {mean_pmw:.2f}). "
                "CV (Coefficient of Variation) measures relative frequency fluctuation across time."
            )
            cv_tooltip = (
                f"Volatility across {time_attr}: {description}&#10;&#10;"
                f"• What is CV Score?&#10;"
                f"CV (Coefficient of Variation) measures relative frequency volatility across time.&#10;&#10;"
                f"• How is CV counted?&#10;"
                f"CV = StdDev / Mean PMW ({std_dev:.2f} / {mean_pmw:.2f} = {cv:.3f}).&#10;&#10;"
                f"• Score Ranges:&#10;"
                f"  🟢 CV < 0.40 : Stable / Low Volatility&#10;"
                f"  🟡 0.40 <= CV < 0.85 : Moderately Volatile&#10;"
                f"  🔴 CV >= 0.85 : Highly Volatile"
            )
                
        df_series = pd.DataFrame(time_series)
        
        return {
            'success': True,
            'token': token,
            'time_attr': time_attr,
            'volatility_label': label,
            'volatility_score': volatility_score,
            'std_dev': round(std_dev, 2),
            'badge_color': badge_color,
            'description': description,
            'cv_explanation': cv_explanation,
            'cv_tooltip': cv_tooltip,
            'num_periods': num_periods,
            'mean_pmw': round(mean_pmw, 2) if num_periods >= 2 else 0.0,
            'max_pmw': round(max(pmw_values), 2) if pmw_values else 0.0,
            'min_pmw': round(min(pmw_values), 2) if pmw_values else 0.0,
            'time_series_df': df_series
        }
    finally:
        if not is_shared:
            conn.close()
