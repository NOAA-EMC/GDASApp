#!/usr/bin/env python3

import sys
from b2iconverter.util import ParseArguments
from b2iconverter.bufr2ioda_config import Bufr2iodaConfig
from b2iconverter.bufr2ioda_converter import Bufr2ioda_Converter
from xbtctd_ioda_variables import XbtctdIODAVariables


platform_description = 'Profiles from XBT/CTD: temperature and salinity'

ocean_basin_nc_file_path = "/scratch2/NCEPDEV/ocean/Guillaume.Vernieres/data/static/common/RECCAP2_region_masks_all_v20221025.nc"


if __name__ == '__main__':

    script_name, config_file, log_file, test_file = ParseArguments()

    bufr2ioda_config = Bufr2iodaConfig(
        script_name,
        config_file,
        platform_description)

    ioda_vars = XbtctdIODAVariables()
    ioda_vars.SetTemperatureVarName("waterTemperature")
    ioda_vars.SetTemperatureError(0.12)
    ioda_vars.SetSalinityVarName("salinity")
    ioda_vars.SetSalinityError(1.0)
    ioda_vars.SetOceanBasinNCFilePath(ocean_basin_nc_file_path)

    xbtctd = Bufr2ioda_Converter(bufr2ioda_config, ioda_vars, log_file)
    xbtctd.run()

    if test_file:
        result = xbtctd.test(test_file)
        sys.exit(result)
