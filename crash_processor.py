# This module interacts with the Socrata Open Data API (SODA) to fetch crash data provided by the MD Open Data Portal.

import requests
import re
from pandas import DataFrame


def infer_report_type(report_no: str) -> str:
    """
    Look at all person and struck object details related to report_no and determine if there are fatalities, injuries or property damage.
    Returns str one of 'Fatal Crash', 'Injury Crash' or 'Property Damage Crash'.
    """
    # Person Details API
    url = f"https://opendata.maryland.gov/resource/py4c-dicf.json?report_no={report_no}"
    r = requests.get(url)
    if r.status_code == 200:
        people = r.json()
        fatality_count = 0
        injury_count = 0
        for person in people:
            # code 5 is fatal
            if (
                person.get("inj_sever_code") is not None
                and int(person.get("inj_sever_code")) == 5
            ):
                fatality_count += 1
            # 1 < code < 5 is injury
            elif (
                person.get("inj_sever_code") is not None
                and 1 < int(person.get("inj_sever_code")) < 5
            ):
                injury_count += 1
        if fatality_count > 0:
            return "Fatal Crash"
        elif injury_count > 0:
            return "Injury Crash"
        else:
            return "Property Damage Crash"
    else:
        r.raise_for_status()


def infer_crash_dir(report_no: str, logmile_dir_flag: str) -> str:
    """
    Look at vehicle details related to report_no to determine the direction of the crash.
    Returns str representing a single cardinal direction code, one of 'N', 'S', 'E', 'W' or 'U' for unknown.
    """
    # Vehicle Details API
    url = f"https://opendata.maryland.gov/resource/mhft-5t5y.json?report_no={report_no}"
    r = requests.get(url)
    if r.status_code == 200:
        vehicles = r.json()
        dirs = [vehicle["going_direction_code"] for vehicle in vehicles]
        if len(dirs) == 0:
            return "NoData"
        else:
            last_max = 0
            most_frequent_dir = None
            # handle north-south crashes
            if logmile_dir_flag in ["N", "S"]:
                for d in ["N", "S"]:
                    current_count = dirs.count(d)
                    if current_count > last_max:
                        last_max = current_count
                        most_frequent_dir = d

            # handle east-west crashes
            elif logmile_dir_flag in ["E", "W"]:
                for d in ["E", "W"]:
                    current_count = dirs.count(d)
                    if current_count > last_max:
                        last_max = current_count
                        most_frequent_dir = d

            if most_frequent_dir is not None:
                return most_frequent_dir
            return "U"
    else:
        r.raise_for_status()


def format_time_str(time_str: str) -> str:
    # reformat crash time into hh:mm:ss format
    return f"{time_str[:2]}:{time_str[2:4]}:{time_str[4:]}"


def format_date_str(date_str: str) -> str:
    # ** date formats on SODA api is not standardized and has multiple variations **
    # convert yyyymmdd format into yyyy-mm-dd
    if re.match("\d{8}", date_str) is not None:
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    # convert mm-dd-yyyy format into yyyy-mm-dd
    elif re.match("\d{2}-\d{2}-\d{4}", date_str) is not None:
        return f"{date_str[-4:]}-{date_str[0:2]}-{date_str[3:5]}"


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
        "collision_type_code",
        "collision_type_desc",
        "fix_obj_code",
        "fix_obj_desc",
        "harm_event_code1",
        "harm_event_desc1",
        "harm_event_code2",
        "harm_event_desc2",
    ]
    query_url = f"{url}?$select={','.join(columns)}&$where=year between {start_year} and {end_year} and log_mile between {start_milepost} and {end_milepost}&route_type_code={route_prefix}&rte_no={route_number}"
    r = requests.get(query_url)
    if r.status_code == 200:
        crashes = r.json()
        for crash in crashes:
            # handle missing data
            for col in columns:
                if crash.get(col) is None:
                    if col == "report_type":
                        crash[col] = infer_report_type(crash.get("report_no"))
                    else:
                        crash[col] = "NoData"
                # convert codes stored as text into int
                if col in [
                    "rte_no",
                    "year",
                    "collision_type_code",
                    "fix_obj_code",
                    "harm_event_code1",
                    "harm_event_code2",
                ]:
                    crash[col] = int(crash.get(col))
                if col == "log_mile":
                    crash[col] = float(crash.get(col))

            # standarize crash time into hh:mm:ss format
            if ":" not in crash["acc_time"]:
                crash["acc_time"] = format_time_str(crash["acc_time"])

            # standardize crash date field into yyyy-mm-dd format
            crash["acc_date"] = format_date_str(crash["acc_date"])

            # infer crash direction based on the direction of travel of all vehicles involved
            crash["crash_dir"] = infer_crash_dir(
                crash.get("report_no"), crash.get("logmile_dir_flag")
            )
        return crashes
    else:
        r.raise_for_status()


def get_crash_types(crashes_df: DataFrame) -> tuple:
    """
    Return a tuple of distinct crash types.
    """
    unique_crash_types = crashes_df.loc[:, "collision_type_desc"].unique()
    unique_crash_types.sort()
    return tuple(unique_crash_types)


def get_crash_directions(crashes_df: DataFrame) -> tuple:
    """
    Returns a tuple of distinct crash_directions. Excludes any missing data or unknowns.
    """
    unique_crash_dirs = crashes_df.loc[:, "crash_dir"].unique()
    unique_crash_dirs.sort()
    # eliminate any rows with value of 'NoData' or 'U' for unknown
    dirs_no_missing_data = [x for x in unique_crash_dirs if x not in ["NoData", "U"]]
    return tuple(dirs_no_missing_data)


def count_fatal_crashes(
    crashes_df: DataFrame, year: int = None, crash_dir: str = None
) -> int:
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
    for crash in crashes_df.itertuples():
        if "fatal" in crash.report_type.lower():
            fatal_count_all += 1
            if crash.year == year:
                fatal_count_year += 1
            if crash.year == year and crash.crash_dir == crash_dir:
                fatal_count_year_with_dir += 1
    if year is not None and crash_dir is not None:
        return fatal_count_year_with_dir
    elif year is not None:
        return fatal_count_year
    return fatal_count_all


def count_injuries(
    crashes_df: DataFrame, year: int = None, crash_dir: str = None
) -> int:
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
    for crash in crashes_df.itertuples():
        if "injury" in crash.report_type.lower():
            injury_count_all += 1
            if crash.year == year:
                injury_count_year += 1
            if crash.year == year and crash.crash_dir == crash_dir:
                injury_count_year_with_dir += 1
    if year is not None and crash_dir is not None:
        return injury_count_year_with_dir
    elif year is not None:
        return injury_count_year
    return injury_count_all


def count_property_damage(
    crashes_df: DataFrame, year: int = None, crash_dir: str = None
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
    for crash in crashes_df.itertuples():
        if "property damage" in crash.report_type.lower():
            prop_damage_count_all += 1
            if crash.year == year:
                prop_damage_count_year += 1
            if crash.year == year and crash.crash_dir == crash_dir:
                prop_damage_count_year_with_dir += 1
    if year is not None and crash_dir is not None:
        return prop_damage_count_year_with_dir
    elif year is not None:
        return prop_damage_count_year
    return prop_damage_count_all


def count_collision_type(
    crashes_df: DataFrame, collision_type: str, year: int = None, crash_dir: str = None
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
    for crash in crashes_df.itertuples():
        if collision_type.lower() in crash.collision_type_desc.lower():
            collision_type_count += 1
            if crash.year == year:
                collision_type_count_year += 1
            if crash.year == year and crash.crash_dir == crash_dir:
                collision_type_count_year_with_dir += 1
    if year is not None and crash_dir is not None:
        return collision_type_count_year_with_dir
    elif year is not None:
        return collision_type_count_year
    return collision_type_count


def count_rear_end(
    crashes_df: DataFrame, year: int = None, crash_dir: str = None
) -> int:
    """
    Returns the number of rear end crashes.
    """
    rend_count_all = 0
    rend_count_year = 0
    rend_count_year_with_dir = 0
    for crash in crashes_df.itertuples():
        if crash.collision_type_code in [3, 4, 5]:
            rend_count_all += 1
            if crash.year == year:
                rend_count_year += 1
            if crash.year == year and crash.crash_dir == crash_dir:
                rend_count_year_with_dir += 1
    if year is not None and crash_dir is not None:
        return rend_count_year_with_dir
    elif year is not None:
        return rend_count_year
    return rend_count_all


def count_sideswipe(
    crashes_df: DataFrame, year: int = None, crash_dir: str = None
) -> int:
    """
    Returns the number of sideswipe crashes.
    """
    sdswp_count_all = 0
    sdswp_count_year = 0
    sdswp_count_year_with_dir = 0
    for crash in crashes_df.itertuples():
        if crash.collision_type_code in [6, 7]:
            sdswp_count_all += 1
            if crash.year == year:
                sdswp_count_year += 1
            if crash.year == year and crash.crash_dir == crash_dir:
                sdswp_count_year_with_dir += 1
    if year is not None and crash_dir is not None:
        return sdswp_count_year_with_dir
    elif year is not None:
        return sdswp_count_year
    return sdswp_count_all


def count_left_turn(
    crashes_df: DataFrame, year: int = None, crash_dir: str = None
) -> int:
    """
    Returns the number of left-turn crashes.
    """
    lftn_count_all = 0
    lftn_count_year = 0
    lftn_count_year_with_dir = 0
    for crash in crashes_df.itertuples():
        if crash.collision_type_code in [2, 5, 9, 10, 13, 14]:
            lftn_count_all += 1
            if crash.year == year:
                lftn_count_year += 1
            if crash.year == year and crash.crash_dir == crash_dir:
                lftn_count_year_with_dir += 1
    if year is not None and crash_dir is not None:
        return lftn_count_year_with_dir
    elif year is not None:
        return lftn_count_year
    return lftn_count_all


def count_fixed_object(
    crashes_df: DataFrame, year: int = None, crash_dir: str = None
) -> int:
    """
    Returns the number of fixed object crashes
    """
    fxobj_count_all = 0
    fxobj_count_year = 0
    fxobj_count_year_with_dir = 0
    for crash in crashes_df.itertuples():
        if crash.fix_obj_code > 0:
            fxobj_count_all += 1
            if crash.year == year:
                fxobj_count_year += 1
            if crash.year == year and crash.crash_dir == crash_dir:
                fxobj_count_year_with_dir += 1
    if year is not None and crash_dir is not None:
        return fxobj_count_year_with_dir
    elif year is not None:
        return fxobj_count_year
    return fxobj_count_all


def count_angle(crashes_df: DataFrame, year: int = None, crash_dir: str = None) -> int:
    """
    Returns the number of angle crashes.
    """
    angle_count_all = 0
    angle_count_year = 0
    angle_count_year_with_dir = 0
    for crash in crashes_df.itertuples():
        if crash.collision_type_code in [12, 13, 14]:
            angle_count_all += 1
            if crash.year == year:
                angle_count_year += 1
            if crash.year == year and crash.crash_dir == crash_dir:
                angle_count_year_with_dir += 1
    if year is not None and crash_dir is not None:
        return angle_count_year_with_dir
    elif year is not None:
        return angle_count_year
    return angle_count_all


def count_opp_dir(
    crashes_df: DataFrame, year: int = None, crash_dir: str = None
) -> int:
    """
    Returns the number of opposite direction crashes.
    """
    opdir_count_all = 0
    opdir_count_year = 0
    opdir_count_year_with_dir = 0
    for crash in crashes_df.itertuples():
        if crash.collision_type_code in [6, 15]:
            opdir_count_all += 1
            if crash.year == year:
                opdir_count_year += 1
            if crash.year == year and crash.crash_dir == crash_dir:
                opdir_count_year_with_dir += 1
    if year is not None and crash_dir is not None:
        return opdir_count_year_with_dir
    elif year is not None:
        return opdir_count_year
    return opdir_count_all


def count_parked(crashes_df: DataFrame, year: int = None, crash_dir: str = None) -> int:
    """
    Returns the number of parked vehicle crashes.
    """
    parked_count_all = 0
    parked_count_year = 0
    parked_count_year_with_dir = 0
    for crash in crashes_df.itertuples():
        if crash.harm_event_code1 == 2 or crash.harm_event_code2 == 2:
            parked_count_all += 1
            if crash.year == year:
                parked_count_year += 1
            if crash.year == year and crash.crash_dir == crash_dir:
                parked_count_year_with_dir += 1
    if year is not None and crash_dir is not None:
        return parked_count_year_with_dir
    elif year is not None:
        return parked_count_year
    return parked_count_all


def count_pedestrian(
    crashes_df: DataFrame, year: int = None, crash_dir: str = None
) -> int:
    """
    Returns the number of pedestrian crashes.
    """
    ped_count_all = 0
    ped_count_year = 0
    ped_count_year_with_dir = 0
    for crash in crashes_df.itertuples():
        if crash.harm_event_code1 == 3 or crash.harm_event_code2 == 3:
            ped_count_all += 1
            if crash.year == year:
                ped_count_year += 1
            if crash.year == year and crash.crash_dir == crash_dir:
                ped_count_year_with_dir += 1
    if year is not None and crash_dir is not None:
        return ped_count_year_with_dir
    elif year is not None:
        return ped_count_year
    return ped_count_all


def count_other(crashes_df: DataFrame, year: int = None, crash_dir: str = None) -> int:
    """
    Returns the number of 'other' crashes.
    """
    # TODO need to figure how other is defined.
    # Does it refer to 'other' collision types or harm event?
    # Does it actually refer to the 'other' category or does it refer to all collision types that are not one of
    # rear end, sideswipe, lef turn, fixed object , angle, opposite dir
    # or harm events that are not pedestrian/parked vehicle.
    return


def calculate_fatal_reduction(crashes_df: DataFrame, direction: str = None) -> dict:
    """
    Calculates total CMF and CRF values for fatal crashes in crashes_df.
    Returns a dict.
    Keyword Arguments:
        crashes_df (REQUIRED) - Pandas dataframe of crash data. MUST contain a 'calculated_cmf' column.
        direction (OPTIONAL) - Limit calculation to only crashes in this direction.
    """
    res = {}

    if direction is None:
        crash_data = crashes_df[crashes_df.report_type == "Fatal Crash"]
    else:
        crash_data = crashes_df[crashes_df.report_type == "Fatal Crash"][
            crashes_df.crash_dir == direction
        ]

    if not crash_data.empty:
        res["NUMBER OF ACCIDENTS"] = crash_data.shape[0]

        cmf_total = crash_data.loc[:, "calculated_cmf"].sum() / float(
            crash_data.shape[0]
        )
        res["CRASH MODIFICATION FACTOR (CMF)"] = cmf_total

        crf_total = (1 - cmf_total) * 100
        res["CRASH REDUCTION FACTOR (CRF)"] = crf_total

        res["EXPECTED CHANGE IN ACCIDENTS (%)"] = cmf_total - 1

        res["ANNUAL NET CRASH REDUCTION"] = (
            (1 - cmf_total)
            * crash_data.shape[0]
            / (
                1
                + int(crash_data.loc[:, "year"].max())
                - int(crash_data.loc[:, "year"].min())
            )
        )
    else:
        for i in [
            "NUMBER OF ACCIDENTS",
            "CRASH MODIFICATION FACTOR (CMF)",
            "CRASH REDUCTION FACTOR (CRF)",
            "EXPECTED CHANGE IN ACCIDENTS (%)",
            "ANNUAL NET CRASH REDUCTION",
        ]:
            res[i] = 0
    return res


def calculate_injury_reduction(crashes_df: DataFrame, direction: str = None) -> dict:
    """
    Calculates total CMF and CRF values for injury crashes in crashes_df.
    Returns a dict.
    Keyword Arguments:
        crashes_df (REQUIRED) - Pandas dataframe of crash data. MUST contain a 'calculated_cmf' column.
        direction (OPTIONAL) - Limit calculation to only crashes in this direction.
    """
    res = {}

    if direction is None:
        crash_data = crashes_df[crashes_df.report_type == "Injury Crash"]
    else:
        crash_data = crashes_df[crashes_df.report_type == "Injury Crash"][
            crashes_df.crash_dir == direction
        ]
    if not crash_data.empty:
        res["NUMBER OF ACCIDENTS"] = crash_data.shape[0]

        cmf_total = crash_data.loc[:, "calculated_cmf"].sum() / crash_data.shape[0]
        res["CRASH MODIFICATION FACTOR (CMF)"] = cmf_total

        crf_total = (1 - cmf_total) * 100
        res["CRASH REDUCTION FACTOR (CRF)"] = crf_total

        res["EXPECTED CHANGE IN ACCIDENTS (%)"] = cmf_total - 1

        res["ANNUAL NET CRASH REDUCTION"] = (
            (1 - cmf_total)
            * crash_data.shape[0]
            / (
                1
                + int(crash_data.loc[:, "year"].max())
                - int(crash_data.loc[:, "year"].min())
            )
        )
    else:
        for i in [
            "NUMBER OF ACCIDENTS",
            "CRASH MODIFICATION FACTOR (CMF)",
            "CRASH REDUCTION FACTOR (CRF)",
            "EXPECTED CHANGE IN ACCIDENTS (%)",
            "ANNUAL NET CRASH REDUCTION",
        ]:
            res[i] = 0
    return res


def calculate_prop_damage_reduction(
    crashes_df: DataFrame, direction: str = None
) -> dict:
    """
    Calculates total CMF and CRF values for property damage crashes in crashes_df.
    Returns a dict.
    Keyword Arguments:
        crashes_df (REQUIRED) - Pandas dataframe of crash data. MUST contain a 'calculated_cmf' column.
        direction (OPTIONAL) - Limit calculation to only crashes in this direction.
    """
    res = {}

    if direction is None:
        crash_data = crashes_df[crashes_df.report_type == "Property Damage Crash"]
    else:
        crash_data = crashes_df[crashes_df.report_type == "Property Damage Crash"][
            crashes_df.crash_dir == direction
        ]

    if not crash_data.empty:
        res["NUMBER OF ACCIDENTS"] = crash_data.shape[0]

        cmf_total = crash_data.loc[:, "calculated_cmf"].sum() / crash_data.shape[0]
        res["CRASH MODIFICATION FACTOR (CMF)"] = cmf_total

        crf_total = (1 - cmf_total) * 100
        res["CRASH REDUCTION FACTOR (CRF)"] = crf_total

        res["EXPECTED CHANGE IN ACCIDENTS (%)"] = cmf_total - 1

        res["ANNUAL NET CRASH REDUCTION"] = (
            (1 - cmf_total)
            * crash_data.shape[0]
            / (
                1
                + int(crash_data.loc[:, "year"].max())
                - int(crash_data.loc[:, "year"].min())
            )
        )
    else:
        for i in [
            "NUMBER OF ACCIDENTS",
            "CRASH MODIFICATION FACTOR (CMF)",
            "CRASH REDUCTION FACTOR (CRF)",
            "EXPECTED CHANGE IN ACCIDENTS (%)",
            "ANNUAL NET CRASH REDUCTION",
        ]:
            res[i] = 0
    return res


def calculate_collision_type_reduction(
    crashes_df: DataFrame, collision_type: str, direction: str = None
) -> dict:
    """
    Calculates total CMF and CRF values for collision_type crashes in crashes_df.
    Returns a dict.
    Keyword Arguments:
        crashes_df (REQUIRED) - Pandas dataframe of crash data. MUST contain a 'calculated_cmf' column.
        collision_type (REQUIRED) - The collision type property of the crash. Must be one of:
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
        direction (OPTIONAL) - Limit calculation to only crashes in this direction.
    """
    res = {}

    if direction is None:
        crash_data = crashes_df[crashes_df.collision_type_desc == collision_type]
    else:
        crash_data = crashes_df[crashes_df.collision_type_desc == collision_type][
            crashes_df.crash_dir == direction
        ]

    if not crash_data.empty:
        res["NUMBER OF ACCIDENTS"] = crash_data.shape[0]

        cmf_total = crash_data.loc[:, "calculated_cmf"].sum() / crash_data.shape[0]
        res["CRASH MODIFICATION FACTOR (CMF)"] = cmf_total

        crf_total = (1 - cmf_total) * 100
        res["CRASH REDUCTION FACTOR (CRF)"] = crf_total

        res["EXPECTED CHANGE IN ACCIDENTS (%)"] = cmf_total - 1

        res["ANNUAL NET CRASH REDUCTION"] = (
            (1 - cmf_total)
            * crash_data.shape[0]
            / (
                1
                + int(crash_data.loc[:, "year"].max())
                - int(crash_data.loc[:, "year"].min())
            )
        )
    else:
        for i in [
            "NUMBER OF ACCIDENTS",
            "CRASH MODIFICATION FACTOR (CMF)",
            "CRASH REDUCTION FACTOR (CRF)",
            "EXPECTED CHANGE IN ACCIDENTS (%)",
            "ANNUAL NET CRASH REDUCTION",
        ]:
            res[i] = 0

    return res


def calculate_rear_end_reduction(crashes_df: DataFrame, direction: str = None) -> dict:
    """
    Calculates total CMF and CRF values for rear end crashes in crashes_df.
    Returns a dict.
    Keyword Arguments:
        crashes_df (REQUIRED) - Pandas dataframe of crash data. MUST contain a 'calculated_cmf' column.
        direction (OPTIONAL) - Limit calculation to only crashes in this direction.
    """
    res = {}

    if direction is None:
        crash_data = crashes_df[crashes_df.collision_type_code.isin([3, 4, 5])]
    else:
        crash_data = crashes_df[crashes_df.collision_type_code.isin([3, 4, 5])][
            crashes_df.crash_dir == direction
        ]

    if not crash_data.empty:
        res["NUMBER OF ACCIDENTS"] = crash_data.shape[0]

        cmf_total = crash_data.loc[:, "calculated_cmf"].sum() / crash_data.shape[0]
        res["CRASH MODIFICATION FACTOR (CMF)"] = cmf_total

        crf_total = (1 - cmf_total) * 100
        res["CRASH REDUCTION FACTOR (CRF)"] = crf_total

        res["EXPECTED CHANGE IN ACCIDENTS (%)"] = cmf_total - 1

        res["ANNUAL NET CRASH REDUCTION"] = (
            (1 - cmf_total)
            * crash_data.shape[0]
            / (
                1
                + int(crash_data.loc[:, "year"].max())
                - int(crash_data.loc[:, "year"].min())
            )
        )
    else:
        for i in [
            "NUMBER OF ACCIDENTS",
            "CRASH MODIFICATION FACTOR (CMF)",
            "CRASH REDUCTION FACTOR (CRF)",
            "EXPECTED CHANGE IN ACCIDENTS (%)",
            "ANNUAL NET CRASH REDUCTION",
        ]:
            res[i] = 0
    return res


def calculate_sideswipe_reduction(crashes_df: DataFrame, direction: str = None) -> dict:
    """
    Calculates total CMF and CRF values for sideswipe crashes in crashes_df.
    Returns a dict.
    Keyword Arguments:
        crashes_df (REQUIRED) - Pandas dataframe of crash data. MUST contain a 'calculated_cmf' column.
        direction (OPTIONAL) - Limit calculation to only crashes in this direction.
    """
    res = {}

    if direction is None:
        crash_data = crashes_df[crashes_df.collision_type_code.isin([6, 7])]
    else:
        crash_data = crashes_df[crashes_df.collision_type_code.isin([6, 7])][
            crashes_df.crash_dir == direction
        ]

    if not crash_data.empty:
        res["NUMBER OF ACCIDENTS"] = crash_data.shape[0]

        cmf_total = crash_data.loc[:, "calculated_cmf"].sum() / crash_data.shape[0]
        res["CRASH MODIFICATION FACTOR (CMF)"] = cmf_total

        crf_total = (1 - cmf_total) * 100
        res["CRASH REDUCTION FACTOR (CRF)"] = crf_total

        res["EXPECTED CHANGE IN ACCIDENTS (%)"] = cmf_total - 1

        res["ANNUAL NET CRASH REDUCTION"] = (
            (1 - cmf_total)
            * crash_data.shape[0]
            / (
                1
                + int(crash_data.loc[:, "year"].max())
                - int(crash_data.loc[:, "year"].min())
            )
        )
    else:
        for i in [
            "NUMBER OF ACCIDENTS",
            "CRASH MODIFICATION FACTOR (CMF)",
            "CRASH REDUCTION FACTOR (CRF)",
            "EXPECTED CHANGE IN ACCIDENTS (%)",
            "ANNUAL NET CRASH REDUCTION",
        ]:
            res[i] = 0
    return res


def calculate_left_turn_reduction(crashes_df: DataFrame, direction: str = None) -> dict:
    """
    Calculates total CMF and CRF values for left turn crashes in crashes_df.
    Returns a dict.
    Keyword Arguments:
        crashes_df (REQUIRED) - Pandas dataframe of crash data. MUST contain a 'calculated_cmf' column.
        direction (OPTIONAL) - Limit calculation to only crashes in this direction.
    """
    res = {}

    if direction is None:
        crash_data = crashes_df[
            crashes_df.collision_type_code.isin([2, 5, 9, 10, 13, 14])
        ]
    else:
        crash_data = crashes_df[
            crashes_df.collision_type_code.isin([2, 5, 9, 10, 13, 14])
        ][crashes_df.crash_dir == direction]

    if not crash_data.empty:
        res["NUMBER OF ACCIDENTS"] = crash_data.shape[0]

        cmf_total = crash_data.loc[:, "calculated_cmf"].sum() / crash_data.shape[0]
        res["CRASH MODIFICATION FACTOR (CMF)"] = cmf_total

        crf_total = (1 - cmf_total) * 100
        res["CRASH REDUCTION FACTOR (CRF)"] = crf_total

        res["EXPECTED CHANGE IN ACCIDENTS (%)"] = cmf_total - 1

        res["ANNUAL NET CRASH REDUCTION"] = (
            (1 - cmf_total)
            * crash_data.shape[0]
            / (
                1
                + int(crash_data.loc[:, "year"].max())
                - int(crash_data.loc[:, "year"].min())
            )
        )
    else:
        for i in [
            "NUMBER OF ACCIDENTS",
            "CRASH MODIFICATION FACTOR (CMF)",
            "CRASH REDUCTION FACTOR (CRF)",
            "EXPECTED CHANGE IN ACCIDENTS (%)",
            "ANNUAL NET CRASH REDUCTION",
        ]:
            res[i] = 0
    return res


def calculate_fixed_object_reduction(
    crashes_df: DataFrame, direction: str = None
) -> dict:
    """
    Calculates total CMF and CRF values for fixed object crashes in crashes_df.
    Returns a dict.
    Keyword Arguments:
        crashes_df (REQUIRED) - Pandas dataframe of crash data. MUST contain a 'calculated_cmf' column.
        direction (OPTIONAL) - Limit calculation to only crashes in this direction.
    """
    res = {}

    if direction is None:
        crash_data = crashes_df[crashes_df.fix_obj_code > 0]
    else:
        crash_data = crashes_df[crashes_df.fix_obj_code > 0][
            crashes_df.crash_dir == direction
        ]

    if not crash_data.empty:
        res["NUMBER OF ACCIDENTS"] = crash_data.shape[0]

        cmf_total = crash_data.loc[:, "calculated_cmf"].sum() / crash_data.shape[0]
        res["CRASH MODIFICATION FACTOR (CMF)"] = cmf_total

        crf_total = (1 - cmf_total) * 100
        res["CRASH REDUCTION FACTOR (CRF)"] = crf_total

        res["EXPECTED CHANGE IN ACCIDENTS (%)"] = cmf_total - 1

        res["ANNUAL NET CRASH REDUCTION"] = (
            (1 - cmf_total)
            * crash_data.shape[0]
            / (
                1
                + int(crash_data.loc[:, "year"].max())
                - int(crash_data.loc[:, "year"].min())
            )
        )
    else:
        for i in [
            "NUMBER OF ACCIDENTS",
            "CRASH MODIFICATION FACTOR (CMF)",
            "CRASH REDUCTION FACTOR (CRF)",
            "EXPECTED CHANGE IN ACCIDENTS (%)",
            "ANNUAL NET CRASH REDUCTION",
        ]:
            res[i] = 0
    return res


def calculate_angle_reduction(crashes_df: DataFrame, direction: str = None) -> dict:
    """
    Calculates total CMF and CRF values for angle crashes in crashes_df.
    Returns a dict.
    Keyword Arguments:
        crashes_df (REQUIRED) - Pandas dataframe of crash data. MUST contain a 'calculated_cmf' column.
        direction (OPTIONAL) - Limit calculation to only crashes in this direction.
    """
    res = {}

    if direction is None:
        crash_data = crashes_df[crashes_df.collision_type_code.isin([12, 13, 14])]
    else:
        crash_data = crashes_df[crashes_df.collision_type_code.isin([12, 13, 14])][
            crashes_df.crash_dir == direction
        ]

    if not crash_data.empty:
        res["NUMBER OF ACCIDENTS"] = crash_data.shape[0]

        cmf_total = crash_data.loc[:, "calculated_cmf"].sum() / crash_data.shape[0]
        res["CRASH MODIFICATION FACTOR (CMF)"] = cmf_total

        crf_total = (1 - cmf_total) * 100
        res["CRASH REDUCTION FACTOR (CRF)"] = crf_total

        res["EXPECTED CHANGE IN ACCIDENTS (%)"] = cmf_total - 1

        res["ANNUAL NET CRASH REDUCTION"] = (
            (1 - cmf_total)
            * crash_data.shape[0]
            / (
                1
                + int(crash_data.loc[:, "year"].max())
                - int(crash_data.loc[:, "year"].min())
            )
        )
    else:
        for i in [
            "NUMBER OF ACCIDENTS",
            "CRASH MODIFICATION FACTOR (CMF)",
            "CRASH REDUCTION FACTOR (CRF)",
            "EXPECTED CHANGE IN ACCIDENTS (%)",
            "ANNUAL NET CRASH REDUCTION",
        ]:
            res[i] = 0
    return res


def calculate_opp_dir_reduction(crashes_df: DataFrame, direction: str = None) -> dict:
    """
    Calculates total CMF and CRF values for opposite direction crashes in crashes_df.
    Returns a dict.
    Keyword Arguments:
        crashes_df (REQUIRED) - Pandas dataframe of crash data. MUST contain a 'calculated_cmf' column.
        direction (OPTIONAL) - Limit calculation to only crashes in this direction.
    """
    res = {}

    if direction is None:
        crash_data = crashes_df[crashes_df.collision_type_code.isin([6, 15])]
    else:
        crash_data = crashes_df[crashes_df.collision_type_code.isin([6, 15])][
            crashes_df.crash_dir == direction
        ]

    if not crash_data.empty:
        res["NUMBER OF ACCIDENTS"] = crash_data.shape[0]

        cmf_total = crash_data.loc[:, "calculated_cmf"].sum() / crash_data.shape[0]
        res["CRASH MODIFICATION FACTOR (CMF)"] = cmf_total

        crf_total = (1 - cmf_total) * 100
        res["CRASH REDUCTION FACTOR (CRF)"] = crf_total

        res["EXPECTED CHANGE IN ACCIDENTS (%)"] = cmf_total - 1

        res["ANNUAL NET CRASH REDUCTION"] = (
            (1 - cmf_total)
            * crash_data.shape[0]
            / (
                1
                + int(crash_data.loc[:, "year"].max())
                - int(crash_data.loc[:, "year"].min())
            )
        )
    else:
        for i in [
            "NUMBER OF ACCIDENTS",
            "CRASH MODIFICATION FACTOR (CMF)",
            "CRASH REDUCTION FACTOR (CRF)",
            "EXPECTED CHANGE IN ACCIDENTS (%)",
            "ANNUAL NET CRASH REDUCTION",
        ]:
            res[i] = 0
    return res


def calculate_parked_reduction(crashes_df: DataFrame, direction: str = None) -> dict:
    """
    Calculates total CMF and CRF values for parked crashes in crashes_df.
    Returns a dict.
    Keyword Arguments:
        crashes_df (REQUIRED) - Pandas dataframe of crash data. MUST contain a 'calculated_cmf' column.
        direction (OPTIONAL) - Limit calculation to only crashes in this direction.
    """
    res = {}

    if direction is None:
        crash_data = crashes_df[
            crashes_df.harm_event_code1.isin([1, 2])
            | crashes_df.harm_event_code2.isin([1, 2])
        ]
    else:
        crash_data = crashes_df[
            crashes_df.harm_event_code1.isin([1, 2])
            | crashes_df.harm_event_code2.isin([1, 2])
        ][crashes_df.crash_dir == direction]

    if not crash_data.empty:
        res["NUMBER OF ACCIDENTS"] = crash_data.shape[0]

        cmf_total = crash_data.loc[:, "calculated_cmf"].sum() / crash_data.shape[0]
        res["CRASH MODIFICATION FACTOR (CMF)"] = cmf_total

        crf_total = (1 - cmf_total) * 100
        res["CRASH REDUCTION FACTOR (CRF)"] = crf_total

        res["EXPECTED CHANGE IN ACCIDENTS (%)"] = cmf_total - 1

        res["ANNUAL NET CRASH REDUCTION"] = (
            (1 - cmf_total)
            * crash_data.shape[0]
            / (
                1
                + int(crash_data.loc[:, "year"].max())
                - int(crash_data.loc[:, "year"].min())
            )
        )
    else:
        for i in [
            "NUMBER OF ACCIDENTS",
            "CRASH MODIFICATION FACTOR (CMF)",
            "CRASH REDUCTION FACTOR (CRF)",
            "EXPECTED CHANGE IN ACCIDENTS (%)",
            "ANNUAL NET CRASH REDUCTION",
        ]:
            res[i] = 0
    return res


def calculate_pedestrian_reduction(
    crashes_df: DataFrame, direction: str = None
) -> dict:
    """
    Calculates total CMF and CRF values for pedestrian crashes in crashes_df.
    Returns a dict.
    Keyword Arguments:
        crashes_df (REQUIRED) - Pandas dataframe of crash data. MUST contain a 'calculated_cmf' column.
        direction (OPTIONAL) - Limit calculation to only crashes in this direction.
    """
    res = {}

    if direction is None:
        crash_data = crashes_df[
            (crashes_df.harm_event_code1 == 3) | (crashes_df.harm_event_code2 == 3)
        ]
    else:
        crash_data = crashes_df[
            (crashes_df.harm_event_code1 == 3) | (crashes_df.harm_event_code2 == 3)
        ][crashes_df.crash_dir == direction]

    if not crash_data.empty:
        res["NUMBER OF ACCIDENTS"] = crash_data.shape[0]

        cmf_total = crash_data.loc[:, "calculated_cmf"].sum() / crash_data.shape[0]
        res["CRASH MODIFICATION FACTOR (CMF)"] = cmf_total

        crf_total = (1 - cmf_total) * 100
        res["CRASH REDUCTION FACTOR (CRF)"] = crf_total

        res["EXPECTED CHANGE IN ACCIDENTS (%)"] = cmf_total - 1

        res["ANNUAL NET CRASH REDUCTION"] = (
            (1 - cmf_total)
            * crash_data.shape[0]
            / (
                1
                + int(crash_data.loc[:, "year"].max())
                - int(crash_data.loc[:, "year"].min())
            )
        )
    else:
        for i in [
            "NUMBER OF ACCIDENTS",
            "CRASH MODIFICATION FACTOR (CMF)",
            "CRASH REDUCTION FACTOR (CRF)",
            "EXPECTED CHANGE IN ACCIDENTS (%)",
            "ANNUAL NET CRASH REDUCTION",
        ]:
            res[i] = 0
    return res


def calculate_other_reduction(crashes_df: DataFrame, direction: str = None) -> dict:
    """
    Calculates total CMF and CRF values for 'Other' crashes in crashes_df.
    Returns a dict.
    Keyword Arguments:
        crashes_df (REQUIRED) - Pandas dataframe of crash data. MUST contain a 'calculated_cmf' column.
        direction (OPTIONAL) - Limit calculation to only crashes in this direction.
    """
    # TODO complete when count_other function has been resolved
    res = {}
    for i in [
        "NUMBER OF ACCIDENTS",
        "CRASH MODIFICATION FACTOR (CMF)",
        "CRASH REDUCTION FACTOR (CRF)",
        "EXPECTED CHANGE IN ACCIDENTS (%)",
        "ANNUAL NET CRASH REDUCTION",
    ]:
        res[i] = 0
    return res
