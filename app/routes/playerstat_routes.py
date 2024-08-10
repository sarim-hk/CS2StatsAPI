from flask import Blueprint, jsonify, request, g
from mysql.connector import Error

playerstat_bp = Blueprint("playerstat_routes", __name__)

@playerstat_bp.route("/get_player_playerstats_by_player_id")
def get_player_playerstats_by_player_id():
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

# unused so far and needs restructuring into two separate api calls
@playerstat_bp.route("/get_playerstats_or_playerstat")
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
