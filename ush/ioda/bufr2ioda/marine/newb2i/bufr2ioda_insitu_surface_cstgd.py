#!/usr/bin/env python3

import sys
from b2ibase.util import parse_arguments
from b2ibase.config import Config
from b2ibase.data_variable_dictionary import DataVariableDictionary
from b2ibase.b2i import B2I
from b2ibase.log import B2ILogger


class CstgdConfig(Config):
    def ioda_filename(self):
        return f"{self.cycle_type}.t{self.hh}z.insitu_surface_{self.data_format}.{self.cycle_datetime}.nc4"


class CstgdData(DataVariableDictionary):
    def read_from_bufr(self, bufr_file_path):
        super().read_from_bufr(bufr_file_path)
        temp = self.get("seaSurfaceTemperature")
        mask = temp.get_filter()
        self.filter(mask)


class CstgdConverter(B2I):
    def process_data(self):
        self.data.add_preqc_vars()
        self.data.add_error_vars()
        ocean_file_path = self.config.ocean_basin_nc_file_path()
        self.data.add_ocean_basin(ocean_file_path)


if __name__ == '__main__':

    script_name, config_file, log_file, test_file = parse_arguments()
    log_to_console = True
    logger = B2ILogger(script_name, log_to_console, log_file)

    config = CstgdConfig(config_file, logger)
    data = CstgdData(logger)
    b2i = CstgdConverter(config, data, logger)
    b2i.run()
    if test_file:
        result = b2i.test(test_file)
        sys.exit(result)
