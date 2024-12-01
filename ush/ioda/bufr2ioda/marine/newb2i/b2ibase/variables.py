import numpy as np
import sys 
from .data_variable import DataVariable
from .ocean import OceanBasin
from .util import *


class Depth(DataVariable):
    # def create_ioda_objects(self, obsspace):
        # self.short_create_ioda_objects(obsspace)

    def create_ioda_objects(self, obsspace):
        obsspace.create_var(
            self._descriptor + "/" + self._short_name,
            dtype=self._data.dtype, fillval=self._data.fill_value
        ) \
            .write_attr('units', self._units) \
            .write_attr('long_name', self._name) \
            .write_data(self._data)


class DepthFromPressure(Depth):
    def set_from_query_result(self, r): 
        super().set_from_query_result(r)
        # convert depth in pressure units to meters (rho * g * h)
        self._data = np.float32(self._data.astype(float) * 0.0001)


class Longitude(DataVariable):
    pass

class Latitude(DataVariable):
    pass


class DateTime(DataVariable):
    def __init__(self, short_name, name, descriptor, units, depth_profile_var_name, data_min, data_max, data_error, bufr_mnemonics, data_dictionary):
        # Pass empty string for bufr_mnemonic
        super().__init__(short_name, name, None, descriptor, units, depth_profile_var_name, data_min, data_max, data_error, data_dictionary)
        self._bufr_mnemonics = bufr_mnemonics
# WARNING: _bufr_mnemonics is a dictionary, but it should be a list
# because position is important in get_datetime

    def print__bufr_mnemonics(self):
        for date_component in self._bufr_mnemonics:
            print(f"\t{date_component}: {self._bufr_mnemonics[date_component]}")

    def describe(self):
        super().describe()
        print("_bufr_mnemonics:")
        self.print__bufr_mnemonics()
        # print(self._bufr_mnemonics)

    def add_query(self, q):
        for date_component in self._bufr_mnemonics:
            q.add(date_component, self._bufr_mnemonics[date_component])
        return q

    def set_from_query_result(self, r):
        date_keys = list(self._bufr_mnemonics.keys())
        if self._depth_profile_var_name:
            self._data = r.get_datetime(*date_keys, group_by = self._depth_profile_var_name)
        else:
            self._data = r.get_datetime(*date_keys)
        # convert to seconds since 1970
        self._data = self._data.astype(np.int64)

    def create_ioda_objects(self, obsspace):
        obsspace.create_var(
            self._descriptor + "/" + self._short_name,
            dtype=self._data.dtype, fillval=self._data.fill_value
        ) \
            .write_attr('units', self._units) \
            .write_attr('long_name', self._name) \
            .write_data(self._data)


# when rcpt date time is 2d in bufr
# extract without grouping by depth
# discard the irrelevant dimension
# tile repeats the variable,
# so we are doing "by_depth" by hand
# we use the dict to get the depth variable
class RcptDateTime2D(DateTime):
    def set_from_query_result(self, r):
        date_keys = list(self._bufr_mnemonics.keys())
        self._data = r.get_datetime(*date_keys)
        self._data = self._data[:, 0]
        self._data = self._data.astype(np.int64)
        n = self._data_dictionary.get_data_size()
        k = int(n / self._data.size)
        self._data = np.tile(self._data, k)


class StationID(DataVariable):
    def create_ioda_objects(self, obsspace):
        self.short_create_ioda_objects(obsspace)

    def log(self, logger):
        logger.debug(f"{self._descriptor}/{self._name}: {len(self._data)}, {self._data.astype(str).dtype}")
        if isinstance(self._data[0], str):
            concatenated_string = ''.join(self._data)
            # Compute the hash using SHA-256
            hash_object = hashlib.sha256(concatenated_string.encode())
            hash_hex = hash_object.hexdigest()
            logger.debug(f"{self._descriptor}/{self._name} hash = {hash_hex}")
        # # elif isinstance(self.stationID[0], int32):
        else:
            logger.debug(f"{self._descriptor}/{self._name} hash = {compute_hash(self._data)}")



class Temperature(DataVariable):
    def set_from_query_result(self, r):
        super().set_from_query_result(r)
        self._data -= 273.15


class Salinity(DataVariable):
    def get_filter(self):
        return (self._data >= self._data_min) & (self._data <= self._data_max)


class BuoyType(DataVariable):
    def create_ioda_objects(self, obsspace):
        self.short_create_ioda_objects(obsspace)



### Additional variables


class PreQCVariable(DataVariable):
    def __init__(self, v):
        super().__init__("PreQC_" + v.get_short_name(),
            v.get_name(),
            bufr_mnemonic = None,
            descriptor = "PreQC",
            units = v.get_units(),
            depth_profile_var_name = v.get_depth_profile_var_name(),
            data_min = 0,
            data_max = 0,
            data_error = 0,
            data_dictionary = None)
        n = v.get_data_size()
        self._data = (np.ma.masked_array(np.full(n, 0))).astype(np.int32)

    def create_ioda_objects(self, obsspace):
        # self.short_create_ioda_objects(obsspace)
        obsspace.create_var(self._descriptor + "/" + self._name, \
            dtype=self._data.dtype, fillval=self._data.fill_value) \
            .write_attr('long_name', 'PreQC') \
            .write_data(self._data)


class ErrorVariable(DataVariable):
    def __init__(self, v):
        e = v.get_error()
        super().__init__("ObsError_" + v.get_short_name(),
            v.get_name(),
            bufr_mnemonic = None,
            descriptor = "ObsError",
            units = v.get_units(),
            depth_profile_var_name = v.get_depth_profile_var_name(),
            data_min = e,
            data_max = e,
            data_error = e,
            data_dictionary = None)
        n = v.get_data_size()
        self._data = np.float32(np.ma.masked_array(np.full(n, e)))

    def create_ioda_objects(self, obsspace):
        obsspace.create_var(self._descriptor + "/" + self._name, \
            dtype=self._data.dtype, fillval=self._data.fill_value) \
            .write_attr('units', self._units) \
            .write_attr('long_name', 'ObsError') \
            .write_data(self._data)


class SequenceNumber(DataVariable):
    def __init__(self, lon, lat, dtype, fill_value):
        self.dtype = dtype
        self.fill_value = fill_value
        super().__init__("sequenceNumber",
            'Sequence Number',
            bufr_mnemonic = None,
            descriptor = "MetaData",
            units = None,
            depth_profile_var_name = None,
            data_min = None,
            data_max = None,
            data_error = None,
            data_dictionary = None)
        combined = np.stack((lon, lat), axis=-1)
        unique_combined, seq_num = np.unique(combined, axis=0, return_inverse=True)
        self._data = np.ma.masked_equal(seq_num.astype(np.int32), 1)

    def create_ioda_objects(self, obsspace):
        # self.short_create_ioda_objects(obsspace)
        # print(f"SequenceNumber self.fill_value = {self.fill_value}")
        obsspace.create_var(self._descriptor + "/" + self._short_name, \
            dtype=self.dtype, fillval=self.fill_value) \
            .write_attr('long_name', self._name) \
            .write_data(self._data)


class OceanBasinVariable(DataVariable):
    def __init__(self, nc_file_path, lon, lat, dtype, fill_value):
        self.dtype = dtype
        self.fill_value = fill_value
        self.ocean = OceanBasin(nc_file_path)
        super().__init__("oceanBasin",
            'Ocean basin',
            bufr_mnemonic = None,
            descriptor = "MetaData",
            units = None,
            depth_profile_var_name = None,
            data_min = 0,
            data_max = 5,
            data_error = 0,
            data_dictionary = None)
        self._data = self.ocean.get_station_basin(lat, lon)

    def create_ioda_objects(self, obsspace):
        obsspace.create_var(self._descriptor + "/" + self._short_name, \
            dtype=self.dtype, fillval=self.fill_value) \
            .write_attr('long_name', self._name) \
            .write_data(self._data)
