#!/usr/bin/env python3

import sys
from b2iconverter.util import parse_arguments
from b2iconverter.bufr2ioda_config import Bufr2iodaConfig
from b2iconverter.bufr2ioda_converter import Bufr2ioda_Converter
from dbuoyb_drifter_ioda_variables import DbuoybDrifterIODAVariables


platform_description = 'Drifters, surface temperature from dbuoyb'


class DbuoybDrifterConfig(Bufr2iodaConfig):

    def ioda_filename(self):
        return f"{self.cycle_type}.t{self.hh}z.insitu_surface_dbuoyb_drifter.{self.cycle_datetime}.nc"


if __name__ == '__main__':

    script_name, config_file, log_file, test_file = parse_arguments()

    bufr2ioda_config = DbuoybDrifterConfig(
        script_name,
        config_file,
        platform_description)

    ioda_vars = DbuoybDrifterIODAVariables()

    ioda_vars.set_temperature_var_name("seaSurfaceTemperature")
    ioda_vars.set_temperature_error(0.3)

    dbuoyb_drifters = Bufr2ioda_Converter(bufr2ioda_config, ioda_vars, log_file)

    dbuoyb_drifters.run()

    if test_file:
        result = dbuoyb_drifters.test(test_file)
        sys.exit(result)
