import numpy as np
from pyiodaconv import bufr
from b2iconverter.ioda_variables import IODAVariables


class ArgoIODAVariables(IODAVariables):
    def __init__(self):
        super().__init__()

    def BuildQuery(self):
        q = super().BuildQuery()
        q.add('stationID', '*/WMOP')
        q.add('latitude', '*/CLATH')
        q.add('longitude', '*/CLONH')
        q.add('depth', '*/GLPFDATA/WPRES')
        q.add('temp', '*/GLPFDATA/SSTH')
        q.add('saln', '*/GLPFDATA/SALNH')
        return q

    def SetFromQueryResult(self, r):
        super().SetFromQueryResult(r)
        # convert depth in pressure units to meters (rho * g * h)
        self.metadata.depth = np.float32(self.metadata.depth.astype(float) * 0.0001)

    def filter(self):
        TS_mask = self.TemperatureFilter() & self.SalinityFilter()
        # Separate ARGO profiles from subpfl tank
        # the index for ARGO floats where the second number of the stationID=9
        id_mask = [True if str(x)[1] == '9' else False for x in self.metadata.stationID]
        mask = TS_mask & id_mask
        self.metadata.filter(mask)
        self.temp = self.temp[mask]
        self.saln = self.saln[mask]
