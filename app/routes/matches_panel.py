from flask import Blueprint, jsonify, g, request
from mysql.connector import Error

matches_panel_bp = Blueprint('matches_panel_bp', __name__)

@matches_panel_bp.route("/matches_panel")
def matches_panel(query_extension="", params=None):
    cursor = None
    try:
        cursor = g.db.cursor(dictionary=True)
        
        base_query = f"""
            SELECT 
                m.MatchID,
                m.MapID,
                m.MatchDate,
                tr_w.TeamID AS WinningTeamID,
                tr_l.TeamID AS LosingTeamID,
                tr_w.Score AS WinningTeamScore,
                tr_l.Score AS LosingTeamScore,
                tr_w.Side AS WinningSide,
                tr_w.DeltaELO AS WinningDeltaELO,
                tr_l.DeltaELO AS LosingDeltaELO
            FROM 
                CS2S_Match m
            JOIN 
                CS2S_TeamResult tr_w ON m.MatchID = tr_w.MatchID AND tr_w.Result = 'Win'
            JOIN 
                CS2S_TeamResult tr_l ON m.MatchID = tr_l.MatchID AND tr_l.Result = 'Loss'
            {query_extension}
            ORDER BY 
                m.MatchDate DESC
        """

        cursor.execute(base_query, params or ())
        matches = cursor.fetchall()
        return jsonify(matches)

    except Error as e:
        print(f"Error: {e}")
        return jsonify({"error": "Failed to fetch data."}), 500
    
    finally:
        if cursor:
            cursor.close()

@matches_panel_bp.route("/matches_panel_by_map")
def matches_panel_by_map():
    map_name = request.args.get("map")

    if map_name:
        query_extension = "WHERE m.MapID = %s"
        params = (map_name,)
        return matches_panel(query_extension=query_extension, params=params)
    else:
        return jsonify({"error": "Map parameter is required."}), 400
    
@matches_panel_bp.route("/matches_panel_by_player_id")
def matches_panel_by_player_id():
    player_id = request.args.get("player_id")

    if player_id:
        query_extension = """
            JOIN CS2S_Player_Matches pm ON m.MatchID = pm.MatchID
            WHERE pm.PlayerID = %s
        """
        params = (player_id,)
        return matches_panel(query_extension=query_extension, params=params)
    else:
        return jsonify({"error": "Player ID parameter is required."}), 400