from flask import Blueprint, jsonify, request, g
from mysql.connector import Error

playerstat_bp = Blueprint("playerstat_routes", __name__)

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
