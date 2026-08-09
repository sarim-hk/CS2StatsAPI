from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.config import Settings, get_settings
from app.database import transaction

from app.routes.upload_match import validate_authorization

router = APIRouter()

@router.post("/upload_player/{player_id}")
async def upload_player(player_id: int, request: Request, settings: Settings = Depends(get_settings)):

    validate_authorization(request, settings.api_auth_key)
    print(f"[upload_player] Request received. PlayerID={player_id}")

    # TODO: query Steam API for Username/AvatarHash using player_id
    username = f"Player_{player_id}"

    with transaction() as db:
        cursor = db.cursor()
        print("[upload_player] Transaction started.")

        try:
            cursor.execute(
                """
                INSERT INTO CS2S_PlayerInfo
                    (PlayerID, Username, AvatarHash)
                VALUES
                    (%s, %s, DEFAULT)
                ON DUPLICATE KEY UPDATE
                    Username = VALUES(Username),
                    AvatarHash = VALUES(AvatarHash);
                """,
                (player_id, username),
            )
            print(f"[upload_player] Player inserted/updated. PlayerID={player_id}, Username={username}, Rows={cursor.rowcount}")
        except Exception as exc:
            print(f"[upload_player] Error while upserting player. PlayerID={player_id}, Error={exc}")
            raise
        finally:
            cursor.close()
            print("[upload_player] Cursor closed.")

    print(f"[upload_player] Transaction committed. PlayerID={player_id}")

    return {
        "success": True,
        "message": "Player uploaded.",
        "PlayerID": player_id,
    }