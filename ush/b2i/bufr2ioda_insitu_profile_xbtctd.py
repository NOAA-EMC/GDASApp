#!/usr/bin/env python3

import sys
import numpy as np
import bufr
from b2iconverter.util import parse_arguments
from b2iconverter.bufr2ioda_config import Bufr2iodaConfig
from b2iconverter.bufr2ioda_converter import Bufr2ioda_Converter
from b2iconverter.ioda_variables import IODAVariables


platform_description = 'Profiles from XBT/CTD: temperature and salinity'


class XbtctdIODAVariables(IODAVariables):
    def __init__(self):
        super().__init__()

    def build_query(self):
        q = super().build_query()
        q.add('stationID', '*/WMOP')
        q.add('latitude', '*/CLATH')
        q.add('longitude', '*/CLONH')
        q.add('depth', '*/TMSLPFSQ/DBSS')
        q.add('temp', '*/TMSLPFSQ/SST1')
        q.add('saln', '*/TMSLPFSQ/SALNH')
        return q

    def filter(self):
        super().filter()
        mask = self.TemperatureFilter() \
            & self.SalinityFilter()
        self.temp = self.temp[mask]
        self.saln = self.saln[mask]
        self.metadata.filter(mask)


if __name__ == '__main__':

    script_name, config_file, log_file, test_file = parse_arguments()

    bufr2ioda_config = Bufr2iodaConfig(
        script_name,
        config_file,
        platform_description)

    ioda_vars = XbtctdIODAVariables()
    ioda_vars.set_temperature_var_name("waterTemperature")
    ioda_vars.set_temperature_error(0.12)
    ioda_vars.set_salinity_var_name("salinity")
    ioda_vars.set_salinity_error(1.0)

    xbtctd = Bufr2ioda_Converter(bufr2ioda_config, ioda_vars, log_file)
    xbtctd.run()

    if test_file:
        result = xbtctd.test(test_file)
        sys.exit(result)
