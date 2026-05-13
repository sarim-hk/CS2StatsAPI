from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from mysql.connector import Error

from app.database import DatabaseConnection, get_db

from .player_info_sql import player_info_select_sql

router = APIRouter()


@router.get("/player_panel_by_player_id")
def player_panel_by_player_id(
    player_id: str = Query(...),
    db: DatabaseConnection = Depends(get_db),
) -> dict[str, Any]:
    cursor = None
    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            f"""
            SELECT
                {player_info_select_sql("p")},
                pow.WeekPosition
            FROM CS2S_PlayerInfo p
            LEFT JOIN CS2S_PlayerOfTheWeek pow
                ON p.PlayerID = pow.PlayerID
            WHERE p.PlayerID = %s
            """,
            (player_id,),
        )

        player = cursor.fetchone()

        if not player:
            raise HTTPException(status_code=404, detail="Player not found.")

        player["PlayerID"] = str(player["PlayerID"])
        return player

    except Error as exc:
        print(f"Error: {exc}")
        raise HTTPException(status_code=500, detail="Failed to fetch data.") from exc

    finally:
        if cursor:
            cursor.close()
