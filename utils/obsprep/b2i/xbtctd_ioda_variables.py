import numpy as np
import bufr
from b2iconverter.ioda_variables import IODAVariables


class XbtctdIODAVariables(IODAVariables):
    def __init__(self):
        super().__init__()

    def build_query(self):
        q = super().build_query()
        q.add('stationID', '*/WMOP')
        q.add('latitude', '*/CLATH')
        q.add('longitude', '*/CLONH')
        q.add('depth', '*/TMSLPFSQ/DBSS')
        q.add('temp', '*/TMSLPFSQ/SST1')
        q.add('saln', '*/TMSLPFSQ/SALNH')
        return q

    def filter(self):
        super().filter()
        mask = self.TemperatureFilter() \
            & self.SalinityFilter()
        self.temp = self.temp[mask]
        self.saln = self.saln[mask]
        self.metadata.filter(mask)
