# This module interacts with the Socrata Open Data API (SODA) to fetch crash data provided by the MD Open Data Portal.

import requests

DATASET_URL = "https://opendata.maryland.gov/resource/65du-s3qu.json"


def fetch_crash_reports(
    route_prefix: str,
    route_number: int,
    start_milepost: float,
    end_milepost: float,
    start_year: int,
    end_year: int,
) -> dict:
    "Executes a GET request against the crash data API to return desired crash information."
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
    query_url = f"{DATASET_URL}?$select={','.join(columns)}&$where=year between {start_year} and {end_year} and log_mile between {start_milepost} and {end_milepost}&route_type_code={route_prefix}&rte_no={route_number}"
    r = requests.get(query_url)
    if r.status_code == 200:
        crashes = r.json()
        return crashes
    else:
        r.raise_for_status()


def get_crash_types(crashes: list) -> tuple:
    """
    Return a list of distinct crash types.
    """
    pass


def get_crash_directions(crashes: list) -> tuple:
    """
    Returns a typle of distinct crash_directions.
    """
    pass
