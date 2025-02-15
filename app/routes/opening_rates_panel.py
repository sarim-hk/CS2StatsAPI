from flask import Blueprint, Response, g, jsonify
from mysql.connector import Error

OPENING_RATES_SQL = """
WITH OpeningStats AS (
    SELECT 
        AttackerID AS PlayerID,
        COUNT(*) AS T_OpeningKills,
        0 AS CT_OpeningKills,
        0 AS T_OpeningDeaths,
        0 AS CT_OpeningDeaths
    FROM CS2S_Death
    WHERE OpeningDeath = TRUE 
      AND AttackerID IS NOT NULL
      AND AttackerSide = 2  -- T side
    GROUP BY AttackerID
    
    UNION ALL
    
    SELECT 
        AttackerID AS PlayerID,
        0 AS T_OpeningKills,
        COUNT(*) AS CT_OpeningKills,
        0 AS T_OpeningDeaths,
        0 AS CT_OpeningDeaths
    FROM CS2S_Death
    WHERE OpeningDeath = TRUE 
      AND AttackerID IS NOT NULL
      AND AttackerSide = 3  -- CT side
    GROUP BY AttackerID
    
    UNION ALL
    
    SELECT 
        VictimID AS PlayerID,
        0 AS T_OpeningKills,
        0 AS CT_OpeningKills,
        COUNT(*) AS T_OpeningDeaths,
        0 AS CT_OpeningDeaths
    FROM CS2S_Death
    WHERE OpeningDeath = TRUE
      AND VictimSide = 2  -- T side
    GROUP BY VictimID
    
    UNION ALL
    
    SELECT 
        VictimID AS PlayerID,
        0 AS T_OpeningKills,
        0 AS CT_OpeningKills,
        0 AS T_OpeningDeaths,
        COUNT(*) AS CT_OpeningDeaths
    FROM CS2S_Death
    WHERE OpeningDeath = TRUE
      AND VictimSide = 3  -- CT side
    GROUP BY VictimID
),
PlayerRounds AS (
    -- Get total rounds played by each player on each side
    SELECT 
        TP.PlayerID,
        COUNT(DISTINCT CASE 
            WHEN (R.WinnerTeamID = TP.TeamID AND R.WinnerSide = 2) OR 
                 (R.LoserTeamID = TP.TeamID AND R.LoserSide = 2) 
            THEN R.RoundID 
        END) AS T_Rounds,
        COUNT(DISTINCT CASE 
            WHEN (R.WinnerTeamID = TP.TeamID AND R.WinnerSide = 3) OR 
                 (R.LoserTeamID = TP.TeamID AND R.LoserSide = 3) 
            THEN R.RoundID 
        END) AS CT_Rounds,
        COUNT(DISTINCT R.RoundID) AS TotalRoundsPlayed
    FROM CS2S_Team_Players TP
    JOIN CS2S_Round R ON (R.WinnerTeamID = TP.TeamID OR R.LoserTeamID = TP.TeamID)
    GROUP BY TP.PlayerID
)

SELECT 
    OS.PlayerID,
    PI.Username,
    SUM(OS.T_OpeningKills) AS T_OpeningKills,
    SUM(OS.T_OpeningDeaths) AS T_OpeningDeaths,
    SUM(OS.T_OpeningDeaths) + SUM(OS.T_OpeningKills) AS T_OpeningAttempts,
    ROUND(CASE 
        WHEN SUM(OS.T_OpeningDeaths) + SUM(OS.T_OpeningKills) = 0 THEN 0
        ELSE SUM(OS.T_OpeningKills) / (SUM(OS.T_OpeningDeaths) + SUM(OS.T_OpeningKills)) * 100 
    END, 2) AS T_OpeningSuccessRate,
    ROUND(CASE 
        WHEN PR.T_Rounds = 0 THEN 0
        ELSE CAST((SUM(OS.T_OpeningDeaths) + SUM(OS.T_OpeningKills)) AS FLOAT) / PR.T_Rounds * 100 
    END, 2) AS T_OpeningAttemptRate,
    
    SUM(OS.CT_OpeningKills) AS CT_OpeningKills,
    SUM(OS.CT_OpeningDeaths) AS CT_OpeningDeaths,
    SUM(OS.CT_OpeningDeaths) + SUM(OS.CT_OpeningKills) AS CT_OpeningAttempts,
    ROUND(CASE 
        WHEN SUM(OS.CT_OpeningDeaths) + SUM(OS.CT_OpeningKills) = 0 THEN 0
        ELSE SUM(OS.CT_OpeningKills) / (SUM(OS.CT_OpeningDeaths) + SUM(OS.CT_OpeningKills)) * 100 
    END, 2) AS CT_OpeningSuccessRate,
    ROUND(CASE 
        WHEN PR.CT_Rounds = 0 THEN 0
        ELSE CAST((SUM(OS.CT_OpeningDeaths) + SUM(OS.CT_OpeningKills)) AS FLOAT) / PR.CT_Rounds * 100 
    END, 2) AS CT_OpeningAttemptRate,
    
    SUM(OS.T_OpeningKills + OS.CT_OpeningKills) AS Total_OpeningKills,
    SUM(OS.T_OpeningDeaths + OS.CT_OpeningDeaths) AS Total_OpeningDeaths,
    SUM(OS.T_OpeningKills + OS.CT_OpeningKills + OS.T_OpeningDeaths + OS.CT_OpeningDeaths) AS Total_OpeningAttempts,
    ROUND(CASE 
        WHEN SUM(OS.T_OpeningKills + OS.CT_OpeningKills + OS.T_OpeningDeaths + OS.CT_OpeningDeaths) = 0 THEN 0
        ELSE SUM(OS.T_OpeningKills + OS.CT_OpeningKills) / 
             SUM(OS.T_OpeningKills + OS.CT_OpeningKills + OS.T_OpeningDeaths + OS.CT_OpeningDeaths) * 100 
    END, 2) AS Total_OpeningSuccessRate,
    ROUND(CAST(SUM(OS.T_OpeningKills + OS.CT_OpeningKills + OS.T_OpeningDeaths + OS.CT_OpeningDeaths) AS FLOAT) / 
    PR.TotalRoundsPlayed * 100, 2) AS Total_OpeningAttemptRate
FROM OpeningStats AS OS
INNER JOIN CS2S_PlayerInfo AS PI ON OS.PlayerID = PI.PlayerID
INNER JOIN PlayerRounds AS PR ON OS.PlayerID = PR.PlayerID
GROUP BY 
    OS.PlayerID, 
    PI.Username, 
    PR.T_Rounds, 
    PR.CT_Rounds, 
    PR.TotalRoundsPlayed
ORDER BY Total_OpeningKills DESC;
"""


opening_rates_bp = Blueprint("opening_rates_bp", __name__)


@opening_rates_bp.route("/opening_rates")
def opening_rates() -> Response:
    try:
        with g.db.cursor(dictionary=True) as cursor:
            cursor.execute(OPENING_RATES_SQL)
            result = cursor.fetchall()

            if result is None:
                return Response("No data found.", status=404)

            return jsonify(result)
    except Error as e:
        print(f"Error: {e}")
        return Response("Failed to fetch data.", status=500)
