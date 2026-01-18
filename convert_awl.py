
from docx import Document
import csv
import re
import os

def convert_awl():
    docx_path = os.path.join("wordlist", "Headwords-of-the-Academic-Word-List.docx")
    csv_path = os.path.join("wordlist", "awl_converted.csv")
    
    if not os.path.exists(docx_path):
        print("DOCX not found")
        return

    data = []
    doc = Document(docx_path)
    for para in doc.paragraphs:
        txt = para.text.strip()
        if not txt: continue
        m = re.search(r'([a-zA-Z\-]+)\s+(\d+)', txt)
        if m:
            data.append([m.group(1).lower(), m.group(2)])
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Headword', 'Sublist'])
        writer.writerows(data)
    
    print(f"Created {csv_path} with {len(data)} entries.")

if __name__ == "__main__":
    convert_awl()
