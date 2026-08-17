from fastapi import APIRouter, Depends, HTTPException, Query
from app.database import fetch_team_panel, get_db

router = APIRouter()

@router.get("/team_panel")
def team_panel(team_id = Query(...), db=Depends(get_db)):
    try:
        team = fetch_team_panel(db, team_id)

        if not team:
            raise HTTPException(status_code=404, detail="Team not found.")

        team["TeamID"] = str(team["TeamID"])
        return team

    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to fetch data.") from e
