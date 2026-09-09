from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from mysql.connector import Error
from app.database import fetch_matches, get_db
from app.routes.playerstats_panel import date_ranges, match_ranges

router = APIRouter()

@router.get("/matches_panel")
def matches_panel(player_id=None, team_id=None,
                  map_name=Query(None, alias="map"),
                  range_filter=Query("overall", alias="range"),
                  db=Depends(get_db)):
    try:
        if range_filter not in date_ranges and range_filter not in match_ranges:
            raise HTTPException(
                status_code=400,
                detail=f"Range is not valid: {list(date_ranges.keys())} , {list(match_ranges.keys())}",
            )

        start_date = None
        match_limit = None
        if range_filter in date_ranges:
            start_date = datetime.now() - date_ranges[range_filter]
        else:
            match_limit = match_ranges[range_filter]

        return fetch_matches(
            db=db,
            player_id=player_id,
            team_id=team_id,
            map_name=map_name,
            start_date=start_date,
            match_limit=match_limit,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to fetch data.") from e
