from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from mysql.connector import Error

from app.database import DatabaseConnection, get_db

from .player_info_sql import avatar_url_sql

router = APIRouter()

UTILITY_WEAPONS = {"smokegrenade", "molotov", "inferno", "hegrenade", "flashbang", "decoy"}
SIDES = ("Overall", "Terrorist", "CounterTerrorist")


@dataclass
class MatchData:
    match: dict[str, Any]
    players_info: dict[str, dict[str, Any]]
    team_results: list[dict[str, Any]]
    rounds: list[dict[str, Any]]
    deaths: list[dict[str, Any]]
    clutches: list[dict[str, Any]]
    duels: list[dict[str, Any]]
    kast_stats: list[dict[str, Any]]
    blinds: list[dict[str, Any]]
    damage_stats: list[dict[str, Any]]
    player_teams: list[dict[str, Any]]


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

        return build_match_response(match_data)

    except Error as exc:
        print(f"Error: {exc}")
        raise HTTPException(status_code=500, detail="Failed to fetch data.") from exc

    finally:
        if cursor:
            cursor.close()


def build_match_response(match_data: MatchData) -> dict[str, Any]:
    players_stats = aggregate_player_stats(match_data)
    apply_player_info_and_derived_stats(players_stats, match_data)

    match_data.match["Teams"] = build_teams(match_data.team_results, match_data.player_teams, players_stats)
    match_data.match["Clutches"] = match_data.clutches
    match_data.match["Duels"] = match_data.duels
    match_data.match["Rounds"] = match_data.rounds
    match_data.match["Deaths"] = match_data.deaths

    return match_data.match


def aggregate_player_stats(match_data: MatchData) -> dict[str, dict[str, Any]]:
    players_stats: dict[str, dict[str, Any]] = {}

    for kast in match_data.kast_stats:
        player_id = kast["PlayerID"]
        stats = _get_or_create_player_stats(players_stats, player_id)

        stats["Overall"]["KAST"] += 1
        side_stats = _side_stats(stats, kast["PlayerSide"])
        if side_stats:
            side_stats["KAST"] += 1

    for blind in match_data.blinds:
        player_id = blind["ThrowerID"]
        stats = _get_or_create_player_stats(players_stats, player_id)
        duration = blind["Duration"]

        _add_blind(stats["Overall"], duration)
        side_stats = _side_stats(stats, blind["ThrowerSide"])
        if side_stats:
            _add_blind(side_stats, duration)

    for death in match_data.deaths:
        victim_id = death["VictimID"]
        attacker_id = death["AttackerID"]
        assister_id = death["AssisterID"]
        attacker_side = opposing_side(death["VictimSide"])

        victim_stats = _get_or_create_player_stats(players_stats, victim_id)
        victim_stats["Overall"]["Deaths"] += 1
        victim_side_stats = _side_stats(victim_stats, death["VictimSide"])
        if victim_side_stats:
            victim_side_stats["Deaths"] += 1

        if attacker_id:
            attacker_stats = _get_or_create_player_stats(players_stats, attacker_id)
            attacker_stats["Overall"]["Kills"] += 1
            attacker_side_stats = _side_stats(attacker_stats, attacker_side)
            if attacker_side_stats:
                attacker_side_stats["Kills"] += 1

            if death["Hitgroup"] == 1:
                attacker_stats["Overall"]["Headshots"] += 1
                if attacker_side_stats:
                    attacker_side_stats["Headshots"] += 1

        if assister_id:
            assister_stats = _get_or_create_player_stats(players_stats, assister_id)
            assister_stats["Overall"]["Assists"] += 1
            assister_side_stats = _side_stats(assister_stats, attacker_side)
            if assister_side_stats:
                assister_side_stats["Assists"] += 1

    for damage in match_data.damage_stats:
        attacker_id = damage["AttackerID"]
        if not attacker_id:
            continue

        stats = _get_or_create_player_stats(players_stats, attacker_id)
        attacker_side = opposing_side(damage["VictimSide"])
        amount = damage["Damage"]
        is_utility = damage["Weapon"] in UTILITY_WEAPONS

        _add_damage(stats["Overall"], amount, is_utility)
        side_stats = _side_stats(stats, attacker_side)
        if side_stats:
            _add_damage(side_stats, amount, is_utility)

    return players_stats


def apply_player_info_and_derived_stats(
    players_stats: dict[str, dict[str, Any]],
    match_data: MatchData,
) -> None:
    player_side_rounds = calculate_player_side_rounds(match_data.rounds, match_data.player_teams)

    for player_id, stats in players_stats.items():
        player_info = match_data.players_info.get(player_id, {})
        for side in SIDES:
            stats[side]["Username"] = player_info.get("Username")
            stats[side]["AvatarL"] = player_info.get("AvatarL")

        t_rounds = player_side_rounds.get(player_id, {}).get("2", 0)
        ct_rounds = player_side_rounds.get(player_id, {}).get("3", 0)

        _calculate_derived_stats(stats["Overall"], t_rounds + ct_rounds)
        _calculate_derived_stats(stats["Terrorist"], t_rounds)
        _calculate_derived_stats(stats["CounterTerrorist"], ct_rounds)


def calculate_player_side_rounds(
    rounds: list[dict[str, Any]],
    player_teams: list[dict[str, Any]],
) -> dict[str, dict[str, int]]:
    player_side_rounds: dict[str, dict[str, int]] = {}
    player_team_map = {player["PlayerID"]: player["TeamID"] for player in player_teams}

    for match_round in rounds:
        for player_id, team_id in player_team_map.items():
            player_side_rounds.setdefault(player_id, {"2": 0, "3": 0})

            if team_id == match_round["WinnerTeamID"]:
                player_side_rounds[player_id][str(match_round["WinnerSide"])] += 1
            elif team_id == match_round["LoserTeamID"]:
                player_side_rounds[player_id][str(match_round["LoserSide"])] += 1

    return player_side_rounds


def build_teams(
    team_results: list[dict[str, Any]],
    player_teams: list[dict[str, Any]],
    players_stats: dict[str, dict[str, Any]],
) -> dict[Any, dict[str, Any]]:
    teams = {
        team_result["TeamID"]: {
            **team_result,
            "Players": {},
        }
        for team_result in team_results
    }

    for player in player_teams:
        team_id = player["TeamID"]
        player_id = player["PlayerID"]
        if team_id in teams and player_id in players_stats:
            teams[team_id]["Players"][player_id] = players_stats[player_id]

    return teams


def fetch_match_data(cursor, match_id: str) -> MatchData | None:
    cursor.execute("SELECT * FROM CS2S_Match WHERE MatchID = %s", (match_id,))
    match = cursor.fetchone()
    if not match:
        return None

    cursor.execute(
        """
        SELECT tr.*, t.Name AS TeamName
        FROM CS2S_TeamResult tr
        LEFT JOIN CS2S_Team t ON tr.TeamID = t.TeamID
        WHERE tr.MatchID = %s
        """,
        (match_id,),
    )
    team_results = cursor.fetchall()

    cursor.execute(
        """
        SELECT tp.PlayerID, tp.TeamID
        FROM CS2S_Team_Players tp
        JOIN CS2S_TeamResult tr ON tp.TeamID = tr.TeamID
        WHERE tr.MatchID = %s
        """,
        (match_id,),
    )
    player_teams = cursor.fetchall()
    for player_team in player_teams:
        player_team["PlayerID"] = str(player_team["PlayerID"])

    cursor.execute(
        f"""
        SELECT
            p.PlayerID,
            p.Username,
            {avatar_url_sql("p", "full")} AS AvatarL
        FROM CS2S_PlayerInfo p
        JOIN CS2S_Team_Players tp ON p.PlayerID = tp.PlayerID
        JOIN CS2S_TeamResult tr ON tp.TeamID = tr.TeamID
        WHERE tr.MatchID = %s
        """,
        (match_id,),
    )
    players_info = cursor.fetchall()
    players_info_dict = {str(player["PlayerID"]): player for player in players_info}

    cursor.execute("SELECT * FROM CS2S_Round WHERE MatchID = %s", (match_id,))
    rounds = cursor.fetchall()

    cursor.execute("SELECT * FROM CS2S_Death WHERE MatchID = %s", (match_id,))
    deaths = cursor.fetchall()
    for death in deaths:
        death["VictimID"] = str(death["VictimID"])
        if death["AttackerID"]:
            death["AttackerID"] = str(death["AttackerID"])
        if death["AssisterID"]:
            death["AssisterID"] = str(death["AssisterID"])

    cursor.execute("SELECT * FROM CS2S_Clutch WHERE MatchID = %s", (match_id,))
    clutches = cursor.fetchall()
    for clutch in clutches:
        clutch["PlayerID"] = str(clutch["PlayerID"])

    cursor.execute("SELECT * FROM CS2S_Duel WHERE MatchID = %s", (match_id,))
    duels = cursor.fetchall()
    for duel in duels:
        duel["WinnerID"] = str(duel["WinnerID"])
        duel["LoserID"] = str(duel["LoserID"])

    cursor.execute("SELECT * FROM CS2S_KAST WHERE MatchID = %s", (match_id,))
    kast_stats = cursor.fetchall()
    for kast in kast_stats:
        kast["PlayerID"] = str(kast["PlayerID"])

    cursor.execute("SELECT * FROM CS2S_Blind WHERE MatchID = %s", (match_id,))
    blinds = cursor.fetchall()
    for blind in blinds:
        blind["ThrowerID"] = str(blind["ThrowerID"])
        blind["BlindedID"] = str(blind["BlindedID"])

    cursor.execute("SELECT * FROM CS2S_Hurt WHERE MatchID = %s", (match_id,))
    damage_stats = cursor.fetchall()
    for damage in damage_stats:
        damage["VictimID"] = str(damage["VictimID"])
        if damage["AttackerID"]:
            damage["AttackerID"] = str(damage["AttackerID"])

    return MatchData(
        match=match,
        players_info=players_info_dict,
        team_results=team_results,
        rounds=rounds,
        deaths=deaths,
        clutches=clutches,
        duels=duels,
        kast_stats=kast_stats,
        blinds=blinds,
        damage_stats=damage_stats,
        player_teams=player_teams,
    )


def _create_empty_playerstat(player_id: str) -> dict[str, Any]:
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
        "Headshots": 0,
    }


def _create_empty_side_stats(player_id: str) -> dict[str, dict[str, Any]]:
    return {
        "Overall": _create_empty_playerstat(player_id),
        "Terrorist": _create_empty_playerstat(player_id),
        "CounterTerrorist": _create_empty_playerstat(player_id),
    }


def _get_or_create_player_stats(
    players_stats: dict[str, dict[str, Any]],
    player_id: str,
) -> dict[str, Any]:
    if player_id not in players_stats:
        players_stats[player_id] = _create_empty_side_stats(player_id)
    return players_stats[player_id]


def _side_stats(stats: dict[str, Any], side: int | None) -> dict[str, Any] | None:
    if side == 2:
        return stats["Terrorist"]
    if side == 3:
        return stats["CounterTerrorist"]
    return None


def opposing_side(victim_side: int | None) -> int | None:
    if victim_side == 2:
        return 3
    if victim_side == 3:
        return 2
    return None


def _add_blind(stats: dict[str, Any], duration: float) -> None:
    stats["Blinds"]["Count"] += 1
    stats["Blinds"]["TotalDuration"] += duration


def _add_damage(stats: dict[str, Any], amount: int, is_utility: bool) -> None:
    stats["Damage"] += amount
    if is_utility:
        stats["UtilityDamage"] += amount


def calculate_impact_and_rating(kpr, apr, dpr, kast, adr):
    kpr, apr, dpr, kast, adr = float(kpr), float(apr), float(dpr), float(kast), float(adr)
    impact = ((2.13 * kpr) + (0.42 * apr) - 0.41) or 0.0
    rating = (
        (0.0073 * kast)
        + (0.3591 * kpr)
        + (-0.5329 * dpr)
        + (0.2372 * impact)
        + (0.0032 * adr)
        + 0.1587
    ) or 0.0
    return impact, rating


def _calculate_derived_stats(stats: dict[str, Any], total_rounds: int) -> None:
    if total_rounds > 0:
        total_rounds_fl: float = float(total_rounds)
        stats["Rounds"] = total_rounds
        stats["KAST"] = (float(stats["KAST"]) / total_rounds_fl) * 100.0
        stats["KPR"] = float(stats["Kills"]) / total_rounds_fl
        stats["APR"] = float(stats["Assists"]) / total_rounds_fl
        stats["DPR"] = float(stats["Deaths"]) / total_rounds_fl
        stats["ADR"] = float(stats["Damage"]) / total_rounds_fl

        stats["Impact"], stats["Rating"] = calculate_impact_and_rating(
            stats["KPR"],
            stats["APR"],
            stats["DPR"],
            stats["KAST"],
            stats["ADR"],
        )

        stats["KAST"] = round(stats["KAST"], 2) or 0.0
        stats["KPR"] = round(stats["KPR"], 2) or 0.0
        stats["APR"] = round(stats["APR"], 2) or 0.0
        stats["DPR"] = round(stats["DPR"], 2) or 0.0
        stats["ADR"] = round(stats["ADR"], 2) or 0.0
        stats["Impact"] = round(stats["Impact"], 2) or 0.0
        stats["Rating"] = round(stats["Rating"], 2) or 0.0
    else:
        stats["Rounds"] = 0.0
        stats["KAST"] = 0.0
        stats["KPR"] = 0.0
        stats["APR"] = 0.0
        stats["DPR"] = 0.0
        stats["ADR"] = 0.0
        stats["Impact"] = 0.0
        stats["Rating"] = 0.0
