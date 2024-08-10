from flask import Blueprint, jsonify, request, g
from mysql.connector import Error

match_bp = Blueprint("match_routes", __name__)

@match_bp.route("/get_matches")
def get_matches():    
    cursor = None
    try:
        cursor = g.db.cursor(dictionary=True)
        cursor.execute(f"SELECT * FROM `Match` ORDER BY `MatchDate` DESC")
        matches = cursor.fetchall()
        return jsonify(matches)

    except Error as e:
        print(f"Error: {e}")
        return jsonify({"error": "Failed to fetch data."}), 500
    
    finally:
        if cursor:
            cursor.close()

@match_bp.route("/get_matches_by_map")
def get_matches_by_map():
    map_name = request.args.get("map")
    
    cursor = None
    try:
        cursor = g.db.cursor(dictionary=True)
        cursor.execute(f"SELECT * FROM `Match` WHERE Map = %s ORDER BY `MatchDate` DESC", (map_name,))
        matches = cursor.fetchall()
        return jsonify(matches)
    
    except Error as e:
        print(f"Error: {e}")
        return jsonify({"error": "Failed to fetch data."}), 500
    
    finally:
        if cursor:
            cursor.close()

@match_bp.route("/get_matches_by_player_id")
def get_matches_by_player_id():
    player_id = request.args.get("player_id")
    map_name = request.args.get("map")
    
    if not player_id:
        return jsonify({"error": "player_id is required"}), 400
    
    cursor = None
    try:
        cursor = g.db.cursor(dictionary=True)
        
        if map_name:
            query = """
            SELECT 
                m.MatchID,
                m.Map,
                m.TeamTID,
                m.TeamCTID,
                m.TeamTScore,
                m.TeamCTScore,
                m.MatchDate
            FROM 
                Player_Match pm
            JOIN 
                `Match` m ON pm.MatchID = m.MatchID
            WHERE 
                pm.PlayerID = %s AND m.Map = %s
            """
            cursor.execute(query, (player_id, map_name))
        
        else:
            query = """
            SELECT 
                m.MatchID,
                m.Map,
                m.TeamTID,
                m.TeamCTID,
                m.TeamTScore,
                m.TeamCTScore,
                m.MatchDate
            FROM 
                Player_Match pm
            JOIN 
                `Match` m ON pm.MatchID = m.MatchID
            WHERE 
                pm.PlayerID = %s
            """
            cursor.execute(query, (player_id,))
        
        player_matches = cursor.fetchall()
        
        if player_matches:
            return jsonify(player_matches)
        else:
            return jsonify({"error": "Player matches not found."}), 404
    
    except Error as e:
        print(f"Error: {e}")
        return jsonify({"error": "Failed to fetch player matches."}), 500
    
    finally:
        if cursor:
            cursor.close()

@match_bp.route("/get_match_by_match_id")
def get_match_by_match_id():
    match_id = request.args.get("match_id")
    
    cursor = None
    try:
        cursor = g.db.cursor(dictionary=True)

        # Query to get match details along with team and player stats, including usernames
        cursor.execute("""
            SELECT 
                m.MatchID, m.Map, m.TeamTID, m.TeamCTID, m.TeamTScore, m.TeamCTScore, m.MatchDate,
                tt.TeamID AS TeamTID, tc.TeamID AS TeamCTID,
                tp.TeamID AS PlayerTeamID, ps.PlayerID, p.Username, ps.Kills, ps.Headshots, ps.Assists, 
                ps.Deaths, ps.TotalDamage, ps.UtilityDamage, ps.RoundsPlayed
            FROM `Match` m
            JOIN `Team` tt ON m.TeamTID = tt.TeamID
            JOIN `Team` tc ON m.TeamCTID = tc.TeamID
            JOIN `Player_Match` pm ON m.MatchID = pm.MatchID
            JOIN `PlayerStat` ps ON pm.PlayerID = ps.PlayerID
            JOIN `Match_PlayerStat` mps ON m.MatchID = mps.MatchID AND ps.PlayerStatID = mps.PlayerStatID
            JOIN `TeamPlayer` tp ON pm.PlayerID = tp.PlayerID
            JOIN `Player` p ON ps.PlayerID = p.PlayerID
            WHERE m.MatchID = %s
            ORDER BY m.MatchDate DESC
        """, (match_id,))
        
        matches = cursor.fetchall()
        
        if not matches:
            return jsonify({"error": "Match not found."}), 404
        
        # Organizing data into a structured JSON response
        match_data = {
            "MatchID": matches[0]['MatchID'],
            "Map": matches[0]['Map'],
            "TeamT": {
                "TeamID": matches[0]['TeamTID'],
                "Players": []
            },
            "TeamCT": {
                "TeamID": matches[0]['TeamCTID'],
                "Players": []
            },
            "TeamTScore": matches[0]['TeamTScore'],
            "TeamCTScore": matches[0]['TeamCTScore'],
            "MatchDate": matches[0]['MatchDate']
        }

        # Organize player stats by teams based on PlayerTeamID
        for row in matches:
            player_stats = {
                "PlayerID": row['PlayerID'],
                "Username": row['Username'],  # Include the Username
                "Kills": row['Kills'],
                "Headshots": row['Headshots'],
                "Assists": row['Assists'],
                "Deaths": row['Deaths'],
                "TotalDamage": row['TotalDamage'],
                "UtilityDamage": row['UtilityDamage'],
                "RoundsPlayed": row['RoundsPlayed']
            }
            
            if row['PlayerTeamID'] == match_data['TeamT']['TeamID']:
                match_data['TeamT']['Players'].append(player_stats)
            elif row['PlayerTeamID'] == match_data['TeamCT']['TeamID']:
                match_data['TeamCT']['Players'].append(player_stats)

        return jsonify(match_data)
        
    except Error as e:
        print(f"Error: {e}")
        return jsonify({"error": "Failed to fetch data."}), 500
    
    finally:
        if cursor:
            cursor.close()
