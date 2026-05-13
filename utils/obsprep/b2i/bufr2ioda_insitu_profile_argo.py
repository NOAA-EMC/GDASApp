#!/usr/bin/env python3

import sys
from b2iconverter.util import parse_arguments
from b2iconverter.bufr2ioda_config import Bufr2iodaConfig
from b2iconverter.bufr2ioda_converter import Bufr2ioda_Converter
from argo_ioda_variables import ArgoIODAVariables


platform_description = 'ARGO profiles from subpfl: temperature and salinity'


class ArgoConfig(Bufr2iodaConfig):
    def ioda_filename(self):
        return f"{self.cycle_type}.t{self.hh}z.insitu_profile_argo.{self.cycle_datetime}.nc"


if __name__ == '__main__':

    script_name, config_file, log_file, test_file = parse_arguments()

    bufr2ioda_config = ArgoConfig(
        script_name,
        config_file,
        platform_description)

    ioda_vars = ArgoIODAVariables()
    ioda_vars.set_temperature_var_name("waterTemperature")
    ioda_vars.set_temperature_error(0.02)
    ioda_vars.set_salinity_var_name("salinity")
    ioda_vars.set_salinity_error(0.01)

    argo = Bufr2ioda_Converter(bufr2ioda_config, ioda_vars, log_file)

    argo.run()

    if test_file:
        result = argo.test(test_file)
        sys.exit(result)
