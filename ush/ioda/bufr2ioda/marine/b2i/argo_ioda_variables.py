import numpy as np
from pyiodaconv import bufr
# from ioda_variables import IODAVariables
from ioda_variables import *
from util import Compute_sequenceNumber


class ArgoIODAVariables(IODAVariables):
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
        self.lat = self.lat[mask]
        self.lon = self.lon[mask]
        self.depth = self.depth[mask]
        self.stationID = self.stationID[mask]

        self.seqNum = Compute_sequenceNumber(self.lon)

        # Separate ARGO profiles from subpfl tank
        # Finding index for ARGO floats where the second number of the stationID=9
        index_list = []
        for index, number in enumerate(self.stationID):
            # Convert the number to a string
            number_str = str(number)

            # Check if the second character is equal to '9'
            if number_str[1] == '9':
                index_list.append(index)

        self.n_obs = len(index_list)

        # Apply index
        self.stationID = self.stationID[index_list]
        self.lat = self.lat[index_list]
        self.lon = self.lon[index_list]
        self.depth = self.depth[index_list]
        self.temp = self.temp[index_list]
        self.saln = self.saln[index_list]
        self.seqNum = self.seqNum[index_list]
        self.dateTime = self.dateTime[index_list]
        self.rcptdateTime = self.rcptdateTime[index_list]

    def createIODAVars(self, obsspace):
        super().createIODAVars(obsspace)

        WriteStationID(obsspace, self.stationID)
        WriteDepth(obsspace, self.depth)
        WriteSequenceNumber(obsspace, self.seqNum, self.PreQC)

        self.WritePreQC(obsspace, "waterTemperature")
        self.WritePreQC(obsspace, "salinity")

        WriteObsError(obsspace, "ObsError/waterTemperature", "degC", self.ObsError_temp)
        WriteObsError(obsspace, "ObsError/salinity", "psu", self.ObsError_saln)

        self.WriteObsValueT(obsspace, 'waterTemperature')
        self.WriteObsValueS(obsspace, 'salinity')

