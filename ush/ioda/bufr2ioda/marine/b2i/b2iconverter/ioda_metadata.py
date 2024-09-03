import numpy as np
from .util import *
import hashlib


class IODAMetadata:
    def __init__(self):
        pass

    def SetFromQueryResult(self, r):
        self.SetDateTimeFromQueryResult(r)
        self.SetRcptDateTimeFromQueryResult(r)
        self.SetLonFromQueryResult(r)
        self.SetLatFromQueryResult(r)
        self.SetStationIDFromQueryResult(r)
        self.SetDepthFromQueryResult(r)

    def filter(self, mask):
        self.dateTime = self.dateTime[mask]
        self.rcptdateTime = self.rcptdateTime[mask]
        self.lat = self.lat[mask]
        self.lon = self.lon[mask]
        self.stationID = self.stationID[mask]
        self.depth = self.depth[mask]

    def WriteToIodaFile(self, obsspace):
        WriteDateTime(obsspace, self.dateTime)
        WriteRcptDateTime(obsspace, self.rcptdateTime)
        WriteLongitude(obsspace, self.lon)
        WriteLatitude(obsspace, self.lat)
        WriteStationID(obsspace, self.stationID)
        WriteDepth(obsspace, self.depth)

    def log(self, logger):
        self.logDateTime(logger)
        self.logRcptDateTime(logger)
        self.logLongitude(logger)
        self.logLatitude(logger)
        self.logDepth(logger)
        self.logStationID(logger)

##########################################################################

    def SetDateTimeFromQueryResult(self, r):
        self.dateTime = r.get_datetime('year', 'month', 'day', 'hour', 'minute', group_by='depth')
        self.dateTime = self.dateTime.astype(np.int64)

    def SetRcptDateTimeFromQueryResult(self, r):
        self.rcptdateTime = r.get_datetime('ryear', 'rmonth', 'rday', 'rhour', 'rminute', group_by='depth')
        self.rcptdateTime = self.rcptdateTime.astype(np.int64)

    def SetLonFromQueryResult(self, r):
        self.lon = r.get('longitude', group_by='depth')

    def SetLatFromQueryResult(self, r):
        self.lat = r.get('latitude', group_by='depth')

    def SetStationIDFromQueryResult(self, r):
        self.stationID = r.get('stationID', group_by='depth')

    def SetDepthFromQueryResult(self, r):
        self.depth = r.get('depth', group_by='depth')

##########################################################################

    def logLongitude(self, logger):
        LogVariable(logger, "lon", self.lon)
        logger.debug(f"lon hash = {compute_hash(self.lon)}")

    def logLatitude(self, logger):
        LogVariable(logger, "lat", self.lat)
        logger.debug(f"lat hash = {compute_hash(self.lat)}")

    def logDateTime(self, logger):
        LogVariable(logger, "dateTime", self.dateTime)
        logger.debug(f"dateTime hash = {compute_hash(self.dateTime)}")

    def logRcptDateTime(self, logger):
        LogVariable(logger, "rcptdateTime", self.rcptdateTime)
        logger.debug(f"rcptdateTime hash = {compute_hash(self.rcptdateTime)}")

    def logStationID(self, logger):
        logger.debug(f"stationID: {len(self.stationID)}, {self.stationID.astype(str).dtype}")
        if isinstance(self.stationID[0], str):
            concatenated_string = ''.join(self.stationID)
            # Compute the hash using SHA-256
            hash_object = hashlib.sha256(concatenated_string.encode())
            hash_hex = hash_object.hexdigest()
            logger.debug(f"stationID hash = {hash_hex}")
        # # elif isinstance(self.stationID[0], int32):
        else:
            logger.debug(f"stationID hash = {compute_hash(self.stationID)}")

    def logDepth(self, logger):
        LogVariable(logger, "depth", self.depth)
        logger.debug(f"depth hash = {compute_hash(self.depth)}")
