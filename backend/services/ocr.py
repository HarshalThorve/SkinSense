"""
OCR Service — Tesseract-based fallback for ingredient scanning.
"""
import os
import re
from flask import current_app


def get_tesseract():
    """Configure and return pytesseract module."""
    import pytesseract
    tesseract_cmd = current_app.config.get('TESSERACT_CMD', 'tesseract')
    if tesseract_cmd and tesseract_cmd != 'tesseract':
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    return pytesseract


def extract_text_from_image(image_path):
    """
    Extract text from an image using Tesseract OCR.
    Returns the raw text string, or empty string on failure.
    """
    try:
        pytesseract = get_tesseract()
        from PIL import Image
        raw_text = pytesseract.image_to_string(Image.open(image_path))
        return raw_text
    except Exception as e:
        print(f"OCR extraction failed: {e}")
        # If Tesseract is not installed, return empty string gracefully
        return ""


def parse_ingredients_from_text(raw_text):
    """
    Parse ingredient names from raw OCR text.
    Filters out marketing words, stop words, and short tokens.
    Returns a list of cleaned ingredient strings.
    """
    lower_text = raw_text.lower()

    # Extract ingredients section
    trigger_keywords = ["ingredients:", "ingredients :", "composition:", "contains:", "inci:"]
    ingredients_section = lower_text
    for tk in trigger_keywords:
        if tk in lower_text:
            ingredients_section = lower_text.split(tk, 1)[1]
            break

    # Filter out non-ingredient tokens
    raw_tokens = re.split(r'[,;\n•]+', ingredients_section)

    stop_words = {
        "juicy", "smooth", "clean", "bright", "deep", "light", "rich", "pure",
        "fresh", "gentle", "advanced", "natural", "new", "with", "for", "and",
        "the", "your", "skin", "providing", "underneath", "revealing", "surface",
        "chemistry", "tone", "spots", "glow", "formula", "complex", "technology",
        "system", "blend"
    }
    marketing_regex = re.compile(
        r'^(juicy|chemistry|surface|providing|underneath|brighter|revealing|smoother|'
        r'complex|formula|serum|cream|gel|lotion|toner|moisturizer|cleanser|scrub|mask|'
        r'essence|ampoule|treatment|solution|boost|care|repair|restore|renew|refresh|'
        r'hydrate|glow|radiance|luminous)$',
        re.IGNORECASE
    )

    filtered_tokens = []
    for t in raw_tokens:
        t = t.strip()
        if not t:
            continue
        if len(t) < 4:
            continue
        if re.match(r'^[\d.%]+$', t):
            continue
        if t in ["ml", "mg", "oz", "spf"]:
            continue

        words = t.split()
        if len(words) == 1:
            w = words[0]
            if w in stop_words or marketing_regex.match(w):
                continue

        filtered_tokens.append(t)

    return filtered_tokens
