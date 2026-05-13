from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import DatabaseConnection, DatabaseCursor, get_db

router = APIRouter()


@router.get("/playerelo_panel")
def playerelo_panel(
    player_id: str = Query(...),
    db: DatabaseConnection = Depends(get_db),
) -> dict[str, Any]:
    cursor: DatabaseCursor | None = None
    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            """
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
            LIMIT 10
            """,
            (player_id,),
        )

        results = cursor.fetchall()

        if not results:
            raise HTTPException(status_code=404, detail="No data found for the given Player ID")

        current_elo = results[0]["CurrentELO"]
        calculated_elo = current_elo
        elo_history: list[dict[str, Any]] = []

        for match in results:
            calculated_elo -= match["DeltaELO"]
            elo_history.append(
                {
                    "MatchID": match["MatchID"],
                    "DeltaELO": match["DeltaELO"],
                    "ELOBeforeMatch": calculated_elo,
                }
            )

        return {
            "PlayerID": player_id,
            "CurrentELO": current_elo,
            "ELOHistory": elo_history,
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    finally:
        if cursor:
            cursor.close()
