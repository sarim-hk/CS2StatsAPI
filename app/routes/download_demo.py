import base64
import urllib.error
import urllib.parse
import urllib.request

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.config import Settings, get_settings
from app.database import fetch_match_by_id, get_db


router = APIRouter()

DEMO_DIRECTORY = "CS2Stats"
DOWNLOAD_CHUNK_SIZE = 64 * 1024


def _demo_filename(match_name: object) -> str:
    """Return a single safe file name sourced from the database."""
    if not isinstance(match_name, str) or not match_name:
        raise HTTPException(status_code=404, detail="Demo is not available for this match.")

    if "\x00" in match_name or "/" in match_name or "\\" in match_name or match_name in {".", ".."}:
        raise HTTPException(status_code=500, detail="Match has an invalid demo filename.")

    return f"{match_name}.dem"


def _dathost_download_url(server_id: str, filename: str) -> str:
    encoded_server_id = urllib.parse.quote(server_id, safe="")
    encoded_path = urllib.parse.quote(f"{DEMO_DIRECTORY}/{filename}", safe="/")
    return f"https://dathost.com/api/0.1/game-servers/{encoded_server_id}/files/{encoded_path}"


def _open_dathost_demo(settings: Settings, filename: str):
    if not all((settings.dathost_email, settings.dathost_password, settings.dathost_server_id)):
        raise HTTPException(status_code=500, detail="DatHost demo downloads are not configured.")

    credentials = f"{settings.dathost_email}:{settings.dathost_password}".encode("utf-8")
    authorization = base64.b64encode(credentials).decode("ascii")
    request = urllib.request.Request(
        _dathost_download_url(settings.dathost_server_id, filename),
        headers={"Authorization": f"Basic {authorization}"},
        method="GET",
    )

    try:
        return urllib.request.urlopen(request, timeout=30)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            raise HTTPException(status_code=404, detail="Demo file not found.") from error
        if error.code in (401, 403):
            raise HTTPException(status_code=502, detail="DatHost rejected the configured credentials.") from error
        raise HTTPException(status_code=502, detail="DatHost could not provide the demo file.") from error
    except urllib.error.URLError as error:
        raise HTTPException(status_code=502, detail="Could not connect to DatHost.") from error


def _stream_response(response):
    try:
        while chunk := response.read(DOWNLOAD_CHUNK_SIZE):
            yield chunk
    finally:
        response.close()


@router.get("/download_demo/{match_id}")
def download_demo(match_id: int, db=Depends(get_db), settings: Settings = Depends(get_settings)):
    cursor = None
    try:
        cursor = db.cursor(dictionary=True)
        match = fetch_match_by_id(cursor, match_id)
    finally:
        if cursor:
            cursor.close()

    if not match:
        raise HTTPException(status_code=404, detail="Match not found.")

    filename = _demo_filename(match.get("MatchName"))
    dathost_response = _open_dathost_demo(settings, filename)

    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{urllib.parse.quote(filename, safe='')}",
    }
    content_length = dathost_response.headers.get("Content-Length")
    if content_length:
        headers["Content-Length"] = content_length

    return StreamingResponse(
        _stream_response(dathost_response),
        media_type=dathost_response.headers.get_content_type() or "application/octet-stream",
        headers=headers,
    )
