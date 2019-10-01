import pandas as pd
import os
from gooey import Gooey, GooeyParser
import crash_processor as cp
from studies import Study_Area
from xlrd import XLRDError


@Gooey(program_name="CMF Calculator", navigation="TABBED", image_dir="./img")
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
    output_settings_grp = parser.add_argument_group(
        "Optional Outputs", gooey_options={"columns": 3}
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

    # optional settings related args
    output_settings_grp.add_argument(
        "-include_input_cmfs",
        action="store_true",
        help="Include input study area CMF definitions in output.",
    )
    output_settings_grp.add_argument(
        "-include_crash_data",
        action="store_true",
        help="Include raw crash data in output.",
    )
    output_settings_grp.add_argument(
        "-include_crash_summary",
        action="store_true",
        help="Include summary count of raw crashes.",
    )

    args = parser.parse_args()

    # define output reports to Excel
    # the output report will be saved to the same location as the input Excel file containing CMF values defined for this study
    out_dir = os.path.split(args.input_cmf)[0]
    out_file = f"{args.route_prefix}-{args.route_number} [{args.start_milepost}-{args.end_milepost}] ({args.start_year}-{args.end_year}) CMF Analysis.xlsx"
    xlsx_writer = pd.ExcelWriter(os.path.join(out_dir, out_file), engine="openpyxl")

    # define study area
    print("Configuring study area...", flush=True)
    study = Study_Area(
        args.route_prefix,
        args.route_number,
        args.start_milepost,
        args.end_milepost,
        args.start_year,
        args.end_year,
        args.input_cmf,
    )

    try:
        # try to run analysis against local crash data by default
        # exception will raise if no sheet named 'Crash Data' in workbook.
        raw_crashes_df = pd.read_excel(args.input_cmf, sheet_name="Crash Data")

        # TODO standardize column names to match column names returned by cp API
        # report_no -> report_no
        # county -> county_desc
        # ro -> route_type_code
        # ute_n -> rte_no
        # N/A -> logmile_dir_flag (this field only used when infering crash direction from API retrieved crashes)
        # log_mile -> log_mile
        # time -> acc_time
        # yr,mo,da -> acc_date
        # yr -> year
        # sever -> report_type
        # ct -> collision_type_code
        # d1 -> crash_dir

    except XLRDError:
        # define crash reports
        print("Fetching crash reports...", flush=True)
        crashes = cp.fetch_crash_reports(
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
        print("Calculating individual crash CMF values...", flush=True)
        for crash in crashes:
            crash_cmfs = study.get_crash_cmfs(
                crash_milepost=crash["log_mile"],
                severity=crash["report_type"],
                crash_type=crash["collision_type_desc"],
                crash_dir=crash["logmile_dir_flag"],
                crash_time=crash["acc_time"],
            )
            crash["calculated_cmf"] = study.reduce_cmfs(crash_cmfs)

        crashes_df = pd.DataFrame(crashes)

    print("Identifying unique crash types...", flush=True)
    crash_types = cp.get_crash_types(crashes_df)

    print("Identifying unique crash directions...", flush=True)
    crash_directions = cp.get_crash_directions(crashes_df)

    # lookup for crash direction code to full name for use in output report tables
    route_dirs = {
        "N": "Northbound",
        "S": "Southbound",
        "E": "Eastbound",
        "W": "Westbound",
        "U": "Unknown",
    }

    # write input cmf definitions
    if args.include_input_cmfs:
        print("Writing study area CMF definitions...", flush=True)
        study.input_cmfs.to_excel(xlsx_writer, sheet_name="Input CMFs", index=False)

    # write raw crash data
    if args.include_crash_data:
        print("Writing raw crash data...", flush=True)
        crashes_df.to_excel(xlsx_writer, sheet_name="Crash Data", index=False)

    # define commmon header used in all output reports
    common_header = [
        "Fatal",
        "Injury",
        "Property Damage",
        "Rear end",
        "Sideswipe",
        "Left Turn",
        "Fixed Object",
        "Angle",
        "Opposite Direction",
        "Parked",
        "Pedestrian",
        "Other",
    ]

    # generate the crash summary report
    if args.include_crash_summary:
        print("Calculating crash summaries...", flush=True)

        summary_dfs = []

        # define dataframes
        total_summ_df = pd.DataFrame(
            index=[year for year in range(args.start_year, args.end_year + 1)],
            columns=[["Total"] * len(common_header), common_header],
        )
        summary_dfs.append(total_summ_df)

        d0_top_header = [route_dirs.get(crash_directions[0])] * len(common_header)
        d0_summ_df = pd.DataFrame(
            index=[year for year in range(args.start_year, args.end_year + 1)],
            columns=[d0_top_header, common_header],
        )
        summary_dfs.append(d0_summ_df)

        if len(crash_directions) > 1:
            d1_top_header = [route_dirs.get(crash_directions[1])] * len(common_header)
            d1_summ_df = pd.DataFrame(
                index=[year for year in range(args.start_year, args.end_year + 1)],
                columns=[d1_top_header, common_header],
            )
            summary_dfs.append(d1_summ_df)

        for year in range(args.start_year, args.end_year + 1):
            # count total fatal
            summary_dfs[0].loc[year, "Total"]["Fatal"] = cp.count_fatal_crashes(
                crashes_df, year
            )
            # count total prop damage
            summary_dfs[0].loc[year, "Total"][
                "Property Damage"
            ] = cp.count_property_damage(crashes_df, year)

            # count total injury
            summary_dfs[0].loc[year, "Total"]["Injury"] = cp.count_injuries(
                crashes_df, year
            )

            # count total rear end
            summary_dfs[0].loc[year, "Total"]["Rear end"] = cp.count_rear_end(
                crashes_df, year
            )

            # count total sideswipe
            summary_dfs[0].loc[year, "Total"]["Sideswipe"] = cp.count_sideswipe(
                crashes_df, year
            )

            # count total left turn
            summary_dfs[0].loc[year, "Total"]["Left Turn"] = cp.count_left_turn(
                crashes_df, year
            )

            # count total fixed object
            summary_dfs[0].loc[year, "Total"]["Fixed Object"] = cp.count_fixed_object(
                crashes_df, year
            )

            # count total angle
            summary_dfs[0].loc[year, "Total"]["Angle"] = cp.count_angle(
                crashes_df, year
            )

            # count total opp dir
            summary_dfs[0].loc[year, "Total"]["Opposite Direction"] = cp.count_opp_dir(
                crashes_df, year
            )

            # count total parked
            summary_dfs[0].loc[year, "Total"]["Parked"] = cp.count_parked(
                crashes_df, year
            )

            # count total pedestrian
            summary_dfs[0].loc[year, "Total"]["Pedestrian"] = cp.count_pedestrian(
                crashes_df, year
            )

            # count total other
            summary_dfs[0].loc[year, "Total"]["Other"] = cp.count_other(
                crashes_df, year
            )

            for d in crash_directions:
                # count fatal in year for crash direction
                summary_dfs[crash_directions.index(d) + 1].loc[year, route_dirs.get(d)][
                    "Fatal"
                ] = cp.count_fatal_crashes(crashes_df, year, d)

                # count injury in year for crash direction
                summary_dfs[crash_directions.index(d) + 1].loc[year, route_dirs.get(d)][
                    "Injury"
                ] = cp.count_injuries(crashes_df, year, d)

                # count property damage in year for crash direction
                summary_dfs[crash_directions.index(d) + 1].loc[year, route_dirs.get(d)][
                    "Property Damage"
                ] = cp.count_property_damage(crashes_df, year, d)

                # count total rear end
                summary_dfs[crash_directions.index(d) + 1].loc[year, route_dirs.get(d)][
                    "Rear end"
                ] = cp.count_rear_end(crashes_df, year, d)

                # count total sideswipe
                summary_dfs[crash_directions.index(d) + 1].loc[year, route_dirs.get(d)][
                    "Sideswipe"
                ] = cp.count_sideswipe(crashes_df, year, d)

                # count total left turn
                summary_dfs[crash_directions.index(d) + 1].loc[year, route_dirs.get(d)][
                    "Left Turn"
                ] = cp.count_left_turn(crashes_df, year, d)

                # count total fixed object
                summary_dfs[crash_directions.index(d) + 1].loc[year, route_dirs.get(d)][
                    "Fixed Object"
                ] = cp.count_fixed_object(crashes_df, year, d)

                # count total angle
                summary_dfs[crash_directions.index(d) + 1].loc[year, route_dirs.get(d)][
                    "Angle"
                ] = cp.count_angle(crashes_df, year, d)

                # count total opp dir
                summary_dfs[crash_directions.index(d) + 1].loc[year, route_dirs.get(d)][
                    "Opposite Direction"
                ] = cp.count_opp_dir(crashes_df, year, d)

                # count total parked
                summary_dfs[crash_directions.index(d) + 1].loc[year, route_dirs.get(d)][
                    "Parked"
                ] = cp.count_parked(crashes_df, year, d)

                # count total pedestrian
                summary_dfs[crash_directions.index(d) + 1].loc[year, route_dirs.get(d)][
                    "Pedestrian"
                ] = cp.count_pedestrian(crashes_df, year, d)

                # count total other
                summary_dfs[crash_directions.index(d) + 1].loc[year, route_dirs.get(d)][
                    "Other"
                ] = cp.count_other(crashes_df, year, d)

        # write crash summary report
        print("Writing crash summaries...", flush=True)
        summary_dfs[0].loc["Total", :] = summary_dfs[0].sum(axis=0)
        summary_dfs[0].to_excel(
            xlsx_writer, sheet_name="Crash Summary", startrow=0, startcol=0
        )
        row_size = len(summary_dfs[0]) + 3
        summary_dfs[1].loc["Total", :] = summary_dfs[1].sum(axis=0)
        summary_dfs[1].to_excel(
            xlsx_writer, sheet_name="Crash Summary", startrow=row_size + 1, startcol=0
        )

        if len(crash_directions) > 1:
            summary_dfs[2].loc["Total", :] = summary_dfs[2].sum(axis=0)
            summary_dfs[2].to_excel(
                xlsx_writer,
                sheet_name="Crash Summary",
                startrow=(row_size * 2) + 2,
                startcol=0,
            )

    print("Analyzing crashes...", flush=True)
    idx = [
        "NUMBER OF ACCIDENTS",
        "CRASH MODIFICATION FACTOR (CMF)",
        "CRASH REDUCTION FACTOR (CRF)",
        "EXPECTED CHANGE IN ACCIDENTS (%)",
        "ANNUAL NET CRASH REDUCTION",
    ]

    # CMF Formula: sum of all CMFs / number of rows
    # CRF Formula: (1 - CMF) * 100
    # Expected Change Formula: CMF - 1
    # Annual Net Reduction Formula: CRF * Number of crashes / Number of years in dataset

    # generate analysis summary for both directions
    total_header = [["TOTAL"] * len(common_header), common_header]
    total_change_df = pd.DataFrame(index=idx, columns=total_header)

    for col in common_header:
        if col == "Fatal":
            res_total = cp.calculate_fatal_reduction(crashes_df)
        elif col == "Injury":
            res_total = cp.calculate_injury_reduction(crashes_df)
        elif col == "Property Damage":
            res_total = cp.calculate_prop_damage_reduction(crashes_df)
        elif col == "Rear end":
            res_total = cp.calculate_rear_end_reduction(crashes_df)
        elif col == "Sideswipe":
            res_total = cp.calculate_sideswipe_reduction(crashes_df)
        elif col == "Left Turn":
            res_total = cp.calculate_left_turn_reduction(crashes_df)
        elif col == "Fixed Object":
            res_total = cp.calculate_fixed_object_reduction(crashes_df)
        elif col == "Angle":
            res_total = cp.calculate_angle_reduction(crashes_df)
        elif col == "Opposite Direction":
            res_total = cp.calculate_opp_dir_reduction(crashes_df)
        elif col == "Parked":
            res_total = cp.calculate_parked_reduction(crashes_df)
        elif col == "Pedestrian":
            res_total = cp.calculate_pedestrian_reduction(crashes_df)
        elif col == "Other":
            res_total = cp.calculate_other_reduction(crashes_df)

        total_change_df.loc["NUMBER OF ACCIDENTS", "TOTAL"][col] = res_total[
            "NUMBER OF ACCIDENTS"
        ]
        total_change_df.loc["CRASH MODIFICATION FACTOR (CMF)", "TOTAL"][
            col
        ] = res_total["CRASH MODIFICATION FACTOR (CMF)"]
        total_change_df.loc["CRASH REDUCTION FACTOR (CRF)", "TOTAL"][col] = res_total[
            "CRASH REDUCTION FACTOR (CRF)"
        ]
        total_change_df.loc["EXPECTED CHANGE IN ACCIDENTS (%)", "TOTAL"][
            col
        ] = res_total["EXPECTED CHANGE IN ACCIDENTS (%)"]
        total_change_df.loc["ANNUAL NET CRASH REDUCTION", "TOTAL"][col] = res_total[
            "ANNUAL NET CRASH REDUCTION"
        ]

    # generate analysis summary for direction 1
    d0_header = [
        [route_dirs.get(crash_directions[0])] * len(common_header),
        common_header,
    ]
    d0_change_df = pd.DataFrame(index=idx, columns=d0_header)
    d0_crashes_df = crashes_df[crashes_df.crash_dir == crash_directions[0]]
    for col in common_header:
        if col == "Fatal":
            res_total = cp.calculate_fatal_reduction(d0_crashes_df)
        elif col == "Injury":
            res_total = cp.calculate_injury_reduction(d0_crashes_df)
        elif col == "Property Damage":
            res_total = cp.calculate_prop_damage_reduction(d0_crashes_df)
        elif col == "Rear end":
            res_total = cp.calculate_rear_end_reduction(d0_crashes_df)
        elif col == "Sideswipe":
            res_total = cp.calculate_sideswipe_reduction(d0_crashes_df)
        elif col == "Left Turn":
            res_total = cp.calculate_left_turn_reduction(d0_crashes_df)
        elif col == "Fixed Object":
            res_total = cp.calculate_fixed_object_reduction(d0_crashes_df)
        elif col == "Angle":
            res_total = cp.calculate_angle_reduction(d0_crashes_df)
        elif col == "Opposite Direction":
            res_total = cp.calculate_opp_dir_reduction(d0_crashes_df)
        elif col == "Parked":
            res_total = cp.calculate_parked_reduction(d0_crashes_df)
        elif col == "Pedestrian":
            res_total = cp.calculate_pedestrian_reduction(d0_crashes_df)
        elif col == "Other":
            res_total = cp.calculate_other_reduction(d0_crashes_df)

        d0_change_df.loc["NUMBER OF ACCIDENTS", route_dirs.get(crash_directions[0])][
            col
        ] = res_total["NUMBER OF ACCIDENTS"]
        d0_change_df.loc[
            "CRASH MODIFICATION FACTOR (CMF)", route_dirs.get(crash_directions[0])
        ][col] = res_total["CRASH MODIFICATION FACTOR (CMF)"]
        d0_change_df.loc[
            "CRASH REDUCTION FACTOR (CRF)", route_dirs.get(crash_directions[0])
        ][col] = res_total["CRASH REDUCTION FACTOR (CRF)"]
        d0_change_df.loc[
            "EXPECTED CHANGE IN ACCIDENTS (%)", route_dirs.get(crash_directions[0])
        ][col] = res_total["EXPECTED CHANGE IN ACCIDENTS (%)"]
        d0_change_df.loc[
            "ANNUAL NET CRASH REDUCTION", route_dirs.get(crash_directions[0])
        ][col] = res_total["ANNUAL NET CRASH REDUCTION"]

    print("Writing analyis results...", flush=True)
    total_change_df.to_excel(xlsx_writer, "Results")
    d0_change_df.to_excel(xlsx_writer, "Results", startrow=9)

    # generate analysis summary for direction 2
    if len(crash_directions) > 1:
        d1_header = [
            [route_dirs.get(crash_directions[1])] * len(common_header),
            common_header,
        ]
        d1_change_df = pd.DataFrame(index=idx, columns=d1_header)
        d1_crashes_df = crashes_df[crashes_df.crash_dir == crash_directions[1]]
        for col in common_header:
            if col == "Fatal":
                res_total = cp.calculate_fatal_reduction(d1_crashes_df)
            elif col == "Injury":
                res_total = cp.calculate_injury_reduction(d1_crashes_df)
            elif col == "Property Damage":
                res_total = cp.calculate_prop_damage_reduction(d1_crashes_df)
            elif col == "Rear end":
                res_total = cp.calculate_rear_end_reduction(d1_crashes_df)
            elif col == "Sideswipe":
                res_total = cp.calculate_sideswipe_reduction(d1_crashes_df)
            elif col == "Left Turn":
                res_total = cp.calculate_left_turn_reduction(d1_crashes_df)
            elif col == "Fixed Object":
                res_total = cp.calculate_fixed_object_reduction(d1_crashes_df)
            elif col == "Angle":
                res_total = cp.calculate_angle_reduction(d1_crashes_df)
            elif col == "Opposite Direction":
                res_total = cp.calculate_opp_dir_reduction(d1_crashes_df)
            elif col == "Parked":
                res_total = cp.calculate_parked_reduction(d1_crashes_df)
            elif col == "Pedestrian":
                res_total = cp.calculate_pedestrian_reduction(d1_crashes_df)
            elif col == "Other":
                res_total = cp.calculate_other_reduction(d1_crashes_df)

            d1_change_df.loc[
                "NUMBER OF ACCIDENTS", route_dirs.get(crash_directions[1])
            ][col] = res_total["NUMBER OF ACCIDENTS"]
            d1_change_df.loc[
                "CRASH MODIFICATION FACTOR (CMF)", route_dirs.get(crash_directions[1])
            ][col] = res_total["CRASH MODIFICATION FACTOR (CMF)"]
            d1_change_df.loc[
                "CRASH REDUCTION FACTOR (CRF)", route_dirs.get(crash_directions[1])
            ][col] = res_total["CRASH REDUCTION FACTOR (CRF)"]
            d1_change_df.loc[
                "EXPECTED CHANGE IN ACCIDENTS (%)", route_dirs.get(crash_directions[1])
            ][col] = res_total["EXPECTED CHANGE IN ACCIDENTS (%)"]
            d1_change_df.loc[
                "ANNUAL NET CRASH REDUCTION", route_dirs.get(crash_directions[1])
            ][col] = res_total["ANNUAL NET CRASH REDUCTION"]

        d1_change_df.to_excel(xlsx_writer, "Results", startrow=18)

    # save output excel file
    xlsx_writer.save()


if __name__ == "__main__":
    main()
