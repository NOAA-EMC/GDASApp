import numpy as np
from .util import *
import hashlib


class IODAMetadata:
    def __init__(self):
        pass

    def set_from_query_result(self, r):
        self.set_date_time_from_query_result(r)
        self.set_rcpt_date_time_from_query_result(r)
        self.set_lon_from_query_result(r)
        self.set_lat_from_query_result(r)
        self.set_station_id_from_query_result(r)
        self.set_depth_from_query_result(r)

    def filter(self, mask):
        self.dateTime = self.dateTime[mask]
        self.rcptdateTime = self.rcptdateTime[mask]
        self.lat = self.lat[mask]
        self.lon = self.lon[mask]
        self.stationID = self.stationID[mask]
        self.depth = self.depth[mask]

    def write_to_ioda_file(self, obsspace):
        write_date_time(obsspace, self.dateTime)
        write_rcpt_date_time(obsspace, self.rcptdateTime)
        write_longitude(obsspace, self.lon)
        write_latitude(obsspace, self.lat)
        write_station_id(obsspace, self.stationID)
        write_depth(obsspace, self.depth)

    def log(self, logger):
        self.log_date_time(logger)
        self.log_rcpt_date_time(logger)
        self.log_longitude(logger)
        self.log_latitude(logger)
        self.log_depth(logger)
        self.log_station_id(logger)

##########################################################################

    def set_date_time_from_query_result(self, r):
        self.dateTime = r.get_datetime('year', 'month', 'day', 'hour', 'minute', group_by='depth')
        self.dateTime = self.dateTime.astype(np.int64)

    def set_rcpt_date_time_from_query_result(self, r):
        self.rcptdateTime = r.get_datetime('ryear', 'rmonth', 'rday', 'rhour', 'rminute', group_by='depth')
        self.rcptdateTime = self.rcptdateTime.astype(np.int64)

    def set_lon_from_query_result(self, r):
        self.lon = r.get('longitude', group_by='depth')

    def set_lat_from_query_result(self, r):
        self.lat = r.get('latitude', group_by='depth')

    def set_station_id_from_query_result(self, r):
        self.stationID = r.get('stationID', group_by='depth')

    def set_depth_from_query_result(self, r):
        self.depth = r.get('depth', group_by='depth')

##########################################################################

    def log_longitude(self, logger):
        log_variable(logger, "lon", self.lon)
        logger.debug(f"lon hash = {compute_hash(self.lon)}")

    def log_latitude(self, logger):
        log_variable(logger, "lat", self.lat)
        logger.debug(f"lat hash = {compute_hash(self.lat)}")

    def log_date_time(self, logger):
        log_variable(logger, "dateTime", self.dateTime)
        logger.debug(f"dateTime hash = {compute_hash(self.dateTime)}")

    def log_rcpt_date_time(self, logger):
        log_variable(logger, "rcptdateTime", self.rcptdateTime)
        logger.debug(f"rcptdateTime hash = {compute_hash(self.rcptdateTime)}")

    def log_station_id(self, logger):
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

    def log_depth(self, logger):
        log_variable(logger, "depth", self.depth)
        logger.debug(f"depth hash = {compute_hash(self.depth)}")
