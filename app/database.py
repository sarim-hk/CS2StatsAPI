from contextlib import contextmanager
import mysql.connector
from .config import get_settings

def create_db_connection(settings):
    return mysql.connector.connect(
        host=settings.mysql_server,
        database=settings.mysql_database,
        user=settings.mysql_username,
        password=settings.mysql_password,
    )

def create_tables(settings=None):
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

    CREATE TABLE IF NOT EXISTS CS2S_PlayerRating (
        PlayerRatingID int UNSIGNED PRIMARY KEY AUTO_INCREMENT NOT NULL,
        PlayerID bigint UNSIGNED NOT NULL,
        RangeDays int UNSIGNED NOT NULL,
        Side tinyint UNSIGNED NOT NULL,
        MatchesPlayed int UNSIGNED NOT NULL DEFAULT 0,
        RoundsPlayed int UNSIGNED NOT NULL DEFAULT 0,
        RoundsKAST int UNSIGNED NOT NULL DEFAULT 0,
        Kills int UNSIGNED NOT NULL DEFAULT 0,
        Assists int UNSIGNED NOT NULL DEFAULT 0,
        Deaths int UNSIGNED NOT NULL DEFAULT 0,
        Damage int UNSIGNED NOT NULL DEFAULT 0,
        Rating decimal(5,2) NOT NULL DEFAULT 0,
        UpdateDate datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (PlayerID) REFERENCES CS2S_PlayerInfo(PlayerID),
        UNIQUE KEY uq_player_rating (PlayerID, Side, RangeDays)
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

    """

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

def _placeholders(values):
    return ", ".join(["%s"] * len(values))

def avatar_hash_base_sql(alias="p"):
    return f"REPLACE({alias}.AvatarHash, '.jpg', '')"

def avatar_url_sql(alias="p", size=""):
    suffix = f"_{size}" if size else ""
    return (
        "CONCAT("
        "'https://avatars.steamstatic.com/', "
        f"{avatar_hash_base_sql(alias)}, "
        f"'{suffix}.jpg'"
        ")"
    )

def player_info_select_sql(alias="p"):
    return f"""
        {alias}.PlayerID,
        {alias}.ELO,
        {alias}.Username,
        {avatar_url_sql(alias)} AS AvatarS,
        {avatar_url_sql(alias, "medium")} AS AvatarM,
        {avatar_url_sql(alias, "full")} AS AvatarL
    """

def fetch_matches(db, player_id=None, map_name=None, page=None):
    cursor = db.cursor(dictionary=True)
    try:
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

        query = f"""
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
                tr_l.DeltaELO AS LosingDeltaELO,
                CASE
                    WHEN tr_w.Result = 'Tie' THEN 'Tie'
                    ELSE 'Win'
                END AS MatchResult
            FROM
                CS2S_Match m
            JOIN
                CS2S_TeamResult tr_w
                    ON m.MatchID = tr_w.MatchID
                    AND tr_w.Result IN ('Win', 'Tie')
            JOIN
                CS2S_TeamResult tr_l
                    ON m.MatchID = tr_l.MatchID
                    AND (
                        (tr_w.Result = 'Win' AND tr_l.Result = 'Loss')
                        OR (
                            tr_w.Result = 'Tie'
                            AND tr_l.Result = 'Tie'
                            AND tr_w.TeamID < tr_l.TeamID
                        )
                    )
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

        try:
            cursor.execute(query, tuple(query_params))
        except Exception as e:
            print(e)
        return cursor.fetchall()
    finally:
        cursor.close()

def fetch_player_elo_history(db, player_id):
    cursor = db.cursor(dictionary=True)
    try:
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
        return cursor.fetchall()
    finally:
        cursor.close()

def fetch_player_panel(db, player_id):
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            f"""
            SELECT {player_info_select_sql("p")}
            FROM CS2S_PlayerInfo p
            WHERE p.PlayerID = %s
            """,
            (player_id,),
        )
        return cursor.fetchone()
    finally:
        cursor.close()

def fetch_players_panel(db):
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            f"""
            SELECT {player_info_select_sql("p")}
            FROM CS2S_PlayerInfo p
            JOIN CS2S_Player_Matches pm ON p.PlayerID = pm.PlayerID
            GROUP BY p.PlayerID
            HAVING COUNT(pm.MatchID) > 0
            ORDER BY p.ELO DESC
            """
        )
        return cursor.fetchall()
    finally:
        cursor.close()

def fetch_match_by_id(cursor, match_id):
    cursor.execute("SELECT * FROM CS2S_Match WHERE MatchID = %s", (match_id,))
    return cursor.fetchone()

def fetch_team_results_for_match(cursor, match_id):
    cursor.execute(
        """
        SELECT tr.*, t.Name AS TeamName
        FROM CS2S_TeamResult tr
        LEFT JOIN CS2S_Team t ON tr.TeamID = t.TeamID
        WHERE tr.MatchID = %s
        """,
        (match_id,),
    )
    return cursor.fetchall()

def fetch_player_teams_for_match(cursor, match_id):
    cursor.execute(
        """
        SELECT tp.PlayerID, tp.TeamID
        FROM CS2S_Team_Players tp
        JOIN CS2S_TeamResult tr ON tp.TeamID = tr.TeamID
        WHERE tr.MatchID = %s
        """,
        (match_id,),
    )
    return cursor.fetchall()

def fetch_players_info_for_match(cursor, match_id):
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
    return cursor.fetchall()

def fetch_rounds_for_match(cursor, match_id):
    cursor.execute("SELECT * FROM CS2S_Round WHERE MatchID = %s", (match_id,))
    return cursor.fetchall()

def fetch_deaths_for_match(cursor, match_id):
    cursor.execute("SELECT * FROM CS2S_Death WHERE MatchID = %s", (match_id,))
    return cursor.fetchall()

def fetch_clutches_for_match(cursor, match_id):
    cursor.execute("SELECT * FROM CS2S_Clutch WHERE MatchID = %s", (match_id,))
    return cursor.fetchall()

def fetch_duels_for_match(cursor, match_id):
    cursor.execute("SELECT * FROM CS2S_Duel WHERE MatchID = %s", (match_id,))
    return cursor.fetchall()

def fetch_kast_for_match(cursor, match_id):
    cursor.execute("SELECT * FROM CS2S_KAST WHERE MatchID = %s", (match_id,))
    return cursor.fetchall()

def fetch_blinds_for_match(cursor, match_id):
    cursor.execute("SELECT * FROM CS2S_Blind WHERE MatchID = %s", (match_id,))
    return cursor.fetchall()

def fetch_damage_for_match(cursor, match_id):
    cursor.execute("SELECT * FROM CS2S_Hurt WHERE MatchID = %s", (match_id,))
    return cursor.fetchall()

def fetch_match_results_match_range(cursor, range_size, player_ids, map_id=None):
    player_id_placeholders = _placeholders(player_ids)
    query = f"""
        SELECT
            pm.MatchID,
            tr.Result
        FROM CS2S_Player_Matches pm
        JOIN CS2S_TeamResult tr ON pm.MatchID = tr.MatchID
        JOIN CS2S_Team_Players tp ON tr.TeamID = tp.TeamID
        JOIN CS2S_Match m ON pm.MatchID = m.MatchID
        WHERE pm.PlayerID IN ({player_id_placeholders})
          AND tp.PlayerID IN ({player_id_placeholders})
        {'' if map_id is None else 'AND m.MapID = %s'}
        GROUP BY pm.MatchID, tr.Result
        ORDER BY pm.MatchID DESC
        LIMIT %s
    """
    if map_id is not None:
        params = (*player_ids, *player_ids, map_id, range_size)
    else:
        params = (*player_ids, *player_ids, range_size)

    cursor.execute(query, params)
    return cursor.fetchall()

def fetch_match_results_date_range(cursor, start_date, player_ids, map_id=None):
    player_id_placeholders = _placeholders(player_ids)
    query = f"""
    WITH DateRangeMatches AS (
        SELECT MatchID, MatchDate
        FROM CS2S_Match
        WHERE MatchDate >= %s
          {'' if map_id is None else 'AND MapID = %s'}
    )
    SELECT
        pm.MatchID,
        tr.Result
    FROM DateRangeMatches drm
    JOIN CS2S_Player_Matches pm ON drm.MatchID = pm.MatchID
    JOIN CS2S_TeamResult tr ON pm.MatchID = tr.MatchID
    JOIN CS2S_Team_Players tp ON tr.TeamID = tp.TeamID
    WHERE pm.PlayerID IN ({player_id_placeholders})
      AND tp.PlayerID IN ({player_id_placeholders})
    GROUP BY pm.MatchID, tr.Result
    """
    if map_id is not None:
        params = (start_date, map_id, *player_ids, *player_ids)
    else:
        params = (start_date, *player_ids, *player_ids)

    cursor.execute(query, params)
    return cursor.fetchall()

def fetch_round_sides_for_player_matches(cursor, match_ids, player_id):
    parameterised_match_ids = _placeholders(match_ids)
    cursor.execute(
        f"""
        SELECT
            R.RoundID,
            R.MatchID,
            CASE
                WHEN T.PlayerID IS NOT NULL THEN R.WinnerSide
                ELSE R.LoserSide
            END AS PlayerSide
        FROM
            CS2S_Round R
        LEFT JOIN
            CS2S_Team_Players T ON R.WinnerTeamID = T.TeamID AND T.PlayerID = %s
        LEFT JOIN
            CS2S_Team_Players LT ON R.LoserTeamID = LT.TeamID AND LT.PlayerID = %s
        WHERE
            (T.PlayerID IS NOT NULL OR LT.PlayerID IS NOT NULL)
            AND R.MatchID IN ({parameterised_match_ids});
        """,
        (player_id, player_id, *match_ids),
    )
    return cursor.fetchall()

def fetch_match_ids_for_map(cursor, match_ids, map_id):
    parameterized_match_ids = _placeholders(match_ids)
    cursor.execute(
        f"""
        SELECT MatchID
        FROM CS2S_Match
        WHERE MatchID IN ({parameterized_match_ids}) AND MapID = %s
        """,
        (*match_ids, map_id),
    )
    return cursor.fetchall()

def fetch_player_stats_for_rounds(cursor, round_ids, player_id, utility_weapons):
    round_placeholders = _placeholders(round_ids)
    utility_placeholders = _placeholders(utility_weapons)
    cursor.execute(
        f"""
        WITH
        damage_stats AS (
            SELECT
                AttackerID,
                SUM(CASE WHEN Weapon IN ({utility_placeholders}) THEN Damage ELSE 0 END) AS UtilityDamage,
                SUM(CASE WHEN Weapon NOT IN ({utility_placeholders}) THEN Damage ELSE 0 END) +
                SUM(CASE WHEN Weapon IN ({utility_placeholders}) THEN Damage ELSE 0 END) AS Damage
            FROM CS2S_Hurt
            WHERE AttackerID = %s AND RoundID IN ({round_placeholders})
            GROUP BY AttackerID
        ),
        death_stats AS (
            SELECT
                %s AS PlayerID,
                SUM(CASE WHEN AttackerID = %s THEN 1 ELSE 0 END) AS Kills,
                SUM(CASE WHEN AssisterID = %s THEN 1 ELSE 0 END) AS Assists,
                SUM(CASE WHEN VictimID = %s THEN 1 ELSE 0 END) AS Deaths,
                SUM(CASE WHEN AttackerID = %s AND Hitgroup = 1 THEN 1 ELSE 0 END) AS Headshots
            FROM CS2S_Death
            WHERE RoundID IN ({round_placeholders})
        ),
        blind_stats AS (
            SELECT
                ThrowerID,
                COUNT(*) AS EnemiesFlashed,
                SUM(Duration) AS TotalDuration
            FROM CS2S_Blind
            WHERE ThrowerID = %s AND RoundID IN ({round_placeholders})
            GROUP BY ThrowerID
        ),
        kast_stats AS (
            SELECT
                PlayerID,
                COUNT(*) AS KAST
            FROM CS2S_KAST
            WHERE PlayerID = %s AND RoundID IN ({round_placeholders})
            GROUP BY PlayerID
        )
        SELECT
            %s AS PlayerID,
            COALESCE(d.Damage, 0) AS Damage,
            COALESCE(d.UtilityDamage, 0) AS UtilityDamage,
            COALESCE(ds.Kills, 0) AS Kills,
            COALESCE(ds.Assists, 0) AS Assists,
            COALESCE(ds.Deaths, 0) AS Deaths,
            COALESCE(ds.Headshots, 0) AS Headshots,
            COALESCE(b.EnemiesFlashed, 0) AS EnemiesFlashed,
            COALESCE(b.TotalDuration, 0.0) AS TotalDuration,
            %s AS RoundsPlayed,
            COALESCE(k.KAST, 0) AS RoundsKAST
        FROM
            death_stats ds
        LEFT JOIN
            damage_stats d ON d.AttackerID = ds.PlayerID
        LEFT JOIN
            blind_stats b ON ds.PlayerID = b.ThrowerID
        LEFT JOIN
            kast_stats k ON ds.PlayerID = k.PlayerID
        """,
        (
            *utility_weapons,
            *utility_weapons,
            *utility_weapons,
            player_id,
            *round_ids,
            player_id,
            player_id,
            player_id,
            player_id,
            player_id,
            *round_ids,
            player_id,
            *round_ids,
            player_id,
            *round_ids,
            player_id,
            len(round_ids),
        ),
    )
    return cursor.fetchone()

def insert_map(cursor, map_id):
    cursor.execute(
        """
        INSERT IGNORE INTO CS2S_Map (MapID)
        VALUES (%s);
        """,
        (map_id,),
    )

def insert_match(cursor, map_id, start_tick, end_tick):
    cursor.execute(
        """
        INSERT INTO CS2S_Match (MapID, StartTick, EndTick)
        VALUES (%s, %s, %s);
        """,
        (map_id, start_tick, end_tick),
    )
    return cursor.lastrowid

def insert_team(cursor, team_id, size, name):
    cursor.execute(
        """
        INSERT IGNORE INTO CS2S_Team (TeamID, Size, Name)
        VALUES (%s, %s, %s);
        """,
        (team_id, size, name),
    )

def insert_team_player(cursor, team_id, player_id):
    cursor.execute(
        """
        INSERT IGNORE INTO CS2S_Team_Players (TeamID, PlayerID)
        VALUES (%s, %s);
        """,
        (team_id, player_id),
    )

def insert_player_match(cursor, player_id, match_id):
    cursor.execute(
        """
        INSERT INTO CS2S_Player_Matches (PlayerID, MatchID)
        VALUES (%s, %s);
        """,
        (player_id, match_id),
    )

def fetch_team_average_elo(cursor, team_id):
    cursor.execute(
        """
        SELECT AVG(p.ELO)
        FROM CS2S_PlayerInfo p
        INNER JOIN CS2S_Team_Players tp ON p.PlayerID = tp.PlayerID
        WHERE tp.TeamID = %s;
        """,
        (team_id,),
    )
    return cursor.fetchone()[0]

def insert_round(cursor, match_id, match_round):
    cursor.execute(
        """
        INSERT INTO CS2S_Round (MatchID, WinnerTeamID, LoserTeamID, WinnerSide, LoserSide, RoundEndReason, StartTick, EndTick)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
        """,
        (
            match_id,
            match_round["WinningTeamID"],
            match_round["LosingTeamID"],
            match_round["WinningTeamNum"],
            match_round["LosingTeamNum"],
            match_round["WinningReason"],
            match_round["StartTick"],
            match_round["EndTick"],
        ),
    )
    return cursor.lastrowid

def insert_clutch(cursor, round_id, match_id, clutch):
    cursor.execute(
        """
        INSERT INTO CS2S_Clutch (RoundID, MatchID, PlayerID, PlayerSide, EnemyCount, Result)
        VALUES (%s, %s, %s, %s, %s, %s);
        """,
        (round_id, match_id, clutch["ClutcherID"], clutch["ClutcherSide"], clutch["EnemyCount"], clutch["Result"]),
    )

def insert_duel(cursor, round_id, match_id, duel):
    cursor.execute(
        """
        INSERT INTO CS2S_Duel (RoundID, MatchID, WinnerID, WinnerSide, LoserID, LoserSide)
        VALUES (%s, %s, %s, %s, %s, %s);
        """,
        (round_id, match_id, duel["WinnerID"], duel["WinnerSide"], duel["LoserID"], duel["LoserSide"]),
    )

def insert_hurt(cursor, round_id, match_id, hurt):
    cursor.execute(
        """
        INSERT INTO CS2S_Hurt (RoundID, MatchID, AttackerID, AttackerSide, VictimID, VictimSide, Damage, Weapon, Hitgroup, RoundTick)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """,
        (
            round_id,
            match_id,
            hurt["AttackerID"],
            hurt["AttackerSide"],
            hurt["VictimID"],
            hurt["VictimSide"],
            hurt["Damage"],
            hurt["Weapon"],
            hurt["Hitgroup"],
            hurt["RoundTick"],
        ),
    )

def insert_death(cursor, round_id, match_id, death):
    cursor.execute(
        """
        INSERT INTO CS2S_Death (RoundID, MatchID, AttackerID, AttackerSide, AssisterID, AssisterSide, VictimID, VictimSide, Weapon, Hitgroup, OpeningDeath, RoundTick)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """,
        (
            round_id,
            match_id,
            death["AttackerID"],
            death["AttackerSide"],
            death["AssisterID"],
            death["AssisterSide"],
            death["VictimID"],
            death["VictimSide"],
            death["Weapon"],
            death["Hitgroup"],
            death["OpeningDeath"],
            death["RoundTick"],
        ),
    )

def insert_blind(cursor, round_id, match_id, blind):
    cursor.execute(
        """
        INSERT INTO CS2S_Blind (RoundID, MatchID, ThrowerID, ThrowerSide, BlindedID, BlindedSide, Duration, RoundTick)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
        """,
        (
            round_id,
            match_id,
            blind["ThrowerID"],
            blind["ThrowerSide"],
            blind["BlindedID"],
            blind["BlindedSide"],
            blind["Duration"],
            blind["RoundTick"],
        ),
    )

def insert_grenade(cursor, round_id, match_id, grenade):
    cursor.execute(
        """
        INSERT INTO CS2S_Grenade (RoundID, MatchID, ThrowerID, ThrowerSide, Weapon, RoundTick)
        VALUES (%s, %s, %s, %s, %s, %s);
        """,
        (round_id, match_id, grenade["ThrowerID"], grenade["ThrowerSide"], grenade["Weapon"], grenade["RoundTick"]),
    )

def insert_kast(cursor, round_id, match_id, kast):
    cursor.execute(
        """
        INSERT INTO CS2S_KAST (RoundID, MatchID, PlayerID, PlayerSide)
        VALUES (%s, %s, %s, %s);
        """,
        (round_id, match_id, kast["PlayerID"], kast["PlayerSide"]),
    )

def insert_team_result(cursor, team_id, match_id, score, result, side, delta_elo):
    cursor.execute(
        """
        INSERT INTO CS2S_TeamResult (TeamID, MatchID, Score, Result, Side, DeltaELO)
        VALUES (%s, %s, %s, %s, %s, %s);
        """,
        (team_id, match_id, score, result, side, delta_elo),
    )

def update_team_elo(cursor, delta_elo, team_id):
    cursor.execute(
        """
        UPDATE CS2S_Team
        SET ELO = ELO + %s
        WHERE TeamID = %s;
        """,
        (delta_elo, team_id),
    )
    return cursor.rowcount

def update_team_players_elo(cursor, delta_elo, team_id):
    cursor.execute(
        """
        UPDATE CS2S_PlayerInfo p
        JOIN CS2S_Team_Players tp ON p.PlayerID = tp.PlayerID
        SET p.ELO = p.ELO + %s
        WHERE tp.TeamID = %s;
        """,
        (delta_elo, team_id),
    )
    return cursor.rowcount

def insert_player_info(cursor, player_id, username, avatar_hash):
    cursor.execute(
        """
        INSERT INTO CS2S_PlayerInfo
            (PlayerID, Username, AvatarHash)
        VALUES
            (%s, COALESCE(%s, DEFAULT(Username)), COALESCE(%s, DEFAULT(AvatarHash)))
        ON DUPLICATE KEY UPDATE
            Username = COALESCE(%s, Username),
            AvatarHash = COALESCE(%s, AvatarHash);
        """,
        (player_id, username, avatar_hash, username, avatar_hash),
    )
    return cursor.rowcount
