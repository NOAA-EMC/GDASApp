#!/usr/bin/env python3

import sys
import numpy as np                                                          
from b2iconverter.util import parse_arguments
from b2iconverter.bufr2ioda_config import Bufr2iodaConfig
from b2iconverter.bufr2ioda_converter import Bufr2ioda_Converter
from b2iconverter.ioda_variables import IODAVariables
from b2iconverter.ioda_metadata import IODAMetadata
from b2iconverter.ioda_addl_vars import IODAAdditionalVariables
from wmo_codes import *
from b2iconverter.util import *


platform_description = 'NDBC buoys from mbuoyb: surface temperature'


class NDBCConfig(Bufr2iodaConfig):
    def ioda_filename(self):
        return f"{self.cycle_type}.t{self.hh}z.insitu_surface_ndbc.{self.cycle_datetime}.nc"


# almost the same as dbuoyb_surface_ioda_variables
class NDBCIODAVariables(IODAVariables):
    def __init__(self):
        self.construct()
        self.metadata = NDBCMetadata()
        self.additional_vars = NDBCAdditionalVariables(self)

    def build_query(self):
        q = super().build_query()
        q.add('stationID', '*/RPID')
        q.add('latitude', '*/CLATH')
        q.add('longitude', '*/CLONH')
        q.add('temp', '*/SST0')
        q.add('borg', '*/BORG')
        return q
    
    def set_obs_from_query_result(self, r):
        self.temp = r.get('temp')
        self.temp -= 273.15

    def filter(self):
        super().filter()
        tropical_mask = ~is_tropical_mooring(self.metadata.stationID)
        knwb_mask = [True if org == 'KWNB' else False for org in self.metadata.borg]
        temp_mask = ~self.temp.mask
        mask = tropical_mask & knwb_mask & temp_mask
        self.metadata.filter(mask)
        self.temp = self.temp[mask]

    def write_to_ioda_file(self, obsspace):
        self.metadata.write_to_ioda_file(obsspace)
        self.additional_vars.write_to_ioda_file(obsspace)
        self.write_obs_value_t(obsspace)

    def log_obs(self, logger):
        self.log_temperature(logger)


class NDBCMetadata(IODAMetadata):
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
        self.borg = r.get('borg')

    def write_to_ioda_file(self, obsspace):
        write_date_time(obsspace, self.dateTime)
        write_rcpt_date_time(obsspace, self.rcptdateTime)
        write_longitude(obsspace, self.lon)
        write_latitude(obsspace, self.lat)
        write_station_id(obsspace, self.stationID)

    def filter(self, mask):
        self.dateTime = self.dateTime[mask]
        self.rcptdateTime = self.rcptdateTime[mask]
        self.lat = self.lat[mask]
        self.lon = self.lon[mask]
        self.stationID = self.stationID[mask]
        self.borg = self.borg[mask]

    def log(self, logger):
        self.log_date_time(logger)
        self.log_rcpt_date_time(logger)
        self.log_longitude(logger)
        self.log_latitude(logger)
        self.log_station_id(logger)


class NDBCAdditionalVariables(IODAAdditionalVariables):

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


if __name__ == '__main__':

    script_name, config_file, log_file, test_file = parse_arguments()

    bufr2ioda_config = NDBCConfig(
        script_name,
        config_file,
        platform_description)

    ioda_vars = NDBCIODAVariables()
    ioda_vars.set_temperature_var_name("seaSurfaceTemperature")
    ioda_vars.set_temperature_error(0.3)

    converter = Bufr2ioda_Converter(bufr2ioda_config, ioda_vars, log_file)

    converter.run()

    if test_file:
        result = converter.test(test_file)
        sys.exit(result)
