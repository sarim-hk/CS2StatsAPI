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

utility_weapons = ["smokegrenade", "molotov", "inferno", "hegrenade", "flashbang", "decoy"]

date_ranges = {
    "7days": timedelta(days=7),
    "14days": timedelta(days=14),
    "1month": timedelta(days=30),
    "3months": timedelta(days=90),
    "6months": timedelta(days=180),
    "1year": timedelta(days=365),
    "overall": timedelta(weeks=9999)
}

match_ranges = {
    "5matches": 5,
    "10matches": 10,
    "15matches": 15,
    "20matches": 20,
    "25matches": 25,
    "50matches": 50,
    "100matches": 100,
}

router = APIRouter()

@router.get("/playerstats_panel")
def playerstats_panel(player_id = Query(...), map_id = None, range_filter = Query("overall", alias="range"), db=Depends(get_db)):
    player_ids = [pid.strip() for pid in player_id.split(",")]
    player_ids = [pid for pid in player_ids if pid]

    if not player_ids:
        raise HTTPException(status_code=400, detail="No valid player IDs provided.")

    if range_filter not in date_ranges and range_filter not in match_ranges:
        raise HTTPException(status_code=400, detail=f"Range is not valid: {list(date_ranges.keys())} , {list(match_ranges.keys())}")

    cursor = None
    try:
        cursor = db.cursor(dictionary=True)
        all_player_stats = {}

        for player_id in player_ids:
            if range_filter in date_ranges:
                results = get_match_results_date_range(cursor, range_filter, [player_id], map_id)
            else:
                results = get_match_results_match_range(cursor, range_filter, [player_id], map_id)

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
            combined_stats = combine_stats(t_stats, ct_stats)

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

def get_match_results_match_range(cursor, range_filter, player_ids, map_id=None):
    match_range = match_ranges[range_filter]
    return db_fetch_match_results_match_range(cursor, match_range, player_ids, map_id)

def get_match_results_date_range(cursor, range_filter, player_ids, map_id=None):
    start_date = datetime.now() - date_ranges[range_filter]
    start_date_str = start_date.strftime("%Y-%m-%d %H:%M:%S")
    return db_fetch_match_results_date_range(cursor, start_date_str, player_ids, map_id)

def get_split_round_ids_from_match_ids(cursor, match_ids, player_id):
    rounds = fetch_round_sides_for_player_matches(cursor, match_ids, player_id)

    t_rounds = [match_round["RoundID"] for match_round in rounds if match_round["PlayerSide"] == 2]
    ct_rounds = [match_round["RoundID"] for match_round in rounds if match_round["PlayerSide"] == 3]

    return t_rounds, ct_rounds

def filter_match_ids_by_map(cursor, match_ids, map_id):
    result = fetch_match_ids_for_map(cursor, match_ids, map_id)
    return [row["MatchID"] for row in result]

def calculate_impact_and_rating(kpr, apr, dpr, kast, adr):
    # Convert inputs to float to ensure float arithmetic
    kpr, apr, dpr, kast, adr = float(kpr), float(apr), float(dpr), float(kast), float(adr)
    impact = ((2.13 * kpr) + (0.42 * apr) - 0.41) or 0.0
    rating = ((0.0073 * kast) + (0.3591 * kpr) + (-0.5329 * dpr) + (0.2372 * impact) + (0.0032 * adr) + 0.1587) or 0.0
    return impact, rating

def empty_stats(player_id):
    return {
        "PlayerID": player_id,
        "Damage": 0,
        "UtilityDamage": 0,
        "Kills": 0,
        "Assists": 0,
        "Deaths": 0,
        "Headshots": 0,
        "Blinds": {"Count": 0, "TotalDuration": 0.0},
        "RoundsPlayed": 0,
        "RoundsKAST": 0,
        "KAST": 0,
        "ADR": 0,
        "KPR": 0,
        "APR": 0,
        "DPR": 0,
        "Impact": 0,
        "Rating": 0,
    }

def get_stats(cursor, round_ids, player_id):
    if not round_ids:
        return empty_stats(player_id)

    result = fetch_player_stats_for_rounds(cursor, round_ids, player_id, utility_weapons)
    if result is None:
        return empty_stats(player_id)

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

    stats["KAST"] = (float(stats["RoundsKAST"]) / float(stats["RoundsPlayed"]) * 100.0) if stats["RoundsPlayed"] > 0 else 0.0
    stats["ADR"] = float(stats["Damage"]) / float(stats["RoundsPlayed"]) if stats["RoundsPlayed"] > 0 else 0.0
    stats["KPR"] = float(stats["Kills"]) / float(stats["RoundsPlayed"]) if stats["RoundsPlayed"] > 0 else 0.0
    stats["APR"] = float(stats["Assists"]) / float(stats["RoundsPlayed"]) if stats["RoundsPlayed"] > 0 else 0.0
    stats["DPR"] = float(stats["Deaths"]) / float(stats["RoundsPlayed"]) if stats["RoundsPlayed"] > 0 else 0.0

    stats["Impact"], stats["Rating"] = calculate_impact_and_rating(
        stats["KPR"],
        stats["APR"],
        stats["DPR"],
        stats["KAST"],
        stats["ADR"],
    )

    stats["KAST"] = round(stats["KAST"], 2) or 0
    stats["ADR"] = round(stats["ADR"], 2) or 0
    stats["KPR"] = round(stats["KPR"], 2) or 0
    stats["APR"] = round(stats["APR"], 2) or 0
    stats["DPR"] = round(stats["DPR"], 2) or 0
    stats["Impact"] = round(stats["Impact"], 2) or 0
    stats["Rating"] = round(stats["Rating"], 2) or 0

    return stats

def combine_stats(t_stats, ct_stats):
    stats = {
        "PlayerID": t_stats["PlayerID"],
        "Damage": t_stats["Damage"] + ct_stats["Damage"],
        "UtilityDamage": t_stats["UtilityDamage"] + ct_stats["UtilityDamage"],
        "Kills": t_stats["Kills"] + ct_stats["Kills"],
        "Assists": t_stats["Assists"] + ct_stats["Assists"],
        "Deaths": t_stats["Deaths"] + ct_stats["Deaths"],
        "Headshots": t_stats["Headshots"] + ct_stats["Headshots"],
        "Blinds": {
            "Count": t_stats["Blinds"]["Count"] + ct_stats["Blinds"]["Count"],
            "TotalDuration": t_stats["Blinds"]["TotalDuration"] + ct_stats["Blinds"]["TotalDuration"]
        },
        "RoundsPlayed": t_stats["RoundsPlayed"] + ct_stats["RoundsPlayed"],
        "RoundsKAST": t_stats["RoundsKAST"] + ct_stats["RoundsKAST"]
    }

    # Fix float division and remove tuple creation
    stats["KAST"] = (float(stats["RoundsKAST"]) / float(stats["RoundsPlayed"]) * 100.0) if stats["RoundsPlayed"] > 0 else 0.0
    stats["ADR"] = float(stats["Damage"]) / float(stats["RoundsPlayed"]) if stats["RoundsPlayed"] > 0 else 0.0
    stats["KPR"] = float(stats["Kills"]) / float(stats["RoundsPlayed"]) if stats["RoundsPlayed"] > 0 else 0.0
    stats["APR"] = float(stats["Assists"]) / float(stats["RoundsPlayed"]) if stats["RoundsPlayed"] > 0 else 0.0
    stats["DPR"] = float(stats["Deaths"]) / float(stats["RoundsPlayed"]) if stats["RoundsPlayed"] > 0 else 0.0
    
    stats["Impact"], stats["Rating"] = calculate_impact_and_rating(
        stats["KPR"],
        stats["APR"],
        stats["DPR"],
        stats["KAST"],
        stats["ADR"],
    )

    stats["KAST"] = round(stats["KAST"], 2) or 0
    stats["ADR"] = round(stats["ADR"], 2) or 0
    stats["KPR"] = round(stats["KPR"], 2) or 0
    stats["APR"] = round(stats["APR"], 2) or 0
    stats["DPR"] = round(stats["DPR"], 2) or 0
    stats["Impact"] = round(stats["Impact"], 2) or 0
    stats["Rating"] = round(stats["Rating"], 2) or 0

    return stats
