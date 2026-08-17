from fastapi import APIRouter, Depends, HTTPException, Query
from app.database import fetch_team_elo_history, get_db

router = APIRouter()

@router.get("/teamelo_panel")
def teamelo_panel(team_id = Query(...), db = Depends(get_db)):
    try:
        results = fetch_team_elo_history(db, team_id)

        if not results:
            raise HTTPException(status_code=404, detail="No data found for the given Team ID.")

        current_elo = results[0]["CurrentELO"]
        calculated_elo = current_elo
        elo_history = []

        for match in results:
            calculated_elo -= match["DeltaELO"]
            elo_history.append(
                {
                    "MatchID": match["MatchID"],
                    "DeltaELO": match["DeltaELO"],
                    "ELOBeforeMatch": calculated_elo,
                }
            )

        return {
            "TeamID": team_id,
            "CurrentELO": current_elo,
            "ELOHistory": elo_history,
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
