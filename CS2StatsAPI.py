from functools import wraps
from Config import Config
from flask import Flask, jsonify, request
from mysql.connector import Error
import mysql.connector

app = Flask(__name__)

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        provided_key = request.args.get("API_KEY")
        if provided_key != api_key:
            return jsonify({"error": "Invalid API key."}), 403
        return f(*args, **kwargs)
    return decorated_function

@app.route("/api/get_matches_or_match")
@require_api_key
def get_matches_or_match():
    match_id = request.args.get("match_id")
    map_name = request.args.get("map")
    
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        
        if match_id:
            cursor.execute("SELECT * FROM `Match` WHERE MatchID = %s", (match_id,))
            match = cursor.fetchone()
            if match:
                return jsonify(match)
            else:
                return jsonify({"error": "Match not found."}), 404
        
        elif map_name:
            cursor.execute("SELECT * FROM `Match` WHERE Map = %s", (map_name,))
            matches = cursor.fetchall()
            return jsonify(matches)
        
        else:
            cursor.execute("SELECT * FROM `Match`")
            matches = cursor.fetchall()
            return jsonify(matches)
    
    except Error as e:
        print(f"Error: {e}")
        return jsonify({"error": "Failed to fetch data."}), 500
    
    finally:
        if cursor:
            cursor.close()

@app.route("/api/get_players_or_player")
@require_api_key
def get_players_or_player():
    player_id = request.args.get("player_id")
    
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        
        if player_id:
            cursor.execute("SELECT * FROM `Player` WHERE PlayerID = %s", (player_id,))
            player = cursor.fetchone()
            if player:
                return jsonify(player)
            else:
                return jsonify({"error": "Player not found."}), 404
        
        else:
            cursor.execute("SELECT * FROM `Player`")
            players = cursor.fetchall()
            return jsonify(players)
    
    except Error as e:
        print(f"Error: {e}")
        return jsonify({"error": "Failed to fetch data."}), 500
    
    finally:
        if cursor:
            cursor.close()

@app.route("/api/get_playerstats_or_playerstat")
@require_api_key
def get_playerstats_or_playerstat():
    playerstat_id = request.args.get("playerstat_id")
    
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        
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

@app.route("/api/get_match_playerstats")
@require_api_key
def get_match_playerstats():
    match_id = request.args.get("match_id")
    if not match_id:
        return jsonify({"error": "match_id is required"}), 400

    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
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

@app.route("/api/get_player_matches")
@require_api_key
def get_player_matches():
    player_id = request.args.get("player_id")
    map_name = request.args.get("map")
    
    if not player_id:
        return jsonify({"error": "player_id is required"}), 400
    
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        
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

@app.route("/api/get_player_playerstats")
@require_api_key
def get_player_playerstats():
    player_id = request.args.get("player_id")
    if not player_id:
        return jsonify({"error": "player_id is required"}), 400

    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
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

@app.route("/api/get_teamplayers")
@require_api_key
def get_teamplayers():
    team_id = request.args.get("team_id")
    if not team_id:
        return jsonify({"error": "team_id is required"}), 400

    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
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

if __name__ == "__main__":
    cfg = Config()
    api_key = cfg.cfg["API_KEY"]

    try:
        connection = mysql.connector.connect(
            host=cfg.cfg["MySQLServer"],
            database=cfg.cfg["MySQLDatabase"],
            user=cfg.cfg["MySQLUsername"],
            password=cfg.cfg["MySQLPassword"]
        )

    except Exception as e:
        print("Failed to connect to the MySQL database.")
        print(e)
        exit()

    app.run(debug=True)
