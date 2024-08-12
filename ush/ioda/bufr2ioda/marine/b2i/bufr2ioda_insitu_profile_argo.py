#!/usr/bin/env python3

import sys
from b2iconverter.util import ParseArguments
from b2iconverter.bufr2ioda_config import Bufr2iodaConfig
from b2iconverter.bufr2ioda_converter import Bufr2ioda_Converter
from argo_ioda_variables import ArgoIODAVariables


if __name__ == '__main__':

    script_name, config_file, log_file, test_file = ParseArguments()

    platform_description = 'ARGO profiles from subpfl: temperature and salinity'
    bufr2ioda_config = Bufr2iodaConfig(
        script_name,
        config_file,
        platform_description)

    ioda_vars = ArgoIODAVariables()
    ioda_vars.SetTemperatureVarName("waterTemperature")
    ioda_vars.SetTemperatureError(0.02)
    ioda_vars.SetSalinityVarName("salinity")
    ioda_vars.SetSalinityError(0.01)
    argo = Bufr2ioda_Converter(bufr2ioda_config, ioda_vars, log_file)

    argo.run()

    if test_file:
        result = argo.test(test_file)
        sys.exit(result)
