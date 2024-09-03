import numpy as np
from pyiodaconv import bufr
from b2iconverter.ioda_variables import IODAVariables
from b2iconverter.ioda_addl_vars import IODAAdditionalVariables, ComputeSeqNum


class BathyIODAVariables(IODAVariables):
    def __init__(self):
        self.construct()
        self.additional_vars = BathyAdditionalVariables(self)

    def BuildQuery(self):
        q = super().BuildQuery()
        q.add('stationID', '*/RPID')
        q.add('latitude', '*/CLAT')
        q.add('longitude', '*/CLON')
        q.add('depth', '*/BTOCN/DBSS')
        q.add('temp', '*/BTOCN/STMP')
        return q

    def SetObsFromQueryResult(self, r):
        self.temp = r.get('temp', group_by='depth')
        self.temp -= 273.15

    def filter(self):
        mask = self.TemperatureFilter()
        self.metadata.filter(mask)
        self.temp = self.temp[mask]

    def WriteToIodaFile(self, obsspace):
        self.metadata.WriteToIodaFile(obsspace)
        self.additional_vars.WriteToIodaFile(obsspace)
        self.WriteObsValueT(obsspace)

    def logObs(self, logger):
        self.logTemperature(logger)


class BathyAdditionalVariables(IODAAdditionalVariables):

    def construct(self):
        self.seqNum = ComputeSeqNum(self.ioda_vars.metadata.lon, self.ioda_vars.metadata.lat)
        n = len(self.seqNum)
        self.PreQC = (np.ma.masked_array(np.full(n, 0))).astype(np.int32)
        self.ObsError_temp = \
            np.float32(np.ma.masked_array(np.full(n, self.ioda_vars.T_error)))
        self.ComputeOceanBasin()

    def WriteToIodaFile(self, obsspace):
        self.WriteSeqNum(obsspace)
        self.WritePreQC(obsspace, self.ioda_vars.T_name)
        self.WriteObsErrorT(obsspace)
        self.WriteOceanBasin(obsspace)

    def log(self, logger):
        self.logSeqNum(logger)
        self.logPreQC(logger)
        self.logObsError_temp(logger)
        self.logOceanBasin(logger)
