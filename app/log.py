"""Logger aplikasi.

Di Vercel, FastAPI tidak dijalankan lewat CLI uvicorn, jadi logger "uvicorn.error"
tidak punya handler dan pesan INFO (mis. jalur RAG) hilang. Logger "macymoo" punya
handler sendiri ke stderr, sehingga log tampil sama di lokal dan di Vercel Runtime Logs.
"""
import logging

_root = logging.getLogger("macymoo")
if not _root.handlers:
    _handler = logging.StreamHandler()  # stderr
    _handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    _root.addHandler(_handler)
_root.setLevel(logging.INFO)
_root.propagate = False  # jangan tercetak dua kali bila root logger juga punya handler


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"macymoo.{name}")
