from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}  # sengaja tanpa secret dan tanpa info sensitif
