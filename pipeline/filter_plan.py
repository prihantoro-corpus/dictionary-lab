import re

def parse_collocate_filter(filter_str, alias="t2"):
    """
    Parses a user input string like "car*, _JJ, -NN" into SQL conditions.
    Returns: (list of include clauses, list of exclude clauses, params)
    """
    if not filter_str: return [], [], []
    
    parts = [p.strip() for p in filter_str.split(',')]
    includes = []
    excludes = []
    params = []
    
    for p in parts:
        if not p: continue
        
        # POS Tag Inclusion (_JJ)
        if p.startswith('_'):
            tag = p[1:]
            includes.append(f"{alias}.tag = ?")
            params.append(tag)
            
        # POS Tag Exclusion (-JJ)
        elif p.startswith('-'):
            tag = p[1:]
            excludes.append(f"{alias}.tag = ?")
            params.append(tag)
            
        # Wildcards (car*)
        elif '*' in p:
            pattern = p.replace('*', '%')
            includes.append(f"{alias}.token ILIKE ?")
            params.append(pattern)
            
        # Regex or complex groups ((a|b))
        elif '(' in p and ')' in p:
             includes.append(f"regexp_matches({alias}.token, ?)")
             params.append(p)
             
        # Exact match
        else:
            includes.append(f"{alias}.token = ?")
            params.append(p)
            
    return includes, excludes, params

def build_filter_sql(includes, excludes):
    clauses = []
    # Inclusions are usually OR logic (either match "car*" OR match "_JJ")
    # UNLESS user wants intersection? 
    # Usually "car*, _JJ" means "tokens that are car* OR tokens that are JJ".
    # User example: "'of'" hide others. "'(of|in)': show if in list".
    # So inclusions act as a WHICHEVER matches whitelist.
    
    if includes:
        or_clause = " OR ".join(includes)
        clauses.append(f"({or_clause})")
        
    # Exclusions are AND NOT (must not be -JJ AND must not be -NN)
    if excludes:
        for ex in excludes:
            clauses.append(f"NOT ({ex})")
            
    return " AND ".join(clauses) if clauses else ""
