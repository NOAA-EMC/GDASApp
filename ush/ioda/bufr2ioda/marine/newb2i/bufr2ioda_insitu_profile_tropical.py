#!/usr/bin/env python3

import sys
from b2ibase.util import parse_arguments
from b2ibase.config import Config
from b2ibase.data_variable_dictionary import DataVariableDictionary
from b2ibase.b2i import B2I
from b2ibase.log import B2ILogger


class TropicalConfig(Config):

    def ioda_filename(self):
        return f"{self.cycle_type}.t{self.hh}z.insitu_profile_tropical.{self.cycle_datetime}.nc4"


class TropicalData(DataVariableDictionary):
    def read_from_bufr(self, bufr_file_path):
        super().read_from_bufr(bufr_file_path)
        temp = self.get("waterTemperature")
        saln = self.get("salinity")
        # Separate tropical mooring profiles from dbuoy tank
        # buoy_type: ATLAS is 21, TRITON is 22
        buoy_type = self.get("buoyType").get_data()
        buoy_mask = [True if x == 21 or x == 22 else False for x in buoy_type]
        mask = buoy_mask & temp.get_filter() & saln.get_filter()
        self.filter(mask)


if __name__ == '__main__':

    script_name, config_file, log_file, test_file = parse_arguments()
    log_to_console = True
    logger = B2ILogger(script_name, log_to_console, log_file)

    config = TropicalConfig(config_file, logger)
    data = TropicalData(logger)
    b2i = B2I(config, data, logger)
    b2i.run()
    if test_file:
        result = b2i.test(test_file)
        print("result = ", result)
        sys.exit(result)
