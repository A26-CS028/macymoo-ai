import hmac

from fastapi import Header, HTTPException, status

from .config import settings


def verify_secret(x_internal_secret: str | None = Header(default=None)) -> None:
    """Tolak permintaan tanpa header X-Internal-Secret yang benar."""
    if not x_internal_secret or not hmac.compare_digest(
        x_internal_secret, settings.internal_secret
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unauthorized")
