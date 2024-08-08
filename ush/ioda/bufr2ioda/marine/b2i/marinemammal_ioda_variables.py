import numpy as np
from pyiodaconv import bufr
from b2iconverter.ioda_variables import IODAVariables
from b2iconverter.util import Compute_sequenceNumber


class MarinemammalIODAVariables(IODAVariables):
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

        self.temp = self.temp[mask]
        self.saln = self.saln[mask]
        self.lat = self.lat[mask]
        self.lon = self.lon[mask]
        self.depth = self.depth[mask]
        self.stationID = self.stationID[mask]
        self.dateTime = self.dateTime[mask]
        self.rcptdateTime = self.rcptdateTime[mask]

        # Separate marine mammals from TESAC tank
        # Creating the mask for marine mammals from TESAC floats based on station ID

        alpha_mask = [item.isalpha() for item in self.stationID]
        indices_true = [index for index, value in enumerate(alpha_mask) if value]

        self.n_obs = len(indices_true)

        # Apply index
        self.stationID = self.stationID[indices_true]
        self.lat = self.lat[indices_true]
        self.lon = self.lon[indices_true]
        self.depth = self.depth[indices_true]
        self.temp = self.temp[indices_true]
        self.saln = self.saln[indices_true]
        self.seqNum = self.seqNum[indices_true]
        self.dateTime = self.dateTime[indices_true]
        self.rcptdateTime = self.rcptdateTime[indices_true]

    def createIODAVars(self, obsspace):
        super().createIODAVars(obsspace)
        self.WriteStationID(obsspace)
        self.WriteDepth(obsspace)
        self.WriteSequenceNumber(obsspace)

        self.WritePreQC(obsspace, "waterTemperature")
        self.WritePreQC(obsspace, "salinity")
        self.WriteObsErrorT(obsspace, "waterTemperature")
        self.WriteObsErrorS(obsspace, "salinity")
        self.WriteObsValueT(obsspace, 'waterTemperature')
        self.WriteObsValueS(obsspace, 'salinity')
