#!/usr/bin/env python3

import sys
from b2ibase.util import parse_arguments
from b2ibase.config import Config
from b2ibase.data_variable_dictionary import DataVariableDictionary
from b2ibase.b2i import B2I 
from b2ibase.log import B2ILogger


class GliderConfig(Config):
    def ioda_filename(self):
        return f"{self.cycle_type}.t{self.hh}z.insitu_profile_glider.{self.cycle_datetime}.nc4"


class GliderData(DataVariableDictionary):
    def read_from_bufr(self, bufr_file_path):
        super().read_from_bufr(bufr_file_path)
        temp = self.get("waterTemperature")
        saln = self.get("salinity")
        id = self.get("stationID").get_data()
        id_mask = (id >= 68900) & (id <= 68999) | \
            (id >= 1800000) & (id <= 1809999) | \
            (id >= 2800000) & (id <= 2809999) | \
            (id >= 3800000) & (id <= 3809999) | \
            (id >= 4800000) & (id <= 4809999) | \
            (id >= 5800000) & (id <= 5809999) | \
            (id >= 6800000) & (id <= 6809999) | \
            (id >= 7800000) & (id <= 7809999)
        mask = id_mask & temp.get_filter() & saln.get_filter()
        self.filter(mask)


if __name__ == '__main__':

    script_name, config_file, log_file, test_file = parse_arguments()
    log_to_console = True
    logger = B2ILogger(script_name, log_to_console, log_file)

    config = GliderConfig(config_file, logger)
    data = GliderData(logger)
    b2i = B2I(config, data, logger)
    b2i.run()
    if test_file:
        result = b2i.test(test_file)
        sys.exit(result)
