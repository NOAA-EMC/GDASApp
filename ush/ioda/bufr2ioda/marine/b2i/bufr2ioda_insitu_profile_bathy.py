#!/usr/bin/env python3

import sys
from b2iconverter.util import parse_arguments
from b2iconverter.bufr2ioda_config import Bufr2iodaConfig
from b2iconverter.bufr2ioda_converter import Bufr2ioda_Converter
from bathy_ioda_variables import BathyIODAVariables


platform_description = 'Profiles from BATHYthermal: temperature'


if __name__ == '__main__':

    script_name, config_file, log_file, test_file = parse_arguments()

    bufr2ioda_config = Bufr2iodaConfig(
        script_name,
        config_file,
        platform_description)

    ioda_vars = BathyIODAVariables()
    ioda_vars.set_temperature_error(0.24)
    ioda_vars.set_temperature_var_name("waterTemperature")

    bathy = Bufr2ioda_Converter(bufr2ioda_config, ioda_vars, log_file)

    bathy.run()

    if test_file:
        result = bathy.test(test_file)
        sys.exit(result)
