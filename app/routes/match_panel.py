from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from mysql.connector import Error

from app.database import DatabaseConnection, get_db

from .player_info_sql import avatar_url_sql

router = APIRouter()
UTILITY_WEAPONS = {"smokegrenade", "molotov", "inferno", "hegrenade", "flashbang", "decoy"}


@router.get("/match_panel_by_match_id")
def match_panel_by_match_id(
    match_id: str = Query(...),
    db: DatabaseConnection = Depends(get_db),
) -> dict[str, Any]:
    cursor = None
    try:
        cursor = db.cursor(dictionary=True)

        match_data = fetch_match_data(cursor, match_id)
        if match_data is None:
            raise HTTPException(status_code=404, detail="Match not found.")

        (match, players_info_dict, team_results, rounds, deaths,
         clutches, duels, kast_stats, blinds, damage_stats, player_teams) = match_data

        players_stats = {}
        player_side_rounds = {}
        player_team_map = {player["PlayerID"]: player["TeamID"] for player in player_teams}

        for match_round in rounds:
            winner_team = match_round["WinnerTeamID"]
            loser_team = match_round["LoserTeamID"]
            winner_side = match_round["WinnerSide"]
            loser_side = match_round["LoserSide"]

            for player_id, team_id in player_team_map.items():
                player_side_rounds.setdefault(player_id, {"2": 0, "3": 0})

                if team_id == winner_team:
                    player_side_rounds[player_id][str(winner_side)] += 1
                elif team_id == loser_team:
                    player_side_rounds[player_id][str(loser_side)] += 1

        for kast in kast_stats:
            player_id = kast["PlayerID"]
            player_side = kast["PlayerSide"]

            if player_id not in players_stats:
                players_stats[player_id] = _create_empty_side_stats(player_id)

            players_stats[player_id]["Overall"]["KAST"] += 1
            if player_side == 2:
                players_stats[player_id]["Terrorist"]["KAST"] += 1
            elif player_side == 3:
                players_stats[player_id]["CounterTerrorist"]["KAST"] += 1

        for blind in blinds:
            player_id = blind["ThrowerID"]
            thrower_side = blind["ThrowerSide"]

            if player_id not in players_stats:
                players_stats[player_id] = _create_empty_side_stats(player_id)

            players_stats[player_id]["Overall"]["Blinds"]["Count"] += 1
            players_stats[player_id]["Overall"]["Blinds"]["TotalDuration"] += blind["Duration"]

            if thrower_side == 2:
                players_stats[player_id]["Terrorist"]["Blinds"]["Count"] += 1
                players_stats[player_id]["Terrorist"]["Blinds"]["TotalDuration"] += blind["Duration"]
            elif thrower_side == 3:
                players_stats[player_id]["CounterTerrorist"]["Blinds"]["Count"] += 1
                players_stats[player_id]["CounterTerrorist"]["Blinds"]["TotalDuration"] += blind["Duration"]

        for death in deaths:
            victim_id = death["VictimID"]
            attacker_id = death["AttackerID"]
            assister_id = death["AssisterID"]
            hitgroup = death["Hitgroup"]
            victim_side = death["VictimSide"]

            if victim_id not in players_stats:
                players_stats[victim_id] = _create_empty_side_stats(victim_id)

            players_stats[victim_id]["Overall"]["Deaths"] += 1
            if victim_side == 2:
                players_stats[victim_id]["Terrorist"]["Deaths"] += 1
            elif victim_side == 3:
                players_stats[victim_id]["CounterTerrorist"]["Deaths"] += 1

            if attacker_id:
                if attacker_id not in players_stats:
                    players_stats[attacker_id] = _create_empty_side_stats(attacker_id)

                players_stats[attacker_id]["Overall"]["Kills"] += 1
                if victim_side == 2:
                    players_stats[attacker_id]["CounterTerrorist"]["Kills"] += 1
                elif victim_side == 3:
                    players_stats[attacker_id]["Terrorist"]["Kills"] += 1

                if hitgroup == 1:
                    players_stats[attacker_id]["Overall"]["Headshots"] += 1
                    if victim_side == 2:
                        players_stats[attacker_id]["CounterTerrorist"]["Headshots"] += 1
                    elif victim_side == 3:
                        players_stats[attacker_id]["Terrorist"]["Headshots"] += 1

            if assister_id:
                if assister_id not in players_stats:
                    players_stats[assister_id] = _create_empty_side_stats(assister_id)

                players_stats[assister_id]["Overall"]["Assists"] += 1
                if victim_side == 2:
                    players_stats[assister_id]["CounterTerrorist"]["Assists"] += 1
                elif victim_side == 3:
                    players_stats[assister_id]["Terrorist"]["Assists"] += 1

        for damage in damage_stats:
            attacker_id = damage["AttackerID"]
            damage_amount = damage["Damage"]
            weapon = damage["Weapon"]
            victim_side = damage["VictimSide"]

            if not attacker_id:
                continue

            if attacker_id not in players_stats:
                players_stats[attacker_id] = _create_empty_side_stats(attacker_id)

            players_stats[attacker_id]["Overall"]["Damage"] += damage_amount
            if weapon in UTILITY_WEAPONS:
                players_stats[attacker_id]["Overall"]["UtilityDamage"] += damage_amount

            if victim_side == 2:
                players_stats[attacker_id]["CounterTerrorist"]["Damage"] += damage_amount
                if weapon in UTILITY_WEAPONS:
                    players_stats[attacker_id]["CounterTerrorist"]["UtilityDamage"] += damage_amount
            elif victim_side == 3:
                players_stats[attacker_id]["Terrorist"]["Damage"] += damage_amount
                if weapon in UTILITY_WEAPONS:
                    players_stats[attacker_id]["Terrorist"]["UtilityDamage"] += damage_amount

        for player_id, stats in players_stats.items():
            player_info = players_info_dict.get(player_id, {})
            for side in ["Overall", "Terrorist", "CounterTerrorist"]:
                stats[side]["Username"] = player_info.get("Username")
                stats[side]["AvatarL"] = player_info.get("AvatarL")

            t_rounds = player_side_rounds.get(player_id, {}).get("2", 0)
            ct_rounds = player_side_rounds.get(player_id, {}).get("3", 0)

            _calculate_derived_stats(stats["Overall"], t_rounds + ct_rounds)
            _calculate_derived_stats(stats["Terrorist"], t_rounds)
            _calculate_derived_stats(stats["CounterTerrorist"], ct_rounds)

        teams = {}
        for team_result in team_results:
            team_id = team_result["TeamID"]

            cursor.execute("SELECT Name FROM CS2S_Team WHERE TeamID = %s", (team_id,))
            team_name_result = cursor.fetchone()

            teams[team_id] = {
                **team_result,
                "TeamName": team_name_result["Name"] if team_name_result else None,
                "Players": {},
            }

            cursor.execute(
                """
                SELECT PlayerID FROM CS2S_Team_Players
                WHERE TeamID = %s
                """,
                (team_id,),
            )
            team_players = cursor.fetchall()

            for player in team_players:
                player_id = str(player["PlayerID"])
                if player_id in players_stats:
                    teams[team_id]["Players"][player_id] = players_stats[player_id]

        match["Teams"] = teams
        match["Clutches"] = clutches
        match["Duels"] = duels
        match["Rounds"] = rounds
        match["Deaths"] = deaths

        return match

    except Error as exc:
        print(f"Error: {exc}")
        raise HTTPException(status_code=500, detail="Failed to fetch data.") from exc
        
    finally:
        if cursor:
            cursor.close()

def _create_empty_playerstat(player_id):
    return {
        "PlayerID": player_id,
        "KAST": 0,
        "Blinds": {"Count": 0, "TotalDuration": 0.0},
        "Deaths": 0,
        "Kills": 0,
        "Assists": 0,
        "Damage": 0,
        "UtilityDamage": 0,
        "Rounds": 0,
        "Headshots": 0
    }

def _create_empty_side_stats(player_id):
    return {
        "Overall": _create_empty_playerstat(player_id),
        "Terrorist": _create_empty_playerstat(player_id),
        "CounterTerrorist": _create_empty_playerstat(player_id)
    }

def fetch_match_data(cursor, match_id):
    match_query = "SELECT * FROM CS2S_Match WHERE MatchID = %s"
    players_info_query = f"""
        SELECT
            PlayerID,
            Username,
            {avatar_url_sql("CS2S_PlayerInfo", "full")} AS AvatarL
        FROM CS2S_PlayerInfo
    """
    team_results_query = "SELECT * FROM CS2S_TeamResult WHERE MatchID = %s"
    rounds_query = "SELECT * FROM CS2S_Round WHERE MatchID = %s"
    deaths_query = "SELECT * FROM CS2S_Death WHERE MatchID = %s"
    clutches_query = "SELECT * FROM CS2S_Clutch WHERE MatchID = %s"
    duels_query = "SELECT * FROM CS2S_Duel WHERE MatchID = %s"
    kast_query = "SELECT * FROM CS2S_KAST WHERE MatchID = %s"
    blinds_query = "SELECT * FROM CS2S_Blind WHERE MatchID = %s"
    damage_query = "SELECT * FROM CS2S_Hurt WHERE MatchID = %s"

    cursor.execute(match_query, (match_id,))
    match = cursor.fetchone()
    if not match:
        return None

    cursor.execute(players_info_query)
    players_info = cursor.fetchall()
    # Convert PlayerIDs to strings in the players_info_dict
    players_info_dict = {str(player['PlayerID']): player for player in players_info}

    cursor.execute(team_results_query, (match_id,))
    team_results = cursor.fetchall()

    cursor.execute(rounds_query, (match_id,))
    rounds = cursor.fetchall()

    cursor.execute(deaths_query, (match_id,))
    deaths = cursor.fetchall()
    # Convert PlayerIDs to strings in deaths
    for death in deaths:
        death['VictimID'] = str(death['VictimID'])
        if death['AttackerID']:
            death['AttackerID'] = str(death['AttackerID'])
        if death['AssisterID']:
            death['AssisterID'] = str(death['AssisterID'])

    cursor.execute(clutches_query, (match_id,))
    clutches = cursor.fetchall()
    # Convert PlayerIDs to strings in clutches
    for clutch in clutches:
        clutch['PlayerID'] = str(clutch['PlayerID'])

    cursor.execute(duels_query, (match_id,))
    duels = cursor.fetchall()
    # Convert PlayerIDs to strings in duels
    for duel in duels:
        duel['WinnerID'] = str(duel['WinnerID'])
        duel['LoserID'] = str(duel['LoserID'])

    cursor.execute(kast_query, (match_id,))
    kast_stats = cursor.fetchall()
    # Convert PlayerIDs to strings in kast_stats
    for kast in kast_stats:
        kast['PlayerID'] = str(kast['PlayerID'])

    cursor.execute(blinds_query, (match_id,))
    blinds = cursor.fetchall()
    # Convert PlayerIDs to strings in blinds
    for blind in blinds:
        blind['ThrowerID'] = str(blind['ThrowerID'])
        blind['BlindedID'] = str(blind['BlindedID'])

    cursor.execute(damage_query, (match_id,))
    damage_stats = cursor.fetchall()
    # Convert PlayerIDs to strings in damage_stats
    for damage in damage_stats:
        damage['VictimID'] = str(damage['VictimID'])
        if damage['AttackerID']:
            damage['AttackerID'] = str(damage['AttackerID'])

    player_teams_query = """
        SELECT tp.PlayerID, tp.TeamID
        FROM CS2S_Team_Players tp
        JOIN CS2S_TeamResult tr ON tp.TeamID = tr.TeamID
        WHERE tr.MatchID = %s
    """
    
    cursor.execute(player_teams_query, (match_id,))
    player_teams = cursor.fetchall()
    # Convert PlayerIDs to strings in player_teams
    for player_team in player_teams:
        player_team['PlayerID'] = str(player_team['PlayerID'])
    
    return match, players_info_dict, team_results, rounds, deaths, clutches, duels, kast_stats, blinds, damage_stats, player_teams

def calculate_impact_and_rating(kpr, apr, dpr, kast, adr):
    # Convert inputs to float to ensure float arithmetic
    kpr, apr, dpr, kast, adr = float(kpr), float(apr), float(dpr), float(kast), float(adr)
    impact = ((2.13 * kpr) + (0.42 * apr) - 0.41) or 0.0
    rating = ((0.0073 * kast) + (0.3591 * kpr) + (-0.5329 * dpr) + (0.2372 * impact) + (0.0032 * adr) + 0.1587) or 0.0
    return impact, rating

def _calculate_derived_stats(stats, total_rounds):
    """Calculate derived statistics for a given side's stats"""
    if total_rounds > 0:
        total_rounds = float(total_rounds)  # Ensure total_rounds is float
        stats["Rounds"] = total_rounds
        stats["KAST"] = (float(stats["KAST"]) / total_rounds) * 100.0
        stats["KPR"] = float(stats["Kills"]) / total_rounds
        stats["APR"] = float(stats["Assists"]) / total_rounds
        stats["DPR"] = float(stats["Deaths"]) / total_rounds
        stats["ADR"] = float(stats["Damage"]) / total_rounds

        stats["Impact"], stats["Rating"] = calculate_impact_and_rating(
            stats["KPR"],
            stats["APR"],
            stats["DPR"],
            stats["KAST"],
            stats["ADR"]
        )

        # Round results to 2 decimal places, with 0.0 as fallback
        stats["KAST"] = round(stats["KAST"], 2) or 0.0
        stats["KPR"] = round(stats["KPR"], 2) or 0.0
        stats["APR"] = round(stats["APR"], 2) or 0.0
        stats["DPR"] = round(stats["DPR"], 2) or 0.0
        stats["ADR"] = round(stats["ADR"], 2) or 0.0
        stats["Impact"] = round(stats["Impact"], 2) or 0.0
        stats["Rating"] = round(stats["Rating"], 2) or 0.0

    else:
        # Set all stats to 0.0 when there are no rounds
        stats["Rounds"] = 0.0
        stats["KAST"] = 0.0
        stats["KPR"] = 0.0
        stats["APR"] = 0.0
        stats["DPR"] = 0.0
        stats["ADR"] = 0.0
        stats["Impact"] = 0.0
        stats["Rating"] = 0.0
