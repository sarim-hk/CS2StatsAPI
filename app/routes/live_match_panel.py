from flask import Blueprint, jsonify, g
from mysql.connector import Error

live_match_panel_bp = Blueprint("live_match_panel_bp", __name__)


@live_match_panel_bp.route("/live_match_panel")
def live_match_panel():
    cursor = None
    try:
        cursor = g.db.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT TPlayers, CTPlayers, TScore, CTScore, BombStatus, 
                   UNIX_TIMESTAMP(InsertDate) AS InsertDate 
            FROM CS2S_Live 
            WHERE StaticID = 1
        """
        )

        match = cursor.fetchone()

        if match is None:
            return jsonify({"error": "No match found."}), 404

        for key, value in match.items():
            if value is None:
                return jsonify({"error": f"The field '{key}' is null."}), 400

        return jsonify(match)

    except Error as e:
        print(f"Error: {e}")
        return jsonify({"error": "Failed to fetch data."}), 500

    finally:
        if cursor:
            cursor.close()
