import pandas as pd
import os
from gooey import Gooey, GooeyParser
import soda
from studies import Study_Area


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
        "route_prefix",
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
        "route_number",
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
        "start_milepost",
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
        "end_milepost",
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
        "start_year",
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
        "end_year",
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
        "crash_data",
        type=str,
        default="https://opendata.maryland.gov/resource/65du-s3qu.json",
        help="The URL where crash reports can be fetched.",
    )

    args = parser.parse_args()

    # define study area
    study = Study_Area(
        args.route_prefix,
        args.route_number,
        args.start_milepost,
        args.end_milepost,
        args.start_year,
        args.end_year,
        args.input_cmf,
    )

    # define crash reports
    crashes = soda.fetch_crash_reports(
        args.crash_data,
        args.route_prefix,
        args.route_number,
        args.start_milepost,
        args.end_milepost,
        args.start_year,
        args.end_year,
    )

    # loop through crashes and calculate total CMFs for each crash
    # calculations should be for both travel directions and the total
    # add the calculated value as a new crash attributes
    for crash in crashes:
        crash_cmfs = study.get_crash_cmfs(
            crash_milepost=crash["log_mile"],
            severity=crash["report_type"],
            crash_type=crash["collision_type_desc"],
            crash_dir=crash["logmile_dir_flag"],
            crash_time=crash["acc_time"],
        )
        crash["calculated_cmf"] = study.reduce_cmfs(crash_cmfs)

    # generate the crash summary report
    crash_types = soda.get_crash_types(crashes)
    crash_directions = soda.get_crash_directions(crashes)

    d0_summary = []
    d1_summary = []
    total_summary = []

    for year in range(args.start_year, args.end_year + 1):
        row = {}
        row_d0 = {}
        row_d1 = {}

        row["year"] = year
        row_d0["year"] = year
        if len(crash_directions) > 1:
            row_d1["year"] = year

        row["logmile_dir"] = "ALL"
        row_d0["logmile_dir"] = crash_directions[0]
        if len(crash_directions) > 1:
            row_d1["logmile_dir"] = crash_directions[1]

        # count fatal in year
        row["fatal"] = soda.count_fatal_crashes(crashes, year)
        # count fatal in year for each direction
        row_d0["fatal"] = soda.count_fatal_crashes(crashes, year, crash_directions[0])
        if len(crash_directions) > 1:
            row_d1["fatal"] = soda.count_fatal_crashes(
                crashes, year, crash_directions[1]
            )

        # count injury in year
        row["injury"] = soda.count_injuries(crashes, year)
        # count injury in year for each direction
        row_d0["injury"] = soda.count_injuries(crashes, year, crash_directions[0])
        if len(crash_directions) > 1:
            row_d1["injury"] = soda.count_injuries(crashes, year, crash_directions[1])

        # count property damage in year
        row["property damage"] = soda.count_property_damage(crashes, year)
        # count property damage in year for each direction
        row_d0["property damage"] = soda.count_property_damage(
            crashes, year, crash_directions[0]
        )
        if len(crash_directions) > 1:
            row_d1["property damage"] = soda.count_property_damage(
                crashes, year, crash_directions[1]
            )

        for crash_type in crash_types:
            # count specific crash types in year
            row[crash_type] = soda.count_collision_type(crashes, crash_type, year)
            # count specific crash types in each direction
            row_d0[crash_type] = soda.count_collision_type(
                crashes, crash_type, year, crash_directions[0]
            )
            if len(crash_directions) > 1:
                row_d1[crash_type] = soda.count_collision_type(
                    crashes, crash_type, year, crash_directions[1]
                )

        d0_summary.append(row_d0)
        if row_d1:
            d1_summary.append(row_d1)
        total_summary.append(row)

    d0_summ_df = pd.DataFrame(d0_summary)
    d1_summ_df = pd.DataFrame(d1_summary)
    total_summ_df = pd.DataFrame(total_summary)

    # convert soda list object to pandas dataframe
    # do this step last so that we can simply write the dataframe to output Excel file.
    raw_crashes_df = pd.DataFrame(crashes)

    # write output reports to Excel
    # the output report will be saved to the same location as the input Excel file containing CMF values defined for this study
    out_dir = os.path.split(args.input_cmf)[0]
    out_file = f"{args.route_prefix}-{args.route_number} [{args.start_milepost}-{args.end_milepost}] ({args.start_year}-{args.end_year}) CMF Analysis.xlsx"
    xlsx_writer = pd.ExcelWriter(os.path.join(out_dir, out_file), engine="openpyxl")

    # write raw crash data
    crashes_df = pd.DataFrame(crashes)
    crashes_df.to_excel(xlsx_writer, sheet_name="Crash Data", index=False)

    # write crash summary report
    d0_summ_df.loc["Total", :] = d0_summ_df.loc[:, "fatal":].sum(axis=0)
    d0_summ_df.to_excel(
        xlsx_writer, sheet_name="Crash Summary", startrow=0, startcol=0, index=True
    )

    if not d1_summ_df.empty:
        d1_summ_df.loc["Total", :] = d1_summ_df.loc[:, "fatal":].sum(axis=0)
        d1_summ_df.to_excel(
            xlsx_writer,
            sheet_name="Crash Summary",
            startrow=len(d0_summary) + 3,
            startcol=0,
            index=True,
        )
        total_summ_df.loc["Total", :] = total_summ_df.loc[:, "fatal":].sum(axis=0)
        total_summ_df.to_excel(
            xlsx_writer,
            sheet_name="Crash Summary",
            startrow=(len(d0_summary) + 3) * 2,
            startcol=0,
            index=True,
        )

    # TODO generate analysis summary for direction 1

    # TODO generate analysis summary for direction 2

    # TODO generate analysis summary for both directions

    # save output excel file
    xlsx_writer.save()


if __name__ == "__main__":
    main()
