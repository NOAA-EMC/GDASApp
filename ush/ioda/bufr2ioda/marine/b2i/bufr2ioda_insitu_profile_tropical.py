#!/usr/bin/env python3

import sys
from b2iconverter.util import parse_arguments
from b2iconverter.bufr2ioda_config import Bufr2iodaConfig
from b2iconverter.bufr2ioda_converter import Bufr2ioda_Converter
from tropical_ioda_variables import TropicalIODAVariables


platform_description = 'Tropical mooring profiles from dbuoy: temperature and salinity'


class TropicalConfig(Bufr2iodaConfig):

    def ioda_filename(self):
        return f"{self.cycle_type}.t{self.hh}z.insitu_profile_tropical.{self.cycle_datetime}.nc4"


if __name__ == '__main__':

    script_name, config_file, log_file, test_file = parse_arguments()

    bufr2ioda_config = TropicalConfig(
        script_name,
        config_file,
        platform_description)

    ioda_vars = TropicalIODAVariables()
    ioda_vars.set_temperature_var_name("waterTemperature")
    ioda_vars.set_temperature_error(0.02)
    ioda_vars.set_salinity_var_name("salinity")
    ioda_vars.set_salinity_error(0.01)

    tropical = Bufr2ioda_Converter(bufr2ioda_config, ioda_vars, log_file)

    tropical.run()

    if test_file:
        result = tropical.test(test_file)
        sys.exit(result)
