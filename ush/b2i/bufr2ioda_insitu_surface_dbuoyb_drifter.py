#!/usr/bin/env python3

import sys
import numpy as np
import bufr
from b2iconverter.util import parse_arguments
from b2iconverter.bufr2ioda_config import Bufr2iodaConfig
from b2iconverter.bufr2ioda_converter import Bufr2ioda_Converter
from b2iconverter.ioda_metadata import IODAMetadata
from b2iconverter.ioda_variables import IODAVariables
from b2iconverter.ioda_addl_vars import IODAAdditionalVariables, compute_seq_num
from b2iconverter.util import *


platform_description = 'Drifters, surface temperature from dbuoyb'


class DbuoybIODAVariables(IODAVariables):

    def __init__(self):
        self.construct()
        self.metadata = DbuoybMetadata()
        self.additional_vars = DbuoybAdditionalVariables(self)

    def build_query(self):
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
        q.add('stationID', '*/RPID')
        q.add('latitude', '*/CLATH')
        q.add('longitude', '*/CLONH')
        q.add('temp', '*/BBYSSTS/SST0')
        return q

    def set_obs_from_query_result(self, r):
        self.temp = r.get('temp').astype(np.float32)
        self.temp -= 273.15

    def filter(self):
        super().filter()
        mask = self.TemperatureFilter()
        self.metadata.filter(mask)
        self.temp = self.temp[mask]

    def write_to_ioda_file(self, obsspace):
        self.metadata.write_to_ioda_file(obsspace)
        self.additional_vars.write_to_ioda_file(obsspace)
        self.write_obs_value_t(obsspace)

    def log_obs(self, logger):
        self.log_temperature(logger)


class DbuoybMetadata(IODAMetadata):

    def set_date_time_from_query_result(self, r):
        self.dateTime = r.get_datetime('year', 'month', 'day', 'hour', 'minute')
        self.dateTime = self.dateTime.astype(np.int64)

    def set_rcpt_date_time_from_query_result(self, r):
        self.rcptdateTime = r.get_datetime('ryear', 'rmonth', 'rday', 'rhour', 'rminute')
        self.rcptdateTime = self.rcptdateTime.astype(np.int64)

    def set_lon_from_query_result(self, r):
        self.lon = r.get('longitude')

    def set_lat_from_query_result(self, r):
        self.lat = r.get('latitude')

    def set_station_id_from_query_result(self, r):
        self.stationID = r.get('stationID')

    def set_from_query_result(self, r):
        self.set_date_time_from_query_result(r)
        self.set_rcpt_date_time_from_query_result(r)
        self.set_lon_from_query_result(r)
        self.set_lat_from_query_result(r)
        self.set_station_id_from_query_result(r)

    def filter(self, mask):
        self.dateTime = self.dateTime[mask]
        self.rcptdateTime = self.rcptdateTime[mask]
        self.lat = self.lat[mask]
        self.lon = self.lon[mask]
        self.stationID = self.stationID[mask]

    def write_to_ioda_file(self, obsspace):
        write_date_time(obsspace, self.dateTime)
        write_rcpt_date_time(obsspace, self.rcptdateTime)
        write_longitude(obsspace, self.lon)
        write_latitude(obsspace, self.lat)
        write_station_id(obsspace, self.stationID)

    def log(self, logger):
        self.log_date_time(logger)
        self.log_rcpt_date_time(logger)
        self.log_longitude(logger)
        self.log_latitude(logger)
        self.log_station_id(logger)


class DbuoybAdditionalVariables(IODAAdditionalVariables):

    def construct(self):
        n = len(self.ioda_vars.metadata.lon)
        self.PreQC = (np.ma.masked_array(np.full(n, 0))).astype(np.int32)
        self.ObsError_temp = \
            np.float32(np.ma.masked_array(np.full(n, self.ioda_vars.T_error)))
        self.compute_ocean_basin()

    def write_to_ioda_file(self, obsspace):
        self.write_preqc(obsspace, self.ioda_vars.T_name)
        self.write_obs_errorT(obsspace)
        self.write_ocean_basin(obsspace)

    def log(self, logger):
        self.log_preqc(logger)
        self.log_obs_error_temp(logger)
        self.log_ocean_basin(logger)


'''
buoy types for drifters:
------------------------
00	Unspecified drifting buoy
01	Standard Lagrangian drifter (Global Drifter Programme)
02	Standard FGGE type drifting buoy (non-Lagrangian meteorological drifting buoy)
03	Wind measuring FGGE type drifting buoy (non-Lagrangian meteorological drifting buoy)
04	Ice drifter
05	SVPG Standard Lagrangian drifter with GPS (BUFR)
06	SVP-HR drifter with high-resolution temperature or thermistor string (BUFR)
10	ALACE (Autonomous Lagrangian Circulation Explorer)
11	MARVOR (MARine VORtical profiler)
12	RAFOS (Ranging and Fixing of Sound)
13	PROVOR (Profiling float with Argos)
14	SOLO (Swimbladder-Operated Lagrangian Oscillating)
15	APEX (Autonomous Profiling Explorer)
'''

drifter_buoy_types = [0, 1, 2, 3, 4, 5, 6, 10, 11, 12, 13, 14, 15]


class DbuoybDrifterIODAVariables(DbuoybIODAVariables):

    def __init__(self):
        self.construct()
        self.metadata = DbuoybDrifterMetadata()
        self.additional_vars = DbuoybAdditionalVariables(self)

    def build_query(self):
        q = super().build_query()
        q.add('buoy_type', '*/BUYT')
        return q

    def filter(self):
        super().filter()

        buoy_type = self.metadata.buoy_type
        rpid = self.metadata.stationID

        # rpid = stationID: string array (e.g., 'A8xxx')
        # buoy_type: int array (e.g., 1, 2, 3), etc.
        drifter_mask = np.isin(buoy_type, drifter_buoy_types, assume_unique=True)

        # Optional: Add RPID check for drifter patterns (e.g., starts with 'A8')
        rpid_drifter_mask = np.array([isinstance(r, str) and r.startswith('A8') for r in rpid.filled('')])
        drifter_mask = drifter_mask | rpid_drifter_mask

        # Handle masked (missing) BUYT values
        # If BUYT is masked, assume not a drifter unless RPID suggests otherwise
        drifter_mask = np.where(buoy_type.mask, rpid_drifter_mask, drifter_mask)

        self.metadata.filter(drifter_mask)
        self.temp = self.temp[drifter_mask]


class DbuoybDrifterMetadata(DbuoybMetadata):

    def set_from_query_result(self, r):
        super().set_from_query_result(r)
        self.buoy_type = r.get('buoy_type')

    def filter(self, mask):
        super().filter(mask)
        self.buoy_type = self.buoy_type[mask]

    def write_to_ioda_file(self, obsspace):
        super().write_to_ioda_file(obsspace)
        obsspace.create_var(
            'MetaData/BuoyType',
            dtype=self.buoy_type.dtype,
            fillval=self.buoy_type.fill_value
        ) \
            .write_attr('long_name', 'Buoy Type') \
            .write_data(self.buoy_type)

    def log(self, logger):
        super().log(logger)
        log_variable(logger, "buoy type", self.buoy_type)
        logger.debug(f"buoy type hash = {compute_hash(self.buoy_type)}")


class DbuoybDrifterConfig(Bufr2iodaConfig):

    def ioda_filename(self):
        return f"{self.cycle_type}.t{self.hh}z.insitu_surface_dbuoyb_drifter.{self.cycle_datetime}.nc"


if __name__ == '__main__':

    script_name, config_file, log_file, test_file = parse_arguments()

    bufr2ioda_config = DbuoybDrifterConfig(
        script_name,
        config_file,
        platform_description)

    ioda_vars = DbuoybDrifterIODAVariables()

    ioda_vars.set_temperature_var_name("seaSurfaceTemperature")
    ioda_vars.set_temperature_error(0.3)

    dbuoyb_drifters = Bufr2ioda_Converter(bufr2ioda_config, ioda_vars, log_file)

    dbuoyb_drifters.run()

    if test_file:
        result = dbuoyb_drifters.test(test_file)
        sys.exit(result)
