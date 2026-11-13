from fastapi import FastAPI

from .health import router as health_router
from .moobot.router import router as moobot_router

# from .moolabel.router import router as moolabel_router  # aktifkan setelah MooLabel siap

API_PREFIX = "/v1"  # sama dengan kontrak di docs/openapi.yaml

app = FastAPI(
    title="macymoo AI",
    docs_url=None,  # service internal, dokumentasi dimatikan
    redoc_url=None,
    openapi_url=None,
)
app.include_router(health_router, prefix=API_PREFIX)
app.include_router(moobot_router, prefix=API_PREFIX)
# app.include_router(moolabel_router, prefix=API_PREFIX)
