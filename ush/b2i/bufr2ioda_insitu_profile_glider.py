#!/usr/bin/env python3

import sys
import numpy as np
import bufr
from b2iconverter.util import parse_arguments
from b2iconverter.bufr2ioda_config import Bufr2iodaConfig
from b2iconverter.bufr2ioda_converter import Bufr2ioda_Converter
from b2iconverter.ioda_variables import IODAVariables


platform_description = 'GLIDER profiles from subpfl: temperature and salinity'


class GliderIODAVariables(IODAVariables):
    def __init__(self):
        super().__init__()

    def build_query(self):
        q = super().build_query()
        q.add('stationID', '*/WMOP')
        q.add('latitude', '*/CLATH')
        q.add('longitude', '*/CLONH')
        q.add('depth', '*/GLPFDATA/WPRES')
        q.add('temp', '*/GLPFDATA/SSTH')
        q.add('saln', '*/GLPFDATA/SALNH')
        return q

    def set_from_query_result(self, r):
        super().set_from_query_result(r)
        # convert depth in pressure units to meters (rho * g * h)
        self.metadata.depth = np.float32(self.metadata.depth.astype(float) * 0.0001)

    def filter(self):
        super().filter()
        # Separate GLIDER profiles from subpfl tank
        id = self.metadata.stationID
        id_mask = (id >= 68900) & (id <= 68999) | \
            (id >= 1800000) & (id <= 1809999) | \
            (id >= 2800000) & (id <= 2809999) | \
            (id >= 3800000) & (id <= 3809999) | \
            (id >= 4800000) & (id <= 4809999) | \
            (id >= 5800000) & (id <= 5809999) | \
            (id >= 6800000) & (id <= 6809999) | \
            (id >= 7800000) & (id <= 7809999)
        mask = self.TemperatureFilter() \
            & self.SalinityFilter() \
            & id_mask
        self.metadata.filter(mask)
        self.temp = self.temp[mask]
        self.saln = self.saln[mask]


class GliderConfig(Bufr2iodaConfig):
    def ioda_filename(self):
        return f"{self.cycle_type}.t{self.hh}z.insitu_profile_glider.{self.cycle_datetime}.nc"


if __name__ == '__main__':

    script_name, config_file, log_file, test_file = parse_arguments()

    bufr2ioda_config = GliderConfig(
        script_name,
        config_file,
        platform_description)

    ioda_vars = GliderIODAVariables()
    ioda_vars.set_temperature_var_name("waterTemperature")
    ioda_vars.set_temperature_error(0.02)
    ioda_vars.set_salinity_var_name("salinity")
    ioda_vars.set_salinity_error(0.01)

    glider = Bufr2ioda_Converter(bufr2ioda_config, ioda_vars, log_file)
    glider.run()

    if test_file:
        result = glider.test(test_file)
        sys.exit(result)
