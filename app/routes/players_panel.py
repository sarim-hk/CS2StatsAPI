from fastapi import APIRouter, Depends, HTTPException
from mysql.connector import Error
from app.database import fetch_players_panel, get_db

router = APIRouter()

@router.get("/players_panel")
def players_panel(db=Depends(get_db)):
    try:
        players = fetch_players_panel(db)
        for player in players:
            player["PlayerID"] = str(player["PlayerID"])

        if not players:
            raise HTTPException(status_code=404, detail="Player(s) not found.")

        return players

    except Error as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch data.") from e
