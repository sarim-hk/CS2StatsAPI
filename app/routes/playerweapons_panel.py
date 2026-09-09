from fastapi import APIRouter, Depends, Query

from app.database import fetch_player_weapon_kills, get_db
from app.routes.playerstats_panel import (
    get_match_results_date_range,
    parse_date_range,
)
from fastapi import HTTPException

router = APIRouter()


@router.get("/playerweapons_panel")
def playerweapons_panel(player_id=Query(...), map_id=None,
                        range_filter=Query(None, alias="range"),
                        db=Depends(get_db)):
    player_ids = [pid.strip() for pid in player_id.split(",") if pid.strip()]
    if not player_ids:
        raise HTTPException(status_code=400, detail="No valid player IDs provided.")
    date_range = parse_date_range(range_filter)

    cursor = db.cursor(dictionary=True)
    try:
        all_player_weapons = {}
        for current_player_id in player_ids:
            results = get_match_results_date_range(
                cursor, date_range, [current_player_id], map_id
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
