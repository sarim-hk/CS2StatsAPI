from fastapi import APIRouter, Depends, HTTPException, Query
from mysql.connector import Error
from app.database import fetch_player_panel, get_db

router = APIRouter()

@router.get("/player_panel")
def player_panel(player_id = Query(...), db=Depends(get_db)):
    try:
        player = fetch_player_panel(db, player_id)

        if not player:
            raise HTTPException(status_code=404, detail="Player not found.")

        player["PlayerID"] = str(player["PlayerID"])
        return player

    except Error as exc:
        print(f"Error: {exc}")
        raise HTTPException(status_code=500, detail="Failed to fetch data.") from exc
