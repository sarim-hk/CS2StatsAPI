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

    if not player_id:
        return jsonify({"error": "player_id is required"}), 400
    
    elif not range:
        range = "overall"

    elif range not in date_ranges and range not in match_ranges:
        return jsonify({"error": f"range is not valid: {date_ranges.keys()} , {match_ranges.keys()}"}), 400
    
    try:
        cursor = g.db.cursor(dictionary=True)

        if range in date_ranges:
            results = get_match_results_date_range(cursor, range, player_id)

        elif range in match_ranges:
            results = get_match_results_match_range(cursor, range, player_id)

        match_ids = [result["MatchID"] for result in results]
        matches_won = sum(1 for result in results if result["Result"] == "Win")
        matches_played = len(match_ids)

        t_round_ids, ct_round_ids = get_split_round_ids_from_match_ids(cursor, match_ids, player_id)
        
        t_stats = get_stats(cursor, t_round_ids, player_id)
        ct_stats = get_stats(cursor, ct_round_ids, player_id)
        combined_stats = combine_stats(t_stats, ct_stats)

        stats = {
            "Overall": combined_stats or 0,
            "Terrorist": t_stats or 0,
            "Counter-Terrorist": ct_stats or 0,
            "MatchesPlayed": matches_played or 0,
            "MatchesWon": matches_won or 0,
        }

        return jsonify(stats)

    except Exception as e:
        error_message = str(e)
        error_traceback = traceback.format_exc()

        print(error_traceback)

        return jsonify({
            "error": error_message,
            "traceback": error_traceback
        }), 500

def get_match_results_match_range(cursor, range, player_id):
    match_range = match_ranges[range]

    cursor.execute("""
        SELECT 
            pm.MatchID,
            tr.Result
        FROM CS2S_Player_Matches pm
        JOIN CS2S_TeamResult tr ON pm.MatchID = tr.MatchID
        JOIN CS2S_Team_Players tp ON tr.TeamID = tp.TeamID
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
        tr.Result
    FROM CS2S_Player_Matches pm
    JOIN CS2S_TeamResult tr ON pm.MatchID = tr.MatchID
    JOIN CS2S_Team_Players tp ON tr.TeamID = tp.TeamID
    WHERE pm.PlayerID = %s AND pm.MatchID BETWEEN %s AND %s AND tp.PlayerID = %s
    GROUP BY pm.MatchID, tr.Result
    """, (player_id, min_id, max_id, player_id))

    results = cursor.fetchall()
    return results

def get_split_round_ids_from_match_ids(cursor, match_ids, player_id):
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

    t_rounds = [round["RoundID"] for round in rounds if round["PlayerSide"] == 2]
    ct_rounds = [round["RoundID"] for round in rounds if round["PlayerSide"] == 3]

    return t_rounds, ct_rounds

def get_stats(cursor, round_ids, player_id):
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
        damage_stats d
    CROSS JOIN 
        death_stats ds
    LEFT JOIN 
        blind_stats b ON d.AttackerID = b.ThrowerID
    LEFT JOIN 
        kast_stats k ON d.AttackerID = k.PlayerID
    """, (
        *utility_weapons, *utility_weapons, *utility_weapons, player_id, *round_ids,
        player_id, player_id, player_id, player_id, player_id, *round_ids,
        player_id, *round_ids,
        player_id, *round_ids,
        player_id, len(round_ids)
    ))

    result = cursor.fetchone()
    
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

    stats["KAST"] = round(((stats["RoundsKAST"] / stats["RoundsPlayed"]) * 100), 2) or 0
    stats["ADR"] = round(stats["Damage"] / stats["RoundsPlayed"], 2) or 0
    stats["KPR"] = round(stats["Kills"] / stats["RoundsPlayed"], 2) or 0
    stats["APR"] = round(stats["Assists"] / stats["RoundsPlayed"], 2) or 0
    stats["DPR"] = round(stats["Deaths"] / stats["RoundsPlayed"], 2) or 0

    stats["Impact"] = round(2.13 * float(stats["KPR"]) + 0.42 * (float(stats["Assists"]) / float(stats["RoundsPlayed"])) - 0.41, 2) or 0
    stats["Rating"] = round((0.0073 * float(stats["KAST"]) + 0.3591 * float(stats["KPR"]) + -0.5329 * float(stats["DPR"]) + 0.2372 * float(stats["Impact"]) + 0.0032 * float(stats["ADR"]) + 0.1587), 2) or 0
    
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

    stats["KAST"] = round(((stats["RoundsKAST"] / stats["RoundsPlayed"]) * 100), 2) or 0
    stats["ADR"] = round(stats["Damage"] / stats["RoundsPlayed"], 2) or 0
    stats["KPR"] = round(stats["Kills"] / stats["RoundsPlayed"], 2) or 0
    stats["APR"] = round(stats["Assists"] / stats["RoundsPlayed"], 2) or 0
    stats["DPR"] = round(stats["Deaths"] / stats["RoundsPlayed"], 2) or 0

    stats["Impact"] = round(2.13 * float(stats["KPR"]) + 0.42 * (float(stats["Assists"]) / float(stats["RoundsPlayed"])) - 0.41, 2) or 0
    stats["Rating"] = round((0.0073 * float(stats["KAST"]) + 0.3591 * float(stats["KPR"]) + -0.5329 * float(stats["DPR"]) + 0.2372 * float(stats["Impact"]) + 0.0032 * float(stats["ADR"]) + 0.1587), 2) or 0

    return stats
