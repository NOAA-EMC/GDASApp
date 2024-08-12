#!/usr/bin/env python3

import sys
from b2iconverter.util import ParseArguments
from b2iconverter.bufr2ioda_config import Bufr2iodaConfig
from b2iconverter.bufr2ioda_converter import Bufr2ioda_Converter
from bathy_ioda_variables import BathyIODAVariables


if __name__ == '__main__':

    script_name, config_file, log_file, test_file = ParseArguments()

    platform_description = 'Profiles from BATHYthermal: temperature'
    bufr2ioda_config = Bufr2iodaConfig(
        script_name,
        config_file,
        platform_description)

    ioda_vars = BathyIODAVariables()
    # ??? ioda_vars.SetTemperatureError(0.3)
    # ??? ioda_vars.SetSalinityError(1.0)
    ioda_vars.SetTemperatureVarName("waterTemperature")
    bathy = Bufr2ioda_Converter(bufr2ioda_config, ioda_vars, log_file)
    bathy.run()

    if test_file:
        result = bathy.test(test_file)
        sys.exit(result)
