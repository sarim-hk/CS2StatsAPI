from flask import Blueprint, jsonify, g
from mysql.connector import Error

live_match_panel_bp = Blueprint("live_match_panel_bp", __name__)


@live_match_panel_bp.route("/live_match_panel")
def live_match_panel():
    cursor = None
    try:
        cursor = g.db.cursor(dictionary=True)
        
        # First get the match status
        cursor.execute(
            """
            SELECT TScore, CTScore, BombStatus, MapID, 
                   UNIX_TIMESTAMP(InsertDate) AS InsertDate 
            FROM CS2S_LiveStatus 
            WHERE StaticID = 1
            """
        )
        match_status = cursor.fetchone()

        if match_status is None:
            return jsonify({"error": "No match found."}), 404

        # Get T-side players
        cursor.execute(
            """
            SELECT CS2S_LivePlayers.PlayerID, CS2S_PlayerInfo.Username, Kills, Assists, Deaths, ADR, Health, Money
            FROM CS2S_LivePlayers
            INNER JOIN CS2S_PlayerInfo ON CS2S_LivePlayers.PlayerID = CS2S_PlayerInfo.PlayerID
            WHERE Side = 2
            """
        )
        t_players = cursor.fetchall()

        # Get CT-side players
        cursor.execute(
            """
            SELECT CS2S_LivePlayers.PlayerID, CS2S_PlayerInfo.Username, Kills, Assists, Deaths, ADR, Health, Money
            FROM CS2S_LivePlayers
            INNER JOIN CS2S_PlayerInfo ON CS2S_LivePlayers.PlayerID = CS2S_PlayerInfo.PlayerID
            WHERE Side = 3
            """
        )
        ct_players = cursor.fetchall()

        # Combine all data
        response = {
            "TScore": match_status["TScore"],
            "CTScore": match_status["CTScore"],
            "BombStatus": match_status["BombStatus"],
            "InsertDate": match_status["InsertDate"],
            "MapID": match_status["MapID"],
            "TPlayers": t_players,
            "CTPlayers": ct_players
        }

        return jsonify(response)

    except Error as e:
        print(f"Error: {e}")
        return jsonify({"error": "Failed to fetch data."}), 500

    finally:
        if cursor:
            cursor.close()
