#!/usr/bin/env python3

import sys
from b2iconverter.util import parse_arguments
from b2iconverter.bufr2ioda_config import Bufr2iodaConfig
from b2iconverter.bufr2ioda_converter import Bufr2ioda_Converter
from dbuoyb_surface_ioda_variables import DbuoybIODAVariables


platform_description = 'Surface temperature from dbuoyb'


class DbuoybConfig(Bufr2iodaConfig):

    def ioda_filename(self):
        return f"{self.cycle_type}.t{self.hh}z.insitu_surface_dbuoyb.{self.cycle_datetime}.nc4"


if __name__ == '__main__':

    script_name, config_file, log_file, test_file = parse_arguments()

    bufr2ioda_config = DbuoybConfig(
        script_name,
        config_file,
        platform_description)

    ioda_vars = DbuoybIODAVariables()

    ioda_vars.set_temperature_var_name("seaSurfaceTemperature")
    ioda_vars.set_temperature_error(0.3)

    dbuoyb = Bufr2ioda_Converter(bufr2ioda_config, ioda_vars, log_file)

    dbuoyb.run()

    if test_file:
        result = dbuoyb.test(test_file)
        sys.exit(result)
