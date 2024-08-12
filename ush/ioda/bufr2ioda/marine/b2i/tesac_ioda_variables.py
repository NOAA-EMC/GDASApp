import numpy as np
from pyiodaconv import bufr
from b2iconverter.ioda_variables import IODAVariables
from b2iconverter.util import Compute_sequenceNumber


class TesacIODAVariables(IODAVariables):
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

        self.seqNum = Compute_sequenceNumber(self.lon)

        # Separate TESAC profiles tesac tank
        # Creating the mask for TESAC floats based on station ID
        digit_mask = [item.isdigit() for item in self.stationID]
        indices_true = [index for index, value in enumerate(digit_mask) if value]

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

        self.n_obs = len(indices_true)

    def SetAdditionalData(self):
        self.PreQC = (np.ma.masked_array(np.full((self.n_obs), 0))).astype(np.int32)
        self.ObsError_temp = \
            np.float32(np.ma.masked_array(np.full((self.n_obs), self.T_error)))
        self.ObsError_saln = \
            np.float32(np.ma.masked_array(np.full((self.n_obs), self.S_error)))
