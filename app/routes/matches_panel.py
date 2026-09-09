from fastapi import APIRouter, Depends, HTTPException, Query
from app.database import fetch_matches, get_db
from app.routes.playerstats_panel import parse_date_range

router = APIRouter()

@router.get("/matches_panel")
def matches_panel(player_id=None, team_id=None,
                  map_id=None,
                  range_filter=Query(None, alias="range"),
                  db=Depends(get_db)):
    try:
        date_range = parse_date_range(range_filter)
        start_date, end_date = date_range or (None, None)

        return fetch_matches(
            db=db,
            player_id=player_id,
            team_id=team_id,
            map_name=map_id,
            start_date=start_date,
            end_date=end_date,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to fetch data.") from e
