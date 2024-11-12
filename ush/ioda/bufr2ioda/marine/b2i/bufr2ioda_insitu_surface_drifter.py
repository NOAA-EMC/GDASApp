#!/usr/bin/env python3

import sys
from b2iconverter.util import parse_arguments
from b2iconverter.bufr2ioda_config import Bufr2iodaConfig
from b2iconverter.bufr2ioda_converter import Bufr2ioda_Converter
from drifter_ioda_variables import DrifterIODAVariables


platform_description = 'Lagrangian drifter drogue profiles from dbuoy: temperature'


class DrifterConfig(Bufr2iodaConfig):

    def ioda_filename(self):
        return f"{self.cycle_type}.t{self.hh}z.insitu_surface_drifter.{self.cycle_datetime}.nc4"


if __name__ == '__main__':

    script_name, config_file, log_file, test_file = parse_arguments()

    bufr2ioda_config = DrifterConfig(
        script_name,
        config_file,
        platform_description)

    ioda_vars = DrifterIODAVariables()
    ioda_vars.set_temperature_var_name("waterTemperature")
    ioda_vars.set_temperature_error(0.02)

    drifter = Bufr2ioda_Converter(bufr2ioda_config, ioda_vars, log_file)

    drifter.run()

    if test_file:
        result = drifter.test(test_file)
        sys.exit(result)
