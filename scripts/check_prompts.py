"""Uji pertanyaan jebakan dan di luar konteks MooBot ke server yang sedang jalan.

Pakai (dari root repo):
  python -m scripts.check_prompts http://localhost:8000
Secret dibaca dari env var INTERNAL_SECRET (atau file .env), bukan dari argumen,
supaya tidak tersimpan di riwayat terminal.

Kasus jenis 'tolak' dan 'luar_konteks' diperiksa otomatis lewat penanda
penolakan (CEK berarti jawabannya perlu dibaca manual). Kasus lain dinilai manual.
"""
import json
import pathlib
import sys
import time
import urllib.request

from app.config import settings
from scripts.prompt_cases import CASES, TANDA_TOLAK

if len(sys.argv) != 2:
    sys.exit("Pakai: python -m scripts.check_prompts <url_server>")

base, secret = sys.argv[1].rstrip("/"), settings.internal_secret
CONTEXT = (pathlib.Path(__file__).parent / "context.example.txt").read_text(encoding="utf-8")

error = 0
cek = 0
for q, expected, jenis in CASES:
    req = urllib.request.Request(
        f"{base}/v1/moobot/chat",
        data=json.dumps({"message": q, "context": CONTEXT}).encode(),
        headers={"Content-Type": "application/json", "X-Internal-Secret": secret},
    )
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            ans = json.loads(r.read())["reply"]
    except Exception as e:
        ans = f"[ERROR] {e}"
        error += 1
    waktu = time.monotonic() - t0

    status = ""
    if jenis in ("tolak", "luar_konteks") and not ans.startswith("[ERROR]"):
        ok = any(t in ans.lower() for t in TANDA_TOLAK)
        status = "OTOMATIS: OK" if ok else "OTOMATIS: CEK (tidak ada penanda penolakan)"
        cek += 0 if ok else 1
    print(f"[{jenis}] Q: {q}\n  harapan: {expected}\n  jawab  : {ans}\n  waktu  : {waktu:.1f}s  {status}\n")

n_tolak = sum(1 for c in CASES if c[2] in ("tolak", "luar_konteks"))
print(f"Ringkasan: {len(CASES)} kasus, {n_tolak} kasus tolak, ERROR={error}, perlu CEK={cek}")
sys.exit(1 if error or cek else 0)
