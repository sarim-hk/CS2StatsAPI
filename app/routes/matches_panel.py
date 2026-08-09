from fastapi import APIRouter, Depends, HTTPException, Query
from mysql.connector import Error
from app.database import fetch_matches, get_db

router = APIRouter()

@router.get("/matches_panel")
def matches_panel(player_id = None, map_name = Query(None, alias="map"), page = Query(None, ge=1), db=Depends(get_db)):
    try:
        return fetch_matches(db=db, player_id=player_id, map_name=map_name, page=page)
    except Error as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch data.") from e
