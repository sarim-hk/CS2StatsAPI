from flask import Blueprint, jsonify, request, g
from mysql.connector import Error

match_bp = Blueprint("match_routes", __name__)

@match_bp.route("/matches_panel")
def matches_panel():
    cursor = None
    try:
        cursor = g.db.cursor(dictionary=True)
        
        cursor.execute("""
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
            ORDER BY 
                m.MatchDate DESC
        """)
        
        matches = cursor.fetchall()
        return jsonify(matches)

    except Error as e:
        print(f"Error: {e}")
        return jsonify({"error": "Failed to fetch data."}), 500
    
    finally:
        if cursor:
            cursor.close()


@match_bp.route("/matches_panel_by_map")
def get_matches_by_map():
    map_name = request.args.get("map")
    
    cursor = None
    try:
        cursor = g.db.cursor(dictionary=True)
        cursor.execute("""
                       SELECT *
                       FROM CS2S_Match
                       WHERE Map = %s
                       ORDER BY MatchDate DESC
                       """, (map_name,))
        
        matches = cursor.fetchall()
        return jsonify(matches)
    
    except Error as e:
        print(f"Error: {e}")
        return jsonify({"error": "Failed to fetch data."}), 500
    
    finally:
        if cursor:
            cursor.close()

@match_bp.route("/matches_panel_by_player_id")
def get_matches_by_player_id():
    player_id = request.args.get("player_id")
    
    cursor = None
    try:
        cursor = g.db.cursor(dictionary=True)
        cursor.execute("""
                       SELECT M.*
                       FROM CS2S_Match M
                       JOIN CS2S_Team_Players TPW ON TPW.TeamID = M.WinningTeamID
                       JOIN CS2S_Team_Players TPL ON TPL.TeamID = M.LosingTeamID
                       WHERE TPW.PlayerID = %s OR TPL.PlayerID = %s
                       ORDER BY M.MatchDate DESC
                       """, (player_id, player_id))
        
        matches = cursor.fetchall()
        return jsonify(matches)
    
    except Error as e:
        print(f"Error: {e}")
        return jsonify({"error": "Failed to fetch data."}), 500
    
    finally:
        if cursor:
            cursor.close()

@match_bp.route("/get_match_by_match_id")
def get_match_by_match_id():
    match_id = request.args.get("match_id")
    
    cursor = None
    try:
        cursor = g.db.cursor(dictionary=True)

        cursor.execute("""
                        SELECT 
                            p.PlayerID,
                            pinfo.Username,
                            
                            -- Kill stats
                            COUNT(DISTINCT CASE WHEN d.AttackerID = p.PlayerID THEN d.DeathID END) AS Kills,
                            COUNT(DISTINCT CASE WHEN d.AttackerID = p.PlayerID AND d.Hitgroup = 1 THEN d.DeathID END) AS Headshots,
                            
                            -- Assist stats
                            COUNT(DISTINCT CASE WHEN d.AssisterID = p.PlayerID THEN d.DeathID END) AS Assists,
                            
                            -- Death stats (when the player is the victim)
                            COUNT(DISTINCT CASE WHEN d.VictimID = p.PlayerID THEN d.DeathID END) AS Deaths,
                            
                            -- Hurt stats (damage inflicted and taken)
                            SUM(CASE WHEN h.AttackerID = p.PlayerID THEN h.DamageAmount END) AS TotalDamageInflicted,
                            SUM(CASE WHEN h.VictimID = p.PlayerID THEN h.DamageAmount END) AS TotalDamageTaken,
                            
                            -- Utility damage (from grenades, etc.)
                            SUM(CASE WHEN h.AttackerID = p.PlayerID AND h.Weapon IN ('smokegrenade', 'hegrenade', 'inferno', 'flashbang', 'decoy') THEN h.DamageAmount END) AS UtilityDamage,
                            
                            -- Rounds played (distinct rounds in which the player was involved)
                            COUNT(DISTINCT r.RoundID) AS RoundsPlayed

                        FROM CS2S_Round r
                        LEFT JOIN CS2S_Death d ON r.RoundID = d.RoundID
                        LEFT JOIN CS2S_Hurt h ON r.RoundID = h.RoundID
                        LEFT JOIN CS2S_Player p ON p.PlayerID = d.AttackerID OR p.PlayerID = d.VictimID OR p.PlayerID = h.AttackerID OR p.PlayerID = h.VictimID
                        LEFT JOIN CS2S_PlayerInfo pinfo ON p.PlayerID = pinfo.PlayerID

                        WHERE r.MatchID = 3  -- Replace %s with the match ID parameter
                        AND p.PlayerID IS NOT NULL  -- Exclude rows with NULL PlayerID

                        GROUP BY p.PlayerID
                        ORDER BY p.PlayerID;
                    """, (match_id, ))

        player_stats = cursor.fetchall()
        
        if not player_stats:
            return jsonify({"error": "Match not found."}), 404
        
        # Organizing data into a structured JSON response
        match_data = {
            "MatchID": matches[0]['MatchID'],
            "Map": matches[0]['Map'],
            "TeamT": {
                "TeamID": matches[0]['TeamTID'],
                "Players": []
            },
            "TeamCT": {
                "TeamID": matches[0]['TeamCTID'],
                "Players": []
            },
            "TeamTScore": matches[0]['TeamTScore'],
            "TeamCTScore": matches[0]['TeamCTScore'],
            "MatchDate": matches[0]['MatchDate']
        }

        # Organize player stats by teams based on PlayerTeamID
        for row in matches:
            player_stats = {
                "PlayerID": row['PlayerID'],
                "Username": row['Username'],  # Include the Username
                "Kills": row['Kills'],
                "Headshots": row['Headshots'],
                "Assists": row['Assists'],
                "Deaths": row['Deaths'],
                "TotalDamage": row['TotalDamage'],
                "UtilityDamage": row['UtilityDamage'],
                "RoundsPlayed": row['RoundsPlayed']
            }
            
            if row['PlayerTeamID'] == match_data['TeamT']['TeamID']:
                match_data['TeamT']['Players'].append(player_stats)
            elif row['PlayerTeamID'] == match_data['TeamCT']['TeamID']:
                match_data['TeamCT']['Players'].append(player_stats)

        return jsonify(match_data)
        
    except Error as e:
        print(f"Error: {e}")
        return jsonify({"error": "Failed to fetch data."}), 500
    
    finally:
        if cursor:
            cursor.close()

@match_bp.route("/live_match_panel")
def live_match_panel():    
    cursor = None
    try:
        cursor = g.db.cursor(dictionary=True)
        cursor.execute("""
            SELECT TPlayers, CTPlayers, TScore, CTScore, BombStatus, 
                   UNIX_TIMESTAMP(InsertDate) AS InsertDate 
            FROM CS2S_Live 
            WHERE StaticID = 1
        """)       

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
