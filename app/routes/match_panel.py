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
             clutches, duels, kast_stats, blinds, damage_stats, player_teams) = fetch_match_data(cursor, match_id)
            
            players_stats = {}
            
            # Create a dict to track rounds played per side for each player
            player_side_rounds = {}
            
            # Create player to team mapping
            player_team_map = {player['PlayerID']: player['TeamID'] for player in player_teams}
            
            # Count rounds per side for each player first
            for round in rounds:
                winner_team = round['WinnerTeamID']
                loser_team = round['LoserTeamID']
                winner_side = round['WinnerSide']
                loser_side = round['LoserSide']
                
                for player_id, team_id in player_team_map.items():
                    if player_id not in player_side_rounds:
                        player_side_rounds[player_id] = {'2': 0, '3': 0}
                    
                    if team_id == winner_team:
                        player_side_rounds[player_id][str(winner_side)] += 1
                    elif team_id == loser_team:
                        player_side_rounds[player_id][str(loser_side)] += 1

            for kast in kast_stats:
                player_id = kast['PlayerID']
                player_side = kast['PlayerSide']
                
                if player_id not in players_stats:
                    players_stats[player_id] = _create_empty_side_stats(player_id)

                players_stats[player_id]["Overall"]["KAST"] += 1
                if player_side == 2:
                    players_stats[player_id]["Terrorist"]["KAST"] += 1
                elif player_side == 3:
                    players_stats[player_id]["CounterTerrorist"]["KAST"] += 1

            for blind in blinds:
                player_id = blind['ThrowerID']
                thrower_side = blind['ThrowerSide']
                
                if player_id not in players_stats:
                    players_stats[player_id] = _create_empty_side_stats(player_id)

                players_stats[player_id]["Overall"]["Blinds"]["Count"] += 1
                players_stats[player_id]["Overall"]["Blinds"]["TotalDuration"] += blind['Duration']
                
                if thrower_side == 2:
                    players_stats[player_id]["Terrorist"]["Blinds"]["Count"] += 1
                    players_stats[player_id]["Terrorist"]["Blinds"]["TotalDuration"] += blind['Duration']
                elif thrower_side == 3:
                    players_stats[player_id]["CounterTerrorist"]["Blinds"]["Count"] += 1
                    players_stats[player_id]["CounterTerrorist"]["Blinds"]["TotalDuration"] += blind['Duration']

            for death in deaths:
                victim_id = death['VictimID']
                attacker_id = death['AttackerID']
                assister_id = death['AssisterID']
                hitgroup = death['Hitgroup']
                victim_side = death['VictimSide']
                
                if victim_id not in players_stats:
                    players_stats[victim_id] = _create_empty_side_stats(victim_id)
                    
                players_stats[victim_id]["Overall"]["Deaths"] += 1
                if victim_side == 2:
                    players_stats[victim_id]["Terrorist"]["Deaths"] += 1
                elif victim_side == 3:
                    players_stats[victim_id]["CounterTerrorist"]["Deaths"] += 1

                if attacker_id:
                    if attacker_id not in players_stats:
                        players_stats[attacker_id] = _create_empty_side_stats(attacker_id)

                    players_stats[attacker_id]["Overall"]["Kills"] += 1
                    if victim_side == 2:  # If victim was Terrorist, attacker was CT
                        players_stats[attacker_id]["CounterTerrorist"]["Kills"] += 1
                    elif victim_side == 3:  # If victim was CT, attacker was Terrorist
                        players_stats[attacker_id]["Terrorist"]["Kills"] += 1

                    if hitgroup == 1:
                        players_stats[attacker_id]["Overall"]["Headshots"] += 1
                        if victim_side == 2:
                            players_stats[attacker_id]["CounterTerrorist"]["Headshots"] += 1
                        elif victim_side == 3:
                            players_stats[attacker_id]["Terrorist"]["Headshots"] += 1

                if assister_id:
                    if assister_id not in players_stats:
                        players_stats[assister_id] = _create_empty_side_stats(assister_id)

                    players_stats[assister_id]["Overall"]["Assists"] += 1
                    if victim_side == 2:
                        players_stats[assister_id]["CounterTerrorist"]["Assists"] += 1
                    elif victim_side == 3:
                        players_stats[assister_id]["Terrorist"]["Assists"] += 1

            for damage in damage_stats:
                attacker_id = damage['AttackerID']
                damage_amount = damage['Damage']
                weapon = damage['Weapon']
                victim_side = damage['VictimSide']

                if attacker_id:
                    if attacker_id not in players_stats:
                        players_stats[attacker_id] = _create_empty_side_stats(attacker_id)

                    players_stats[attacker_id]["Overall"]["Damage"] += damage_amount
                    
                    if weapon in ['smokegrenade', 'molotov', 'inferno', 'hegrenade', 'flashbang', 'decoy']:
                        players_stats[attacker_id]["Overall"]["UtilityDamage"] += damage_amount
                    
                    if victim_side == 2:  # If victim was Terrorist, attacker was CT
                        players_stats[attacker_id]["CounterTerrorist"]["Damage"] += damage_amount
                        if weapon in ['smokegrenade', 'molotov', 'inferno', 'hegrenade', 'flashbang', 'decoy']:
                            players_stats[attacker_id]["CounterTerrorist"]["UtilityDamage"] += damage_amount
                    elif victim_side == 3:  # If victim was CT, attacker was Terrorist
                        players_stats[attacker_id]["Terrorist"]["Damage"] += damage_amount
                        if weapon in ['smokegrenade', 'molotov', 'inferno', 'hegrenade', 'flashbang', 'decoy']:
                            players_stats[attacker_id]["Terrorist"]["UtilityDamage"] += damage_amount

            for player_id, stats in players_stats.items():
                # Set common player info for all sides
                for side in ["Overall", "Terrorist", "CounterTerrorist"]:
                    stats[side]["Username"] = players_info_dict[player_id]["Username"]
                    stats[side]["AvatarL"] = players_info_dict[player_id]["AvatarL"]
                
                # Get the actual rounds played per side for this player
                if player_id in player_side_rounds:
                    t_rounds = player_side_rounds[player_id]['2']  # Terrorist rounds
                    ct_rounds = player_side_rounds[player_id]['3']  # CT rounds
                    total_rounds = t_rounds + ct_rounds
                else:
                    t_rounds = 0
                    ct_rounds = 0
                    total_rounds = 0
                
                # Calculate stats for each side
                _calculate_derived_stats(stats["Overall"], total_rounds)
                _calculate_derived_stats(stats["Terrorist"], t_rounds)
                _calculate_derived_stats(stats["CounterTerrorist"], ct_rounds)

            teams = {}
            for team_result in team_results:
                team_id = team_result["TeamID"]
                
                # Fetch team name
                team_name_query = "SELECT Name FROM CS2S_Team WHERE TeamID = %s"
                cursor.execute(team_name_query, (team_id,))
                team_name_result = cursor.fetchone()
                
                teams[team_id] = {
                    **team_result, 
                    "TeamName": team_name_result['Name'],
                    "Players": {}
                }
                
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
            match['Deaths'] = deaths

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

def _create_empty_side_stats(player_id):
    return {
        "Overall": _create_empty_playerstat(player_id),
        "Terrorist": _create_empty_playerstat(player_id),
        "CounterTerrorist": _create_empty_playerstat(player_id)
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

    player_teams_query = """
        SELECT tp.PlayerID, tp.TeamID
        FROM CS2S_Team_Players tp
        JOIN CS2S_TeamResult tr ON tp.TeamID = tr.TeamID
        WHERE tr.MatchID = %s
    """
    
    cursor.execute(player_teams_query, (match_id,))
    player_teams = cursor.fetchall()
    
    return match, players_info_dict, team_results, rounds, deaths, clutches, duels, kast_stats, blinds, damage_stats, player_teams

def calculate_impact_and_rating(kpr, apr, dpr, kast, adr):
    impact = ((2.13 * kpr) + (0.42 * apr) - 0.41) or 0
    rating = ((0.0073 * kast) + (0.3591 * kpr) + (-0.5329 * dpr) + (0.2372 * impact) + (0.0032 * adr)  + 0.1587) or 0
    return impact, rating



def _calculate_derived_stats(stats, total_rounds):
    """Calculate derived statistics for a given side's stats"""
    if total_rounds > 0:
        stats["Rounds"] = total_rounds
        stats["KAST"] = (stats["KAST"] / total_rounds) * 100
        stats["KPR"] = stats["Kills"] / total_rounds
        stats["APR"] = stats["Assists"] / total_rounds
        stats["DPR"] = stats["Deaths"] / total_rounds
        stats["ADR"] = stats["Damage"] / total_rounds

        stats["Impact"], stats["Rating"] = calculate_impact_and_rating(
            stats["KPR"],
            stats["APR"],
            stats["DPR"],
            stats["KAST"],
            stats["ADR"]
        )

        stats["KAST"] = round(stats["KAST"], 2) or 0
        stats["KPR"] = round(stats["KPR"], 2) or 0
        stats["APR"] = round(stats["APR"], 2) or 0
        stats["DPR"] = round(stats["DPR"], 2) or 0
        stats["ADR"] = round(stats["ADR"], 2) or 0
        stats["Impact"] = round(stats["Impact"], 2) or 0
        stats["Rating"] = round(stats["Rating"], 2) or 0

    else:
        stats["Rounds"] = 0
        stats["KAST"] = 0
        stats["KPR"] = 0
        stats["APR"] = 0
        stats["DPR"] = 0
        stats["ADR"] = 0
        stats["Impact"] = 0
        stats["Rating"] = 0