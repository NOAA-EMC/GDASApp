import numpy as np
from pyiodaconv import bufr
from ioda_variables import *
from util import Compute_sequenceNumber


class BathyIODAVariables(IODAVariables):
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
        return q

    def SetObsFromQueryResult(self, r):
        self.temp = r.get('temp', group_by='depth')
        self.temp -= 273.15

    def filter(self):
        mask = self.TemperatureFilter()
        self.n_obs = len(mask)

        self.lat = self.lat[mask]
        self.lon = self.lon[mask]
        self.depth = self.depth[mask]
        self.stationID = self.stationID[mask]
        self.dateTime = self.dateTime[mask]
        self.rcptdateTime = self.rcptdateTime[mask]
        self.temp = self.temp[mask]

    def SetAdditionalData(self):
        self.seqNum = Compute_sequenceNumber(self.lon)
        self.PreQC = (np.ma.masked_array(np.full((self.n_obs), 0))).astype(np.int32)

        # ObsError -- UNUSED
        # ObsError_temp = np.float32(np.ma.masked_array(np.full((len(temp)), 0.24)))

    def createIODAVars(self, obsspace):
        super().createIODAVars(obsspace)

        WriteStationID(obsspace, self.stationID)
        WriteDepth(obsspace, self.depth)
        WriteSequenceNumber(obsspace, self.seqNum, self.PreQC)

        self.WritePreQC(obsspace, "waterTemperature")
        self.WriteObsValueT(obsspace, "waterTemperature")

    def logObs(self, logger):
        self.logTemperature(logger)

    def logAdditionalData(self, logger):
        self.LogSeqNum(logger)
        self.LogPreQC(logger)
