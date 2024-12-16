from flask import g
import traceback, pprint
from ..routes.playerstats_panel import get_stats, get_match_results_date_range, get_split_round_ids_from_match_ids, combine_stats

def set_player_of_the_week(app, get_db_connection):
    with app.app_context():
        db = get_db_connection()
        cursor = db.cursor()

        try:
            cursor = g.db.cursor(dictionary=True)
            all_player_stats_7_days = get_all_players_stats_last_7_days(cursor)
            all_player_stats_overall = get_all_players_stats_overall(cursor)

            cursor.execute("UPDATE CS2S_PlayerInfo SET PlayerOfTheWeek = 0")

            # Calculate rating increase
            player_rating_increases = {}
            for player_id, seven_day_stats in all_player_stats_7_days.items():

                if player_id in all_player_stats_overall:
                    seven_day_rating = seven_day_stats.get("Rating", 0)
                    overall_rating = all_player_stats_overall[player_id].get("Rating", 0)
                    
                    rating_increase = seven_day_rating - overall_rating
                    player_rating_increases[player_id] = {
                        "seven_day_rating": seven_day_rating,
                        "overall_rating": overall_rating,
                        "rating_increase": rating_increase
                    }

            # Find top 3 rating increases
            if player_rating_increases:

                top_3_players = sorted(
                    player_rating_increases.items(), 
                    key=lambda x: x[1]["rating_increase"], 
                    reverse=True
                )

                pprint.pprint(top_3_players)

                top_3_players = top_3_players[:3]

                # Update PlayerOfTheWeek in DB
                for idx, (player_id, _) in enumerate(top_3_players, start=1):
                    cursor.execute(
                        "UPDATE CS2S_PlayerInfo SET PlayerOfTheWeek = %s WHERE PlayerID = %s", 
                        (idx, player_id)
                    )
                    
                db.commit()

            return player_rating_increases

        except Exception as e:
            error_traceback = traceback.format_exc()
            print(error_traceback)
            db.rollback()

def get_all_players_stats_last_7_days(cursor):
    cursor.execute("""
    SELECT DISTINCT PlayerID
    FROM CS2S_Player_Matches pm
    JOIN CS2S_Match m ON pm.MatchID = m.MatchID
    WHERE m.MatchDate >= DATE_SUB(NOW(), INTERVAL 7 DAY)
    """)
    
    player_ids = [row["PlayerID"] for row in cursor.fetchall()]
    
    if not player_ids:
        return {}
    
    all_player_stats = {}

    for player_id in player_ids:
        results = get_match_results_date_range(cursor, "7days", [player_id])

        # Skip players with less than 3 matches
        if not results or len(set(result["MatchID"] for result in results)) < 3:
            continue

        # Extract match and round IDs
        match_ids = list(set(result["MatchID"] for result in results))
        matches_won = sum(1 for result in results if result["Result"] == "Win")
        matches_played = len(match_ids)
        t_round_ids, ct_round_ids = get_split_round_ids_from_match_ids(cursor, match_ids, player_id)
        
        t_stats = get_stats(cursor, t_round_ids, player_id)
        ct_stats = get_stats(cursor, ct_round_ids, player_id)
        combined_stats = combine_stats(t_stats, ct_stats)

        all_player_stats[player_id] = {
            "Overall": combined_stats or 0,
            "Terrorist": t_stats or 0,
            "CounterTerrorist": ct_stats or 0,
            "MatchesPlayed": matches_played or 0,
            "MatchesWon": matches_won or 0,
            "MatchIDs": match_ids or [],
            "Rating": combined_stats["Rating"] if combined_stats else 0
        }

    return all_player_stats

def get_all_players_stats_overall(cursor):
    # Get all distinct player IDs who have played matches
    cursor.execute("""
    SELECT DISTINCT PlayerID
    FROM CS2S_Player_Matches pm
    JOIN CS2S_Match m ON pm.MatchID = m.MatchID
    """)
    
    player_ids = [row["PlayerID"] for row in cursor.fetchall()]
    
    if not player_ids:
        return {}
    
    all_player_stats = {}

    for player_id in player_ids:
        # Get match results for all matches
        results = get_match_results_date_range(cursor, "overall", [player_id])

        # Skip players with less than 3 matches
        if not results or len(set(result["MatchID"] for result in results)) < 3:
            continue

        # Extract match and round IDs
        match_ids = list(set(result["MatchID"] for result in results))
        matches_won = sum(1 for result in results if result["Result"] == "Win")
        matches_played = len(match_ids)
        t_round_ids, ct_round_ids = get_split_round_ids_from_match_ids(cursor, match_ids, player_id)
        
        t_stats = get_stats(cursor, t_round_ids, player_id)
        ct_stats = get_stats(cursor, ct_round_ids, player_id)
        combined_stats = combine_stats(t_stats, ct_stats)

        all_player_stats[player_id] = {
            "Overall": combined_stats or 0,
            "Terrorist": t_stats or 0,
            "CounterTerrorist": ct_stats or 0,
            "MatchesPlayed": matches_played or 0,
            "MatchesWon": matches_won or 0,
            "MatchIDs": match_ids or [],
            "Rating": combined_stats["Rating"] if combined_stats else 0
        }

    return all_player_stats