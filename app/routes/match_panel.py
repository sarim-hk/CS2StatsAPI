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

            # Query to get the match details
            match_query = """
                SELECT * FROM CS2S_Match
                WHERE MatchID = %s
            """
            cursor.execute(match_query, (match_id,))
            match = cursor.fetchone()

            if not match:
                return jsonify({"error": "Match not found."}), 404
            
            players_info_query = """
                SELECT PlayerID, Username, AvatarS
                FROM CS2S_PlayerInfo
            """
            cursor.execute(players_info_query)
            players_info = cursor.fetchall()

            # Convert the player info into a dictionary for easy lookup
            players_info_dict = {player['PlayerID']: player for player in players_info}

            # Query to get team results
            team_results_query = """
                SELECT * FROM CS2S_TeamResult
                WHERE MatchID = %s
            """
            cursor.execute(team_results_query, (match_id,))
            team_results = cursor.fetchall()
            
            # Query to get rounds
            rounds_query = """
                SELECT * FROM CS2S_Round
                WHERE MatchID = %s
            """
            cursor.execute(rounds_query, (match_id,))
            rounds = cursor.fetchall()

            # Query to get deaths
            deaths_query = """
                SELECT * FROM CS2S_Death
                WHERE MatchID = %s
            """
            cursor.execute(deaths_query, (match_id,))
            deaths = cursor.fetchall()

            # Query to get clutches
            clutches_query = """
                SELECT * FROM CS2S_Clutch
                WHERE MatchID = %s AND Result = 'Win'
            """
            cursor.execute(clutches_query, (match_id,))
            clutches = cursor.fetchall()

            # Query to get duels
            duels_query = """
                SELECT * FROM CS2S_Duel
                WHERE MatchID = %s
            """
            cursor.execute(duels_query, (match_id,))
            duels = cursor.fetchall()

            # Query to get KAST statistics
            kast_query = """
                SELECT * FROM CS2S_KAST
                WHERE MatchID = %s
            """
            cursor.execute(kast_query, (match_id,))
            kast_stats = cursor.fetchall()

            # Query to get blind statistics
            blinds_query = """
                SELECT * FROM CS2S_Blind
                WHERE MatchID = %s
            """
            cursor.execute(blinds_query, (match_id,))
            blinds = cursor.fetchall()

            # Query to get damage statistics
            damage_query = """
                SELECT * FROM CS2S_Hurt
                WHERE MatchID = %s
            """
            cursor.execute(damage_query, (match_id,))
            damage_stats = cursor.fetchall()

            # Aggregating player statistics
            players_stats = {}

            # Process KAST stats
            for kast in kast_stats:
                player_id = kast['PlayerID']
                if player_id not in players_stats:
                    players_stats[player_id] = {
                        "KAST": 0,
                        "Blinds": {"Count": 0, "TotalDuration": 0.0},
                        "Deaths": 0,
                        "Kills": 0,
                        "Assists": 0,
                        "DamageAmount": 0,
                        "UtilityDamage": 0,
                        "Rounds": 0,
                    }
                players_stats[player_id]["KAST"] += 1

            # Process blind stats
            for blind in blinds:
                player_id = blind['ThrowerID']
                if blind['TeamFlash'] == 0:  # Only count non-team flashes
                    if player_id not in players_stats:
                        players_stats[player_id] = {
                            "KAST": 0,
                            "Blinds": {"Count": 0, "TotalDuration": 0.0},
                            "Deaths": 0,
                            "Kills": 0,
                            "Assists": 0,
                            "DamageAmount": 0,
                            "UtilityDamage": 0,
                            "Rounds": 0,
                        }
                    players_stats[player_id]["Blinds"]["Count"] += 1
                    players_stats[player_id]["Blinds"]["TotalDuration"] += blind['Duration']

            # Process death stats
            for death in deaths:
                victim_id = death['VictimID']
                attacker_id = death['AttackerID']
                assister_id = death['AssisterID']

                if victim_id not in players_stats:
                    players_stats[victim_id] = {
                        "KAST": 0,
                        "Blinds": {"Count": 0, "TotalDuration": 0.0},
                        "Deaths": 0,
                        "Kills": 0,
                        "Assists": 0,
                        "DamageAmount": 0,
                        "UtilityDamage": 0,
                        "Rounds": 0,
                    }
                players_stats[victim_id]["Deaths"] += 1

                if attacker_id:
                    if attacker_id not in players_stats:
                        players_stats[attacker_id] = {
                            "KAST": 0,
                            "Blinds": {"Count": 0, "TotalDuration": 0.0},
                            "Deaths": 0,
                            "Kills": 0,
                            "Assists": 0,
                            "DamageAmount": 0,
                            "UtilityDamage": 0,
                            "Rounds": 0,
                        }
                    players_stats[attacker_id]["Kills"] += 1

                if assister_id:
                    if assister_id not in players_stats:
                        players_stats[assister_id] = {
                            "KAST": 0,
                            "Blinds": {"Count": 0, "TotalDuration": 0.0},
                            "Deaths": 0,
                            "Kills": 0,
                            "Assists": 0,
                            "DamageAmount": 0,
                            "UtilityDamage": 0,
                            "Rounds": 0,
                        }
                    players_stats[assister_id]["Assists"] += 1

            # Process damage stats
            for damage in damage_stats:
                attacker_id = damage['AttackerID']
                damage_amount = damage['DamageAmount']
                weapon = damage['Weapon']

                if attacker_id:
                    if attacker_id not in players_stats:
                        players_stats[attacker_id] = {
                            "KAST": 0,
                            "Blinds": {"Count": 0, "TotalDuration": 0.0},
                            "Deaths": 0,
                            "Kills": 0,
                            "Assists": 0,
                            "DamageAmount": 0,
                            "UtilityDamage": 0,
                            "Rounds": 0,
                        }
                    
                    players_stats[attacker_id]["DamageAmount"] += damage_amount
                    
                    # Check if damage was from a grenade
                    if weapon in ['smokegrenade', 'molotov', 'inferno', 'hegrenade', 'flashbang', 'decoy']:
                        players_stats[attacker_id]["UtilityDamage"] += damage_amount

            # Calculate total rounds played
            total_rounds = len(rounds)
            for player_id, stats in players_stats.items():
                stats["Rounds"] = total_rounds  # Set the total rounds played
                stats["Username"] = players_info_dict[player_id]["Username"]
                stats["AvatarS"] = players_info_dict[player_id]["AvatarS"]

                # Calculate KAST percentage
                if total_rounds > 0:
                    stats["KAST"] = round((stats["KAST"] / total_rounds) * 100, 2)
                
                # Calculate KPR, DPR, and ADR
                kpr = round(stats["Kills"] / total_rounds, 2) if total_rounds > 0 else 0
                dpr = round(stats["Deaths"] / total_rounds, 2) if total_rounds > 0 else 0
                adr = round(stats["DamageAmount"] / total_rounds, 2) if total_rounds > 0 else 0

                # Calculate Impact
                impact = round(2.13 * kpr + 0.42 * (stats["Assists"] / total_rounds) - 0.41, 2) if total_rounds > 0 else 0

                # Calculate Rating 2.0
                rating = round(
                    (0.0073 * stats["KAST"] +
                     0.3591 * kpr +
                     -0.5329 * dpr +
                     0.2372 * impact +
                     0.0032 * adr +
                     0.1587), 2
                )
                
                # Store ratings
                stats["KPR"] = kpr
                stats["DPR"] = dpr
                stats["ADR"] = adr
                stats["Impact"] = impact
                stats["Rating"] = rating

            # Query to get players grouped by teams
            teams = {}
            for team_result in team_results:
                team_id = team_result["TeamID"]
                
                # Initialize the team with the results and an empty player dictionary
                teams[team_id] = {**team_result, "Players": {}}
                
                # Get players for this team
                team_players_query = """
                    SELECT PlayerID FROM CS2S_Team_Players
                    WHERE TeamID = %s
                """
                cursor.execute(team_players_query, (team_id,))
                team_players = cursor.fetchall()

                # Add player stats to the team
                for player in team_players:
                    player_id = player['PlayerID']
                    if player_id in players_stats:
                        teams[team_id]["Players"][player_id] = players_stats[player_id]

            # Build the final match dictionary
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
