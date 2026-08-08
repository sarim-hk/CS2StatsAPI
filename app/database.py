from contextlib import contextmanager
import mysql.connector

from .config import get_settings


CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS CS2S_Map (
    MapID varchar(128) PRIMARY KEY NOT NULL
);

CREATE TABLE IF NOT EXISTS CS2S_PlayerInfo (
    PlayerID bigint UNSIGNED PRIMARY KEY NOT NULL,
    ELO int UNSIGNED DEFAULT 1000 NOT NULL,
    Username varchar(255) DEFAULT 'Anonymous' NOT NULL,
    AvatarHash varchar(255) DEFAULT 'b5bd56c1aa4644a474a2e4972be27ef9e82e517e' NOT NULL
);

CREATE TABLE IF NOT EXISTS CS2S_Match (
    MatchID int UNSIGNED PRIMARY KEY AUTO_INCREMENT NOT NULL,
    MapID varchar(128) NOT NULL,
    StartTick int UNSIGNED NOT NULL,
    EndTick int UNSIGNED NOT NULL,
    MatchDate datetime DEFAULT CURRENT_TIMESTAMP NOT NULL,
    FOREIGN KEY (MapID) REFERENCES CS2S_Map(MapID)
);

CREATE TABLE IF NOT EXISTS CS2S_Team (
    TeamID varchar(32) PRIMARY KEY,
    Size tinyint UNSIGNED NOT NULL,
    ELO int UNSIGNED DEFAULT 1000 NOT NULL,
    Name varchar(64) DEFAULT 'Team' NOT NULL
);

CREATE TABLE IF NOT EXISTS CS2S_TeamResult (
    TeamID varchar(32) NOT NULL,
    MatchID int UNSIGNED NOT NULL,
    Score smallint UNSIGNED NOT NULL,
    Result ENUM('Win', 'Loss', 'Tie') NOT NULL,
    Side tinyint UNSIGNED NOT NULL,
    DeltaELO int DEFAULT 0 NOT NULL,
    PRIMARY KEY (TeamID, MatchID),
    FOREIGN KEY (TeamID) REFERENCES CS2S_Team(TeamID),
    FOREIGN KEY (MatchID) REFERENCES CS2S_Match(MatchID)
);

CREATE TABLE IF NOT EXISTS CS2S_Round (
    RoundID int UNSIGNED PRIMARY KEY AUTO_INCREMENT NOT NULL,
    MatchID int UNSIGNED NOT NULL,
    WinnerTeamID varchar(32) NOT NULL,
    LoserTeamID varchar(32) NOT NULL,
    WinnerSide tinyint UNSIGNED NOT NULL,
    LoserSide tinyint UNSIGNED NOT NULL,
    RoundEndReason tinyint UNSIGNED NOT NULL,
    StartTick int UNSIGNED NOT NULL,
    EndTick int UNSIGNED NOT NULL,
    FOREIGN KEY (MatchID) REFERENCES CS2S_Match(MatchID),
    FOREIGN KEY (WinnerTeamID) REFERENCES CS2S_Team(TeamID),
    FOREIGN KEY (LoserTeamID) REFERENCES CS2S_Team(TeamID)
);

CREATE TABLE IF NOT EXISTS CS2S_Death (
    DeathID int UNSIGNED PRIMARY KEY AUTO_INCREMENT NOT NULL,
    RoundID int UNSIGNED NOT NULL,
    MatchID int UNSIGNED NOT NULL,
    AttackerID bigint UNSIGNED NULL,
    AttackerSide tinyint UNSIGNED NULL,
    AssisterID bigint UNSIGNED NULL,
    AssisterSide tinyint UNSIGNED NULL,
    VictimID bigint UNSIGNED NOT NULL,
    VictimSide tinyint UNSIGNED NOT NULL,
    Weapon varchar(32) NOT NULL,
    Hitgroup tinyint UNSIGNED NOT NULL,
    RoundTick int UNSIGNED NOT NULL,
    OpeningDeath bool NOT NULL,
    FOREIGN KEY (RoundID) REFERENCES CS2S_Round(RoundID),
    FOREIGN KEY (MatchID) REFERENCES CS2S_Match(MatchID),
    FOREIGN KEY (AttackerID) REFERENCES CS2S_PlayerInfo(PlayerID),
    FOREIGN KEY (AssisterID) REFERENCES CS2S_PlayerInfo(PlayerID),
    FOREIGN KEY (VictimID) REFERENCES CS2S_PlayerInfo(PlayerID)
);

CREATE TABLE IF NOT EXISTS CS2S_Hurt (
    HurtID int UNSIGNED PRIMARY KEY AUTO_INCREMENT NOT NULL,
    RoundID int UNSIGNED NOT NULL,
    MatchID int UNSIGNED NOT NULL,
    AttackerID bigint UNSIGNED NULL,
    AttackerSide tinyint UNSIGNED NULL,
    VictimID bigint UNSIGNED NOT NULL,
    VictimSide tinyint UNSIGNED NULL,
    Damage smallint UNSIGNED NOT NULL,
    Weapon varchar(32) NOT NULL,
    Hitgroup tinyint UNSIGNED NOT NULL,
    RoundTick int UNSIGNED NOT NULL,
    FOREIGN KEY (RoundID) REFERENCES CS2S_Round(RoundID),
    FOREIGN KEY (MatchID) REFERENCES CS2S_Match(MatchID),
    FOREIGN KEY (AttackerID) REFERENCES CS2S_PlayerInfo(PlayerID),
    FOREIGN KEY (VictimID) REFERENCES CS2S_PlayerInfo(PlayerID)
);

CREATE TABLE IF NOT EXISTS CS2S_Blind (
    BlindID int UNSIGNED PRIMARY KEY AUTO_INCREMENT NOT NULL,
    RoundID int UNSIGNED NOT NULL,
    MatchID int UNSIGNED NOT NULL,
    ThrowerID bigint UNSIGNED NOT NULL,
    ThrowerSide tinyint UNSIGNED NOT NULL,
    BlindedID bigint UNSIGNED NOT NULL,
    BlindedSide tinyint UNSIGNED NOT NULL,
    Duration float NOT NULL,
    RoundTick int UNSIGNED NOT NULL,
    FOREIGN KEY (RoundID) REFERENCES CS2S_Round(RoundID),
    FOREIGN KEY (MatchID) REFERENCES CS2S_Match(MatchID),
    FOREIGN KEY (ThrowerID) REFERENCES CS2S_PlayerInfo(PlayerID),
    FOREIGN KEY (BlindedID) REFERENCES CS2S_PlayerInfo(PlayerID)
);

CREATE TABLE IF NOT EXISTS CS2S_Grenade (
    GrenadeID int UNSIGNED PRIMARY KEY AUTO_INCREMENT NOT NULL,
    RoundID int UNSIGNED NOT NULL,
    MatchID int UNSIGNED NOT NULL,
    ThrowerID bigint UNSIGNED NOT NULL,
    ThrowerSide tinyint UNSIGNED NOT NULL,
    Weapon varchar(32) NOT NULL,
    RoundTick int UNSIGNED NOT NULL,
    FOREIGN KEY (RoundID) REFERENCES CS2S_Round(RoundID),
    FOREIGN KEY (MatchID) REFERENCES CS2S_Match(MatchID),
    FOREIGN KEY (ThrowerID) REFERENCES CS2S_PlayerInfo(PlayerID)
);

CREATE TABLE IF NOT EXISTS CS2S_KAST (
    KASTID int UNSIGNED PRIMARY KEY AUTO_INCREMENT NOT NULL,
    RoundID int UNSIGNED NOT NULL,
    MatchID int UNSIGNED NOT NULL,
    PlayerID bigint UNSIGNED NOT NULL,
    PlayerSide tinyint UNSIGNED NOT NULL,
    FOREIGN KEY (RoundID) REFERENCES CS2S_Round(RoundID),
    FOREIGN KEY (MatchID) REFERENCES CS2S_Match(MatchID),
    FOREIGN KEY (PlayerID) REFERENCES CS2S_PlayerInfo(PlayerID)
);

CREATE TABLE IF NOT EXISTS CS2S_Clutch (
    ClutchID int UNSIGNED PRIMARY KEY AUTO_INCREMENT NOT NULL,
    RoundID int UNSIGNED NOT NULL,
    MatchID int UNSIGNED NOT NULL,
    PlayerID bigint UNSIGNED NOT NULL,
    PlayerSide tinyint UNSIGNED NOT NULL,
    EnemyCount tinyint UNSIGNED NOT NULL,
    Result ENUM('Win', 'Loss') NOT NULL,
    FOREIGN KEY (RoundID) REFERENCES CS2S_Round(RoundID),
    FOREIGN KEY (MatchID) REFERENCES CS2S_Match(MatchID),
    FOREIGN KEY (PlayerID) REFERENCES CS2S_PlayerInfo(PlayerID)
);

CREATE TABLE IF NOT EXISTS CS2S_Duel (
    DuelID int UNSIGNED PRIMARY KEY AUTO_INCREMENT NOT NULL,
    RoundID int UNSIGNED NOT NULL,
    MatchID int UNSIGNED NOT NULL,
    WinnerID bigint UNSIGNED NOT NULL,
    WinnerSide tinyint UNSIGNED NOT NULL,
    LoserID bigint UNSIGNED NOT NULL,
    LoserSide tinyint UNSIGNED NOT NULL,
    FOREIGN KEY (RoundID) REFERENCES CS2S_Round(RoundID),
    FOREIGN KEY (MatchID) REFERENCES CS2S_Match(MatchID),
    FOREIGN KEY (WinnerID) REFERENCES CS2S_PlayerInfo(PlayerID),
    FOREIGN KEY (LoserID) REFERENCES CS2S_PlayerInfo(PlayerID)
);

CREATE TABLE IF NOT EXISTS CS2S_LivePlayers (
    PlayerID bigint NOT NULL,
    Kills int DEFAULT 0 NOT NULL,
    Assists int UNSIGNED DEFAULT 0 NOT NULL,
    Deaths int UNSIGNED DEFAULT 0 NOT NULL,
    ADR float UNSIGNED DEFAULT 0 NOT NULL,
    Health smallint UNSIGNED DEFAULT 0 NOT NULL,
    Money int UNSIGNED DEFAULT 0 NOT NULL,
    Side tinyint UNSIGNED NOT NULL
);

CREATE TABLE IF NOT EXISTS CS2S_LiveStatus (
    StaticID int PRIMARY KEY,
    MapID varchar(128),
    BombStatus tinyint UNSIGNED,
    TScore smallint UNSIGNED,
    CTScore smallint UNSIGNED,
    InsertDate datetime DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS CS2S_Team_Players (
    TeamID varchar(32) NOT NULL,
    PlayerID bigint UNSIGNED NOT NULL,
    PRIMARY KEY (TeamID, PlayerID),
    FOREIGN KEY (TeamID) REFERENCES CS2S_Team(TeamID),
    FOREIGN KEY (PlayerID) REFERENCES CS2S_PlayerInfo(PlayerID)
);

CREATE TABLE IF NOT EXISTS CS2S_Player_Matches (
    PlayerID bigint UNSIGNED NOT NULL,
    MatchID int UNSIGNED NOT NULL,
    PRIMARY KEY (PlayerID, MatchID),
    FOREIGN KEY (PlayerID) REFERENCES CS2S_PlayerInfo(PlayerID),
    FOREIGN KEY (MatchID) REFERENCES CS2S_Match(MatchID)
);

CREATE TABLE IF NOT EXISTS CS2S_PlayerOfTheWeek (
    PlayerID bigint UNSIGNED NOT NULL,
    WeekPosition smallint UNSIGNED DEFAULT 0 NOT NULL,
    BaseRating float DEFAULT 0 NOT NULL,
    WeekRating float DEFAULT 0 NOT NULL,
    RatingDelta float DEFAULT 0 NOT NULL,
    PRIMARY KEY (PlayerID),
    FOREIGN KEY (PlayerID) REFERENCES CS2S_PlayerInfo(PlayerID)
);
"""

def create_db_connection(settings):
    return mysql.connector.connect(
        host=settings.mysql_server,
        database=settings.mysql_database,
        user=settings.mysql_username,
        password=settings.mysql_password,
    )

def create_tables(settings=None):
    db = create_db_connection(settings or get_settings())
    cursor = None
    try:
        cursor = db.cursor()
        for statement in CREATE_TABLES_SQL.split(";"):
            statement = statement.strip()
            if statement:
                cursor.execute(statement)
        db.commit()
    finally:
        if cursor is not None:
            cursor.close()
        db.close()

@contextmanager
def transaction(settings=None):
    db = create_db_connection(settings or get_settings())
    try:
        db.start_transaction()
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def get_db():
    db = create_db_connection(get_settings())
    try:
        yield db
    finally:
        db.close()
