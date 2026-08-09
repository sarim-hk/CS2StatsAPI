import gzip
import json
import math
import secrets
from fastapi import APIRouter, Depends, HTTPException, Request, status
from app.config import Settings, get_settings
from app.database import (
    fetch_team_average_elo,
    insert_blind,
    insert_clutch,
    insert_death,
    insert_duel,
    insert_grenade,
    insert_hurt,
    insert_kast,
    insert_map,
    insert_match,
    insert_player_match,
    insert_round,
    insert_team,
    insert_team_player,
    insert_team_result,
    transaction,
    update_team_elo,
    update_team_players_elo,
)

router = APIRouter()

PLAYER_ID_FIELDS = (
    "PlayerID",
    "ClutcherID",
    "WinnerID",
    "LoserID",
    "AttackerID",
    "AssisterID",
    "VictimID",
    "ThrowerID",
    "BlindedID",
)

@router.post("/upload_match")
def upload_match(request: Request, settings: Settings = Depends(get_settings)):

    validate_authorization(request, settings.api_auth_key)
    body = request.body()
    print(f"[upload_match] Request received. Bytes={len(body)}, encoding={request.headers.get('content-encoding', 'none')}")

    if request.headers.get("content-encoding", "").lower() == "gzip":
        try:
            body = gzip.decompress(body)
            print(f"[upload_match] Gzip decompressed. Bytes={len(body)}")
        except gzip.BadGzipFile as exc:
            print("[upload_match] Invalid gzip payload.")
            raise HTTPException(status_code=400, detail="Invalid gzip payload.") from exc

    try:
        match_json = json.loads(body.decode("utf-8"))
        print(
            "[upload_match] JSON parsed. "
            f"Map={match_json.get('MapName')}, Teams={len(match_json.get('Teams', []))}, "
            f"Rounds={len(match_json.get('Rounds', []))}"
        )
    except UnicodeDecodeError as exc:
        print("[upload_match] Request body was not valid UTF-8.")
        raise HTTPException(status_code=400, detail="Request body must be UTF-8 encoded.") from exc
    except json.JSONDecodeError as exc:
        print("[upload_match] Request body was not valid JSON.")
        raise HTTPException(status_code=400, detail="Invalid JSON payload.") from exc

    with transaction() as db:
        cursor = db.cursor()
        print("[upload_match] Transaction started.")

        try:
            insert_map(cursor, match_json["MapName"])
            print(f"[upload_match] Map inserted/confirmed. MapID={match_json['MapName']}")

            match_id = insert_match(cursor, match_json["MapName"], match_json["StartTick"], match_json["EndTick"])
            print(f"[upload_match] Match inserted. MatchID={match_id}")

            for team in match_json["Teams"].values():
                insert_team(cursor, team["TeamID"], len(team["PlayerIDs"]), team["TeamName"])
                print(
                    "[upload_match] Team inserted/confirmed. "
                    f"TeamID={team['TeamID']}, Name={team['TeamName']}, Players={len(team['PlayerIDs'])}, "
                    f"PlayerIDs={team['PlayerIDs']}"
                )

                for player_id in team["PlayerIDs"]:
                    try:
                        insert_team_player(cursor, team["TeamID"], player_id)
                    except Exception as exc:
                        print(
                            "[upload_match] Team player insert failed. "
                            f"TeamID={team['TeamID']}, PlayerID={player_id}, Error={exc}"
                        )
                        raise
                    print(f"[upload_match] Team player inserted/confirmed. TeamID={team['TeamID']}, PlayerID={player_id}")

                    try:
                        insert_player_match(cursor, player_id, match_id)
                    except Exception as exc:
                        print(
                            "[upload_match] Player match insert failed. "
                            f"MatchID={match_id}, PlayerID={player_id}, Error={exc}"
                        )
                        raise
                    print(f"[upload_match] Player match inserted. MatchID={match_id}, PlayerID={player_id}")

                team["AverageELO"] = fetch_team_average_elo(cursor, team["TeamID"]) or 1000
                print(
                    "[upload_match] Team average Elo loaded. "
                    f"TeamID={team['TeamID']}, AverageELO={team['AverageELO']}, PlayerIDs={team['PlayerIDs']}"
                )

            for round_index, match_round in enumerate(match_json["Rounds"], start=1):
                round_id = insert_round(cursor, match_id, match_round)
                print(f"[upload_match] Round inserted. RoundIndex={round_index}, RoundID={round_id}")

                if match_round["ClutchEvent"]:
                    clutch = match_round["ClutchEvent"]
                    try:
                        insert_clutch(cursor, round_id, match_id, clutch)
                    except Exception as exc:
                        print_insert_failure("Clutch", match_id, round_index, round_id, clutch, exc)
                        raise
                    print(f"[upload_match] Clutch inserted. RoundID={round_id}, {format_player_ids(clutch)}")
                else:
                    print(f"[upload_match] No clutch event. RoundID={round_id}")

                if match_round["DuelEvent"]:
                    duel = match_round["DuelEvent"]
                    try:
                        insert_duel(cursor, round_id, match_id, duel)
                    except Exception as exc:
                        print_insert_failure("Duel", match_id, round_index, round_id, duel, exc)
                        raise
                    print(f"[upload_match] Duel inserted. RoundID={round_id}, {format_player_ids(duel)}")
                else:
                    print(f"[upload_match] No duel event. RoundID={round_id}")

                for hurt in match_round["HurtEvents"]:
                    try:
                        insert_hurt(cursor, round_id, match_id, hurt)
                    except Exception as exc:
                        print_insert_failure("Hurt", match_id, round_index, round_id, hurt, exc)
                        raise
                print(
                    "[upload_match] Hurt events inserted. "
                    f"RoundID={round_id}, Count={len(match_round['HurtEvents'])}, {format_events_player_ids(match_round['HurtEvents'])}"
                )

                for death in match_round["DeathEvents"]:
                    try:
                        insert_death(cursor, round_id, match_id, death)
                    except Exception as exc:
                        print_insert_failure("Death", match_id, round_index, round_id, death, exc)
                        raise
                print(
                    "[upload_match] Death events inserted. "
                    f"RoundID={round_id}, Count={len(match_round['DeathEvents'])}, {format_events_player_ids(match_round['DeathEvents'])}"
                )

                for blind in match_round["BlindEvents"]:
                    try:
                        insert_blind(cursor, round_id, match_id, blind)
                    except Exception as exc:
                        print_insert_failure("Blind", match_id, round_index, round_id, blind, exc)
                        raise
                print(
                    "[upload_match] Blind events inserted. "
                    f"RoundID={round_id}, Count={len(match_round['BlindEvents'])}, {format_events_player_ids(match_round['BlindEvents'])}"
                )

                for grenade in match_round["GrenadeEvents"]:
                    try:
                        insert_grenade(cursor, round_id, match_id, grenade)
                    except Exception as exc:
                        print_insert_failure("Grenade", match_id, round_index, round_id, grenade, exc)
                        raise
                print(
                    "[upload_match] Grenade events inserted. "
                    f"RoundID={round_id}, Count={len(match_round['GrenadeEvents'])}, {format_events_player_ids(match_round['GrenadeEvents'])}"
                )

                for kast in match_round["KASTEvents"]:
                    try:
                        insert_kast(cursor, round_id, match_id, kast)
                    except Exception as exc:
                        print_insert_failure("KAST", match_id, round_index, round_id, kast, exc)
                        raise
                print(
                    "[upload_match] KAST events inserted. "
                    f"RoundID={round_id}, Count={len(match_round['KASTEvents'])}, {format_events_player_ids(match_round['KASTEvents'])}"
                )

            print(f"[upload_match] All rounds inserted. MatchID={match_id}, Count={len(match_json['Rounds'])}")

            if len(match_json["Teams"]) == 2:
                team_a, team_b = match_json["Teams"].values()
                calculate_team_delta_elo(team_a, team_b)
                print(
                    "[upload_match] Elo deltas calculated. "
                    f"{team_a['TeamID']}={team_a['DeltaELO']}, PlayerIDs={team_a['PlayerIDs']}; "
                    f"{team_b['TeamID']}={team_b['DeltaELO']}, PlayerIDs={team_b['PlayerIDs']}"
                )
            else:
                print(f"[upload_match] Elo delta skipped. Expected 2 teams, got {len(match_json['Teams'])}.")

            for team in match_json["Teams"].values():
                delta_elo = team.get("DeltaELO", 0)
                side = team.get("Side", team.get("TeamNum"))

                insert_team_result(cursor, team["TeamID"], match_id, team["Score"], team["Result"], side, delta_elo)
                print(
                    "[upload_match] Team result inserted. "
                    f"MatchID={match_id}, TeamID={team['TeamID']}, Result={team['Result']}, "
                    f"Score={team['Score']}, DeltaELO={delta_elo}, PlayerIDs={team['PlayerIDs']}"
                )

                team_rows = update_team_elo(cursor, delta_elo, team["TeamID"])
                print(
                    "[upload_match] Team Elo updated. "
                    f"TeamID={team['TeamID']}, DeltaELO={delta_elo}, Rows={team_rows}, PlayerIDs={team['PlayerIDs']}"
                )

                player_rows = update_team_players_elo(cursor, delta_elo, team["TeamID"])
                print(
                    "[upload_match] Player Elo updated. "
                    f"TeamID={team['TeamID']}, DeltaELO={delta_elo}, Rows={player_rows}, PlayerIDs={team['PlayerIDs']}"
                )

            print(f"[upload_match] Database writes finished. MatchID={match_id}. Committing transaction.")
        except Exception as exc:
            print(f"[upload_match] Error while importing match. MatchID={locals().get('match_id', 'not-created')}, Error={exc}")
            raise
        finally:
            cursor.close()
            print("[upload_match] Cursor closed.")

    print(f"[upload_match] Transaction committed. MatchID={match_id}")

    return {
        "success": True,
        "message": "Match JSON received.",
        "type": type(match_json).__name__,
    }

def calculate_team_delta_elo(team_a, team_b):
    team_a["DeltaELO"] = 0
    team_b["DeltaELO"] = 0

    if team_a["Result"] == "Win":
        expected_win = expected_elo_win(team_a["AverageELO"], team_b["AverageELO"])
        team_a["DeltaELO"] = int(round(50 * (1 - expected_win)))
        team_b["DeltaELO"] = -team_a["DeltaELO"]
    elif team_b["Result"] == "Win":
        expected_win = expected_elo_win(team_b["AverageELO"], team_a["AverageELO"])
        team_b["DeltaELO"] = int(round(50 * (1 - expected_win)))
        team_a["DeltaELO"] = -team_b["DeltaELO"]
    elif team_a["Result"] == "Tie" and team_b["Result"] == "Tie":
        expected_win = expected_elo_win(team_a["AverageELO"], team_b["AverageELO"])
        team_a["DeltaELO"] = int(round(50 * (0.5 - expected_win)))
        team_b["DeltaELO"] = -team_a["DeltaELO"]

def expected_elo_win(team_elo, opponent_elo):
    return 1 / (1 + math.pow(10, (float(opponent_elo) - float(team_elo)) / 400))

def format_player_ids(event):
    player_ids = [f"{field}={event.get(field)}" for field in PLAYER_ID_FIELDS if field in event]
    return f"PlayerIDs=[{', '.join(player_ids)}]"

def format_events_player_ids(events):
    player_ids = []
    for event in events:
        player_ids.extend(f"{field}={event.get(field)}" for field in PLAYER_ID_FIELDS if field in event)
    return f"PlayerIDs=[{', '.join(player_ids)}]"

def print_insert_failure(event_name, match_id, round_index, round_id, event, exc):
    print(
        f"[upload_match] {event_name} insert failed. "
        f"MatchID={match_id}, RoundIndex={round_index}, RoundID={round_id}, "
        f"{format_player_ids(event)}, Event={event}, Error={exc}"
    )

def validate_authorization(request, expected_auth_key):
    if not expected_auth_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Upload auth key is not configured.",
        )

    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")

    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not secrets.compare_digest(token, expected_auth_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid bearer token.",
        )