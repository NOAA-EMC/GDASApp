#!/usr/bin/env python3

import sys
from b2iconverter.util import parse_arguments
from b2iconverter.bufr2ioda_config import Bufr2iodaConfig
from b2iconverter.bufr2ioda_converter import Bufr2ioda_Converter
from tesac_ioda_variables import TesacIODAVariables


platform_description = 'Profiles from TESAC: temperature and salinity'


if __name__ == '__main__':

    script_name, config_file, log_file, test_file = parse_arguments()

    bufr2ioda_config = Bufr2iodaConfig(
        script_name,
        config_file,
        platform_description)

    ioda_vars = TesacIODAVariables()
    ioda_vars.set_temperature_error(0.02)
    ioda_vars.set_temperature_var_name("waterTemperature")
    ioda_vars.set_salinity_error(0.01)
    ioda_vars.set_salinity_var_name("salinity")

    tesac = Bufr2ioda_Converter(bufr2ioda_config, ioda_vars, log_file)

    tesac.run()

    if test_file:
        result = tesac.test(test_file)
        sys.exit(result)
