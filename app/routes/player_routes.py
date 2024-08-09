from flask import Blueprint, jsonify, request, g, current_app
from mysql.connector import Error
from ..utilities import get_steam_summaries

player_bp = Blueprint("player_routes", __name__)

@player_bp.route("/get_players_or_player")
def get_players_or_player():
    cursor = None
    player_id = request.args.get("player_id")
    try:
        cursor = g.db.cursor(dictionary=True)

        if player_id:
            cursor.execute("SELECT * FROM `Player` WHERE PlayerID = %s", (player_id,))
            players = cursor.fetchall()
        else:
            cursor.execute("SELECT * FROM `Player` ORDER BY `ELO` DESC")
            players = cursor.fetchall()
        
        if not players:
            return jsonify({"error": "Player(s) not found."}), 404
        
        steam_ids = [str(player["PlayerID"]) for player in players]
        steam_summaries = get_steam_summaries(steam_ids, current_app.config["STEAM_API_KEY"])
        
        for player in players:
            steam_summary = steam_summaries.get(str(player["PlayerID"]), {})
            player["Avatar"] = steam_summary.get("avatarmedium")
            player["Username"] = steam_summary.get("personaname")

        if player_id:
            return jsonify(players[0])
        else:
            return jsonify(players)

    except Error as e:
        print(f"Error: {e}")
        return jsonify({"error": "Failed to fetch data."}), 500
    
    finally:
        if cursor:
            cursor.close()

@player_bp.route("/get_player_matches")
def get_player_matches():
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

@player_bp.route("/get_player_playerstats")
def get_player_playerstats():
    player_id = request.args.get("player_id")
    if not player_id:
        return jsonify({"error": "player_id is required"}), 400

    cursor = None
    try:
        cursor = g.db.cursor(dictionary=True)
        query = """
        SELECT 
            ps.PlayerStatID,
            ps.Kills,
            ps.Headshots,
            ps.Assists,
            ps.Deaths,
            ps.TotalDamage,
            ps.UtilityDamage,
            ps.RoundsPlayed
        FROM 
            Player_PlayerStat pps
        JOIN 
            PlayerStat ps ON pps.PlayerStatID = ps.PlayerStatID
        WHERE 
            pps.PlayerID = %s
        """
        cursor.execute(query, (player_id,))
        player_playerstats = cursor.fetchall()
        
        if player_playerstats:
            return jsonify(player_playerstats)
        else:
            return jsonify({"error": "Player playerstats not found."}), 404
        
    except Error as e:
        print(f"Error: {e}")
        return jsonify({"error": "Failed to fetch player playerstats."}), 500
    
    finally:
        if cursor:
            cursor.close()
