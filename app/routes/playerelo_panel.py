from fastapi import APIRouter, Depends, HTTPException, Query
from app.database import fetch_player_elo_history, get_db
from app.routes.playerstats_panel import parse_date_range

router = APIRouter()

@router.get("/playerelo_panel")
def playerelo_panel(player_id=Query(...),
                    range_filter=Query(None, alias="range"),
                    db=Depends(get_db)):
    try:
        date_range = parse_date_range(range_filter)
        results = fetch_player_elo_history(db, player_id)

        if not results:
            raise HTTPException(status_code=404, detail="No data found for the given Player ID.")

        current_elo = results[0]["CurrentELO"]
        calculated_elo = current_elo
        elo_history = []

        for match in results:
            elo_before_match = calculated_elo - match["DeltaELO"]

            if date_range is None or (
                date_range[0] <= match["MatchDate"] < date_range[1]
            ):
                elo_history.append(
                    {
                        "MatchID": match["MatchID"],
                        "DeltaELO": match["DeltaELO"],
                        "ELOBeforeMatch": elo_before_match,
                    }
                )

            calculated_elo = elo_before_match

        if not elo_history:
            raise HTTPException(status_code=404, detail="No data found for the given Player ID and date range.")

        if date_range is not None:
            current_elo = elo_history[0]["ELOBeforeMatch"] + elo_history[0]["DeltaELO"]

        return {
            "PlayerID": player_id,
            "CurrentELO": current_elo,
            "ELOHistory": elo_history,
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
