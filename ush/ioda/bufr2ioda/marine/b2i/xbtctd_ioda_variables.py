import numpy as np
from pyiodaconv import bufr
from b2iconverter.ioda_variables import IODAVariables
from b2iconverter.util import Compute_sequenceNumber


class XbtctdIODAVariables(IODAVariables):
    def __init__(self):
        super().__init__()

    def BuildQuery(self):
        q = super().BuildQuery()
        q.add('stationID', '*/WMOP')
        q.add('latitude', '*/CLATH')
        q.add('longitude', '*/CLONH')
        q.add('depth', '*/TMSLPFSQ/DBSS')
        # ObsValue
        q.add('temp', '*/TMSLPFSQ/SST1')
        q.add('saln', '*/TMSLPFSQ/SALNH')
        return q

    def filter(self):
        mask = self.TemperatureFilter() \
            & self.SalinityFilter()
        self.n_obs = len(mask)

        self.temp = self.temp[mask]
        self.saln = self.saln[mask]
        self.lat = self.lat[mask]
        self.lon = self.lon[mask]
        self.depth = self.depth[mask]
        self.stationID = self.stationID[mask]
        self.dateTime = self.dateTime[mask]
        self.rcptdateTime = self.rcptdateTime[mask]
