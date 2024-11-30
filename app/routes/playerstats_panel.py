from datetime import datetime, timedelta
from flask import Blueprint, jsonify, g, request
import traceback

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

playerstats_panel_bp = Blueprint("playerstats_panel_bp", __name__)

@playerstats_panel_bp.route("/playerstats_panel_by_player_id")
def playerstats_panel_by_player_id():
    player_id = request.args.get("player_id")
    range = request.args.get("range")

    if not player_id or not range:
        return jsonify({"error": "player_id and range are required"}), 400
    
    elif range not in date_ranges and range not in match_ranges:
        return jsonify({"error": f"range is not valid: {date_ranges.keys()} , {match_ranges.keys()}"}), 400
    
    try:
        cursor = g.db.cursor(dictionary=True)

        if range in date_ranges:
            results = get_match_results_date_range(cursor, range, player_id)

        elif range in match_ranges:
            results = get_match_results_match_range(cursor, range, player_id)

        match_ids = [result["MatchID"] for result in results]
        parameterised_match_ids = ", ".join(["%s"] * len(match_ids))
        matches_won = sum(1 for result in results if result["Result"] == "Win")
        matches_played = len(match_ids)
        rounds_played = sum(result["RoundsPlayed"] for result in results)
        
        # Get Damage and UtilityDamage
        cursor.execute(f"""
            SELECT 
                SUM(CASE WHEN Weapon IN ({", ".join(["%s"] * len(utility_weapons))}) THEN Damage ELSE 0 END) AS UtilityDamage,
                SUM(CASE WHEN Weapon NOT IN ({", ".join(["%s"] * len(utility_weapons))}) THEN Damage ELSE 0 END) +
                SUM(CASE WHEN Weapon IN ({", ".join(["%s"] * len(utility_weapons))}) THEN Damage ELSE 0 END) AS Damage
            FROM CS2S_Hurt
            WHERE AttackerID = %s AND MatchID IN ({parameterised_match_ids})
        """, (*utility_weapons, *utility_weapons, *utility_weapons, player_id, *match_ids))

        damage = cursor.fetchone()

        # Get Kills, Assists, Deaths
        cursor.execute(f"""
        SELECT 
            SUM(CASE WHEN AttackerID = %s THEN 1 ELSE 0 END) AS Kills,
            SUM(CASE WHEN AssisterID = %s THEN 1 ELSE 0 END) AS Assists,
            SUM(CASE WHEN VictimID = %s THEN 1 ELSE 0 END) AS Deaths,
            SUM(CASE WHEN AttackerID = %s AND Hitgroup = 1 THEN 1 ELSE 0 END) AS Headshots
        FROM CS2S_Death
        WHERE MatchID IN ({parameterised_match_ids})
        """, (player_id, player_id, player_id, player_id, *match_ids))
        
        stats = cursor.fetchone()

        # Get EnemiesFlashed and Duration
        cursor.execute(f"""
        SELECT 
            COUNT(*) AS EnemiesFlashed,
            SUM(Duration) AS TotalDuration
        FROM CS2S_Blind
        WHERE ThrowerID = %s AND MatchID IN ({parameterised_match_ids})
        """, (player_id, *match_ids))

        blinds = cursor.fetchone()

        # Get KAST
        cursor.execute(f"""
        SELECT 
            COUNT(*) AS KAST
        FROM CS2S_KAST
        WHERE PlayerID = %s AND MatchID IN ({parameterised_match_ids})
        """, (player_id, *match_ids))

        kast = cursor.fetchone()

        stats = {
            "PlayerID": player_id,
            "Damage": damage["Damage"] or 0,
            "UtilityDamage": damage["UtilityDamage"] or 0,
            "Kills": stats["Kills"] or 0,
            "Assists": stats["Assists"] or 0,
            "Deaths": stats["Deaths"] or 0,
            "Headshots": stats["Headshots"] or 0,
            "Blinds": {
                "Count": blinds["EnemiesFlashed"] or 0,
                "TotalDuration": blinds["TotalDuration"] or 0.0
            },
            "MatchesPlayed": matches_played or 0,
            "MatchesWon": matches_won or 0,
            "RoundsPlayed": rounds_played or 0,
        }

        stats["KAST"] = round(((kast["KAST"] / stats["RoundsPlayed"]) * 100), 2) or 0
        stats["ADR"] = round(stats["Damage"] / stats["RoundsPlayed"], 2) or 0
        stats["KPR"] = round(stats["Kills"] / stats["RoundsPlayed"], 2) or 0
        stats["APR"] = round(stats["Assists"] / stats["RoundsPlayed"], 2) or 0
        stats["DPR"] = round(stats["Deaths"] / stats["RoundsPlayed"], 2) or 0

        stats["Impact"] = round(2.13 * float(stats["KPR"]) + 0.42 * (float(stats["Assists"]) / float(stats["RoundsPlayed"])) - 0.41, 2) or 0
        stats["Rating"] = round((0.0073 * float(stats["KAST"]) + 0.3591 * float(stats["KPR"]) + -0.5329 * float(stats["DPR"]) + 0.2372 * float(stats["Impact"]) + 0.0032 * float(stats["ADR"]) + 0.1587), 2) or 0
        
        return jsonify(stats)

    except Exception as e:
        error_message = str(e)
        error_traceback = traceback.format_exc()

        return jsonify({
            "error": error_message,
            "traceback": error_traceback
        }), 500

def get_match_results_match_range(cursor, range, player_id):
    match_range = match_ranges[range]

    cursor.execute("""
        SELECT 
            pm.MatchID,
            tr.Result,
            COUNT(r.MatchID) AS RoundsPlayed
        FROM CS2S_Player_Matches pm
        JOIN CS2S_TeamResult tr ON pm.MatchID = tr.MatchID
        JOIN CS2S_Team_Players tp ON tr.TeamID = tp.TeamID
        LEFT JOIN CS2S_Round r ON r.MatchID = pm.MatchID
        WHERE pm.PlayerID = %s AND tp.PlayerID = %s
        GROUP BY pm.MatchID, tr.Result
        ORDER BY pm.MatchID DESC
        LIMIT %s
    """, (player_id, player_id, match_range))

    results = cursor.fetchall()
    return results

def get_match_results_date_range(cursor, range, player_id):
    end_date = datetime.now()
    start_date = end_date - date_ranges[range]
    start_date_str = start_date.strftime("%Y-%m-%d %H:%M:%S")
    end_date_str = end_date.strftime("%Y-%m-%d %H:%M:%S")

    # Query for the min and max match IDs based on the date range
    query = """
    SELECT MIN(MatchID) AS MinMatchID, MAX(MatchID) AS MaxMatchID
    FROM CS2S_Match
    WHERE (%s IS NULL OR MatchDate >= %s) AND (%s IS NULL OR MatchDate <= %s)
    """
    
    cursor.execute(query, (start_date_str, start_date_str, end_date_str, end_date_str))
    date_range_result = cursor.fetchone()

    min_id = date_range_result["MinMatchID"] or 0
    max_id = date_range_result["MaxMatchID"] or 999

    # Query for matches played by the player
    cursor.execute("""
    SELECT 
        pm.MatchID,
        tr.Result,
        COUNT(r.MatchID) AS RoundsPlayed
    FROM CS2S_Player_Matches pm
    JOIN CS2S_TeamResult tr ON pm.MatchID = tr.MatchID
    JOIN CS2S_Team_Players tp ON tr.TeamID = tp.TeamID
    LEFT JOIN CS2S_Round r ON r.MatchID = pm.MatchID
    WHERE pm.PlayerID = %s AND pm.MatchID BETWEEN %s AND %s AND tp.PlayerID = %s
    GROUP BY pm.MatchID, tr.Result
    """, (player_id, min_id, max_id, player_id))

    results = cursor.fetchall()
    return results
