import numpy as np
import yaml
from .data_object import DataObject
from .data_variable import DataVariable
from .variables import *
from pyiodaconv import bufr


class DataSet(DataObject):
    def __init__(self, logger):
        self.logger = logger
        self.data_variables = []

    def add(self, data_variable: DataVariable):
        if not isinstance(data_variable, DataVariable):
            raise TypeError("Only DataVariable objects can be added to DataSet.")
        self.data_variables.append(data_variable)

    def remove(self, data_variable: DataVariable):
        self.data_variables.remove(data_variable)

    def describe(self):
        for v in self.data_variables:
            v.describe()

    def add_query(self, q): 
        for v in self.data_variables:
            q = v.add_query(q)
        return q

    def set_from_query_result(self, r): 
        for v in self.data_variables:
            v.set_from_query_result(r)

    def filter(self, mask):
        for v in self.data_variables:
            v.filter(mask)

    def create_ioda_objects(self, obsspace):
        for v in self.data_variables:
            v.create_ioda_objects(obsspace)

    def log(self, logger):
        for v in self.data_variables:
            v.log(logger)

    # return the size of the first data variable
    # it is assumed that all data variables have the same size
    def get_data_size(self):
        if len(self.data_variables) == 0:
            return 0
        else:
            return self.data_variables[0].get_data_size()

    """Return the logical AND of all the filters (masks) in the dataset."""
    def get_filter(self):
        f = self.data_variables[0].get_filter()
        for v in self.data_variables[1:]:
            f = np.logical_and(f, v.get_filter())
        return f

### same methods as in DataVariable:

    def read_from_bufr(self, bufr_file_path):
        q = bufr.QuerySet()
        q = self.add_query(q)
        with bufr.File(bufr_file_path) as f:
            r = f.execute(q)
        self.set_from_query_result(r)
        self.logger.debug(f"read from bufr: data size = {self.get_data_size()}")

    def read_from_bufr_by_depth(self, bufr_file_path, depth):
        q = bufr.QuerySet()
        q = depth.add_query(q)
        q = self.add_query(q)
        with bufr.File(bufr_file_path) as f:
            r = f.execute(q)
        self.set_from_query_result(r)
