import os
import numpy as np
import bufr
from bufr.encoders.netcdf import Encoder as netcdfEncoder
from .ocean import OceanBasin


class DataContainer:
    def __init__(self, logger):
        self.logger = logger
        self.container = None
        self.description = None

    def print_var_names(self):
        for v in self.container.list():
            print(v)

    def get_data_size(self):
        v_list = self.container.list()
        if not v_list:
            return 0
        v_name = v_list[0]
        v0 = self.container.get(v_name)
        if isinstance(v0, np.ma.MaskedArray):
            return v0.size
        return 0

    def filter(self, mask):
        new_container = bufr.DataContainer()
        for v_name in self.container.list():
            v = self.container.get(v_name)
            paths = self.container.get_paths(v_name)
            v = v[mask]
            new_container.add(v_name, v, paths)
        self.container = new_container

    def log(self, logger):
        for v_name in self.container.list():
            v = self.container.get(v_name)
            logger.log_var(v_name, v)

    def read_from_bufr(self, bufr_file_path, converter_yaml_path):
        self.container = bufr.Parser(bufr_file_path, converter_yaml_path).parse()

    def write_to_ioda_file(self, iodafile_path, mapping_path, b2i_config):
        self.description = bufr.encoders.Description(mapping_path)

        date_time = self.container.get("variables/dateTime")
        min_date = date_time.min()
        max_date = date_time.max()
        date_range = [str(min_date), str(max_date)]
        date_range_str = date_range[0] + ", " + date_range[1]
        self.description.add_global(name='datetimeRange', value=date_range_str)
        self.description.add_global(name='sourceFiles', value=b2i_config.bufr_filename())

        netcdfEncoder(self.description).encode(self.container, iodafile_path)
        self.logger.debug(f"written ioda file: {iodafile_path}")

    def convert_temp_to_celsius(self, name):
        temp_name = "variables/" + name
        temp = self.container.get(temp_name)
        temp -= 273.15
        self.container.replace(temp_name, temp)

    def convert_depth_from_pressure(self, name):
        depth_name = "variables/" + name
        depth = self.container.get(depth_name)
        depth = np.float32(depth.astype(float) * 0.0001)
        self.container.replace(depth_name, depth)

    def add_preqc_var(self, name):
        v_name = "variables/" + name
        v = self.container.get(v_name)
        v_path = self.container.get_paths(v_name)
        preqc_name = "variables/PreQC" + name
        preqc = np.zeros_like(v)
        self.container.add(preqc_name, preqc, v_path)

    def add_error_var(self, name, error):
        v_name = "variables/" + name
        v = self.container.get(v_name)
        v_path = self.container.get_paths(v_name)
        error_var_name = "variables/ObsError" + name
        error_var = np.full_like(v, error)
        self.container.add(error_var_name, error_var, v_path)

    def add_seq_num(self):
        lon = self.container.get("variables/longitude")
        lat = self.container.get("variables/latitude")
        v_path = self.container.get_paths("variables/latitude")
        combined = np.stack((lon, lat), axis=-1)
        unique_combined, seq_num = np.unique(combined, axis=0, return_inverse=True)
        v = np.ma.masked_array(seq_num, mask=lon.mask)
        self.container.add("variables/SequenceNumber", v, v_path)

    def add_ocean_basin(self, ocean_basin_nc_file_path):
        lon = self.container.get("variables/longitude")
        lat = self.container.get("variables/latitude")
        v_path = self.container.get_paths("variables/latitude")
        ocean = OceanBasin(ocean_basin_nc_file_path)
        v = ocean.get_station_basin(lat, lon)
        self.container.add("variables/OceanBasin", v, v_path)
