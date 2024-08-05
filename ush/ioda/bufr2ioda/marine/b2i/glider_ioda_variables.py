import numpy as np
from pyiodaconv import bufr
from ioda_variables import *
from util import Compute_sequenceNumber


class GliderIODAVariables(IODAVariables):
    def __init__(self):
        super().__init__()


    def BuildQuery(self):
        q = super().BuildQuery()

        q.add('stationID', '*/WMOP')
        q.add('latitude', '*/CLATH')
        q.add('longitude', '*/CLONH')
        q.add('depth', '*/GLPFDATA/WPRES')

        # ObsValue
        q.add('temp', '*/GLPFDATA/SSTH')
        q.add('saln', '*/GLPFDATA/SALNH')

        return q


    def SetFromQueryResult(self, r):
        super().SetFromQueryResult(r)
        # convert depth in pressure units to meters (rho * g * h)
        self.depth = np.float32(self.depth.astype(float) * 0.0001)


    def filter(self):
        mask = self.TemperatureFilter() \
            & self.SalinityFilter()

        self.temp = self.temp[mask]
        self.saln = self.saln[mask]
        self.lat = self.lat[mask]
        self.lon = self.lon[mask]
        self.depth = self.depth[mask]
        self.stationID = self.stationID[mask]
        self.dateTime = self.dateTime[mask]
        self.rcptdateTime = self.rcptdateTime[mask]

        self.seqNum = Compute_sequenceNumber(self.lon)

        # Separate GLIDER profiles from subpfl tank
        # Creating the mask for GLIDER floats based on station ID numbers

        mask_gldr = (self.stationID >= 68900) & (self.stationID <= 68999) | (self.stationID >= 1800000) & (self.stationID <= 1809999) | \
                    (self.stationID >= 2800000) & (self.stationID <= 2809999) | (self.stationID >= 3800000) & (self.stationID <= 3809999) | \
                    (self.stationID >= 4800000) & (self.stationID <= 4809999) | (self.stationID >= 5800000) & (self.stationID <= 5809999) | \
                    (self.stationID >= 6800000) & (self.stationID <= 6809999) | (self.stationID >= 7800000) & (self.stationID <= 7809999)

        # Apply mask
        self.stationID = self.stationID[mask_gldr]
        self.lat = self.lat[mask_gldr]
        self.lon = self.lon[mask_gldr]
        self.depth = self.depth[mask_gldr]
        self.temp = self.temp[mask_gldr]
        self.saln = self.saln[mask_gldr]
        self.seqNum = self.seqNum[mask_gldr]
        self.dateTime = self.dateTime[mask_gldr]
        self.rcptdateTime = self.rcptdateTime[mask_gldr]

        self.n_obs = len(mask_gldr)


    def SetAdditionalData(self):
        self.PreQC = (np.ma.masked_array(np.full((self.n_obs), 0))).astype(np.int32)
        self.ObsError_temp = \
            np.float32(np.ma.masked_array(np.full((self.n_obs), self.errorT)))
        self.ObsError_saln = \
            np.float32(np.ma.masked_array(np.full((self.n_obs), self.errorS)))



    def createIODAVars(self, obsspace):
        super().createIODAVars(obsspace)

        WriteStationID(obsspace, self.stationID)
        WriteDepth(obsspace, self.depth)
        WriteSequenceNumber(obsspace, self.seqNum, self.PreQC)

        self.WritePreQC(obsspace, "waterTemperature")
        self.WritePreQC(obsspace, "salinity")
        WriteObsError(obsspace, 'ObsError/waterTemperature', 'degC', self.ObsError_temp)
        WriteObsError(obsspace, 'ObsError/salinity', 'psu', self.ObsError_saln)
        self.WriteObsValueT(obsspace, 'waterTemperature')
        self.WriteObsValueS(obsspace, 'salinity')
         

