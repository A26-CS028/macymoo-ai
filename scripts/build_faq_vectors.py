"""Buat ulang data/faq_vectors.json setiap kali faq_seed.json atau faq_variasi.json berubah.

Pakai (dari root repo, butuh GEMINI_API_KEY di env atau .env):
  python -m scripts.build_faq_vectors
"""
import sys

from app.config import settings
from app.moobot.rag import DATA_DIR, embed_sinkron, tulis_vektor

if not settings.gemini_api_key:
    sys.exit("GEMINI_API_KEY kosong")

n = tulis_vektor(DATA_DIR, lambda teks: embed_sinkron(teks, "RETRIEVAL_DOCUMENT"), settings.gemini_embed_model)
print(f"disimpan data/faq_vectors.json: {n} kalimat, model {settings.gemini_embed_model}")
