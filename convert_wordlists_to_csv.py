
import os
import csv
import re
from pypdf import PdfReader
from docx import Document

BASE_DIR = "wordlist"

def convert_gsl():
    pdf_path = os.path.join(BASE_DIR, "general-service-list-headwords.pdf")
    csv_path = os.path.join(BASE_DIR, "gsl_converted.csv")
    
    if not os.path.exists(pdf_path):
        print(f"Skipping GSL: {pdf_path} not found")
        return

    print("Converting GSL PDF...")
    reader = PdfReader(pdf_path)
    words = []
    
    for page in reader.pages:
        text = page.extract_text()
        # GSL PDF usually has simple list of words
        # Split by whitespace
        tokens = text.split()
        for t in tokens:
            # Clean
            clean_t = re.sub(r'[^a-zA-Z\-\']', '', t).lower()
            if clean_t and len(clean_t) > 1:
                words.append(clean_t)
    
    # Remove duplicates but keep order? Or set? GSL is a list.
    # Let's keep unique
    unique_words = []
    seen = set()
    for w in words:
        if w not in seen:
            unique_words.append(w)
            seen.add(w)
            
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Headword', 'In_GSL'])
        for w in unique_words:
            writer.writerow([w, 'Yes'])
            
    print(f"Saved {csv_path} with {len(unique_words)} entries.")

def convert_awl():
    docx_path = os.path.join(BASE_DIR, "Headwords-of-the-Academic-Word-List.docx")
    csv_path = os.path.join(BASE_DIR, "awl_converted.csv")
    
    if not os.path.exists(docx_path):
        print(f"Skipping AWL: {docx_path} not found")
        return

    print("Converting AWL DOCX...")
    data = []
    doc = Document(docx_path)
    for para in doc.paragraphs:
        txt = para.text.strip()
        if not txt: continue
        # Match "word   number"
        m = re.search(r'([a-zA-Z\-]+)\s+(\d+)', txt)
        if m:
            data.append([m.group(1).lower(), m.group(2)])
        else:
             # Try simple word
             clean_t = re.sub(r'[^a-zA-Z\-\']', '', txt).lower()
             if clean_t: data.append([clean_t, 'Unknown'])

    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Headword', 'Sublist'])
        writer.writerows(data)
    
    print(f"Saved {csv_path} with {len(data)} entries.")

if __name__ == "__main__":
    convert_gsl()
    convert_awl()
