from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    internal_secret: str
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.1-flash-lite"
    gemini_fallback_model: str = ""  # opsional, dipakai kalau model utama gagal

    # Anggaran waktu MooBot (detik). Total untuk SEMUA model, bukan per model.
    moobot_total_timeout: float = 10.0
    # Batas untuk model utama; sisanya untuk model cadangan.
    moobot_primary_timeout: float = 6.0

    # Ruang token output. Dibuat longgar supaya mode thinking tidak menghabiskannya.
    gemini_max_output_tokens: int = 1024
    # Opsional: minimal | low | medium | high. Kosong = pakai bawaan model.
    gemini_thinking_level: str = ""


settings = Settings()
