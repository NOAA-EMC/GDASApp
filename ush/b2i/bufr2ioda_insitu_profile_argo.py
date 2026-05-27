#!/usr/bin/env python3

import sys
import numpy as np
import bufr
from b2iconverter.util import parse_arguments
from b2iconverter.bufr2ioda_config import Bufr2iodaConfig
from b2iconverter.bufr2ioda_converter import Bufr2ioda_Converter
from b2iconverter.ioda_variables import IODAVariables


platform_description = 'ARGO profiles from subpfl: temperature and salinity'


class ArgoIODAVariables(IODAVariables):
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
        TS_mask = self.TemperatureFilter() & self.SalinityFilter()
        # Separate ARGO profiles from subpfl tank
        # the index for ARGO floats where the second number of the stationID=9
        id_mask = [True if str(x)[1] == '9' else False for x in self.metadata.stationID]
        mask = TS_mask & id_mask
        self.metadata.filter(mask)
        self.temp = self.temp[mask]
        self.saln = self.saln[mask]


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
