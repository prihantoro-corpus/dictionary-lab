import streamlit as st
import duckdb
import os
import time

CORPORA_DIR = os.path.join(os.getcwd(), "corpora")

def _connect_with_retry(path, read_only=False, retries=5):
    """Internal helper to connect with retries for locked DB."""
    for i in range(retries):
        try:
            conn = duckdb.connect(path, read_only=read_only)
            # Ensure JSON extension is loaded
            try:
                conn.execute("INSTALL json; LOAD json;")
            except:
                pass
            return conn
        except Exception as e:
            if "used by another process" in str(e) and i < retries - 1:
                time.sleep(0.5 * (i + 1))
                continue
            raise e

def attach_corpora(conn, corpora_names):
    """
    Attaches multiple corpus .duckdb files to the given connection
    and builds a unified `tokens` view.
    """
    if not corpora_names:
        # Create an empty view so queries don't crash when no corpus is loaded
        conn.execute("""
            CREATE OR REPLACE VIEW tokens AS 
            SELECT CAST(NULL AS BIGINT) as id, 
                   CAST(NULL AS VARCHAR) as token, 
                   CAST(NULL AS VARCHAR) as tag, 
                   CAST(NULL AS VARCHAR) as lemma, 
                   CAST(NULL AS VARCHAR) as corpus, 
                   CAST(NULL AS JSON) as metadata, 
                   CAST(NULL AS VARCHAR) as file_id, 
                   CAST(NULL AS BIGINT) as sentence_id, 
                   CAST(NULL AS BIGINT) as doc_id, 
                   CAST(NULL AS BIGINT) as sentence_num 
            WHERE 1=0
        """)
        return

    union_queries = []
    
    # Detach any existing databases first (to allow hot-swapping)
    try:
        dbs = conn.execute("SELECT database_name FROM duckdb_databases() WHERE database_name NOT IN ('memory', 'system')").fetchall()
        for db in dbs:
            conn.execute(f"DETACH {db[0]}")
    except:
        pass

    for corpus in corpora_names:
        # Clean up corpus name to be a valid identifier
        safe_alias = corpus.replace('-', '_').replace(' ', '_').replace('.', '_')
        db_file = os.path.join(CORPORA_DIR, f"{corpus}.duckdb")
        if os.path.exists(db_file):
            try:
                # Attach the database in read-only mode for querying
                conn.execute(f"ATTACH '{db_file}' AS {safe_alias} (READ_ONLY)")
                union_queries.append(f'SELECT * FROM {safe_alias}.tokens')
            except Exception as e:
                print(f"Failed to attach {db_file}: {e}")

    if union_queries:
        # Create a unified view
        full_query = "CREATE OR REPLACE VIEW tokens AS " + " UNION ALL ".join(union_queries)
        conn.execute(full_query)
    else:
        # Empty fallback
        attach_corpora(conn, [])

def get_connection(read_only=False, allow_fallback=True):
    """
    Returns (conn, is_shared). 
    In Streamlit, maintains an in-memory DB connection in session state.
    """
    try:
        # Check if we are in a Streamlit context
        if 'duckdb_conn' not in st.session_state:
            try:
                # Use in-memory DB for the global connection
                st.session_state.duckdb_conn = duckdb.connect(':memory:')
                
                try:
                    st.session_state.duckdb_conn.execute("INSTALL json; LOAD json;")
                except:
                    pass
                
                # Attach currently loaded corpora
                loaded = st.session_state.get('loaded_corpora', [])
                attach_corpora(st.session_state.duckdb_conn, loaded)
                
            except Exception as e:
                raise e
            
            try:
                st.session_state.duckdb_conn.execute("SET preserve_insertion_order=false")
                st.session_state.duckdb_conn.execute("PRAGMA memory_limit='512MB'")
                st.session_state.duckdb_conn.execute("PRAGMA threads=1")
            except:
                pass
                
        return st.session_state.duckdb_conn, True
        
    except (st.errors.StreamlitAPIException, Exception):
        # Fallback for background scripts
        conn = duckdb.connect(':memory:')
        try:
            conn.execute("INSTALL json; LOAD json;")
        except:
            pass
        return conn, False

def safe_execute(conn, query, params=(), retries=3):
    """Executes query with retries for locked database and logs duration."""
    start_time = time.time()
    for i in range(retries):
        try:
            res = conn.execute(query, params)
            duration = time.time() - start_time
            if duration > 1.0: # Log slow queries (> 1s)
                 try:
                     with open("slow_queries.log", "a", encoding="utf-8") as f:
                         f.write(f"SLOW QUERY ({duration:.2f}s): {query[:200]}... PARAMS={params}\n")
                 except: pass
            return res
        except Exception as e:
            msg = str(e)
            if "used by another process" in msg or "TransactionContext Error" in msg:
                if i < retries - 1:
                    time.sleep(1 * (i + 1))
                    continue
            raise e

def init_db(conn=None):
    """Legacy init_db. Now handled individually by CorpusParser in ingest.py"""
    pass

def reset_db():
    """Legacy reset_db. Deletions handled in sidebar.py"""
    pass
