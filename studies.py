# This module defines the properties of each study and their associated calculations.
import pandas as pd


class Study_Area:
    """
    Class to represent a study area.
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

    def count_segments(self):
        """
        Returns the number of segments in this study area.
        """
        pass

    def get_mp_range(self):
        """
        Returns the milepost range of this study area.
        """
        pass

    def get_cmfs(
        self,
        crash_milepost: float,
        severity: str,
        crash_type: str,
        crash_dir: str,
        crash_time: str,
    ) -> list:
        """
        Returns the CMF value(s) that match the given input parameters at the crash milepost.
        """
        pass
