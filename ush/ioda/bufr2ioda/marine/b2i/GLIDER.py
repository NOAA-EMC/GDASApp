#!/usr/bin/env python3

import sys
from b2iconverter.util import ParseArguments
from b2iconverter.bufr2ioda_config import Bufr2iodaConfig
from b2iconverter.bufr2ioda_converter import Bufr2ioda_Converter
from glider_ioda_variables import GliderIODAVariables


class GliderConfig(Bufr2iodaConfig):
    def IODAFilename(self):
        return f"{self.cycle_type}.t{self.hh}z.{self.data_type}_profiles.{self.data_format}.nc4"


if __name__ == '__main__':

    script_name, config_file, log_file, test_file = ParseArguments()

    platform_description = 'GLIDER profiles from subpfl: temperature and salinity'
    bufr2ioda_config = GliderConfig(
        script_name,
        config_file,
        platform_description)

    ioda_vars = GliderIODAVariables()
    ioda_vars.SetTemperatureError(0.02)
    ioda_vars.SetSalinityError(0.01)

    glider = Bufr2ioda_Converter(bufr2ioda_config, ioda_vars, log_file)
    glider.run()

    if test_file:
        result = glider.test(test_file)
        sys.exit(result)
