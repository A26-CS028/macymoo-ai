from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # minimal 32 karakter supaya tidak bisa ditebak; app gagal start kalau lebih pendek
    internal_secret: str = Field(min_length=32)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.1-flash-lite"
    gemini_fallback_model: str = ""  # opsional, dipakai kalau model utama gagal

    # Anggaran waktu MooBot (detik). Total untuk SEMUA model, bukan per model.
    moobot_total_timeout: float = 10.0
    # Batas untuk model utama; sisanya untuk model cadangan.
    moobot_primary_timeout: float = 6.0

    # Ruang token output. Dibuat longgar supaya mode thinking tidak menghabiskannya.
    gemini_max_output_tokens: int = 1024
    # Kosong = pakai bawaan model. Nilai salah ditolak saat start.
    gemini_thinking_level: Literal["", "minimal", "low", "medium", "high"] = ""

    # RAG MooBot: FAQ terkait yang ditempel ke prompt
    rag_top_k: int = 3
    rag_min_skor_tfidf: float = 0.43  # dipilih scripts.eval_rag
    rag_min_skor_embed: float = 0.72  # dipilih scripts.eval_rag --embed
    # model embedding harus sama dengan yang dipakai saat build data/faq_vectors.json
    gemini_embed_model: str = "gemini-embedding-001"
    moobot_embed_timeout: float = 1.5

    # MooLabel: path relatif dibaca dari root repo; file dimuat hanya jika sha256-nya sama
    moolabel_model_path: str = "models/moolabel-v2.joblib"
    moolabel_model_sha256: str = "d3e13781abadbeeca35451fa952586cbc24b923f2b947ba53176d1d8b4b3cefb"


settings = Settings()
