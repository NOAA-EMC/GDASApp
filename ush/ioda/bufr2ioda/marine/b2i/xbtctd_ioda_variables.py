import numpy as np
from pyiodaconv import bufr
from b2iconverter.ioda_variables import IODAVariables


class XbtctdIODAVariables(IODAVariables):
    def __init__(self):
        super().__init__()

    def BuildQuery(self):
        q = super().BuildQuery()
        q.add('stationID', '*/WMOP')
        q.add('latitude', '*/CLATH')
        q.add('longitude', '*/CLONH')
        q.add('depth', '*/TMSLPFSQ/DBSS')
        q.add('temp', '*/TMSLPFSQ/SST1')
        q.add('saln', '*/TMSLPFSQ/SALNH')
        return q

    def filter(self):
        mask = self.TemperatureFilter() \
            & self.SalinityFilter()
        self.temp = self.temp[mask]
        self.saln = self.saln[mask]
        self.metadata.filter(mask)
