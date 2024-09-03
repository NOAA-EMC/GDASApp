import numpy as np
from pyiodaconv import bufr
from b2iconverter.ioda_variables import IODAVariables
from b2iconverter.ioda_addl_vars import IODAAdditionalVariables
from b2iconverter.ioda_metadata import IODAMetadata
from b2iconverter.util import WriteDateTime, WriteRcptDateTime, WriteLongitude, WriteLatitude, WriteStationID


class TrkobIODAVariables(IODAVariables):
    def __init__(self):
        self.construct()
        self.metadata = TrkobMetadata()
        self.additional_vars = TrkobAdditionalVariables(self)

    def BuildQuery(self):
        q = super().BuildQuery()
        q.add('stationID', '*/RPID')
        q.add('latitude', '*/CLAT')
        q.add('longitude', '*/CLON')
        q.add('depth', '*/BTOCN/DBSS')
        q.add('temp', '*/BTOCN/STMP')
        q.add('saln', '*/BTOCN/SALN')
        return q

    def filter(self):
        mask = self.TemperatureFilter() \
            & self.SalinityFilter()
        self.temp = self.temp[mask]
        self.saln = self.saln[mask]
        self.metadata.filter(mask)


class TrkobMetadata(IODAMetadata):

    def SetFromQueryResult(self, r):
        self.SetDateTimeFromQueryResult(r)
        self.SetRcptDateTimeFromQueryResult(r)
        self.SetLonFromQueryResult(r)
        self.SetLatFromQueryResult(r)
        self.SetStationIDFromQueryResult(r)

    def filter(self, mask):
        self.dateTime = self.dateTime[mask]
        self.rcptdateTime = self.rcptdateTime[mask]
        self.lat = self.lat[mask]
        self.lon = self.lon[mask]
        self.stationID = self.stationID[mask]

    def WriteToIodaFile(self, obsspace):
        WriteDateTime(obsspace, self.dateTime)
        WriteRcptDateTime(obsspace, self.rcptdateTime)
        WriteLongitude(obsspace, self.lon)
        WriteLatitude(obsspace, self.lat)
        WriteStationID(obsspace, self.stationID)

    def log(self, logger):
        self.logDateTime(logger)
        self.logRcptDateTime(logger)
        # self.logLonLat(logger)
        self.logLongitude(logger)
        self.logLatitude(logger)
        self.logStationID(logger)


class TrkobAdditionalVariables(IODAAdditionalVariables):

    def construct(self):
        n = len(self.ioda_vars.temp)
        self.PreQC = (np.ma.masked_array(np.full(n, 0))).astype(np.int32)
        self.ObsError_temp = \
            np.float32(np.ma.masked_array(np.full(n, self.ioda_vars.T_error)))
        self.ObsError_saln = \
            np.float32(np.ma.masked_array(np.full(n, self.ioda_vars.S_error)))
        self.ComputeOceanBasin()

    def WriteToIodaFile(self, obsspace):
        self.WritePreQC(obsspace, self.ioda_vars.T_name)
        self.WritePreQC(obsspace, self.ioda_vars.S_name)
        self.WriteObsErrorT(obsspace)
        self.WriteObsErrorS(obsspace)
        self.WriteOceanBasin(obsspace)

    def log(self, logger):
        self.logPreQC(logger)
        self.logObsError_temp(logger)
        self.logObsError_saln(logger)
        self.logOceanBasin(logger)
