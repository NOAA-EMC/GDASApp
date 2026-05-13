import numpy as np
import bufr
from b2iconverter.ioda_variables import IODAVariables


class GliderIODAVariables(IODAVariables):
    def __init__(self):
        super().__init__()

    def build_query(self):
        q = super().build_query()
        q.add('stationID', '*/WMOP')
        q.add('latitude', '*/CLATH')
        q.add('longitude', '*/CLONH')
        q.add('depth', '*/GLPFDATA/WPRES')
        q.add('temp', '*/GLPFDATA/SSTH')
        q.add('saln', '*/GLPFDATA/SALNH')
        return q

    def set_from_query_result(self, r):
        super().set_from_query_result(r)
        # convert depth in pressure units to meters (rho * g * h)
        self.metadata.depth = np.float32(self.metadata.depth.astype(float) * 0.0001)

    def filter(self):
        super().filter()
        # Separate GLIDER profiles from subpfl tank
        id = self.metadata.stationID
        id_mask = (id >= 68900) & (id <= 68999) | \
            (id >= 1800000) & (id <= 1809999) | \
            (id >= 2800000) & (id <= 2809999) | \
            (id >= 3800000) & (id <= 3809999) | \
            (id >= 4800000) & (id <= 4809999) | \
            (id >= 5800000) & (id <= 5809999) | \
            (id >= 6800000) & (id <= 6809999) | \
            (id >= 7800000) & (id <= 7809999)
        mask = self.TemperatureFilter() \
            & self.SalinityFilter() \
            & id_mask
        self.metadata.filter(mask)
        self.temp = self.temp[mask]
        self.saln = self.saln[mask]
