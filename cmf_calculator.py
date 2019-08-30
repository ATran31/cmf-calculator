from gooey import Gooey, GooeyParser


@Gooey(program_name="CMF Calculator", navigation="TABBED")
def main():
    parser = GooeyParser(
        description="Calculate Crash Modification Factor for a given segment of roadway."
    )

    study_settings_grp = parser.add_argument_group(
        "Study Area Settings", gooey_options={"columns": 2}
    )
    data_source_grp = parser.add_argument_group(
        "Data Source Settings", gooey_options={"columns": 1}
    )

    # study related args
    study_settings_grp.add_argument(
        "route-prefix",
        type=str,
        choices=[
            "IS",
            "US",
            "MD",
            "CO",
            "GV",
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
    study_settings_grp.add_argument(
        "route-number",
        type=int,
        help="The route number.",
        gooey_options={
            "validator": {
                "test": "int(user_input)",
                "message": "Valid input must be a number",
            }
        },
    )
    study_settings_grp.add_argument(
        "start-milepost",
        type=float,
        help="Starting milepost of analysis area.",
        gooey_options={
            "validator": {
                "test": "float(user_input)",
                "message": "Valid input must be a number",
            }
        },
    )
    study_settings_grp.add_argument(
        "end-milepost",
        type=float,
        help="Ending milepost of analysis area.",
        gooey_options={
            "validator": {
                "test": "float(user_input)",
                "message": "Valid input must be a number",
            }
        },
    )
    study_settings_grp.add_argument(
        "start-year",
        type=int,
        help="Analyze crash data starting in this year.",
        gooey_options={
            "validator": {
                "test": "float(user_input)",
                "message": "Valid input must be a number",
            }
        },
    )
    study_settings_grp.add_argument(
        "end-year",
        type=int,
        help="Analyze crash data up to this year.",
        gooey_options={
            "validator": {
                "test": "int(user_input)",
                "message": "Valid input must be a number",
            }
        },
    )

    # data source related args
    data_source_grp.add_argument(
        "input_cmf",
        type=str,
        help="Full path to an Excel file defining the CMF values and road segments to analyze.",
        widget="FileChooser",
        gooey_options={
            "validator": {
                "test": "user_input.lower().endswith('.xlsx')",
                "message": "Input must be valid Excel(.xlsx) file",
            }
        },
    )
    data_source_grp.add_argument(
        "crash-data",
        type=str,
        default="https://opendata.maryland.gov/resource/65du-s3qu.json",
        help="The URL where crash reports can be fetched.",
    )

    args = parser.parse_args()


if __name__ == "__main__":
    main()
