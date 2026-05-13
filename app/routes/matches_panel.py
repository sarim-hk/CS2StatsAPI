from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from mysql.connector import Error

from app.database import DatabaseConnection, DatabaseCursor, get_db

router = APIRouter()


def fetch_matches(
    db: DatabaseConnection,
    query_extension: str = "",
    params: tuple[Any, ...] | None = None,
    page: int | None = None,
) -> list[dict[str, Any]]:
    cursor: DatabaseCursor | None = None
    try:
        cursor = db.cursor(dictionary=True)
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
            {query_extension}
            ORDER BY
                m.MatchDate DESC
            {" LIMIT %s OFFSET %s" if page is not None else ""}
        """

        query_params: list[Any] = list(params) if params is not None else []
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
def matches_panel(
    page: int | None = Query(None, ge=1),
    db: DatabaseConnection = Depends(get_db),
) -> list[dict[str, Any]]:
    return fetch_matches(db=db, page=page)


@router.get("/matches_panel_by_map")
def matches_panel_by_map(
    map_name: str = Query(..., alias="map"),
    page: int | None = Query(None, ge=1),
    db: DatabaseConnection = Depends(get_db),
) -> list[dict[str, Any]]:
    return fetch_matches(
        db=db,
        query_extension="WHERE m.MapID = %s",
        params=(map_name,),
        page=page,
    )


@router.get("/matches_panel_by_player_id")
def matches_panel_by_player_id(
    player_id: str = Query(...),
    page: int | None = Query(None, ge=1),
    db: DatabaseConnection = Depends(get_db),
) -> list[dict[str, Any]]:
    return fetch_matches(
        db=db,
        query_extension="""
            JOIN CS2S_Player_Matches pm ON m.MatchID = pm.MatchID
            WHERE pm.PlayerID = %s
        """,
        params=(player_id,),
        page=page,
    )
