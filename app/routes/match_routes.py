from flask import Blueprint, jsonify, request, g
from mysql.connector import Error

match_bp = Blueprint("match_routes", __name__)

@match_bp.route("/get_matches_or_match")
def get_matches_or_match():
    match_id = request.args.get("match_id")
    map_name = request.args.get("map")
    
    cursor = None
    try:
        cursor = g.db.cursor(dictionary=True)
        
        if match_id:
            cursor.execute(f"SELECT * FROM `Match` WHERE MatchID = %s ORDER BY `MatchDate` DESC", (match_id,))
            match = cursor.fetchone()
            if match:
                return jsonify(match)
            else:
                return jsonify({"error": "Match not found."}), 404
        
        elif map_name:
            cursor.execute(f"SELECT * FROM `Match` WHERE Map = %s ORDER BY `MatchDate` DESC", (map_name,))
            matches = cursor.fetchall()
            return jsonify(matches)
        
        else:
            cursor.execute(f"SELECT * FROM `Match` ORDER BY `MatchDate` DESC")
            matches = cursor.fetchall()
            return jsonify(matches)
    
    except Error as e:
        print(f"Error: {e}")
        return jsonify({"error": "Failed to fetch data."}), 500
    
    finally:
        if cursor:
            cursor.close()

@match_bp.route("/get_match_playerstats")
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
