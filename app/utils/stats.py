UTILITY_WEAPONS = ("smokegrenade", "molotov", "inferno", "hegrenade", "flashbang", "decoy")
DERIVED_STAT_KEYS = ("KAST", "ADR", "KPR", "APR", "DPR", "Impact", "Rating")


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


def apply_derived_stats(stats, total_rounds, kast_rounds=None, rounds_key=None, zero_value=0):
    if total_rounds > 0:
        total_rounds_fl = float(total_rounds)
        if rounds_key:
            stats[rounds_key] = total_rounds

        if kast_rounds is None:
            kast_rounds = stats["KAST"]

        stats["KAST"] = (float(kast_rounds) / total_rounds_fl) * 100.0
        stats["ADR"] = float(stats["Damage"]) / total_rounds_fl
        stats["KPR"] = float(stats["Kills"]) / total_rounds_fl
        stats["APR"] = float(stats["Assists"]) / total_rounds_fl
        stats["DPR"] = float(stats["Deaths"]) / total_rounds_fl

        stats["Impact"], stats["Rating"] = calculate_impact_and_rating(
            stats["KPR"],
            stats["APR"],
            stats["DPR"],
            stats["KAST"],
            stats["ADR"],
        )

        for key in DERIVED_STAT_KEYS:
            stats[key] = round(stats[key], 2) or zero_value
    else:
        if rounds_key:
            stats[rounds_key] = zero_value
        for key in DERIVED_STAT_KEYS:
            stats[key] = zero_value

    return stats


def empty_player_stats(player_id):
    return {
        "PlayerID": player_id,
        "Damage": 0,
        "UtilityDamage": 0,
        "Kills": 0,
        "Assists": 0,
        "Deaths": 0,
        "Headshots": 0,
        "Blinds": {"Count": 0, "TotalDuration": 0.0},
        "RoundsPlayed": 0,
        "RoundsKAST": 0,
        "KAST": 0,
        "ADR": 0,
        "KPR": 0,
        "APR": 0,
        "DPR": 0,
        "Impact": 0,
        "Rating": 0,
    }


def combine_player_stats(t_stats, ct_stats):
    stats = {
        "PlayerID": t_stats["PlayerID"],
        "Damage": t_stats["Damage"] + ct_stats["Damage"],
        "UtilityDamage": t_stats["UtilityDamage"] + ct_stats["UtilityDamage"],
        "Kills": t_stats["Kills"] + ct_stats["Kills"],
        "Assists": t_stats["Assists"] + ct_stats["Assists"],
        "Deaths": t_stats["Deaths"] + ct_stats["Deaths"],
        "Headshots": t_stats["Headshots"] + ct_stats["Headshots"],
        "Blinds": {
            "Count": t_stats["Blinds"]["Count"] + ct_stats["Blinds"]["Count"],
            "TotalDuration": t_stats["Blinds"]["TotalDuration"] + ct_stats["Blinds"]["TotalDuration"],
        },
        "RoundsPlayed": t_stats["RoundsPlayed"] + ct_stats["RoundsPlayed"],
        "RoundsKAST": t_stats["RoundsKAST"] + ct_stats["RoundsKAST"],
    }

    return apply_derived_stats(
        stats,
        stats["RoundsPlayed"],
        kast_rounds=stats["RoundsKAST"],
        zero_value=0,
    )
