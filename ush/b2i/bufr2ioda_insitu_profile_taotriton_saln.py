#!/usr/bin/env python3

import sys
from b2iconverter.util import parse_arguments
from b2iconverter.bufr2ioda_config import Bufr2iodaConfig
from b2iconverter.bufr2ioda_converter import Bufr2ioda_Converter
from b2iconverter.ioda_variables import IODAVariables
from b2iconverter.ioda_metadata import IODAMetadata
from b2iconverter.ioda_addl_vars import IODAAdditionalVariables
from b2iconverter.wmo_codes import *

import numpy as np


platform_description = 'TAO/TRITON Tropical mooring profiles from mbuoyb: salinity'


class TaotritonConfig(Bufr2iodaConfig):
    def ioda_filename(self):
        return f"{self.cycle_type}.t{self.hh}z.insitu_profile_taotriton_saln.{self.cycle_datetime}.nc"


class TaotritonIODAVariables(IODAVariables):
    def __init__(self):
        self.construct()
        self.metadata = IODAMetadata()
        self.additional_vars = TaotritonAdditionalVariables(self)

    def build_query(self):
        q = super().build_query()
        q.add('latitude', '*/CLATH')
        q.add('longitude', '*/CLONH')
        q.add('stationID', '*/RPID')
        q.add('depth', '*/IDMSMDBS/BBYSTSL/DBSS')
        q.add('saln', '*/IDMSMDBS/BBYSTSL/SALN')
        return q

    def set_obs_from_query_result(self, r):
        self.saln = r.get('saln', group_by='depth')

    def filter(self):
        super().filter()
        mask = [True if int(rpid) in TAO_TRITON else False for rpid in self.metadata.stationID]
        mask = mask & self.SalinityFilter()
        self.metadata.filter(mask)
        self.saln = self.saln[mask]

    def write_to_ioda_file(self, obsspace):
        self.metadata.write_to_ioda_file(obsspace)
        self.additional_vars.write_to_ioda_file(obsspace)
        self.write_obs_value_s(obsspace)

    def log_obs(self, logger):
        self.log_salinity(logger)


class TaotritonAdditionalVariables(IODAAdditionalVariables):
    def construct(self):
        n = len(self.ioda_vars.metadata.lon)
        self.PreQC = (np.ma.masked_array(np.full(n, 0))).astype(np.int32)
        self.ObsError_saln = \
            np.float32(np.ma.masked_array(np.full(n, self.ioda_vars.S_error)))
        self.compute_ocean_basin()

    def write_to_ioda_file(self, obsspace):
        self.write_preqc(obsspace, self.ioda_vars.S_name)
        self.write_obs_errorS(obsspace)
        self.write_ocean_basin(obsspace)

    def log(self, logger):
        self.log_preqc(logger)
        self.log_obs_error_saln(logger)
        self.log_ocean_basin(logger)


if __name__ == '__main__':

    script_name, config_file, log_file, test_file = parse_arguments()

    bufr2ioda_config = TaotritonConfig(
        script_name,
        config_file,
        platform_description)

    ioda_vars = TaotritonIODAVariables()
    ioda_vars.set_salinity_var_name("salinity")
    ioda_vars.set_salinity_error(0.01)

    tropical = Bufr2ioda_Converter(bufr2ioda_config, ioda_vars, log_file)

    tropical.run()

    if test_file:
        result = tropical.test(test_file)
        sys.exit(result)
