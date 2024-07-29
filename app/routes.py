from flask import Blueprint, jsonify, request, current_app, g
from .utilities import get_steam_summaries
from mysql.connector import Error

bp = Blueprint("routes", __name__)

@bp.route("/api/get_matches_or_match")
def get_matches_or_match():
    match_id = request.args.get("match_id")
    map_name = request.args.get("map")
    
    cursor = None
    try:
        cursor = g.db.cursor(dictionary=True)
        
        columns = """
            MatchID,
            Map,
            TeamTID,
            TeamCTID,
            TeamTScore,
            TeamCTScore,
            DATE_FORMAT(MatchDate, '%d/%m/%Y %H:%i:%s') AS MatchDate
            """
        
        if match_id:
            cursor.execute(f"SELECT {columns} FROM `Match` WHERE MatchID = %s", (match_id,))
            match = cursor.fetchone()
            if match:
                return jsonify(match)
            else:
                return jsonify({"error": "Match not found."}), 404
        
        elif map_name:
            cursor.execute(f"SELECT {columns} FROM `Match` WHERE Map = %s", (map_name,))
            matches = cursor.fetchall()
            return jsonify(matches)
        
        else:
            cursor.execute(f"SELECT {columns} FROM `Match`")
            matches = cursor.fetchall()
            return jsonify(matches)
    
    except Error as e:
        print(f"Error: {e}")
        return jsonify({"error": "Failed to fetch data."}), 500
    
    finally:
        if cursor:
            cursor.close()

@bp.route("/api/get_players_or_player")
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
            player["Avatar"] = steam_summary["avatarmedium"]
            player["Username"] = steam_summary["personaname"]

        return jsonify(players)
    
    except Error as e:
        print(f"Error: {e}")
        return jsonify({"error": "Failed to fetch data."}), 500
    
    finally:
        if cursor:
            cursor.close()

@bp.route("/api/get_playerstats_or_playerstat")
def get_playerstats_or_playerstat():
    playerstat_id = request.args.get("playerstat_id")
    
    cursor = None
    try:
        cursor = g.db.cursor(dictionary=True)
        
        if playerstat_id:
            cursor.execute("SELECT * FROM `PlayerStat` WHERE PlayerStatID = %s", (playerstat_id,))
            playerstat = cursor.fetchone()
            
            if playerstat:
                return jsonify(playerstat)
            else:
                return jsonify({"error": "Playerstat not found."}), 404
        
        else:
            cursor.execute("SELECT * FROM `PlayerStat`")
            playerstats = cursor.fetchall()
            return jsonify(playerstats)
    
    except Error as e:
        print(f"Error: {e}")
        return jsonify({"error": "Failed to fetch playerstat(s)."}), 500
    
    finally:
        if cursor:
            cursor.close()

@bp.route("/api/get_match_playerstats")
def get_match_playerstats():
    match_id = request.args.get("match_id")
    if not match_id:
        return jsonify({"error": "match_id is required"}), 400

    cursor = None
    try:
        cursor = g.db.cursor(dictionary=True)
        query = """
        SELECT 
            ps.PlayerStatID,
            ps.PlayerID,
            ps.Kills,
            ps.Headshots,
            ps.Assists,
            ps.Deaths,
            ps.TotalDamage,
            ps.UtilityDamage,
            ps.RoundsPlayed
        FROM 
            Match_PlayerStat mp
        JOIN 
            PlayerStat ps ON mp.PlayerStatID = ps.PlayerStatID
        WHERE 
            mp.MatchID = %s
        """
        cursor.execute(query, (match_id,))
        match_playerstats = cursor.fetchall()
        
        if match_playerstats:
            return jsonify(match_playerstats)
        else:
            return jsonify({"error": "Match playerstats not found."}), 404
        
    except Error as e:
        print(f"Error: {e}")
        return jsonify({"error": "Failed to fetch match playerstats."}), 500
    
    finally:
        if cursor:
            cursor.close()

@bp.route("/api/get_player_matches")
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

@bp.route("/api/get_player_playerstats")
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

@bp.route("/api/get_teamplayers")
def get_teamplayers():
    team_id = request.args.get("team_id")
    if not team_id:
        return jsonify({"error": "team_id is required"}), 400

    cursor = None
    try:
        cursor = g.db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM `TeamPlayer` WHERE TeamID = %s", (team_id,))
        team_players = cursor.fetchall()
        
        if team_players:
            return jsonify(team_players)
        else:
            return jsonify({"error": "Team players not found."}), 404
        
    except Error as e:
        print(f"Error: {e}")
        return jsonify({"error": "Failed to fetch team players."}), 500
    
    finally:
        if cursor:
            cursor.close()
