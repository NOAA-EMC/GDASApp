#!/usr/bin/env python3

import sys
from b2iconverter.util import parse_arguments
from b2iconverter.bufr2ioda_config import Bufr2iodaConfig
from b2iconverter.bufr2ioda_converter import Bufr2ioda_Converter
from trkob_ioda_variables import TrkobIODAVariables


platform_description = 'Surface obs from TRACKOB: temperature and salinity'


class TrkobConfig(Bufr2iodaConfig):
    def ioda_filename(self):
        return f"{self.cycle_type}.t{self.hh}z.insitu_surface_{self.data_format}.{self.cycle_datetime}.nc4"


if __name__ == '__main__':

    script_name, config_file, log_file, test_file = parse_arguments()

    bufr2ioda_config = TrkobConfig(
        script_name,
        config_file,
        platform_description)

    ioda_vars = TrkobIODAVariables()
    ioda_vars.set_temperature_var_name("seaSurfaceTemperature")
    ioda_vars.set_temperature_error(0.3)
    ioda_vars.set_salinity_var_name("seaSurfaceSalinity")
    ioda_vars.set_salinity_error(1.0)

    trkob = Bufr2ioda_Converter(bufr2ioda_config, ioda_vars, log_file)
    trkob.run()

    if test_file:
        result = trkob.test(test_file)
        sys.exit(result)
