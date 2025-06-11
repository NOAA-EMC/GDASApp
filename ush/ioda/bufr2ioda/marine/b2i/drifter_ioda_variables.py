import numpy as np
from pyiodaconv import bufr
from b2iconverter.ioda_variables import IODAVariables
from b2iconverter.ioda_metadata import IODAMetadata
from b2iconverter.ioda_addl_vars import IODAAdditionalVariables, compute_seq_num
from b2iconverter.util import *


class DrifterIODAVariables(IODAVariables):

    def __init__(self):
        self.construct()
        self.metadata = DrifterMetadata()
        self.additional_vars = DrifterAdditionalVariables(self)

    def build_query(self):
        q = bufr.QuerySet()
        q.add('year', '*/YEAR')
        q.add('month', '*/MNTH')
        q.add('day', '*/DAYS')
        q.add('hour', '*/HOUR')
        q.add('minute', '*/MINU')
        q.add('ryear', '*/RCPTIM/RCYR')
        q.add('rmonth', '*/RCPTIM/RCMO')
        q.add('rday', '*/RCPTIM/RCDY')
        q.add('rhour', '*/RCPTIM/RCHR')
        q.add('rminute', '*/RCPTIM/RCMI')
        q.add('stationID', '*/RPID')
        q.add('latitude', '*/CLAT')
        q.add('longitude', '*/CLON')
        q.add('depth', '*/DTSCUR/DBSS')
        q.add('temp', '*/DTSCUR/STMP')
        q.add('buoy_type', '*/RPSEC4/BUYT')
        return q

    def set_obs_from_query_result(self, r):
        self.temp = r.get('temp', group_by='depth')
        self.temp -= 273.15

    def filter(self):
        super().filter()
        T_mask = self.TemperatureFilter()

        # Separate Drifter profiles from dbuoy tank
        # buoy_type:
        # 1 - Standard Lagrangian drifter (Global Drifter Programme)
        # 4 - Ice drifter
        # 5 - SVPG Standard Lagrangian drifter with GPS
        values_to_select = [1, 4, 5]
        buoy_mask = np.isin(self.metadata.buoy_type, values_to_select)

        mask = T_mask & buoy_mask

        self.metadata.filter(mask)
        self.temp = self.temp[mask]

    def write_to_ioda_file(self, obsspace):
        self.metadata.write_to_ioda_file(obsspace)
        self.additional_vars.write_to_ioda_file(obsspace)
        self.write_obs_value_t(obsspace)

    def log_obs(self, logger):
        self.log_temperature(logger)


class DrifterMetadata(IODAMetadata):
    def set_from_query_result(self, r):
        self.set_date_time_from_query_result(r)
        self.set_rcpt_date_time_from_query_result(r)
        self.set_lon_from_query_result(r)
        self.set_lat_from_query_result(r)
        self.set_station_id_from_query_result(r)
        self.buoy_type = r.get('buoy_type', group_by='depth')

    def set_rcpt_date_time_from_query_result(self, r):
        self.rcptdateTime = r.get_datetime('ryear', 'rmonth', 'rday', 'rhour', 'rminute')
        self.rcptdateTime = self.rcptdateTime[:, 0]
        self.rcptdateTime = self.rcptdateTime.astype(np.int64)
        k = int(len(self.dateTime) / len(self.rcptdateTime))
        self.rcptdateTime = np.tile(self.rcptdateTime, k)

    def filter(self, mask):
        self.dateTime = self.dateTime[mask]
        self.rcptdateTime = self.rcptdateTime[mask]
        self.lat = self.lat[mask]
        self.lon = self.lon[mask]
        self.stationID = self.stationID[mask]
        self.buoy_type = self.buoy_type[mask]

    def write_to_ioda_file(self, obsspace):
        write_date_time(obsspace, self.dateTime)
        write_rcpt_date_time(obsspace, self.rcptdateTime)
        write_longitude(obsspace, self.lon)
        write_latitude(obsspace, self.lat)
        write_station_id(obsspace, self.stationID)
        obsspace.create_var(
            'MetaData/BuoyType',
            dtype=self.buoy_type.dtype, fillval=self.buoy_type.fill_value
        ) \
            .write_attr('long_name', 'Buoy Type') \
            .write_data(self.buoy_type)

    def log(self, logger):
        self.log_date_time(logger)
        self.log_rcpt_date_time(logger)
        self.log_longitude(logger)
        self.log_latitude(logger)
        self.log_station_id(logger)
        log_variable(logger, "buoy type", self.buoy_type)
        logger.debug(f"buoy type hash = {compute_hash(self.buoy_type)}")


class DrifterAdditionalVariables(IODAAdditionalVariables):

    def construct(self):
        self.seqNum = compute_seq_num(self.ioda_vars.metadata.lon, self.ioda_vars.metadata.lat)
        n = len(self.seqNum)
        self.PreQC = (np.ma.masked_array(np.full(n, 0))).astype(np.int32)
        self.ObsError_temp = \
            np.float32(np.ma.masked_array(np.full(n, self.ioda_vars.T_error)))
        self.compute_ocean_basin()

    def write_to_ioda_file(self, obsspace):
        self.write_seq_num(obsspace)
        self.write_preqc(obsspace, self.ioda_vars.T_name)
        self.write_obs_errorT(obsspace)
        self.write_ocean_basin(obsspace)

    def log(self, logger):
        self.log_seq_num(logger)
        self.log_preqc(logger)
        self.log_obs_error_temp(logger)
        self.log_ocean_basin(logger)
