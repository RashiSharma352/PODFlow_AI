"""Advisory OCR checks. OCR is not a vision model and never auto-approves PODs."""
import re
from pathlib import Path

def inspect_image(path, expected_lr):
    text = ""
    available = False
    error = ""
    try:
        import pytesseract
        from PIL import Image, ImageOps, ImageEnhance, ImageFilter
        exe = Path(r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe")
        if exe.exists():
            pytesseract.pytesseract.tesseract_cmd = str(exe)
        with Image.open(path) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
            image.thumbnail((2200, 2200))
            gray = ImageOps.autocontrast(ImageOps.grayscale(image))
            gray = ImageEnhance.Contrast(gray).enhance(2)
            gray = gray.filter(ImageFilter.SHARPEN)
            results = [
                pytesseract.image_to_string(gray, lang="eng", config="--oem 3 --psm 6"),
                pytesseract.image_to_string(gray, lang="eng", config="--oem 3 --psm 11"),
            ]
            text = max(results, key=lambda value: len(value.strip()))
            text = re.sub(r"\\s+", " ", text).strip()
            available = True
    except Exception as exc:
        error = str(exc)

    lr_match = expected_lr.lower() in text.lower() if available and text and expected_lr else None
    date_match = bool(re.search(r"\\b(\\d{1,2}[/-]\\d{1,2}[/-]\\d{2,4}|\\d{4}-\\d{2}-\\d{2})\\b", text))
    quantity_match = bool(re.search(r"\\b(qty|quantity|cartons|bags|pieces|pcs|mt|tonnes?)\\b", text, re.I))
    flags = []
    if not available:
        flags.append("OCR unavailable — install Tesseract; manual review required")
    elif not text:
        flags.append("No readable text detected — retake or manual review")
    elif lr_match is False:
        flags.append("Expected LR number not found in OCR text")
    if not date_match:
        flags.append("Delivery date not confidently detected")
    if not quantity_match:
        flags.append("Quantity not confidently detected")
    flags.append("Human must visually confirm consignee stamp, signature, shortage/damage remarks and document date")
    return {
        "extracted_text": text[:3000], "ocr_available": available,
        "lr_match": lr_match, "date_detected": date_match,
        "quantity_keyword_detected": quantity_match,
        "confidence": "low" if not available or not text or lr_match is False else "medium",
        "status": "Needs review", "flags": flags,
        "message": "POD received. Human review is required before billing.",
        "ocr_error": error[:300] if error else ""
    }
