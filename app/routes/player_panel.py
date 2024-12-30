from flask import Blueprint, jsonify, request, g, current_app
from mysql.connector import Error

player_panel_bp = Blueprint("player_panel_bp", __name__)

@player_panel_bp.route("/player_panel_by_player_id")
def player_panel_by_player_id():
    cursor = None
    player_id = request.args.get("player_id")
    try:
        cursor = g.db.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                p.*,
                pow.WeekPosition
            FROM CS2S_PlayerInfo p
            LEFT JOIN CS2S_PlayerOfTheWeek pow 
                ON p.PlayerID = pow.PlayerID
            WHERE p.PlayerID = %s
        """, (player_id,))

        player = cursor.fetchone()

        if not player:
            return jsonify({"error": "Player not found."}), 404
        else:
            return jsonify(player)

    except Error as e:
        print(f"Error: {e}")
        return jsonify({"error": "Failed to fetch data."}), 500
    
    finally:
        if cursor:
            cursor.close()