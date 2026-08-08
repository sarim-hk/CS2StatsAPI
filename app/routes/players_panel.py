from fastapi import APIRouter, Depends, HTTPException
from mysql.connector import Error

from app.database import get_db

from .utils.player_info_sql import player_info_select_sql

router = APIRouter()


@router.get("/players_panel")
def players_panel(db=Depends(get_db)):
    cursor = None
    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            f"""
            SELECT {player_info_select_sql("p")}
            FROM CS2S_PlayerInfo p
            JOIN CS2S_Player_Matches pm ON p.PlayerID = pm.PlayerID
            GROUP BY p.PlayerID
            HAVING COUNT(pm.MatchID) > 0
            ORDER BY p.ELO DESC
            """
        )

        players = cursor.fetchall()
        for player in players:
            player["PlayerID"] = str(player["PlayerID"])

        if not players:
            raise HTTPException(status_code=404, detail="Player(s) not found.")

        return players

    except Error as exc:
        print(f"Error: {exc}")
        raise HTTPException(status_code=500, detail="Failed to fetch data.") from exc

    finally:
        if cursor:
            cursor.close()
