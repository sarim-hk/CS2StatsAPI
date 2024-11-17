from flask import Blueprint, jsonify, g, request
from mysql.connector import Error

match_panel_bp = Blueprint('match_panel_bp', __name__)

@match_panel_bp.route("/match_panel_by_match_id")
def match_panel_by_match_id():
    match_id = request.args.get("match_id")

    if match_id:
        cursor = None
        try:
            cursor = g.db.cursor(dictionary=True)

            (match, players_info_dict, team_results, rounds, deaths,
             clutches, duels, kast_stats, blinds, damage_stats) = fetch_match_data(cursor, match_id)
            
            players_stats = {}

            for kast in kast_stats:
                player_id = kast['PlayerID']
                if player_id not in players_stats:
                    players_stats[player_id] = _create_empty_playerstat(player_id)

                players_stats[player_id]["KAST"] += 1

            for blind in blinds:
                player_id = blind['ThrowerID']
                if player_id not in players_stats:
                    players_stats[player_id] = _create_empty_playerstat(player_id)

                players_stats[player_id]["Blinds"]["Count"] += 1
                players_stats[player_id]["Blinds"]["TotalDuration"] += blind['Duration']

            for death in deaths:
                victim_id = death['VictimID']
                attacker_id = death['AttackerID']
                assister_id = death['AssisterID']
                hitgroup = death['Hitgroup']

                if victim_id not in players_stats:
                    players_stats[victim_id] = _create_empty_playerstat(victim_id)
                    
                players_stats[victim_id]["Deaths"] += 1

                if attacker_id:
                    if attacker_id not in players_stats:
                        players_stats[attacker_id] = _create_empty_playerstat(attacker_id)

                    players_stats[attacker_id]["Kills"] += 1

                    if hitgroup == 1:
                        players_stats[attacker_id]["Headshots"] += 1

                if assister_id:
                    if assister_id not in players_stats:
                        players_stats[assister_id] = _create_empty_playerstat(assister_id)

                    players_stats[assister_id]["Assists"] += 1

            for damage in damage_stats:
                attacker_id = damage['AttackerID']
                damage_amount = damage['Damage']
                weapon = damage['Weapon']

                if attacker_id:
                    if attacker_id not in players_stats:
                        players_stats[attacker_id] = _create_empty_playerstat(attacker_id)

                    players_stats[attacker_id]["Damage"] += damage_amount
                    
                    if weapon in ['smokegrenade', 'molotov', 'inferno', 'hegrenade', 'flashbang', 'decoy']:
                        players_stats[attacker_id]["UtilityDamage"] += damage_amount

            total_rounds = len(rounds)
            for player_id, stats in players_stats.items():
                stats["Rounds"] = total_rounds
                stats["Username"] = players_info_dict[player_id]["Username"]
                stats["AvatarL"] = players_info_dict[player_id]["AvatarL"]

                if total_rounds > 0:
                    stats["KAST"] = round((stats["KAST"] / total_rounds) * 100, 2)
                
                stats["KPR"] = round(stats["Kills"] / total_rounds, 2) if total_rounds > 0 else 0
                stats["DPR"] = round(stats["Deaths"] / total_rounds, 2) if total_rounds > 0 else 0
                stats["ADR"] = round(stats["Damage"] / total_rounds, 2) if total_rounds > 0 else 0

                stats["Impact"] = round(2.13 * stats["KPR"] + 0.42 * (stats["Assists"] / total_rounds) - 0.41, 2) if total_rounds > 0 else 0
                stats["Rating"] = round((0.0073 * stats["KAST"] + 0.3591 * stats["KPR"] + -0.5329 * stats["DPR"] + 0.2372 *
                                stats["Impact"] + 0.0032 * stats["ADR"] + 0.1587), 2)
                
            teams = {}
            for team_result in team_results:
                team_id = team_result["TeamID"]
                
                teams[team_id] = {**team_result, "Players": {}}
                
                team_players_query = """
                    SELECT PlayerID FROM CS2S_Team_Players
                    WHERE TeamID = %s
                """
                cursor.execute(team_players_query, (team_id,))
                team_players = cursor.fetchall()

                for player in team_players:
                    player_id = player['PlayerID']
                    if player_id in players_stats:
                        teams[team_id]["Players"][player_id] = players_stats[player_id]

            match['Teams'] = teams
            match['Clutches'] = clutches
            match['Duels'] = duels
            match['Rounds'] = rounds

            return jsonify(match)

        except Error as e:
            print(f"Error: {e}")
            return jsonify({"error": "Failed to fetch data."}), 500
        
        finally:
            if cursor:
                cursor.close()
    else:
        return jsonify({"error": "Match ID parameter is required."}), 400

def _create_empty_playerstat(player_id):
    return {
    "PlayerID": player_id,
    "KAST": 0,
    "Blinds": {"Count": 0, "TotalDuration": 0.0},
    "Deaths": 0,
    "Kills": 0,
    "Assists": 0,
    "Damage": 0,
    "UtilityDamage": 0,
    "Rounds": 0,
    "Headshots": 0
    }

def fetch_match_data(cursor, match_id):
    match_query = "SELECT * FROM CS2S_Match WHERE MatchID = %s"
    players_info_query = "SELECT PlayerID, Username, AvatarL FROM CS2S_PlayerInfo"
    team_results_query = "SELECT * FROM CS2S_TeamResult WHERE MatchID = %s"
    rounds_query = "SELECT * FROM CS2S_Round WHERE MatchID = %s"
    deaths_query = "SELECT * FROM CS2S_Death WHERE MatchID = %s"
    clutches_query = "SELECT * FROM CS2S_Clutch WHERE MatchID = %s"
    duels_query = "SELECT * FROM CS2S_Duel WHERE MatchID = %s"
    kast_query = "SELECT * FROM CS2S_KAST WHERE MatchID = %s"
    blinds_query = "SELECT * FROM CS2S_Blind WHERE MatchID = %s"
    damage_query = "SELECT * FROM CS2S_Hurt WHERE MatchID = %s"

    cursor.execute(match_query, (match_id,))
    match = cursor.fetchone()
    if not match:
        return None

    cursor.execute(players_info_query)
    players_info = cursor.fetchall()
    players_info_dict = {player['PlayerID']: player for player in players_info}

    cursor.execute(team_results_query, (match_id,))
    team_results = cursor.fetchall()

    cursor.execute(rounds_query, (match_id,))
    rounds = cursor.fetchall()

    cursor.execute(deaths_query, (match_id,))
    deaths = cursor.fetchall()

    cursor.execute(clutches_query, (match_id,))
    clutches = cursor.fetchall()

    cursor.execute(duels_query, (match_id,))
    duels = cursor.fetchall()

    cursor.execute(kast_query, (match_id,))
    kast_stats = cursor.fetchall()

    cursor.execute(blinds_query, (match_id,))
    blinds = cursor.fetchall()

    cursor.execute(damage_query, (match_id,))
    damage_stats = cursor.fetchall()

    return match, players_info_dict, team_results, rounds, deaths, clutches, duels, kast_stats, blinds, damage_stats
