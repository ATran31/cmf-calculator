import pandas as pd


class CMF:
    """
    A Class used to query the CMF clearing house database.
    """

    def __init__(self, xlsx_file: str):
        """
        Keyword Arguments:
        xlsx_file -- path to an Excel CMF clearing house database.
        """
        # TODO download a new copy of xlsx_file if its created date is older than the current month.
        self.data_frame = pd.read_excel(xlsx_file)

    def get_categories(self) -> str:
        """
        Return a list of countermeasure categories.
        """
        pass

    def get_subcategories(self, catname: str) -> list:
        """
        Return a list of countermeasure subcategories.
        Keyword Arguments:
        catname -- Countermeasure category name.
        """
        pass

    def get_cm_name(self, catname: str, subcatname: str) -> list:
        """
        Return a list of countermeasure names.
        Keyword Arguments:
        catname -- Countermeasure category name.
        subcatname -- Countermeasure subcategory name.
        """
        pass

    def get_cmf_attributes(self, crfid: int) -> dict:
        """
        Return a dict of a CMF attributes.
        Keyword Arguments:
        crfid -- Unique ID assigned to each CMF.
        """
        pass
