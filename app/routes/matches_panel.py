from fastapi import APIRouter, Depends, HTTPException, Query
from mysql.connector import Error

from app.database import get_db

router = APIRouter()


def fetch_matches(db, player_id=None, map_name=None, page=None):
    cursor = None
    try:
        cursor = db.cursor(dictionary=True)

        joins = []
        filters = []
        query_params = []

        if player_id is not None:
            joins.append("JOIN CS2S_Player_Matches pm ON m.MatchID = pm.MatchID")
            filters.append("pm.PlayerID = %s")
            query_params.append(player_id)

        if map_name is not None:
            filters.append("m.MapID = %s")
            query_params.append(map_name)

        join_sql = "\n".join(joins)
        where_sql = f"WHERE {' AND '.join(filters)}" if filters else ""

        base_query = f"""
            SELECT
                m.MatchID,
                m.MapID,
                m.MatchDate,
                tr_w.TeamID AS WinningTeamID,
                t_w.Name AS WinningTeamName,
                tr_l.TeamID AS LosingTeamID,
                t_l.Name AS LosingTeamName,
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
            JOIN
                CS2S_Team t_w ON tr_w.TeamID = t_w.TeamID
            JOIN
                CS2S_Team t_l ON tr_l.TeamID = t_l.TeamID
            {join_sql}
            {where_sql}
            ORDER BY
                m.MatchID DESC
            {" LIMIT %s OFFSET %s" if page is not None else ""}
        """

        if page is not None:
            per_page = 25
            query_params.extend([per_page, (page - 1) * per_page])

        cursor.execute(base_query, tuple(query_params))
        return cursor.fetchall()

    except Error as exc:
        print(f"Error: {exc}")
        raise HTTPException(status_code=500, detail="Failed to fetch data.") from exc

    finally:
        if cursor:
            cursor.close()


@router.get("/matches_panel")
def matches_panel(player_id = None, map_name = Query(None, alias="map"), page = Query(None, ge=1), db=Depends(get_db)):
    return fetch_matches(db=db, player_id=player_id, map_name=map_name, page=page)
