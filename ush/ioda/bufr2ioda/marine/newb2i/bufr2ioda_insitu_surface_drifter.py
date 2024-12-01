#!/usr/bin/env python3

import sys
from b2ibase.util import parse_arguments
from b2ibase.config import Config
from b2ibase.data_variable_dictionary import DataVariableDictionary
from b2ibase.b2i import B2I 
from b2ibase.log import B2ILogger


class DrifterConfig(Config):
    def ioda_filename(self):
        return f"{self.cycle_type}.t{self.hh}z.insitu_surface_drifter..{self.cycle_datetime}.nc4"


class DrifterData(DataVariableDictionary):
    def read_from_bufr(self, bufr_file_path):
        super().read_from_bufr(bufr_file_path)
        temp = self.get("waterTemperature")
        buoy_type = self.get("buoyType").get_data()
        # Separate Drifter profiles from dbuoy tank
        # buoy_type:
        # 1 - Standard Lagrangian drifter (Global Drifter Programme)
        # 4 - Ice drifter
        # 5 - SVPG Standard Lagrangian drifter with GPS
        values_to_select = [1, 4, 5]
        buoy_mask = np.isin(buoy_type, values_to_select)
        mask = buoy_mask & temp.get_filter() & saln.get_filter()
        self.filter(mask)


class DrifterConverter(B2I):
    def process_data(self):
        self.data.remove("depth")
        self.data.add_preqc_vars()
        self.data.add_error_vars()
        ocean_file_path = self.config.ocean_basin_nc_file_path()
        self.data.add_ocean_basin(ocean_file_path)


if __name__ == '__main__':

    script_name, config_file, log_file, test_file = parse_arguments()
    log_to_console = True
    logger = B2ILogger(script_name, log_to_console, log_file)

    config = DrifterConfig(config_file, logger)
    data = DrifterData(logger)
    b2i = DrifterConverter(config, data, logger)
    b2i.run()
    if test_file:
        result = b2i.test(test_file)
        sys.exit(result)
