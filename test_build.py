import sys
import os

from pipeline.online_corpus import build_online_corpus

keywords = ["jokowi", "ijazah", "roy", "suryo"]
params = {'keywords': keywords}

print("Running keyword search...")
files, warning = build_online_corpus("keyword", params, lambda p, msg: print(f"{p:.1f}: {msg}"))

print(f"Warning: {warning}")
if files:
    print(f"Files found: {len(files)}")
    for f in files:
        print(f" - {f['filename']} ({len(f['content'])} chars)")
else:
    print("No files returned.")
