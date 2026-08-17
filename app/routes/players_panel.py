from fastapi import APIRouter, Depends, HTTPException
from app.database import fetch_players_panel, get_db

router = APIRouter()


@router.get("/players_panel")
def players_panel(team_id = None, db=Depends(get_db)):
    try:
        players = fetch_players_panel(db, team_id=team_id)
        for player in players:
            player["PlayerID"] = str(player["PlayerID"])
            
        if not players:
            raise HTTPException(status_code=404, detail="Player(s) not found.")
        return players
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to fetch data.") from e