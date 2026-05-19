import numpy as np
import bufr
from b2iconverter.ioda_variables import IODAVariables
from b2iconverter.ioda_addl_vars import IODAAdditionalVariables, compute_seq_num


class BathyIODAVariables(IODAVariables):
    def __init__(self):
        self.construct()
        self.additional_vars = BathyAdditionalVariables(self)

    def build_query(self):
        q = super().build_query()
        q.add('stationID', '*/RPID')
        q.add('latitude', '*/CLAT')
        q.add('longitude', '*/CLON')
        q.add('depth', '*/BTOCN/DBSS')
        q.add('temp', '*/BTOCN/STMP')
        return q

    def set_obs_from_query_result(self, r):
        self.temp = r.get('temp', group_by='depth')
        self.temp -= 273.15

    def filter(self):
        super().filter()
        mask = self.TemperatureFilter()
        self.metadata.filter(mask)
        self.temp = self.temp[mask]

    def write_to_ioda_file(self, obsspace):
        self.metadata.write_to_ioda_file(obsspace)
        self.additional_vars.write_to_ioda_file(obsspace)
        self.write_obs_value_t(obsspace)

    def log_obs(self, logger):
        self.log_temperature(logger)


class BathyAdditionalVariables(IODAAdditionalVariables):

    def construct(self):
        self.seqNum = compute_seq_num(self.ioda_vars.metadata.lon, self.ioda_vars.metadata.lat)
        n = len(self.seqNum)
        self.PreQC = (np.ma.masked_array(np.full(n, 0))).astype(np.int32)
        self.ObsError_temp = \
            np.float32(np.ma.masked_array(np.full(n, self.ioda_vars.T_error)))
        self.compute_ocean_basin()

    def write_to_ioda_file(self, obsspace):
        self.write_seq_num(obsspace)
        self.write_preqc(obsspace, self.ioda_vars.T_name)
        self.write_obs_errorT(obsspace)
        self.write_ocean_basin(obsspace)

    def log(self, logger):
        self.log_seq_num(logger)
        self.log_preqc(logger)
        self.log_obs_error_temp(logger)
        self.log_ocean_basin(logger)
