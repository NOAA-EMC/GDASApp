#!/usr/bin/env python3

import sys 
from altkob_ioda_variables import AltkobIODAVariables
from b2iconverter.util import ParseArguments
from b2iconverter.bufr2ioda_config import Bufr2iodaConfig
from b2iconverter.bufr2ioda_converter import Bufr2ioda_Converter



class AltkobConfig(Bufr2iodaConfig):
    def IODAFilename(self):
        return f"{self.cycle_type}.t{self.hh}z.{self.data_type}_profiles.{self.data_format}.nc4"


if __name__ == '__main__':

    script_name, config_file, log_file, test_file = ParseArguments()

    platform_description = 'Surface obs from ALTKOB: temperature and salinity'
    bufr2ioda_config = AltkobConfig(
        script_name,
        config_file,
        platform_description)

    ioda_vars = AltkobIODAVariables()
    ioda_vars.SetTemperatureError(0.3)
    ioda_vars.SetSalinityError(1.0)
    altkob = Bufr2ioda_Converter(bufr2ioda_config, ioda_vars, log_file)
    altkob.run()

    if test_file:
        result = altkob.test(test_file)
        sys.exit(result)
