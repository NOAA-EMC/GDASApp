import numpy as np
from .data_object import DataObject
from .util import *
from pyiodaconv import bufr


class DataVariable(DataObject):
    def __init__(self, 
        short_name, 
        name, 
        bufr_mnemonic = "", 
        descriptor = "", 
        units = "", 
        depth_profile_var_name = "depth",
        data_min = 0.0, 
        data_max = 0.0, 
        data_error = 0.0,
        data_dictionary = None):
#########
        self._short_name = short_name
        self._name = name
        self._bufr_mnemonic = bufr_mnemonic
        self._descriptor = descriptor
        self._units = units
        self._depth_profile_var_name = depth_profile_var_name
        self._data_min = data_min
        self._data_max = data_max
        self._data_error = data_error
        self._data_dictionary = data_dictionary

        self._data = np.ma.masked_all(0)   # masked array of size 0

    def __repr__(self):
        return f"{self.__class__.__name__}: {self._short_name}, {self._name} {self._data.shape}"

    def describe(self):
        print(f"DataVariable instance: {self.__repr__()}")
        print(f"_short_name = {self._short_name}")
        print(f"_name = {self._name}")
        print(f"_bufr_mnemonic = {self._bufr_mnemonic}")
        print(f"_descriptor = {self._descriptor}")
        print(f"_units = {self._units}")
        print(f"_depth_profile_var_name = {self._depth_profile_var_name}")
        print(f"_data_min = {self._data_min}")
        print(f"_data_max = {self._data_max}")
        print(f"_data_error = {self._data_error}")

##########################

    def add_query(self, q):
        q.add(self._short_name, self._bufr_mnemonic)
        return q

    def set_from_query_result(self, r):
        if self._depth_profile_var_name:
            self._data = r.get(self._short_name, group_by=self._depth_profile_var_name)
        else:
            self._data = r.get(self._short_name)

    def filter(self, mask):
        self._data = self._data[mask]

    def create_ioda_objects(self, obsspace):
        obsspace.create_var(self._descriptor + "/" + self._short_name, \
            dtype=self._data.dtype, fillval=self._data.fill_value) \
            .write_attr('units', self._units) \
            .write_attr('valid_range', np.array([self._data_min, self._data_max], dtype=np.float32)) \
            .write_attr('long_name', self._name) \
            .write_data(self._data)

    def log(self, logger):
        logger.debug(f"{self._descriptor}/{self._name}: {len(self._data)}, {self._data.dtype}    min, max = {self._data.min()}, {self._data.max()}")
        logger.debug(f"{self._descriptor}/{self._name} hash = {compute_hash(self._data)}")

    def get_data_size(self):
        return self._data.size

##########################

    # useful for many variables
    def short_create_ioda_objects(self, obsspace):
        obsspace.create_var(self._descriptor + "/" + self._short_name, \
            dtype=self._data.dtype, fillval=self._data.fill_value) \
            .write_attr('long_name', self._name) \
            .write_data(self._data)

    def get_data(self):
        return self._data

    def set_data(self, data):
        self._data = data

    def get_filter(self):
        return (self._data > self._data_min) & (self._data <= self._data_max)

    def get_short_name(self):
        return self._short_name

    def get_name(self):
        return self._name

    def set_name(self, name):
        self._name = name

    def get_error(self):
        return self._data_error

    def set_error(self, e):
        self._data_error = e

    def get_units(self):
        return self._units

    def get_descriptor(self):
        return self._descriptor

    def get_depth_profile_var_name(self):
        return self._depth_profile_var_name

    def read_from_bufr(self, bufr_file_path):
        q = bufr.QuerySet()
        q = self.add_query(q)
        with bufr.File(bufr_file_path) as f:
            r = f.execute(q)
        self.set_from_query_result(r)

    def read_from_bufr_by_depth(self, bufr_file_path, depth):
        q = bufr.QuerySet()
        q = depth.add_query(q)
        q = self.add_query(q)
        with bufr.File(bufr_file_path) as f:
            r = f.execute(q)
        self.set_from_query_result(r)


################ debug methods

    def print_data(self):
        for index, value in np.ndenumerate(self._data):
            print(f"{index[0]}: {value}")

