#!/usr/bin/env python3

import sys
from b2iconverter.util import parse_arguments
from b2iconverter.bufr2ioda_config import Bufr2iodaConfig
from b2iconverter.bufr2ioda_converter import Bufr2ioda_Converter
from mbuoyb_tropical_ioda_variables import MbuoybTropicalIODAVariables
from wmo_codes import *


platform_description = 'RAMA Tropical mooring profiles from mbuoyb: temperature and salinity'


class RamaConfig(Bufr2iodaConfig):
    def ioda_filename(self):
        return f"{self.cycle_type}.t{self.hh}z.insitu_profile_rama.{self.cycle_datetime}.nc"


class RamaIODAVariables(MbuoybTropicalIODAVariables):
    def filter(self):
        super().filter()
        mask = is_rama(self.metadata.stationID)
        self.metadata.filter(mask)
        self.temp = self.temp[mask]
        self.saln = self.saln[mask]


if __name__ == '__main__':

    script_name, config_file, log_file, test_file = parse_arguments()

    bufr2ioda_config = RamaConfig(
        script_name,
        config_file,
        platform_description)

    ioda_vars = RamaIODAVariables()
    ioda_vars.set_temperature_var_name("waterTemperature")
    ioda_vars.set_temperature_error(0.02)
    ioda_vars.set_salinity_var_name("salinity")
    ioda_vars.set_salinity_error(0.01)

    tropical = Bufr2ioda_Converter(bufr2ioda_config, ioda_vars, log_file)

    tropical.run()

    if test_file:
        result = tropical.test(test_file)
        sys.exit(result)
