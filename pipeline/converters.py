"""
Converts uploaded corpus files to plain text before ingestion.

Supported uploads:
    .txt / .xml / .vert / .vrt  -> decoded to UTF-8 (BOM / UTF-8 / Windows-1252 detection),
                                   content untouched so vertical format and XML tags still work
    .docx                       -> paragraph + table text (python-docx)
    .pdf                        -> page text with line-wrap reflow (pypdf); no OCR

Usage:
    result = convert_upload("laporan.pdf", data_bytes)
    result.text, result.warnings, result.plain_text, result.out_ext
"""
import codecs
import io
import os
import re
import shutil
import tempfile
from dataclasses import dataclass, field

TEXT_TYPES = ['txt', 'xml', 'vert', 'vrt']
DOCUMENT_TYPES = ['docx', 'pdf']
SUPPORTED_UPLOAD_TYPES = TEXT_TYPES + DOCUMENT_TYPES


class ConversionError(Exception):
    """Raised with a user-friendly message when a file cannot be converted."""


@dataclass
class ConversionResult:
    text: str
    out_ext: str                  # extension to use for the converted temp file
    plain_text: bool              # True for DOCX/PDF: never parse '<...>' as metadata tags
    warnings: list = field(default_factory=list)


# --------------------------------------------------------------------------- TXT
def _decode_text(data: bytes, filename: str):
    warnings = []
    if data.startswith(codecs.BOM_UTF8):
        return data[len(codecs.BOM_UTF8):].decode('utf-8', errors='replace'), warnings
    if data.startswith(codecs.BOM_UTF16_LE) or data.startswith(codecs.BOM_UTF16_BE):
        return data.decode('utf-16', errors='replace'), warnings
    if b'\x00' in data[:4096]:
        raise ConversionError(
            f"'{filename}' does not look like a text file. "
            "Supported formats: TXT, XML, VRT, DOCX, PDF."
        )
    try:
        return data.decode('utf-8'), warnings
    except UnicodeDecodeError:
        warnings.append(f"'{filename}' is not UTF-8; it was read as Windows-1252 (ANSI).")
        return data.decode('cp1252', errors='replace'), warnings


# -------------------------------------------------------------------------- DOCX
def _clean_inline(s: str) -> str:
    """Tabs would make the ingester think the file is in vertical format."""
    return re.sub(r'[ \t\u00a0]+', ' ', s).strip()


def _docx_to_text(data: bytes, filename: str):
    try:
        from docx import Document
    except ImportError:
        raise ConversionError("DOCX support is not installed on the server (python-docx).")
    if not data.startswith(b'PK'):
        raise ConversionError(
            f"'{filename}' is not a valid .docx file. If it is an old Word 97-2003 (.doc) "
            "document, open it in Word and use Save As → .docx."
        )
    try:
        doc = Document(io.BytesIO(data))
    except Exception as e:
        raise ConversionError(f"Could not read '{filename}' as DOCX ({e}).")

    from docx.table import Table
    from docx.text.paragraph import Paragraph

    blocks = []
    body = doc.element.body
    for child in body.iterchildren():
        tag = child.tag.rsplit('}', 1)[-1]
        if tag == 'p':
            txt = _clean_inline(Paragraph(child, doc).text)
            if txt:
                blocks.append(txt)
        elif tag == 'tbl':
            for row in Table(child, doc).rows:
                cells, seen = [], set()
                for cell in row.cells:
                    if id(cell._tc) in seen:   # merged cells repeat the same element
                        continue
                    seen.add(id(cell._tc))
                    ct = _clean_inline(cell.text.replace('\n', ' '))
                    if ct:
                        cells.append(ct)
                if cells:
                    blocks.append(' ; '.join(cells))

    if not blocks:
        raise ConversionError(f"'{filename}' contains no text.")
    # Blank line between paragraphs = paragraph/sentence boundary for the ingester
    return '\n\n'.join(blocks), []


# --------------------------------------------------------------------------- PDF
_SENT_END = re.compile(r'[.!?:;"”’)\]]$')
_BULLET = re.compile(r'^([•▪◦\-–—*]|\d+[.)]|[a-zA-Z][.)])\s')


def _join_hyphenated(prev: str, nxt: str) -> str:
    """Join a word split across lines with a hyphen.
    Keeps the hyphen for reduplication (anak-anak, sehari-hari, kupu-kupu), drops it otherwise."""
    m1 = re.search(r'(\w+)-$', prev)
    m2 = re.match(r'(\w+)', nxt)
    if m1 and m2:
        a, b = m1.group(1).lower(), m2.group(1).lower()
        if a == b or a.endswith(b) or b.startswith(a):
            return prev + nxt
        return prev[:-1] + nxt
    return prev + nxt


def _reflow_page(text: str) -> list:
    """Turns PDF visual lines into paragraphs (list of strings)."""
    paragraphs, current = [], ''
    for raw in text.splitlines():
        line = _clean_inline(raw)
        if not line:
            if current:
                paragraphs.append(current)
                current = ''
            continue
        if not current:
            current = line
            continue
        starts_new = bool(_BULLET.match(line)) or (
            _SENT_END.search(current) and (line[0].isupper() or line[0].isdigit())
            and len(current) < 60  # short line ending a sentence = likely paragraph end
        )
        if starts_new:
            paragraphs.append(current)
            current = line
        elif current.endswith('-') and line[:1].islower():
            current = _join_hyphenated(current, line)
        else:
            current = current + ' ' + line
    if current:
        paragraphs.append(current)
    return paragraphs


def _pdf_to_text(data: bytes, filename: str):
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ConversionError("PDF support is not installed on the server (pypdf).")
    if not data.lstrip()[:5].startswith(b'%PDF'):
        raise ConversionError(f"'{filename}' is not a valid PDF file.")
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            try:
                ok = reader.decrypt('')
            except Exception:
                ok = 0
            if not ok:
                raise ConversionError(f"'{filename}' is password-protected. Remove the password and upload again.")
        pages = list(reader.pages)
    except ConversionError:
        raise
    except Exception as e:
        raise ConversionError(f"Could not read '{filename}' as PDF ({e}).")

    warnings, paragraphs, empty_pages = [], [], []
    for i, page in enumerate(pages, 1):
        try:
            page_text = page.extract_text() or ''
        except Exception:
            page_text = ''
        if not page_text.strip():
            empty_pages.append(i)
            continue
        paragraphs.extend(_reflow_page(page_text))

    if not paragraphs:
        raise ConversionError(
            f"'{filename}' has no selectable text — it looks like a scanned PDF (images only). "
            "Run OCR on it first (e.g. in Adobe Acrobat, or by uploading it to Google Drive and "
            "opening it with Google Docs), then upload the result."
        )
    if empty_pages:
        shown = ', '.join(map(str, empty_pages[:10])) + (' …' if len(empty_pages) > 10 else '')
        warnings.append(
            f"'{filename}': {len(empty_pages)} of {len(pages)} page(s) had no selectable text "
            f"(scanned/image pages were skipped): {shown}"
        )
    return '\n\n'.join(paragraphs), warnings


# ------------------------------------------------------------------------ public
def convert_upload(filename: str, data: bytes) -> ConversionResult:
    """Converts an uploaded file to text. Raises ConversionError with a readable message."""
    ext = os.path.splitext(filename)[1].lower().lstrip('.')
    if not data:
        raise ConversionError(f"'{filename}' is empty.")
    if ext == 'docx':
        text, warnings = _docx_to_text(data, filename)
        return ConversionResult(text, '.txt', True, warnings)
    if ext == 'pdf':
        text, warnings = _pdf_to_text(data, filename)
        return ConversionResult(text, '.txt', True, warnings)
    if ext == 'doc':
        raise ConversionError(
            f"'{filename}' is an old Word 97-2003 (.doc) file. Open it in Word and use Save As → .docx."
        )
    if ext in TEXT_TYPES or ext == '':
        text, warnings = _decode_text(data, filename)
        return ConversionResult(text, f".{ext}" if ext else '.txt', False, warnings)
    raise ConversionError(
        f"'{filename}': .{ext} files are not supported. Supported formats: TXT, XML, VRT, DOCX, PDF."
    )


def safe_corpus_name(name: str, fallback: str = 'uploaded_corpus') -> str:
    """Makes a corpus name safe to use as a .duckdb filename."""
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', '_', str(name or '')).strip(' ._')
    return name or fallback


class ConvertedFile:
    """Context manager: writes the converted text to a temp file that keeps the original
    file name (so the 'attribute' metadata shows e.g. 'laporan' instead of 'tmpab12cd')."""

    def __init__(self, filename: str, data: bytes):
        self.filename = filename
        self.result = convert_upload(filename, data)
        self._dir = None
        self.path = None

    def __enter__(self):
        self._dir = tempfile.mkdtemp(prefix='upload_')
        stem = safe_corpus_name(os.path.splitext(os.path.basename(self.filename))[0], 'document')
        self.path = os.path.join(self._dir, stem + self.result.out_ext)
        with open(self.path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(self.result.text)
        return self

    def __exit__(self, *exc):
        if self._dir:
            shutil.rmtree(self._dir, ignore_errors=True)
        return False
