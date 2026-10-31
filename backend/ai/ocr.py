"""
DukaanSaathi AI — Bill / Invoice OCR pipeline.

Supports:
  * Images  (JPG / PNG / WEBP / BMP / TIFF)  -> RapidOCR (ONNX, fully local)
  * PDFs    (digital text layer first, then rendered pages through OCR)

The parser groups OCR words into visual rows, then detects the trailing numeric
columns of Indian wholesale invoices (quantity, rate, amount) and returns
normalised line items:

    {
      "items": [{"product_name": "Parle-G 100g", "quantity": 50.0,
                 "cost_price": 8.5, "amount": 425.0, "unit": "pcs",
                 "confidence": 0.91}],
      "raw_text": "...",
      "engine": "rapidocr" | "pdf-text" | "none",
      "confidence": 0.88,
      "pages": 1,
      "warnings": [...]
    }
"""
from __future__ import annotations

import io
import re
import logging
from statistics import median

logger = logging.getLogger(__name__)

MAX_PDF_PAGES = 5
PDF_RENDER_ZOOM = 2.2  # ~158 DPI, good balance of accuracy/speed

_NUM_RE = re.compile(r"^[₹Rs.\s]*([0-9][0-9,]*\.?[0-9]*)$")
_UNIT_RE = re.compile(
    r"\b(kg|kgs|gm|gms|g|gram|grams|ltr|ltrs|litre|liter|litres|ml|pcs|pc|"
    r"pack|pkt|packet|box|dozen|dz|bag|bori|tin|jar|bottle|roll|tray)\b",
    re.IGNORECASE,
)

SKIP_KEYWORDS = (
    "total", "subtotal", "sub total", "grand total", "net total", "amount payable",
    "balance", "gst", "gstin", "tax", "sgst", "cgst", "igst", "hsn", "cess",
    "bill no", "billno", "invoice", "inv no", "date", "time", "phone", "mobile",
    "tel", "address", "email", "gmail", "www", "thank", "thanks", "cash", "change",
    "upi", "paytm", "card", "discount", "round off", "roundoff", "qty", "rate",
    "amount", "item", "description", "particulars", "sr", "s.no", "sno", "terms",
    "authorised", "signature", "customer", "voucher", "delivery", "order no",
    "licence", "license", "bank", "ifsc", "account", "e.&.o.e", "declaration",
)

_OCR = None
_OCR_FAILED = False


def _get_ocr():
    """Lazily create the RapidOCR engine (loads ONNX models once)."""
    global _OCR, _OCR_FAILED
    if _OCR is not None:
        return _OCR
    if _OCR_FAILED:
        return None
    try:
        from rapidocr_onnxruntime import RapidOCR  # type: ignore

        _OCR = RapidOCR()
        return _OCR
    except Exception as exc:  # pragma: no cover - environment dependent
        _OCR_FAILED = True
        logger.warning("RapidOCR unavailable: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Image handling
# ---------------------------------------------------------------------------

def _image_to_array(data: bytes):
    from PIL import Image, ImageOps
    import numpy as np

    image = Image.open(io.BytesIO(data))
    if getattr(image, "n_frames", 1) > 1:  # animated webp / multi-page tiff
        image.seek(0)
    image = image.convert("RGB")
    # Upscale small phone photos for better small-text recognition
    width, height = image.size
    if max(width, height) < 1400:
        scale = 1400 / max(width, height)
        image = image.resize((int(width * scale), int(height * scale)), Image.LANCZOS)
    image = ImageOps.exif_transpose(image)
    return np.asarray(image)


def _ocr_array(array) -> list[tuple[str, float, tuple[float, float]]]:
    """Run OCR and return (text, confidence, (y_center, x_left)) triples."""
    engine = _get_ocr()
    if engine is None:
        return []
    try:
        result, _elapsed = engine(array)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("OCR inference failed: %s", exc)
        return []
    if not result:
        return []
    words = []
    for entry in result:
        try:
            box, text, score = entry[0], entry[1], entry[2]
            xs = [float(p[0]) for p in box]
            ys = [float(p[1]) for p in box]
            words.append((str(text), float(score), (sum(ys) / len(ys), min(xs))))
        except Exception:
            continue
    return words


def _group_rows(words, y_tolerance: float | None = None) -> list[str]:
    """Merge words that share a visual line into single text rows."""
    if not words:
        return []
    # Estimate line height from the vertical spread of word centres
    ys = sorted(w[2][0] for w in words)
    gaps = [b - a for a, b in zip(ys, ys[1:]) if b - a > 1]
    tolerance = y_tolerance or (median(gaps) * 0.6 if gaps else 12.0)
    tolerance = max(6.0, min(tolerance, 28.0))

    ordered = sorted(words, key=lambda w: (w[2][0], w[2][1]))
    rows: list[list[tuple[float, float, str]]] = []
    for text, _score, (y, x) in ordered:
        placed = False
        for row in rows:
            if abs(row[0][0] - y) <= tolerance:
                row.append((y, x, text))
                placed = True
                break
        if not placed:
            rows.append([(y, x, text)])

    lines = []
    for row in rows:
        row.sort(key=lambda item: item[1])  # left-to-right within the line
        text = " ".join(part[2] for part in row).strip()
        if text:
            lines.append(text)
    return lines


# ---------------------------------------------------------------------------
# Text parsing
# ---------------------------------------------------------------------------

def _is_number(token: str) -> bool:
    return bool(_NUM_RE.match(token.strip()))


def _to_float(token: str) -> float | None:
    match = _NUM_RE.match(token.strip())
    if not match:
        return None
    raw = match.group(1).replace(",", "")
    if raw.count(".") > 1:
        # e.g. "1.250.00" seen from noisy OCR
        head, tail = raw.rsplit(".", 1)
        raw = head.replace(".", "") + "." + tail
    try:
        return float(raw)
    except ValueError:
        return None


def _looks_like_header(line: str) -> bool:
    lowered = line.lower()
    if any(keyword in lowered for keyword in SKIP_KEYWORDS):
        return True
    # Rows that are mostly digits/symbols are not product names
    letters = sum(ch.isalpha() for ch in line)
    return letters < 2


def _clean_name(name: str) -> str:
    name = re.sub(r"^[\s\-–—*•.]+", "", name)
    name = re.sub(r"\s+", " ", name)
    name = re.sub(r"\s*[*|]+\s*$", "", name)
    return name.strip(" :;-—–")


def _extract_unit(name: str) -> str:
    found = _UNIT_RE.search(name)
    if not found:
        return "pcs"
    unit = found.group(1).lower()
    mapping = {
        "kgs": "kg", "gms": "g", "gm": "g", "gram": "g", "grams": "g",
        "ltr": "l", "ltrs": "l", "litre": "l", "liter": "l", "litres": "l",
        "pc": "pcs", "packet": "pack", "pkt": "pack", "dz": "dozen",
    }
    return mapping.get(unit, unit)


def _parse_item_line(line: str) -> dict | None:
    tokens = line.replace("\t", " ").split()
    if len(tokens) < 2:
        return None

    trailing: list[float] = []
    while tokens and _is_number(tokens[-1]) and len(trailing) < 4:
        value = _to_float(tokens.pop())
        if value is None:
            break
        trailing.insert(0, value)

    if not trailing:
        return None

    name = _clean_name(" ".join(tokens))
    if len(name) < 2 or sum(ch.isalpha() for ch in name) < 2:
        return None
    if _looks_like_header(line) or _looks_like_header(name):
        return None

    qty = 1.0
    rate = None
    amount = None

    if len(trailing) >= 3:
        q, r, a = trailing[-3], trailing[-2], trailing[-1]
        # Prefer qty * rate == amount, otherwise treat the middle number as rate
        if q > 0 and a > 0 and r > 0 and abs(q * r - a) <= max(1.0, a * 0.08):
            qty, rate, amount = q, r, a
        elif a > 0:
            qty, rate, amount = (q if q > 0 else 1.0), r, a
    elif len(trailing) == 2:
        first, second = trailing
        if first > 0 and float(first).is_integer() and second > 0 and second >= first:
            qty, amount = first, second
            rate = amount / qty if qty else amount
        else:
            rate, amount = first, second
            qty = 1.0
    else:
        amount = trailing[0]
        rate = amount
        qty = 1.0

    if amount is None and rate is not None and qty:
        amount = rate * qty
    if amount is None or amount <= 0:
        return None
    if qty <= 0 or qty > 100000:
        return None
    if rate is not None and rate < 0:
        rate = None
    if rate is None and amount:
        rate = amount / qty if qty else amount

    return {
        "product_name": name[:120],
        "quantity": round(float(qty), 3),
        "cost_price": round(float(rate), 2) if rate else round(float(amount), 2),
        "amount": round(float(amount), 2),
        "unit": _extract_unit(name),
    }


def _dedupe(items: list[dict]) -> list[dict]:
    seen = set()
    output = []
    for item in items:
        key = (item["product_name"].lower(), round(item["amount"], 2))
        if key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output


def parse_bill_text(text: str) -> list[dict]:
    """Parse OCR / PDF text into normalised line items."""
    items = []
    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if len(line) < 4:
            continue
        item = _parse_item_line(line)
        if item:
            items.append(item)
    return _dedupe(items)


def _meaningful_text(text: str) -> bool:
    """True when a PDF text layer contains enough real content to parse."""
    cleaned = (text or "").strip()
    if len(cleaned) < 40:
        return False
    letters = sum(ch.isalpha() for ch in cleaned)
    return letters >= 25 and cleaned.count("\n") >= 2


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _is_pdf(data: bytes, filename: str | None, content_type: str | None) -> bool:
    if data[:5] == b"%PDF-":
        return True
    if (content_type or "").lower().startswith("application/pdf"):
        return True
    return bool(filename and filename.lower().endswith(".pdf"))


def extract_pdf(data: bytes) -> dict:
    """Extract text (and fall back to OCR) from every page of a PDF."""
    warnings: list[str] = []
    try:
        import fitz  # PyMuPDF
    except Exception as exc:  # pragma: no cover
        return {
            "items": [], "raw_text": "", "engine": "none", "confidence": 0.0,
            "pages": 0, "warnings": [f"PDF support unavailable: {exc}"],
        }

    try:
        document = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        return {
            "items": [], "raw_text": "", "engine": "none", "confidence": 0.0,
            "pages": 0, "warnings": [f"Could not open PDF: {exc}"],
        }

    page_count = len(document)
    pages = document[:MAX_PDF_PAGES]
    text_parts: list[str] = []
    ocr_lines: list[str] = []
    scores: list[float] = []
    used_ocr = False

    for page_index, page in enumerate(pages):
        page_text = page.get_text("text") or ""
        if _meaningful_text(page_text):
            text_parts.append(page_text)
            continue

        used_ocr = True
        try:
            pixmap = page.get_pixmap(matrix=fitz.Matrix(PDF_RENDER_ZOOM, PDF_RENDER_ZOOM))
            png_bytes = pixmap.tobytes("png")
            array = _image_to_array(png_bytes)
            words = _ocr_array(array)
            if not words:
                warnings.append(f"Page {page_index + 1}: no readable text found.")
                continue
            scores.extend(w[1] for w in words)
            ocr_lines.extend(_group_rows(words))
        except Exception as exc:  # pragma: no cover
            warnings.append(f"Page {page_index + 1}: OCR failed ({exc}).")

    if page_count > MAX_PDF_PAGES:
        warnings.append(
            f"Only the first {MAX_PDF_PAGES} pages were processed "
            f"(PDF has {page_count})."
        )

    raw_text = "\n".join(part.strip() for part in text_parts).strip()
    if ocr_lines:
        raw_text = (raw_text + "\n" if raw_text else "") + "\n".join(ocr_lines)

    engine = "pdf-text+rapidocr" if (text_parts and used_ocr) else (
        "rapidocr" if used_ocr else ("pdf-text" if text_parts else "none")
    )
    confidence = round(sum(scores) / len(scores), 3) if scores else (0.95 if text_parts else 0.0)

    document.close()
    items = parse_bill_text(raw_text)
    if not items and raw_text:
        warnings.append("Text was read but no line items could be recognised. "
                        "You can add the items manually.")

    return {
        "items": items,
        "raw_text": raw_text[:20000],
        "engine": engine,
        "confidence": confidence,
        "pages": page_count,
        "warnings": warnings,
    }


def extract_image(data: bytes) -> dict:
    warnings: list[str] = []
    try:
        array = _image_to_array(data)
    except Exception as exc:
        return {
            "items": [], "raw_text": "", "engine": "none", "confidence": 0.0,
            "pages": 1, "warnings": [f"Could not read image: {exc}"],
        }

    words = _ocr_array(array)
    if not words:
        return {
            "items": [], "raw_text": "", "engine": "none", "confidence": 0.0,
            "pages": 1,
            "warnings": ["No text could be detected in this image. "
                         "Try a sharper, well-lit photo."],
        }

    lines = _group_rows(words)
    raw_text = "\n".join(lines)
    items = parse_bill_text(raw_text)
    confidence = round(sum(w[1] for w in words) / len(words), 3)
    if not items:
        warnings.append("Text was read but no line items could be recognised. "
                        "You can add the items manually.")

    return {
        "items": items,
        "raw_text": raw_text[:20000],
        "engine": "rapidocr",
        "confidence": confidence,
        "pages": 1,
        "warnings": warnings,
    }


def extract_bill(
    data: bytes,
    filename: str | None = None,
    content_type: str | None = None,
) -> dict:
    """Main entry point: extract line items from an uploaded bill."""
    if not data:
        return {
            "items": [], "raw_text": "", "engine": "none", "confidence": 0.0,
            "pages": 0, "warnings": ["Empty file."],
        }
    if _is_pdf(data, filename, content_type):
        return extract_pdf(data)
    return extract_image(data)
