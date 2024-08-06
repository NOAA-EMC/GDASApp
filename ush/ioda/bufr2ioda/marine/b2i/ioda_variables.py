import numpy as np
from pyiodaconv import bufr
from util import Compute_sequenceNumber


class IODAVariables:
    def __init__(self):
        self.n_obs = 0
        self.errorT = 0.0
        self.errorS = 0.0
        self.SetTemperatureRange(-10.0, 50.0)
        self.SetSalinityRange(0.0, 45.0)

    def SetTemperatureError(self, e):
        self.errorT = e

    def SetSalinityError(self, e):
        self.errorS = e

    def SetTemperatureRange(self, tmin, tmax):
        self.Tmin = tmin
        self.Tmax = tmax

    def SetSalinityRange(self, smin, smax):
        self.Smin = smin
        self.Smax = smax

    def BuildQuery(self):
        q = bufr.QuerySet()
        q.add('year', '*/YEAR')
        q.add('month', '*/MNTH')
        q.add('day', '*/DAYS')
        q.add('hour', '*/HOUR')
        q.add('minute', '*/MINU')
        q.add('ryear', '*/RCYR')
        q.add('rmonth', '*/RCMO')
        q.add('rday', '*/RCDY')
        q.add('rhour', '*/RCHR')
        q.add('rminute', '*/RCMI')
        return q

    def SetDatesFromQueryResult(self, r):
        self.dateTime = r.get_datetime('year', 'month', 'day', 'hour', 'minute', group_by='depth')
        self.dateTime = self.dateTime.astype(np.int64)

        self.rcptdateTime = r.get_datetime('ryear', 'rmonth', 'rday', 'rhour', 'rminute', group_by='depth')
        self.rcptdateTime = self.rcptdateTime.astype(np.int64)

    def SetLonLatFromQueryResult(self, r):
        self.lat = r.get('latitude', group_by='depth')
        self.lon = r.get('longitude', group_by='depth')

    def SetObsFromQueryResult(self, r):
        self.temp = r.get('temp', group_by='depth')
        self.temp -= 273.15
        self.saln = r.get('saln', group_by='depth')

    def SetFromQueryResult(self, r):
        self.SetDatesFromQueryResult(r)
        self.SetLonLatFromQueryResult(r)
        self.stationID = r.get('stationID', group_by='depth')
        self.depth = r.get('depth', group_by='depth')
        self.SetObsFromQueryResult(r)

    def TemperatureFilter(self):
        return (self.temp > self.Tmin) & (self.temp <= self.Tmax)
    def SalinityFilter(self):
        return (self.saln >= self.Smin) & (self.saln <= self.Smax)

    def filter(self):
        pass

    def SetAdditionalData(self):
        self.seqNum = Compute_sequenceNumber(self.lon)
        self.PreQC = (np.ma.masked_array(np.full((self.n_obs), 0))).astype(np.int32)
        self.ObsError_temp = \
            np.float32(np.ma.masked_array(np.full((self.n_obs), self.errorT)))
        self.ObsError_saln = \
            np.float32(np.ma.masked_array(np.full((self.n_obs), self.errorS)))

    def createIODAVars(self, obsspace):
        WriteDateTime(obsspace, self.dateTime)
        WriteRcptDateTime(obsspace, self.rcptdateTime)
        WriteLongitude(obsspace, self.lon)
        WriteLatitude(obsspace, self.lat)

    def WritePreQC(self, obsspace, name):
        obsspace.create_var("PreQC/" + name, dtype=self.PreQC.dtype, fillval=self.PreQC.fill_value) \
            .write_attr('long_name', 'PreQC') \
            .write_data(self.PreQC)

    def WriteObsValueT(self, obsspace, v_name):
        obsspace.create_var('ObsValue/' + v_name, dtype=self.temp.dtype, fillval=self.temp.fill_value) \
            .write_attr('units', 'degC') \
            .write_attr('valid_range', \
                np.array([self.Tmin, self.Tmax], dtype=np.float32)) \
            .write_attr('long_name', v_name) \
            .write_data(self.temp)

    def WriteObsValueS(self, obsspace, v_name):
        obsspace.create_var('ObsValue/' + v_name, dtype=self.saln.dtype, fillval=self.saln.fill_value) \
            .write_attr('units', 'psu') \
            .write_attr('valid_range', \
                np.array([self.Smin, self.Smax], dtype=np.float32)) \
            .write_attr('long_name', v_name) \
            .write_data(self.saln)

##############################################################################

    def logTemperature(self, logger):
        logger.debug(f" temp          min, max, length, dtype = {self.temp.min()}, {self.temp.max()}, {len(self.temp)}, {self.temp.dtype}")

    def logSalinity(self, logger):
        logger.debug(f" saln          min, max, length, dtype = {self.saln.min()}, {self.saln.max()}, {len(self.saln)}, {self.saln.dtype}")

    def logLonLat(self, logger):
        logger.debug(f" lon           min, max, length, dtype = {self.lon.min()}, {self.lon.max()}, {len(self.lon)}, {self.lon.dtype}")
        logger.debug(f" lat           min, max, length, dtype = {self.lat.min()}, {self.lat.max()}, {len(self.lat)}, {self.lat.dtype}")

    def logDates(self, logger):
        logger.debug(f" dateTime                 shape, dtype = {self.dateTime.shape}, {self.dateTime.dtype}")
        logger.debug(f" rcptdateTime             shape, dytpe = {self.rcptdateTime.shape}, {self.rcptdateTime.dtype}")

    def logStationID(self, logger):
        logger.debug(f" stationID                shape, dtype = {self.stationID.shape}, {self.stationID.astype(str).dtype}")

    def logDepth(self, logger):
        logger.debug(f" depth         min, max, length, dtype = {self.depth.min()}, {self.depth.max()}, {len(self.depth)}, {self.depth.dtype}")

    def LogSeqNum(self, logger):
        logger.debug(f" sequence Num             shape, dtype = {self.seqNum.shape}, {self.seqNum.dtype}")

    def LogPreQC(self, logger):
        logger.debug(f" PreQC         min, max, length, dtype = \
        {self.PreQC.min()}, \
        {self.PreQC.max()}, \
        {len(self.PreQC)}, \
        {self.PreQC.dtype}")

    def LogObsError_temp(self, logger):
        logger.debug(f" ObsError_temp min, max, length, dtype = \
            {self.ObsError_temp.min()}, \
            {self.ObsError_temp.max()}, \
            {len(self.ObsError_temp)}, \
            {self.ObsError_temp.dtype}")

    def LogObsError_saln(self, logger):
        logger.debug(f" ObsError_saln min, max, length, dtype = \
            {self.ObsError_saln.min()}, \
            {self.ObsError_saln.max()}, \
            {len(self.ObsError_saln)}, \
            {self.ObsError_saln.dtype}")

    def logMetadata(self, logger):
        self.logDates(logger)
        self.logLonLat(logger)
        self.logDepth(logger)
        self.logStationID(logger)

    def logObs(self, logger):
        self.logTemperature(logger)
        self.logSalinity(logger)

    def logAdditionalData(self, logger):
        self.LogSeqNum(logger)
        self.LogPreQC(logger)
        self.LogObsError_temp(logger)
        self.LogObsError_saln(logger)

    def log(self, logger):
        self.logMetadata(logger)
        self.logObs(logger)
        self.logAdditionalData(logger)

#####################################################################

def WriteDateTime(obsspace, dateTime):
    obsspace.create_var('MetaData/dateTime',
            dtype=dateTime.dtype, fillval=dateTime.fill_value)
        .write_attr('units', 'seconds since 1970-01-01T00:00:00Z')
        .write_attr('long_name', 'Datetime')
        .write_data(dateTime)

def WriteRcptDateTime(obsspace, rcptdateTime):
    obsspace.create_var('MetaData/rcptdateTime',
            dtype=rcptdateTime.dtype, fillval=rcptdateTime.fill_value)
        .write_attr('units', 'seconds since 1970-01-01T00:00:00Z')
        .write_attr('long_name', 'receipt Datetime')
        .write_data(rcptdateTime)

def WriteLongitude(obsspace, lon):
    obsspace.create_var('MetaData/longitude',
            dtype=lon.dtype, fillval=lon.fill_value)
        .write_attr('units', 'degrees_east')
        .write_attr('valid_range', np.array([-180, 180], dtype=np.float32))
        .write_attr('long_name', 'Longitude')
        .write_data(lon)

def WriteLatitude(obsspace, lat):
    obsspace.create_var('MetaData/latitude',
            dtype=lat.dtype, fillval=lat.fill_value)
        .write_attr('units', 'degrees_north')
        .write_attr('valid_range', np.array([-90, 90], dtype=np.float32))
        .write_attr('long_name', 'Latitude')
        .write_data(lat)

def WriteStationID(obsspace, stationID):
    obsspace.create_var('MetaData/stationID',
            dtype=stationID.dtype, fillval=stationID.fill_value)
        .write_attr('long_name', 'Station Identification')
        .write_data(stationID)

def WriteDepth(obsspace, depth):
    obsspace.create_var('MetaData/depth',
            dtype=depth.dtype, fillval=depth.fill_value)
        .write_attr('units', 'm')
        .write_attr('long_name', 'Water depth')
        .write_data(depth)

def WriteSequenceNumber(obsspace, seqNum, PreQC):
    obsspace.create_var('MetaData/sequenceNumber',
            dtype=PreQC.dtype, fillval=PreQC.fill_value)
        .write_attr('long_name', 'Sequence Number')
        .write_data(seqNum)

def WriteObsError(obsspace, v_name, units, v):
    obsspace.create_var(
        v_name,
        dtype=v.dtype, fillval=v.fill_value
    ) \
        .write_attr('units', units) \
        .write_attr('long_name', 'ObsError') \
        .write_data(v)
