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
