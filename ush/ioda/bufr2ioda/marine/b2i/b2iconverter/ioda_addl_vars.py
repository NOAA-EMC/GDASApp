import numpy as np
import sys
from .ocean import OceanBasin
from .util import *


class IODAAdditionalVariables:
    def __init__(self, ioda_vars):
        self.ioda_vars = ioda_vars
        self.ocean = OceanBasin()

    def construct(self):
        self.seqNum = ComputeSeqNum(self.ioda_vars.metadata.lon,
                                    self.ioda_vars.metadata.lat)
        n = len(self.seqNum)
        self.PreQC = (np.ma.masked_array(np.full(n, 0))).astype(np.int32)
        self.ObsError_temp = \
            np.float32(np.ma.masked_array(np.full(n, self.ioda_vars.T_error)))
        self.ObsError_saln = \
            np.float32(np.ma.masked_array(np.full(n, self.ioda_vars.S_error)))
        self.ComputeOceanBasin()

    def SetOceanBasinNCFilePath(self, nc_file_path):
        self.ocean.SetOceanBasinNCFilePath(nc_file_path)

    def ComputeOceanBasin(self):
        lat = self.ioda_vars.metadata.lat
        lon = self.ioda_vars.metadata.lon
        self.ocean.ReadNCFile()
        ob = self.ocean.GetStationBasin(lat, lon)
        self.OceanBasin = np.array(ob, dtype=np.int32)

    def SetTemperatureError(self, e):
        self.T_error = e

    def SetSalinityError(self, e):
        self.S_error = e

    def WriteToIodaFile(self, obsspace):
        self.WriteSeqNum(obsspace)
        self.WritePreQC(obsspace, self.ioda_vars.T_name)
        self.WritePreQC(obsspace, self.ioda_vars.S_name)
        self.WriteObsErrorT(obsspace)
        self.WriteObsErrorS(obsspace)
        self.WriteOceanBasin(obsspace)

    def log(self, logger):
        self.logSeqNum(logger)
        self.logPreQC(logger)
        self.logObsError_temp(logger)
        self.logObsError_saln(logger)
        self.logOceanBasin(logger)

#########################################################################

    def WriteSeqNum(self, obsspace):
        WriteSeqNum(obsspace, self.seqNum, self.PreQC.dtype, self.PreQC.fill_value)

    # should the long name be "PreQC" + name?
    def WritePreQC(self, obsspace, name):
        obsspace.create_var("PreQC/" + name, dtype=self.PreQC.dtype, fillval=self.PreQC.fill_value) \
            .write_attr('long_name', 'PreQC') \
            .write_data(self.PreQC)

    def WriteObsErrorT(self, obsspace):
        WriteObsError(obsspace, "ObsError/" + self.ioda_vars.T_name, "degC", self.ObsError_temp)

    def WriteObsErrorS(self, obsspace):
        WriteObsError(obsspace, "ObsError/" + self.ioda_vars.S_name, "psu", self.ObsError_saln)

    def WriteOceanBasin(self, obsspace):
        WriteOceanBasin(obsspace, self.OceanBasin, self.PreQC.dtype, self.PreQC.fill_value)

#########################################################################

    def logSeqNum(self, logger):
        LogVariable(logger, "seqNum", self.seqNum)
        logger.debug(f"seqNum hash = {compute_hash(self.seqNum)}")

    def logPreQC(self, logger):
        LogVariable(logger, "PreQC", self.PreQC)

    def logObsError_temp(self, logger):
        LogVariable(logger, "ObsError_temp", self.ObsError_temp)

    def logObsError_saln(self, logger):
        LogVariable(logger, "ObsError_saln", self.ObsError_saln)

    def logOceanBasin(self, logger):
        LogVariable(logger, "OceanBasin", self.OceanBasin)
        logger.debug(f"OceanBasin hash = {compute_hash(self.OceanBasin)}")

#########################################################################


# seqNum depends both on lat and lon
def ComputeSeqNum(lon, lat):
    combined = np.stack((lon, lat), axis=-1)
    unique_combined, seqNum = np.unique(combined, axis=0, return_inverse=True)
    seqNum = seqNum.astype(np.int32)
    return seqNum
