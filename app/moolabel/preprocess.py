import json
import re
import unicodedata
from pathlib import Path

# aturan lengkap ada di PREPROCESSING.md
PREP_VERSION = "prep-v1"

with open(Path(__file__).parent / "slang.json", encoding="utf-8") as f:
    slang = json.load(f)


def clean(text):
    text = unicodedata.normalize("NFKC", text or "")
    text = text.lower()
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    text = re.sub(r"([a-z])\1{2,}", r"\1", text)  # yaaa -> ya, maaf tetap
    words = [slang.get(w, w) for w in text.split()]
    return " ".join(words)
