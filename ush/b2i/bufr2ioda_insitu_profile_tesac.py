#!/usr/bin/env python3

import sys
import bufr
from b2iconverter.util import parse_arguments
from b2iconverter.bufr2ioda_config import Bufr2iodaConfig
from b2iconverter.bufr2ioda_converter import Bufr2ioda_Converter
from b2iconverter.ioda_variables import IODAVariables


platform_description = 'Profiles from TESAC: temperature and salinity'


class TesacIODAVariables(IODAVariables):
    def __init__(self):
        super().__init__()

    def build_query(self):
        q = super().build_query()
        q.add('stationID', '*/RPID')
        q.add('latitude', '*/CLAT')
        q.add('longitude', '*/CLON')
        q.add('depth', '*/BTOCN/DBSS')
        q.add('temp', '*/BTOCN/STMP')
        q.add('saln', '*/BTOCN/SALN')
        return q

    def filter(self):
        super().filter()
        # Separate TESAC profiles tesac tank
        id_mask = [True if id.isdigit() and id != 0 else False for id in self.metadata.stationID]
        mask = id_mask \
            & self.TemperatureFilter() \
            & self.SalinityFilter()
        self.metadata.filter(mask)
        self.temp = self.temp[mask]
        self.saln = self.saln[mask]


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
