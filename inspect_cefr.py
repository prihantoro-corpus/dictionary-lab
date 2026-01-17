import cefrpy
print(f"Directory of cefrpy: {dir(cefrpy)}")
try:
    from cefrpy import CEFRAnalyzer
    print("Successfully imported CEFRAnalyzer")
    analyzer = CEFRAnalyzer()
    print(f"Analyzer methods: {[m for m in dir(analyzer) if not m.startswith('_')]}")
    # Try a sample lookup
    # Usually these analyzers have a get_level or similar
    # Let's try guess
except Exception as e:
    print(f"Error: {e}")
