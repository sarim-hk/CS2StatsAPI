from flask import Blueprint, jsonify, g, request
from mysql.connector import Error

playerstats_panel_bp = Blueprint('playerstats_panel_bp', __name__)

@playerstats_panel_bp.route("/playerstats_panel_by_player_id")
def playerstats_panel_by_player_id():
    player_id = request.args.get("player_id")

    try:
        cursor = g.db.cursor(dictionary=True)
        cursor.execute("""
                       SELECT *
                       FROM CS2S_PlayerStats
                       WHERE PlayerID = %s
                       """, (player_id,))

        temp = cursor.fetchall()

        playerstats = {}
        terrorist_stats = None
        ct_stats = None

        for playerstat in temp:
            if playerstat["Side"] == 2:
                terrorist_stats = _create_playerstat(playerstat)
                playerstats["Terrorist"] = terrorist_stats

            elif playerstat["Side"] == 3:
                ct_stats = _create_playerstat(playerstat)
                playerstats["CounterTerrorist"] = ct_stats

        if terrorist_stats and ct_stats:
            playerstats["Overall"] = _combine_playerstats(terrorist_stats, ct_stats)
        elif terrorist_stats:
            playerstats["Overall"] = terrorist_stats
        elif ct_stats:
            playerstats["Overall"] = ct_stats

        cursor.execute("""
                       SELECT COUNT(MatchID) AS MatchesPlayed
                       FROM CS2S_Player_Matches
                       WHERE PlayerID = %s
                       """, (player_id,))

        temp = cursor.fetchone()
        playerstats.update(temp)

        cursor.execute("""
                       SELECT COUNT(MatchID) AS MatchesPlayed
                       FROM CS2S_Player_Matches
                       WHERE PlayerID = %s
                       """, (player_id,))

        temp = cursor.fetchone()
        playerstats.update(temp)

        cursor.execute("""
                       SELECT COUNT(DISTINCT tr.MatchID) AS MatchesWon
                       FROM CS2S_Team_Players tp
                       JOIN CS2S_TeamResult tr ON tp.TeamID = tr.TeamID
                       WHERE tr.Result = 'Win' AND tp.PlayerID = %s
                       """, (player_id,))

        temp = cursor.fetchone()
        playerstats.update(temp)

        return jsonify(playerstats)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

def _create_playerstat(temp):
    rounds_played = temp["RoundsPlayed"]
    playerstat = {
        "Kills": temp["Kills"],
        "Headshots": temp["Headshots"],
        "Assists": temp["Assists"],
        "Deaths": temp["Deaths"],
        "Damage": temp["Damage"],
        "UtilityDamage": temp["UtilityDamage"],
        "EnemiesFlashed": temp["EnemiesFlashed"],
        "GrenadesThrown": temp["GrenadesThrown"],
        "ClutchAttempts": temp["ClutchAttempts"],
        "ClutchWins": temp["ClutchWins"],
        "DuelAttempts": temp["DuelAttempts"],
        "DuelWins": temp["DuelWins"],
        "Rounds": rounds_played,
        "KAST": round(temp["RoundsKAST"] / rounds_played * 100, 2) if rounds_played > 0 else 0,
        "ADR": round(temp["Damage"] / rounds_played, 2) if rounds_played > 0 else 0,
        "KPR": round(temp["Kills"] / rounds_played, 2) if rounds_played > 0 else 0,
        "APR": round(temp["Assists"] / rounds_played, 2) if rounds_played > 0 else 0,
        "DPR": round(temp["Deaths"] / rounds_played, 2) if rounds_played > 0 else 0
    }

    playerstat["Impact"] = round(2.13 * playerstat["KPR"] + 0.42 * playerstat["APR"] - 0.41, 2) if rounds_played > 0 else 0
    playerstat["Rating"] = round((0.0073 * playerstat["KAST"] + 0.3591 * playerstat["KPR"] - 0.5329 * playerstat["DPR"] +
                                  0.2372 * playerstat["Impact"] + 0.0032 * playerstat["ADR"] + 0.1587), 2) if rounds_played > 0 else 0

    return playerstat

def _combine_playerstats(stat1, stat2):
    combined_rounds = stat1["Rounds"] + stat2["Rounds"]

    combined_stat = {
        "Kills": stat1["Kills"] + stat2["Kills"],
        "Headshots": stat1["Headshots"] + stat2["Headshots"],
        "Assists": stat1["Assists"] + stat2["Assists"],
        "Deaths": stat1["Deaths"] + stat2["Deaths"],
        "Damage": stat1["Damage"] + stat2["Damage"],
        "UtilityDamage": stat1["UtilityDamage"] + stat2["UtilityDamage"],
        "EnemiesFlashed": stat1["EnemiesFlashed"] + stat2["EnemiesFlashed"],
        "GrenadesThrown": stat1["GrenadesThrown"] + stat2["GrenadesThrown"],
        "ClutchAttempts": stat1["ClutchAttempts"] + stat2["ClutchAttempts"],
        "ClutchWins": stat1["ClutchWins"] + stat2["ClutchWins"],
        "DuelAttempts": stat1["DuelAttempts"] + stat2["DuelAttempts"],
        "DuelWins": stat1["DuelWins"] + stat2["DuelWins"],
        "Rounds": combined_rounds,
        "KAST": round((stat1["KAST"] * stat1["Rounds"] + stat2["KAST"] * stat2["Rounds"]) / combined_rounds, 2) if combined_rounds > 0 else 0,
        "ADR": round((stat1["Damage"] + stat2["Damage"]) / combined_rounds, 2) if combined_rounds > 0 else 0,
        "KPR": round((stat1["Kills"] + stat2["Kills"]) / combined_rounds, 2) if combined_rounds > 0 else 0,
        "APR": round((stat1["Assists"] + stat2["Assists"]) / combined_rounds, 2) if combined_rounds > 0 else 0,
        "DPR": round((stat1["Deaths"] + stat2["Deaths"]) / combined_rounds, 2) if combined_rounds > 0 else 0
    }

    combined_stat["Impact"] = round(2.13 * combined_stat["KPR"] + 0.42 * combined_stat["APR"] - 0.41, 2) if combined_rounds > 0 else 0
    combined_stat["Rating"] = round((0.0073 * combined_stat["KAST"] + 0.3591 * combined_stat["KPR"] -
                                     0.5329 * combined_stat["DPR"] + 0.2372 * combined_stat["Impact"] +
                                     0.0032 * combined_stat["ADR"] + 0.1587), 2) if combined_rounds > 0 else 0

    return combined_stat
