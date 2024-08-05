import numpy as np
from pyiodaconv import bufr
# from ioda_variables import IODAVariables
from ioda_variables import *
from util import Compute_sequenceNumber


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
            np.float32(np.ma.masked_array(np.full((self.n_obs), self.errorT)))
        self.ObsError_saln = \
            np.float32(np.ma.masked_array(np.full((self.n_obs), self.errorS)))



    def createIODAVars(self, obsspace):
        super().createIODAVars(obsspace)

        WriteStationID(obsspace, self.stationID)

        self.WritePreQC(obsspace, "seaSurfaceTemperature")
        self.WritePreQC(obsspace, "seaSurfaceSalinity")

        WriteObsError(obsspace, "ObsError/seaSurfaceTemperature", "degC", self.ObsError_temp)  
        WriteObsError(obsspace, "ObsError/seaSurfaceSalinity", "psu", self.ObsError_saln)  

        self.WriteObsValueT(obsspace, 'seaSurfaceTemperature')
        self.WriteObsValueS(obsspace, 'seaSurfaceSalinity')


    def logMetadata(self, logger):
        self.logDates(logger)
        self.logLonLat(logger)
        self.logStationID(logger)

    def logAdditionalData(self, logger):
        self.LogPreQC(logger)
        self.LogObsError_temp(logger)
        self.LogObsError_saln(logger)

