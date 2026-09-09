from datetime import datetime, timedelta
import traceback
from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import (
    fetch_match_ids_for_map,
    fetch_match_results_date_range as db_fetch_match_results_date_range,
    fetch_match_results_match_range as db_fetch_match_results_match_range,
    fetch_player_stats_for_rounds,
    fetch_round_sides_for_player_matches,
    get_db,
)
from app.utils.stats import (
    UTILITY_WEAPONS,
    apply_derived_stats,
    combine_player_stats,
    empty_player_stats,
)

router = APIRouter()

@router.get("/playerstats_panel")
def playerstats_panel(player_id = Query(...), map_id = None, range_filter = Query(None, alias="range"), db=Depends(get_db)):
    player_ids = [pid.strip() for pid in player_id.split(",")]
    player_ids = [pid for pid in player_ids if pid]

    if not player_ids:
        raise HTTPException(status_code=400, detail="No valid player IDs provided.")

    date_range = parse_date_range(range_filter)

    cursor = None
    try:
        cursor = db.cursor(dictionary=True)
        all_player_stats = {}

        for player_id in player_ids:
            results = get_match_results_date_range(cursor, date_range, [player_id], map_id)

            if not results:
                all_player_stats[player_id] = {
                    "Overall": 0,
                    "Terrorist": 0,
                    "CounterTerrorist": 0,
                    "MatchesPlayed": 0,
                    "MatchesWon": 0,
                    "MatchIDs": [],
                }
                continue

            match_ids = list(set(result["MatchID"] for result in results))
            matches_won = sum(1 for result in results if result["Result"] == "Win")
            matches_played = len(match_ids)

            t_round_ids, ct_round_ids = get_split_round_ids_from_match_ids(cursor, match_ids, player_id)
            t_stats = get_stats(cursor, t_round_ids, player_id)
            ct_stats = get_stats(cursor, ct_round_ids, player_id)
            combined_stats = combine_player_stats(t_stats, ct_stats)

            all_player_stats[player_id] = {
                "Overall": combined_stats or 0,
                "Terrorist": t_stats or 0,
                "CounterTerrorist": ct_stats or 0,
                "MatchesPlayed": matches_played or 0,
                "MatchesWon": matches_won or 0,
                "MatchIDs": match_ids or [],
            }

        return all_player_stats

    except Exception as e:
        if isinstance(e, HTTPException):
            raise

        raise HTTPException(status_code=500, detail="An internal server error occurred.") from e

    finally:
        if cursor:
            cursor.close()

def parse_date_range(range_filter):
    if not range_filter:
        return None
    try:
        start, end = [datetime.strptime(value, "%Y-%m-%d") for value in range_filter.split(",")]
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Range must be YYYY-MM-DD,YYYY-MM-DD.")
    if start > end:
        raise HTTPException(status_code=400, detail="Range start date must not be after the end date.")
    return start, end + timedelta(days=1)

def get_match_results_date_range(cursor, date_range, player_ids, map_id=None):
    if date_range is None:
        start_date = "1000-01-01"
        end_date = "9999-12-31"
    else:
        start_date, end_date = date_range
    return db_fetch_match_results_date_range(cursor, start_date, player_ids, map_id, end_date)

def get_split_round_ids_from_match_ids(cursor, match_ids, player_id):
    rounds = fetch_round_sides_for_player_matches(cursor, match_ids, player_id)

    t_rounds = [match_round["RoundID"] for match_round in rounds if match_round["PlayerSide"] == 2]
    ct_rounds = [match_round["RoundID"] for match_round in rounds if match_round["PlayerSide"] == 3]

    return t_rounds, ct_rounds

def filter_match_ids_by_map(cursor, match_ids, map_id):
    result = fetch_match_ids_for_map(cursor, match_ids, map_id)
    return [row["MatchID"] for row in result]

def get_stats(cursor, round_ids, player_id):
    if not round_ids:
        return empty_player_stats(player_id)

    result = fetch_player_stats_for_rounds(cursor, round_ids, player_id, UTILITY_WEAPONS)
    if result is None:
        return empty_player_stats(player_id)

    stats = {
        "PlayerID": player_id,
        "Damage": result['Damage'],
        "UtilityDamage": result['UtilityDamage'],
        "Kills": result['Kills'],
        "Assists": result['Assists'],
        "Deaths": result['Deaths'],
        "Headshots": result['Headshots'],
        "Blinds": {
            "Count": result['EnemiesFlashed'],
            "TotalDuration": result['TotalDuration']
        },
        "RoundsPlayed": len(round_ids),
        "RoundsKAST": result['RoundsKAST']
    }

    apply_derived_stats(
        stats,
        stats["RoundsPlayed"],
        kast_rounds=stats["RoundsKAST"],
        zero_value=0,
    )

    return stats
