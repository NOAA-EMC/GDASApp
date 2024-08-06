#!/usr/bin/env python3

import sys
from util import ParseArguments
from bufr2ioda_config import Bufr2iodaConfig
from bufr2ioda_converter import Bufr2ioda_Converter
from xbtctd_ioda_variables import XbtctdIODAVariables


class XbtctdConfig(Bufr2iodaConfig):
    def IODAFilename(self):
        return f"{self.cycle_type}.t{self.hh}z.{self.data_type}_profiles.{self.data_format}.nc4"


if __name__ == '__main__':

    script_name, config_file, log_file, test_file = ParseArguments()

    platform_description = 'Profiles from XBT/CTD: temperature and salinity'
    bufr2ioda_config = XbtctdConfig(
        script_name,
        config_file,
        platform_description)

    ioda_vars = XbtctdIODAVariables()
    ioda_vars.SetTemperatureError(0.12)
    ioda_vars.SetSalinityError(1.0)

    xbtctd = Bufr2ioda_Converter(bufr2ioda_config, ioda_vars, log_file)
    xbtctd.run()

    if test_file:
        result = xbtctd.test(test_file)
        sys.exit(result)
