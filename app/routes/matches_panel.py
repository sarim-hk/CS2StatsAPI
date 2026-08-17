from fastapi import APIRouter, Depends, HTTPException, Query
from mysql.connector import Error
from app.database import fetch_matches, get_db

router = APIRouter()

@router.get("/matches_panel")
def matches_panel(player_id = None, team_id = None, map_name = Query(None, alias="map"), db=Depends(get_db)):
    try:
        return fetch_matches(db=db, player_id=player_id, team_id=team_id, map_name=map_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to fetch data.") from e
