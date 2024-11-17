from flask import Blueprint, jsonify, request, g, current_app
from mysql.connector import Error

playerelo_panel_bp = Blueprint("playerelo_panel_bp", __name__)

@playerelo_panel_bp.route("/playerelo_panel_bp_by_player_id")
def playerelo_panel_bp_by_player_id():
    player_id = request.args.get("player_id")
    
    if not player_id:
        return jsonify({"error": "Player ID is required"}), 400

    try:
        cursor = g.db.cursor(dictionary=True)

        # Query to get the current ELO and the last 10 matches with DeltaELO
        cursor.execute("""
            SELECT 
                p.PlayerID,
                p.ELO AS CurrentELO,
                tr.MatchID,
                tr.DeltaELO
            FROM 
                CS2S_PlayerInfo p
            JOIN 
                CS2S_Player_Matches pm ON p.PlayerID = pm.PlayerID
            JOIN 
                CS2S_TeamResult tr ON pm.MatchID = tr.MatchID
            WHERE 
                tr.TeamID IN (
                    SELECT TeamID 
                    FROM CS2S_Team_Players 
                    WHERE PlayerID = p.PlayerID
                )
                AND p.PlayerID = %s
            ORDER BY 
                tr.MatchID DESC
            LIMIT 10;
        """, (player_id,))

        results = cursor.fetchall()

        if not results:
            return jsonify({"error": "No data found for the given Player ID"}), 404

        # Extract current ELO
        current_elo = results[0]["CurrentELO"]

        # Calculate ELO history
        elo_history = []
        calculated_elo = current_elo  # Start with the current ELO
        for match in results:
            calculated_elo -= match["DeltaELO"]  # Reverse-apply DeltaELO to get previous ELO
            elo_history.append({
                "MatchID": match["MatchID"],
                "DeltaELO": match["DeltaELO"],
                "ELOBeforeMatch": calculated_elo
            })

        # Format the response
        response = {
            "PlayerID": player_id,
            "CurrentELO": current_elo,
            "ELOHistory": elo_history
        }

        return jsonify(response)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
