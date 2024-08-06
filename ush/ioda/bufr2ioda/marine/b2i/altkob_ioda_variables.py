import numpy as np
from pyiodaconv import bufr
from ioda_variables import *
from util import Compute_sequenceNumber


class AltkobIODAVariables(IODAVariables):
    def __init__(self):
        super().__init__()

    def BuildQuery(self):
        q = super().BuildQuery()
        q.add('latitude', '*/CLATH')
        q.add('longitude', '*/CLONH')
        # ObsValue
        q.add('temp', '*/SST0')
        q.add('saln', '*/SSS0')
        return q

    def SetFromQueryResult(self, r):
        self.SetDatesFromQueryResult(r)
        self.SetLonLatFromQueryResult(r)
        self.SetObsFromQueryResult(r)

    def filter(self):
        mask = self.TemperatureFilter() \
            & SalinityFilter()
        n_obs = len(mask)

        self.lat = self.lat[mask]
        self.lon = self.lon[mask]
        self.dateTime = self.dateTime[mask]
        self.rcptdateTime = self.rcptdateTime[mask]
        self.temp = self.temp[mask]
        self.saln = self.saln[mask]

    def SetAdditionalData(self):
        self.PreQC = (np.ma.masked_array(np.full((self.n_obs), 0))).astype(np.int32)
        self.ObsError_temp = \
            np.float32(np.ma.masked_array(np.full((self.n_obs), self.ErrorT)))
        self.ObsError_saln = \
            np.float32(np.ma.masked_array(np.full((self.n_obs), self.ErrorS)))

    def createIODAVars(self, obsspace):
        super().createIODAVars(obsspace)

        # BUG: StationID is undefined
        WriteStationID(obsspace, self.stationID)

        self.WritePreQC(obsspace, "seaSurfaceTemperature")
        self.WritePreQC(obsspace, "seaSurfaceSalinity")

        WriteObsError(obsspace, "ObsError/seaSurfaceTemperature", "degC", self.ObsError_temp)
        WriteObsError(obsspace, "ObsError/seaSurfaceSalinity", "psu", self.ObsError_saln)

        self.WriteObsValueT(obsspace, 'waterTemperature')
        self.WriteObsValueS(obsspace, 'salinity')