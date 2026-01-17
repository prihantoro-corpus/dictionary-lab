try:
    from cefrpy import CEFR
    c = CEFR()
    print(f"Level for 'apple': {c.level('apple')}")
    print(f"Level for 'research': {c.level('research')}")
except Exception as e:
    print(f"Error: {e}")
