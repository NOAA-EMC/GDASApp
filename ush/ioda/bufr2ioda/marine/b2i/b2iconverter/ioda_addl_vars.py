import numpy as np
import sys
from .ocean import OceanBasin
from .util import *


class IODAAdditionalVariables:
    def __init__(self, ioda_vars):
        self.ioda_vars = ioda_vars
        self.ocean = OceanBasin()

    def construct(self):
        self.seqNum = compute_seq_num(self.ioda_vars.metadata.lon, self.ioda_vars.metadata.lat)
        n = len(self.seqNum)
        self.PreQC = (np.ma.masked_array(np.full(n, 0))).astype(np.int32)
        self.ObsError_temp = \
            np.float32(np.ma.masked_array(np.full(n, self.ioda_vars.T_error)))
        self.ObsError_saln = \
            np.float32(np.ma.masked_array(np.full(n, self.ioda_vars.S_error)))
        self.compute_ocean_basin()

    def set_ocean_basin_nc_file(self, nc_file_path):
        self.ocean.set_ocean_basin_nc_file(nc_file_path)

    def compute_ocean_basin(self):
        lat = self.ioda_vars.metadata.lat
        lon = self.ioda_vars.metadata.lon
        self.ocean.read_nc_file()
        ob = self.ocean.get_station_basin(lat, lon)
        self.OceanBasin = np.array(ob, dtype=np.int32)

    def set_temperature_error(self, e):
        self.T_error = e

    def set_salinity_error(self, e):
        self.S_error = e

    def write_to_ioda_file(self, obsspace):
        self.write_seq_num(obsspace)
        self.write_preqc(obsspace, self.ioda_vars.T_name)
        self.write_preqc(obsspace, self.ioda_vars.S_name)
        self.write_obs_errorT(obsspace)
        self.write_obs_errorS(obsspace)
        self.write_ocean_basin(obsspace)

    def log(self, logger):
        self.log_seq_num(logger)
        self.log_preqc(logger)
        self.log_obs_error_temp(logger)
        self.log_obs_error_saln(logger)
        self.log_ocean_basin(logger)

#########################################################################

    def write_seq_num(self, obsspace):
        write_seq_num(obsspace, self.seqNum, self.PreQC.dtype, self.PreQC.fill_value)

    # should the long name be "PreQC" + name?
    def write_preqc(self, obsspace, name):
        obsspace.create_var("PreQC/" + name, dtype=self.PreQC.dtype, fillval=self.PreQC.fill_value) \
            .write_attr('long_name', 'PreQC') \
            .write_data(self.PreQC)

    def write_obs_errorT(self, obsspace):
        write_obs_error(obsspace, "ObsError/" + self.ioda_vars.T_name, "degC", self.ObsError_temp)

    def write_obs_errorS(self, obsspace):
        write_obs_error(obsspace, "ObsError/" + self.ioda_vars.S_name, "psu", self.ObsError_saln)

    def write_ocean_basin(self, obsspace):
        write_ocean_basin(obsspace, self.OceanBasin, self.PreQC.dtype, self.PreQC.fill_value)

#########################################################################

    def log_seq_num(self, logger):
        log_variable(logger, "seqNum", self.seqNum)
        logger.debug(f"seqNum hash = {compute_hash(self.seqNum)}")

    def log_preqc(self, logger):
        log_variable(logger, "PreQC", self.PreQC)

    def log_obs_error_temp(self, logger):
        log_variable(logger, "ObsError_temp", self.ObsError_temp)

    def log_obs_error_saln(self, logger):
        log_variable(logger, "ObsError_saln", self.ObsError_saln)

    def log_ocean_basin(self, logger):
        log_variable(logger, "OceanBasin", self.OceanBasin)
        logger.debug(f"OceanBasin hash = {compute_hash(self.OceanBasin)}")

#########################################################################


def compute_seq_num(lon, lat):
    combined = np.stack((lon, lat), axis=-1)
    unique_combined, seqNum = np.unique(combined, axis=0, return_inverse=True)
    seqNum = seqNum.astype(np.int32)
    return seqNum
