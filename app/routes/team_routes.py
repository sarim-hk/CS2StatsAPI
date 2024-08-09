from flask import Blueprint, jsonify, request, g
from mysql.connector import Error

team_bp = Blueprint("team_routes", __name__)

@team_bp.route("/get_teamplayers")
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
