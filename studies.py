# This module defines the properties of each study and their associated calculations.
import pandas as pd
import functools


class Study_Area:
    """
    Class to define and execute CMF studies.
    """

    def __init__(
        self,
        route_prefix: str,
        route_number: int,
        start_milepost: float,
        end_milepost: float,
        start_year: int,
        end_year: int,
        input_cmfs: str,
    ):
        self.route_prefix = (route_prefix,)
        self.route_number = (route_number,)
        self.start_milepost = (start_milepost,)
        self.end_milepost = (end_milepost,)
        self.start_year = (start_year,)
        self.end_year = end_year
        self.input_cmfs = pd.read_excel(input_cmfs)

    def count_segments(self) -> int:
        """
        Returns the number of segments in this study area.
        """
        return len(self.input_cmfs.Segment.unique())

    def get_segment_names(self) -> tuple:
        """
        Returns tuple of distinct segment names.
        """
        return self.input_cmfs.Segment.unique()

    def get_mp_range(self) -> tuple:
        """
        Returns the milepost range of this study area.
        """
        return (self.input_cmfs.Start_MP.min(), self.input_cmfs.End_MP.max())

    def get_crash_cmfs(
        self,
        crash_milepost: float,
        severity: str = "all",
        crash_type: str = "all",
        crash_dir: str = "all",
        crash_time: str = "all",
    ) -> list:
        """
        Returns the product of all input CMF value(s) that match the given input parameters at the crash milepost.
        """
        coefficients = []
        results = self.input_cmfs.query(
            f"Start_MP <= {crash_milepost} and {crash_milepost} < End_MP", inplace=False
        )
        cmf_stack = results.iloc[0 : len(results), 6]
        for row in range(len(results)):
            if (
                (
                    results[row]["Severity"].lower() == "all"
                    or results[row]["Severity"].lower() == severity.lower()
                )
                and (
                    results[row]["Crash_Type"].lower() == "all"
                    or results[row]["Crash_Type"] == crash_type.lower()
                )
                and (
                    results[row]["Direction"].lower() == "all"
                    or results[row]["Direction"] == crash_dir.lower()
                )
                and (
                    results[row]["Time"].lower() == "all"
                    or results[row]["Time"] == crash_time.lower()
                )
            ):
                coefficients.append(cmf_stack.pop(row))
        return coefficients

    @staticmethod
    def reduce_cmfs(cmfs: list) -> float:
        """
        Return product of all CMF values in cmfs list.
        """
        return functools.reduce(lambda a, b: a * b, cmfs)
