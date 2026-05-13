from datetime import datetime, timedelta
import traceback
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import DatabaseConnection, DatabaseCursor, get_db

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


@router.get("/playerstats_panel_by_player_id")
def playerstats_panel_by_player_id(
    player_id: str = Query(...),
    map_id: str | None = None,
    range_filter: str = Query("overall", alias="range"),
    db: DatabaseConnection = Depends(get_db),
) -> dict[str, Any]:
    player_ids = [pid.strip() for pid in player_id.split(",")]
    player_ids = [pid for pid in player_ids if pid]

    if not player_ids:
        raise HTTPException(status_code=400, detail="No valid player IDs provided")

    if range_filter not in date_ranges and range_filter not in match_ranges:
        raise HTTPException(
            status_code=400,
            detail=f"range is not valid: {list(date_ranges.keys())} , {list(match_ranges.keys())}",
        )

    cursor: DatabaseCursor | None = None
    try:
        cursor = db.cursor(dictionary=True)
        all_player_stats: dict[str, Any] = {}

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
        error_message = str(e)
        error_traceback = traceback.format_exc()

        print(error_traceback)

        raise HTTPException(
            status_code=500,
            detail={"error": error_message, "traceback": error_traceback},
        ) from e

    finally:
        if cursor:
            cursor.close()

def get_match_results_match_range(
    cursor: DatabaseCursor,
    range_filter: str,
    player_ids: list[str],
    map_id: str | None = None,
) -> list[dict[str, Any]]:
    match_range = match_ranges[range_filter]
    
    player_id_placeholders = ", ".join(["%s"] * len(player_ids))
    
    query = f"""
        SELECT 
            pm.MatchID,
            tr.Result
        FROM CS2S_Player_Matches pm
        JOIN CS2S_TeamResult tr ON pm.MatchID = tr.MatchID
        JOIN CS2S_Team_Players tp ON tr.TeamID = tp.TeamID
        JOIN CS2S_Match m ON pm.MatchID = m.MatchID
        WHERE pm.PlayerID IN ({player_id_placeholders}) 
          AND tp.PlayerID IN ({player_id_placeholders})
        {'' if map_id is None else 'AND m.MapID = %s'}
        GROUP BY pm.MatchID, tr.Result
        ORDER BY pm.MatchID DESC
        LIMIT %s
    """
    
    # Prepare parameters
    if map_id is not None:
        params = (*player_ids, *player_ids, map_id, match_range)
    else:
        params = (*player_ids, *player_ids, match_range)
    
    cursor.execute(query, params)
    results = cursor.fetchall()
    return results

def get_match_results_date_range(
    cursor: DatabaseCursor,
    range_filter: str,
    player_ids: list[str],
    map_id: str | None = None,
) -> list[dict[str, Any]]:
    end_date = datetime.now()
    start_date = end_date - date_ranges[range_filter]
    start_date_str = start_date.strftime("%Y-%m-%d %H:%M:%S")
    end_date_str = end_date.strftime("%Y-%m-%d %H:%M:%S")
    
    # Prepare placeholders for player IDs
    player_id_placeholders = ", ".join(["%s"] * len(player_ids))
    
    query = f"""
    WITH DateRangeMatches AS (
        SELECT MatchID, MatchDate
        FROM CS2S_Match
        WHERE (%s IS NULL OR MatchDate >= %s) 
          AND (%s IS NULL OR MatchDate <= %s)
          {'' if map_id is None else 'AND MapID = %s'}
    )
    SELECT 
        pm.MatchID,
        tr.Result
    FROM DateRangeMatches drm
    JOIN CS2S_Player_Matches pm ON drm.MatchID = pm.MatchID
    JOIN CS2S_TeamResult tr ON pm.MatchID = tr.MatchID
    JOIN CS2S_Team_Players tp ON tr.TeamID = tp.TeamID
    WHERE pm.PlayerID IN ({player_id_placeholders}) 
      AND tp.PlayerID IN ({player_id_placeholders})
    GROUP BY pm.MatchID, tr.Result
    """
    
    # Prepare parameters
    if map_id is not None:
        params = (
            start_date_str, start_date_str, 
            end_date_str, end_date_str,
            map_id,
            *player_ids, *player_ids
        )
    else:
        params = (
            start_date_str, start_date_str, 
            end_date_str, end_date_str,
            *player_ids, *player_ids
        )
    
    cursor.execute(query, params)
    results = cursor.fetchall()
    return results

def get_split_round_ids_from_match_ids(
    cursor: DatabaseCursor,
    match_ids: list[Any],
    player_id: str,
) -> tuple[list[Any], list[Any]]:
    parameterised_match_ids = ", ".join(["%s"] * len(match_ids))

    cursor.execute(f"""
    SELECT 
        R.RoundID,
        R.MatchID,
        CASE 
            WHEN T.PlayerID IS NOT NULL THEN R.WinnerSide
            ELSE R.LoserSide
        END AS PlayerSide
    FROM 
        CS2S_Round R
    LEFT JOIN 
        CS2S_Team_Players T ON R.WinnerTeamID = T.TeamID AND T.PlayerID = %s
    LEFT JOIN 
        CS2S_Team_Players LT ON R.LoserTeamID = LT.TeamID AND LT.PlayerID = %s
    WHERE 
        (T.PlayerID IS NOT NULL OR LT.PlayerID IS NOT NULL)
        AND R.MatchID IN ({parameterised_match_ids});
    """, (player_id, player_id, *match_ids))

    rounds = cursor.fetchall()

    t_rounds = [match_round["RoundID"] for match_round in rounds if match_round["PlayerSide"] == 2]
    ct_rounds = [match_round["RoundID"] for match_round in rounds if match_round["PlayerSide"] == 3]

    return t_rounds, ct_rounds

def filter_match_ids_by_map(
    cursor: DatabaseCursor,
    match_ids: list[Any],
    map_id: str,
) -> list[Any]:
    parameterized_match_ids = ", ".join(["%s"] * len(match_ids))

    cursor.execute(f"""
        SELECT MatchID
        FROM CS2S_Match
        WHERE MatchID IN ({parameterized_match_ids}) AND MapID = %s
    """, (*match_ids, map_id))

    result = cursor.fetchall()

    filtered_match_ids = [row['MatchID'] for row in result]
    return filtered_match_ids

def calculate_impact_and_rating(
    kpr: float,
    apr: float,
    dpr: float,
    kast: float,
    adr: float,
) -> tuple[float, float]:
    # Convert inputs to float to ensure float arithmetic
    kpr, apr, dpr, kast, adr = float(kpr), float(apr), float(dpr), float(kast), float(adr)
    impact = ((2.13 * kpr) + (0.42 * apr) - 0.41) or 0.0
    rating = ((0.0073 * kast) + (0.3591 * kpr) + (-0.5329 * dpr) + (0.2372 * impact) + (0.0032 * adr) + 0.1587) or 0.0
    return impact, rating


def empty_stats(player_id: str) -> dict[str, Any]:
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


def get_stats(cursor: DatabaseCursor, round_ids: list[Any], player_id: str) -> dict[str, Any]:
    if not round_ids:
        return empty_stats(player_id)

    cursor.execute(f"""
    WITH 
    damage_stats AS (
        SELECT 
            AttackerID,
            SUM(CASE WHEN Weapon IN ({", ".join(["%s"] * len(utility_weapons))}) THEN Damage ELSE 0 END) AS UtilityDamage,
            SUM(CASE WHEN Weapon NOT IN ({", ".join(["%s"] * len(utility_weapons))}) THEN Damage ELSE 0 END) +
            SUM(CASE WHEN Weapon IN ({", ".join(["%s"] * len(utility_weapons))}) THEN Damage ELSE 0 END) AS Damage
        FROM CS2S_Hurt
        WHERE AttackerID = %s AND RoundID IN ({", ".join(["%s"] * len(round_ids))})
        GROUP BY AttackerID
    ),
    death_stats AS (
        SELECT 
            %s AS PlayerID,
            SUM(CASE WHEN AttackerID = %s THEN 1 ELSE 0 END) AS Kills,
            SUM(CASE WHEN AssisterID = %s THEN 1 ELSE 0 END) AS Assists,
            SUM(CASE WHEN VictimID = %s THEN 1 ELSE 0 END) AS Deaths,
            SUM(CASE WHEN AttackerID = %s AND Hitgroup = 1 THEN 1 ELSE 0 END) AS Headshots
        FROM CS2S_Death
        WHERE RoundID IN ({", ".join(["%s"] * len(round_ids))})
    ),
    blind_stats AS (
        SELECT 
            ThrowerID,
            COUNT(*) AS EnemiesFlashed,
            SUM(Duration) AS TotalDuration
        FROM CS2S_Blind
        WHERE ThrowerID = %s AND RoundID IN ({", ".join(["%s"] * len(round_ids))})
        GROUP BY ThrowerID
    ),
    kast_stats AS (
        SELECT 
            PlayerID,
            COUNT(*) AS KAST
        FROM CS2S_KAST
        WHERE PlayerID = %s AND RoundID IN ({", ".join(["%s"] * len(round_ids))})
        GROUP BY PlayerID
    )
    SELECT 
        %s AS PlayerID,
        COALESCE(d.Damage, 0) AS Damage,
        COALESCE(d.UtilityDamage, 0) AS UtilityDamage,
        COALESCE(ds.Kills, 0) AS Kills,
        COALESCE(ds.Assists, 0) AS Assists,
        COALESCE(ds.Deaths, 0) AS Deaths,
        COALESCE(ds.Headshots, 0) AS Headshots,
        COALESCE(b.EnemiesFlashed, 0) AS EnemiesFlashed,
        COALESCE(b.TotalDuration, 0.0) AS TotalDuration,
        %s AS RoundsPlayed,
        COALESCE(k.KAST, 0) AS RoundsKAST
    FROM 
        death_stats ds
    LEFT JOIN
        damage_stats d ON d.AttackerID = ds.PlayerID
    LEFT JOIN 
        blind_stats b ON ds.PlayerID = b.ThrowerID
    LEFT JOIN 
        kast_stats k ON ds.PlayerID = k.PlayerID
    """, (
        *utility_weapons, *utility_weapons, *utility_weapons, player_id, *round_ids,
        player_id, player_id, player_id, player_id, player_id, *round_ids,
        player_id, *round_ids,
        player_id, *round_ids,
        player_id, len(round_ids)
    ))

    result = cursor.fetchone()
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

    # Ensure float division
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

def combine_stats(t_stats: dict[str, Any], ct_stats: dict[str, Any]) -> dict[str, Any]:
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
