from flask import Blueprint, jsonify, request, g, current_app
from mysql.connector import Error

player_bp = Blueprint("player_routes", __name__)

@player_bp.route("/get_player_by_player_id")
def get_player_by_player_id():
    cursor = None
    player_id = request.args.get("player_id")
    try:
        cursor = g.db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM `Player` WHERE PlayerID = %s", (player_id,))
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

@player_bp.route("/get_players")
def get_players_or_player():
    cursor = None
    try:
        cursor = g.db.cursor(dictionary=True)

        cursor.execute("SELECT * FROM `Player` ORDER BY `ELO` DESC")
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

