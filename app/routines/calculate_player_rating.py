from datetime import datetime, timedelta
from pathlib import Path

from app.database import fetch_player_stats_for_rounds, fetch_round_sides_for_player_matches, transaction
from app.utils.stats import UTILITY_WEAPONS, apply_derived_stats, combine_player_stats, empty_player_stats

SIDE_OVERALL = 0
SIDE_TERRORIST = 2
SIDE_COUNTER_TERRORIST = 3
STORED_SIDES = (SIDE_OVERALL, SIDE_TERRORIST, SIDE_COUNTER_TERRORIST)


def refresh_player_ratings(range_days, settings=None, player_ids=None):
    with transaction(settings) as db:
        return refresh_player_ratings_for_db(db, range_days, player_ids=player_ids)


def refresh_player_ratings_for_db(db, range_days, player_ids=None):
    cutoff = datetime.now() - timedelta(days=range_days)
    cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")

    cursor = db.cursor(dictionary=True)
    try:
        if player_ids is None:
            player_ids = fetch_player_ids_since(cursor, cutoff_str)
            clear_player_ratings(cursor, range_days)
        else:
            player_ids = list(dict.fromkeys(player_ids))
            if not player_ids:
                return {
                    "RangeDays": range_days,
                    "PlayersProcessed": 0,
                    "RowsWritten": 0,
                }
            clear_player_ratings(cursor, range_days, player_ids=player_ids)

        rows_written = 0
        for player_id in player_ids:
            player_ratings = calculate_player_rating_for_range(cursor, player_id, cutoff_str)
            for side, stats in player_ratings.items():
                upsert_player_rating(cursor, player_id, range_days, side, stats)
                rows_written += 1

        return {
            "RangeDays": range_days,
            "PlayersProcessed": len(player_ids),
            "RowsWritten": rows_written,
        }
    finally:
        cursor.close()


def calculate_player_rating_for_range(cursor, player_id, cutoff_str):
    match_ids = fetch_player_match_ids_since(cursor, player_id, cutoff_str)
    matches_played = len(match_ids)
    t_round_ids, ct_round_ids = split_round_ids_by_side(cursor, match_ids, player_id)

    t_stats = calculate_stats_for_rounds(cursor, t_round_ids, player_id)
    ct_stats = calculate_stats_for_rounds(cursor, ct_round_ids, player_id)
    overall_stats = combine_player_stats(t_stats, ct_stats)

    overall_stats["MatchesPlayed"] = matches_played
    t_stats["MatchesPlayed"] = matches_played
    ct_stats["MatchesPlayed"] = matches_played

    return {
        SIDE_OVERALL: overall_stats,
        SIDE_TERRORIST: t_stats,
        SIDE_COUNTER_TERRORIST: ct_stats,
    }


def fetch_player_ids_since(cursor, cutoff_str):
    cursor.execute(
        """
        SELECT DISTINCT pm.PlayerID
        FROM CS2S_Player_Matches pm
        JOIN CS2S_Match m ON pm.MatchID = m.MatchID
        WHERE m.MatchDate >= %s
        ORDER BY pm.PlayerID
        """,
        (cutoff_str,),
    )
    return [row["PlayerID"] for row in cursor.fetchall()]


def fetch_player_match_ids_since(cursor, player_id, cutoff_str):
    cursor.execute(
        """
        SELECT DISTINCT pm.MatchID
        FROM CS2S_Player_Matches pm
        JOIN CS2S_Match m ON pm.MatchID = m.MatchID
        WHERE pm.PlayerID = %s
          AND m.MatchDate >= %s
        ORDER BY pm.MatchID DESC
        """,
        (player_id, cutoff_str),
    )
    return [row["MatchID"] for row in cursor.fetchall()]


def split_round_ids_by_side(cursor, match_ids, player_id):
    if not match_ids:
        return [], []

    rounds = fetch_round_sides_for_player_matches(cursor, match_ids, player_id)
    t_round_ids = [match_round["RoundID"] for match_round in rounds if match_round["PlayerSide"] == SIDE_TERRORIST]
    ct_round_ids = [
        match_round["RoundID"]
        for match_round in rounds
        if match_round["PlayerSide"] == SIDE_COUNTER_TERRORIST
    ]

    return t_round_ids, ct_round_ids


def calculate_stats_for_rounds(cursor, round_ids, player_id):
    if not round_ids:
        return empty_player_stats(player_id)

    result = fetch_player_stats_for_rounds(cursor, round_ids, player_id, UTILITY_WEAPONS)
    if result is None:
        return empty_player_stats(player_id)

    stats = {
        "PlayerID": player_id,
        "Damage": int(result["Damage"] or 0),
        "UtilityDamage": int(result["UtilityDamage"] or 0),
        "Kills": int(result["Kills"] or 0),
        "Assists": int(result["Assists"] or 0),
        "Deaths": int(result["Deaths"] or 0),
        "Headshots": int(result["Headshots"] or 0),
        "Blinds": {
            "Count": int(result["EnemiesFlashed"] or 0),
            "TotalDuration": float(result["TotalDuration"] or 0),
        },
        "RoundsPlayed": len(round_ids),
        "RoundsKAST": int(result["RoundsKAST"] or 0),
    }

    return apply_derived_stats(
        stats,
        stats["RoundsPlayed"],
        kast_rounds=stats["RoundsKAST"],
        zero_value=0,
    )


def clear_player_ratings(cursor, range_days, player_ids=None):
    if player_ids is not None and not player_ids:
        return

    side_placeholders = ", ".join(["%s"] * len(STORED_SIDES))
    player_filter = ""
    params = [range_days, *STORED_SIDES]

    if player_ids:
        player_placeholders = ", ".join(["%s"] * len(player_ids))
        player_filter = f"AND PlayerID IN ({player_placeholders})"
        params.extend(player_ids)

    cursor.execute(
        f"""
        DELETE FROM CS2S_PlayerRating
        WHERE RangeDays = %s
          AND Side IN ({side_placeholders})
          {player_filter}
        """,
        tuple(params),
    )


def upsert_player_rating(cursor, player_id, range_days, side, stats):
    cursor.execute(
        """
        INSERT INTO CS2S_PlayerRating
            (PlayerID, RangeDays, Side, MatchesPlayed, RoundsPlayed, RoundsKAST, Kills, Assists, Deaths, Damage, Rating)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            MatchesPlayed = VALUES(MatchesPlayed),
            RoundsPlayed = VALUES(RoundsPlayed),
            RoundsKAST = VALUES(RoundsKAST),
            Kills = VALUES(Kills),
            Assists = VALUES(Assists),
            Deaths = VALUES(Deaths),
            Damage = VALUES(Damage),
            Rating = VALUES(Rating),
            UpdateDate = CURRENT_TIMESTAMP
        """,
        (
            player_id,
            range_days,
            side,
            stats["MatchesPlayed"],
            stats["RoundsPlayed"],
            stats["RoundsKAST"],
            stats["Kills"],
            stats["Assists"],
            stats["Deaths"],
            stats["Damage"],
            stats["Rating"],
        ),
    )


if __name__ == "__main__":
    import argparse, sys

    if __package__ in (None, ""):
        sys.path.append(str(Path(__file__).resolve().parents[2]))

    parser = argparse.ArgumentParser(description="Refresh cached player ratings.")
    parser.add_argument("--range-days", type=int, required=True, help="Number of trailing days to include.")
    args = parser.parse_args()
    result = refresh_player_ratings(range_days=args.range_days)
    print(
        "Player ratings refreshed. "
        f"RangeDays={result['RangeDays']}, "
        f"PlayersProcessed={result['PlayersProcessed']}, "
        f"RowsWritten={result['RowsWritten']}"
    )
