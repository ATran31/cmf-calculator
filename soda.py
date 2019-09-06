# This module interacts with the Socrata Open Data API (SODA) to fetch crash data provided by the MD Open Data Portal.

import requests


def fetch_crash_reports(
    url: str,
    route_prefix: str,
    route_number: int,
    start_milepost: float,
    end_milepost: float,
    start_year: int,
    end_year: int,
) -> list:
    """
    Executes a GET request against the crash data API.
    Returns desired crash reports as list of dicts.
    """
    columns = [
        "report_no",
        "county_desc",
        "route_type_code",
        "rte_no",
        "logmile_dir_flag",
        "log_mile",
        "acc_time",
        "acc_date",
        "year",
        "report_type",
        "collision_type_desc",
    ]
    query_url = f"{url}?$select={','.join(columns)}&$where=year between {start_year} and {end_year} and log_mile between {start_milepost} and {end_milepost}&route_type_code={route_prefix}&rte_no={route_number}"
    r = requests.get(query_url)
    if r.status_code == 200:
        crashes = r.json()
        for crash in crashes:
            # reformat crash time into hh:mm:ss format
            crash[
                "acc_time"
            ] = f"{crash['acc_time'][:2]}:{crash['acc_time'][2:4]}:{crash['acc_time'][4:]}"
            # reformat crash date into yyyy-mm-dd format
            crash[
                "acc_date"
            ] = f"{crash['acc_date'][:4]}-{crash['acc_date'][4:6]}-{crash['acc_date'][6:]}"
        return crashes
    else:
        r.raise_for_status()


def get_crash_types(crashes: list) -> tuple:
    """
    Return a tuple of distinct crash types.
    """
    crash_types = []
    for crash in crashes:
        if crash["collision_type_desc"] not in crash_types:
            crash_types.append("collision_type_desc")
    crash_types.sort()
    return tuple(crash_types)


def get_crash_directions(crashes: list) -> tuple:
    """
    Returns a tuple of distinct crash_directions.
    """
    crash_dirs = []
    for crash in crashes:
        if crash["logmile_dir_flag"] not in crash_dirs:
            crash_dirs.append("logmile_dir_flag")
    crash_dirs.sort()
    return tuple(crash_dirs)


def count_fatal_crashes(crashes: list, year: int = None, crash_dir: str = None) -> int:
    """
    Return the number of fatal crashes.
    Keyword Arguments:
    crashes (REQUIRED) - a list of dicts representing crash reports.
    year (OPTIONAL) - only count crashes that occured in this year.
    crash_dir (OPTIONAL) - only count crashes that occur in this direction.
    """
    fatal_count_all = 0
    fatal_count_year = 0
    fatal_count_year_with_dir = 0
    for crash in crashes:
        if "fatal" in crash["report_type"].lower():
            fatal_count_all += 1
            if int(crash["year"]) == year:
                fatal_count_year += 1
            if int(crash["year"]) == year and crash["logmile_dir_flag"] == crash_dir:
                fatal_count_year_with_dir += 1
    if year is not None and crash_dir is not None:
        return fatal_count_year_with_dir
    elif year is not None:
        return fatal_count_year
    return fatal_count_all


def count_injuries(crashes: list, year: int = None, crash_dir: str = None) -> int:
    """
    Return the number of injury crashes.
    Keyword Arguments:
    crashes (REQUIRED) - a list of dicts representing crash reports.
    year (OPTIONAL) - only count crashes that occured in this year.
    crash_dir (OPTIONAL) - only count crashes that occur in this direction.
    """
    injury_count_all = 0
    injury_count_year = 0
    injury_count_year_with_dir = 0
    for crash in crashes:
        if "injury" in crash["report_type"].lower():
            injury_count_all += 1
            if int(crash["year"]) == year:
                injury_count_year += 1
            if int(crash["year"]) == year and crash["logmile_dir_flag"] == crash_dir:
                injury_count_year_with_dir += 1
    if year is not None and crash_dir is not None:
        return injury_count_year_with_dir
    elif year is not None:
        return injury_count_year
    return injury_count_all


def count_property_damage(
    crashes: list, year: int = None, crash_dir: str = None
) -> int:
    """
    Return the number of property damage crashes.
    Keyword Arguments:
    crashes (REQUIRED) - a list of dicts representing crash reports.
    year (OPTIONAL) - only count crashes that occured in this year.
    crash_dir (OPTIONAL) - only count crashes that occur in this direction.
    """
    prop_damage_count_all = 0
    prop_damage_count_year = 0
    prop_damage_count_year_with_dir = 0
    for crash in crashes:
        if "property damage" in crash["report_type"].lower():
            prop_damage_count_all += 1
            if year is not None and int(crash["year"]) == year:
                prop_damage_count_year += 1
            if int(crash["year"]) == year and crash["logmile_dir_flag"] == crash_dir:
                prop_damage_count_year_with_dir += 1
    if year is not None and crash_dir is not None:
        return prop_damage_count_year_with_dir
    elif year is not None:
        return prop_damage_count_year
    return prop_damage_count_all


def count_collision_type(
    crashes: list, crash_type: str, year: int = None, crash_dir: str = None
) -> int:
    """
    Return the number of crashes of a given type.
    Keyword Arguments:
    crashes (REQUIRED) - a list of dicts representing crash reports.
    collision_type(REQUIRED) - a string representing a type of collision. Valid values are:
        Not Applicable
        Head On
        Head On Left Turn
        Same Direction Rear End
        Same Direction Rear End Right Turn
        Same Direction Rear End Left Turn
        Opposite Direction Sideswipe
        Same Direction Sideswipe
        Same Direction Right Turn
        Same Direction Left Turn
        Same Direction Both Left Turn
        Same Movement Angle
        Angle Meets Right Turn
        Angle Meets Left Turn
        Angle Meets Left Turn Head On
        Opposite Direction Both Left Turn
        Single Vehicle
        Other
        Unknown
    year (OPTIONAL) - only count crashes that occured in this year.
    crash_dir (OPTIONAL) - only count crashes that occur in this direction.
    """
    collision_type_count = 0
    collision_type_count_year = 0
    collision_type_count_year_with_dir = 0
    for crash in crashes:
        if crash_type.lower() in crash["collision_type_desc"].lower():
            collision_type_count += 1
            if year is not None and int(crash["year"]) == year:
                collision_type_count_year += 1
            if int(crash["year"]) == year and crash["logmile_dir_flag"] == crash_dir:
                collision_type_count_year_with_dir += 1
    if year is not None and crash_dir is not None:
        return collision_type_count_year_with_dir
    elif year is not None:
        return collision_type_count_year
    return collision_type_count
