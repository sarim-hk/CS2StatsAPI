import json
import os
import urllib.parse
import urllib.request
import urllib.error
from fastapi import APIRouter, Depends, HTTPException, Request, status
from app.config import Settings, get_settings
from app.database import transaction, insert_player_info
from app.routes.upload_match import validate_authorization

router = APIRouter()

@router.post("/upload_player")
def upload_player(request: Request, settings: Settings = Depends(get_settings)):

    validate_authorization(request, settings.api_auth_key)
    body = request.body()
    print(f"[upload_player] Request received. Bytes={len(body)}")

    try:
        payload = json.loads(body.decode("utf-8"))
        print(f"[upload_player] JSON parsed. Payload={payload}")

    except UnicodeDecodeError as exc:
        print("[upload_player] Request body was not valid UTF-8.")
        raise HTTPException(status_code=400, detail="Request body must be UTF-8 encoded.") from exc
    
    except json.JSONDecodeError as exc:
        print("[upload_player] Request body was not valid JSON.")
        raise HTTPException(status_code=400, detail="Invalid JSON payload.") from exc

    player_id = payload.get("playerID")
    if player_id is None:
        print("[upload_player] Missing playerID in payload.")
        raise HTTPException(status_code=400, detail="playerID is required.")

    username, avatar_hash = get_steam_summary(player_id, settings.steam_api_auth_key)
    print(f"[upload_player] Steam summary fetched. PlayerID={player_id}, Username={username}, AvatarHash={avatar_hash}")

    with transaction() as db:
        cursor = db.cursor()
        print("[upload_player] Transaction started.")

        try:
            rows = insert_player_info(cursor, player_id, username, avatar_hash)
            print(f"[upload_player] Player inserted/updated. PlayerID={player_id}, Username={username}, Rows={rows}")

        except Exception as exc:
            print(f"[upload_player] Error while inserting player. PlayerID={player_id}, Error={exc}")
            raise

        finally:
            cursor.close()
            print("[upload_player] Cursor closed.")

    print(f"[upload_player] Transaction committed. PlayerID={player_id}")

    return {
        "success": True,
        "message": "Player uploaded.",
        "PlayerID": player_id,
        "Username": username,
        "AvatarHash": avatar_hash,
    }

def get_steam_summary(steam_id, steam_api_key: str):
    query = urllib.parse.urlencode({"key": steam_api_key, "steamids": steam_id})
    url = f"https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?{query}"

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            if 200 <= response.status < 300:
                data = json.loads(response.read().decode("utf-8"))
                players = data.get("response", {}).get("players", [])
                if players:
                    player_data = players[0]
                    personaname = player_data.get("personaname")
                    avatar_url = player_data.get("avatar")
                    avatar_hash = None
                    if avatar_url:
                        filename = avatar_url.rsplit("/", 1)[-1]
                        avatar_hash = os.path.splitext(filename)[0]
                    return personaname, avatar_hash
            print(f"[upload_player] Failed to fetch Steam summary. Status={response.status}")

    except urllib.error.HTTPError as exc:
        print(f"[upload_player] Steam HTTP error. Status={exc.code}, Error={exc}")

    except urllib.error.URLError as exc:
        print(f"[upload_player] Steam request exception. Error={exc}")

    return None, None