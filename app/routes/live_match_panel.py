from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from mysql.connector import Error

from app.database import DatabaseConnection, get_db

router = APIRouter()


@router.get("/live_match_panel")
def live_match_panel(db: DatabaseConnection = Depends(get_db)) -> dict[str, Any]:
    cursor = None
    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT TScore, CTScore, BombStatus, MapID,
                   UNIX_TIMESTAMP(InsertDate) AS InsertDate
            FROM CS2S_LiveStatus
            WHERE StaticID = 1
            """
        )
        match_status = cursor.fetchone()

        if match_status is None:
            raise HTTPException(status_code=404, detail="No match found.")

        cursor.execute(
            """
            SELECT CS2S_LivePlayers.PlayerID, CS2S_PlayerInfo.Username, Kills, Assists, Deaths, ADR, Health, Money
            FROM CS2S_LivePlayers
            INNER JOIN CS2S_PlayerInfo ON CS2S_LivePlayers.PlayerID = CS2S_PlayerInfo.PlayerID
            WHERE Side = 2
            """
        )
        t_players = cursor.fetchall()

        cursor.execute(
            """
            SELECT CS2S_LivePlayers.PlayerID, CS2S_PlayerInfo.Username, Kills, Assists, Deaths, ADR, Health, Money
            FROM CS2S_LivePlayers
            INNER JOIN CS2S_PlayerInfo ON CS2S_LivePlayers.PlayerID = CS2S_PlayerInfo.PlayerID
            WHERE Side = 3
            """
        )
        ct_players = cursor.fetchall()

        return {
            "TScore": match_status["TScore"],
            "CTScore": match_status["CTScore"],
            "BombStatus": match_status["BombStatus"],
            "InsertDate": match_status["InsertDate"],
            "MapID": match_status["MapID"],
            "TPlayers": t_players,
            "CTPlayers": ct_players,
        }

    except Error as exc:
        print(f"Error: {exc}")
        raise HTTPException(status_code=500, detail="Failed to fetch data.") from exc

    finally:
        if cursor:
            cursor.close()
