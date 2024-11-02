from flask import Blueprint, jsonify, request, g, current_app
from mysql.connector import Error

players_panel_bp = Blueprint("players_panel_bp", __name__)

@players_panel_bp.route("/players_panel")
def players_panel():
    cursor = None
    try:
        cursor = g.db.cursor(dictionary=True)

        cursor.execute("""
                       SELECT *
                       FROM CS2S_Player
                       INNER JOIN CS2S_PlayerInfo ON CS2S_Player.PlayerID = CS2S_PlayerInfo.PlayerID
                       ORDER BY ELO DESC
                       """)

        players = cursor.fetchall()
        
        if not players:
            return jsonify({"error": "Player(s) not found."}), 404
        else:
            return jsonify(players)

    except Error as e:
        print(f"Error: {e}")
        return jsonify({"error": "Failed to fetch data."}), 500
    
    finally:
        if cursor:
            cursor.close()

