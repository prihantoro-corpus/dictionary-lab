from cefrpy import CEFRAnalyzer
analyzer = CEFRAnalyzer()
print(f"Apple: {analyzer.get_pos_level_dict_for_word('apple')}")
print(f"Research: {analyzer.get_pos_level_dict_for_word('research')}")
