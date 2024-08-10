from flask import Blueprint, jsonify, request, g, current_app
from mysql.connector import Error
from ..utilities import get_steam_summaries

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
        
        steam_summaries = get_steam_summaries([player["PlayerID"]], current_app.config["STEAM_API_KEY"])
        steam_summary = steam_summaries.get(player["PlayerID"], {})
        player["Avatar"] = steam_summary.get("avatarmedium")
        player["Username"] = steam_summary.get("personaname")

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
        
        steam_ids = [str(player["PlayerID"]) for player in players]
        steam_summaries = get_steam_summaries(steam_ids, current_app.config["STEAM_API_KEY"])
        
        for player in players:
            steam_summary = steam_summaries.get(str(player["PlayerID"]), {})
            player["Avatar"] = steam_summary.get("avatarmedium")
            player["Username"] = steam_summary.get("personaname")

        return jsonify(players)

    except Error as e:
        print(f"Error: {e}")
        return jsonify({"error": "Failed to fetch data."}), 500
    
    finally:
        if cursor:
            cursor.close()

