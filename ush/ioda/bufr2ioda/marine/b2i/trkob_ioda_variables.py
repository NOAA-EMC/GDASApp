import numpy as np
from pyiodaconv import bufr
from b2iconverter.ioda_variables import IODAVariables
from b2iconverter.util import Compute_sequenceNumber


class TrkobIODAVariables(IODAVariables):
    def __init__(self):
        super().__init__()

    def BuildQuery(self):
        q = super().BuildQuery()
        q.add('stationID', '*/RPID')
        q.add('latitude', '*/CLAT')
        q.add('longitude', '*/CLON')
        q.add('depth', '*/BTOCN/DBSS')
        # ObsValue
        q.add('temp', '*/BTOCN/STMP')
        q.add('saln', '*/BTOCN/SALN')
        return q

    def filter(self):
        mask = self.TemperatureFilter() \
            & self.SalinityFilter()
        self.n_obs = len(mask)

        self.temp = self.temp[mask]
        self.saln = self.saln[mask]
        self.lat = self.lat[mask]
        self.lon = self.lon[mask]
        self.stationID = self.stationID[mask]
        self.dateTime = self.dateTime[mask]
        self.rcptdateTime = self.rcptdateTime[mask]

    def SetAdditionalData(self):
        self.PreQC = (np.ma.masked_array(np.full((self.n_obs), 0))).astype(np.int32)
        self.ObsError_temp = \
            np.float32(np.ma.masked_array(np.full((self.n_obs), self.T_error)))
        self.ObsError_saln = \
            np.float32(np.ma.masked_array(np.full((self.n_obs), self.S_error)))

    def createIODAVars(self, obsspace):
        self.WriteBasicMetadata(obsspace)

        self.WriteStationID(obsspace)

        self.WritePreQC(obsspace, self.T_name)
        self.WritePreQC(obsspace, self.S_name)
        self.WriteObsErrorT(obsspace)
        self.WriteObsErrorS(obsspace)
        self.WriteObsValueT(obsspace)
        self.WriteObsValueS(obsspace)

    def logMetadata(self, logger):
        self.logDates(logger)
        self.logLonLat(logger)
        self.logStationID(logger)

    def logAdditionalData(self, logger):
        self.LogPreQC(logger)
        self.LogObsError_temp(logger)
        self.LogObsError_saln(logger)
