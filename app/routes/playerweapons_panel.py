from fastapi import APIRouter, Depends, Query

from app.database import fetch_player_weapon_kills, get_db
from app.routes.playerstats_panel import (
    date_ranges,
    get_match_results_date_range,
    get_match_results_match_range,
    match_ranges,
)
from fastapi import HTTPException

router = APIRouter()


@router.get("/playerweapons_panel")
def playerweapons_panel(player_id=Query(...), map_id=None,
                        range_filter=Query("overall", alias="range"),
                        db=Depends(get_db)):
    player_ids = [pid.strip() for pid in player_id.split(",") if pid.strip()]
    if not player_ids:
        raise HTTPException(status_code=400, detail="No valid player IDs provided.")
    if range_filter not in date_ranges and range_filter not in match_ranges:
        raise HTTPException(
            status_code=400,
            detail=f"Range is not valid: {list(date_ranges.keys())} , {list(match_ranges.keys())}",
        )

    cursor = db.cursor(dictionary=True)
    try:
        all_player_weapons = {}
        for current_player_id in player_ids:
            if range_filter in date_ranges:
                results = get_match_results_date_range(
                    cursor, range_filter, [current_player_id], map_id
                )
            else:
                results = get_match_results_match_range(
                    cursor, range_filter, [current_player_id], map_id
                )

            match_ids = list({result["MatchID"] for result in results})
            all_player_weapons[current_player_id] = {
                "PlayerID": current_player_id,
                "Weapons": fetch_player_weapon_kills(
                    db, current_player_id, match_ids
                ),
                "MatchIDs": match_ids,
            }

        return all_player_weapons
    finally:
        cursor.close()
