import gzip
import json
import secrets
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.config import Settings, get_settings

router = APIRouter()


@router.post("/upload_match")
async def upload_match(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    validate_authorization(request, settings.api_auth_key)

    body = await request.body()

    if request.headers.get("content-encoding", "").lower() == "gzip":
        try:
            body = gzip.decompress(body)
        except gzip.BadGzipFile as exc:
            raise HTTPException(status_code=400, detail="Invalid gzip payload.") from exc

    try:
        match_json = json.loads(body.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="Request body must be UTF-8 encoded.") from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.") from exc

    return {
        "success": True,
        "message": "Match JSON received.",
        "type": type(match_json).__name__,
    }

def validate_authorization(request: Request, expected_auth_key: str) -> None:
    if not expected_auth_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Upload auth key is not configured.",
        )

    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")

    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not secrets.compare_digest(token, expected_auth_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid bearer token.",
        )
