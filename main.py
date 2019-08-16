import argparse

parser = argparse.ArgumentParser(
    description="Calculate Crash Modification Factor for a given segment of roadway."
)
parser.add_argument(
    "route-prefix",
    type=str,
    choices=[
        "CO",
        "GV",
        "IS",
        "US",
        "MD",
        "MO",
        "MU",
        "OP",
        "RA",
        "RP",
        "RT",
        "SB",
        "SR",
        "UU",
    ],
    help="The type of route e.g. IS (interstate), US (US route), MD (State route) etc.)",
)
parser.add_argument("route-number", type=int, help="The route number.")
parser.add_argument(
    "start-milepost", type=float, help="Starting milepost of analysis area."
)
parser.add_argument(
    "end-milepost", type=float, help="Ending milepost of analysis area."
)
parser.add_argument(
    "start-year", type=int, help="Gather crash data starting in this year."
)
parser_add_argument("end-year", type=int, help="Gather crash data up to this year.")
parser_add_argument(
    "input_cmf",
    type=str,
    help="Full path to an Excel file defining the CMF values and road segments to analyze.",
)

args = parser.parse_args()
