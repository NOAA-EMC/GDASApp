#!/usr/bin/env python3

import sys
import numpy as np
import bufr
from b2iconverter.util import parse_arguments
from b2iconverter.bufr2ioda_config import Bufr2iodaConfig
from b2iconverter.bufr2ioda_converter import Bufr2ioda_Converter
from b2iconverter.ioda_variables import IODAVariables
from b2iconverter.ioda_addl_vars import IODAAdditionalVariables
from b2iconverter.ioda_metadata import IODAMetadata
from b2iconverter.util import write_date_time, write_rcpt_date_time, write_longitude, write_latitude, write_station_id


platform_description = 'Surface obs from TRACKOB: temperature and salinity'


class TrkobIODAVariables(IODAVariables):
    def __init__(self):
        self.construct()
        self.metadata = TrkobMetadata()
        self.additional_vars = TrkobAdditionalVariables(self)

    def build_query(self):
        q = super().build_query()
        q.add('stationID', '*/RPID')
        q.add('latitude', '*/CLAT')
        q.add('longitude', '*/CLON')
        q.add('depth', '*/BTOCN/DBSS')
        q.add('temp', '*/BTOCN/STMP')
        q.add('saln', '*/BTOCN/SALN')
        return q

    def filter(self):
        super().filter()
        mask = self.TemperatureFilter() \
            & self.SalinityFilter()
        self.temp = self.temp[mask]
        self.saln = self.saln[mask]
        self.metadata.filter(mask)


class TrkobMetadata(IODAMetadata):

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


class TrkobAdditionalVariables(IODAAdditionalVariables):

    def construct(self):
        n = len(self.ioda_vars.temp)
        self.PreQC = (np.ma.masked_array(np.full(n, 0))).astype(np.int32)
        self.ObsError_temp = \
            np.float32(np.ma.masked_array(np.full(n, self.ioda_vars.T_error)))
        self.ObsError_saln = \
            np.float32(np.ma.masked_array(np.full(n, self.ioda_vars.S_error)))
        self.compute_ocean_basin()

    def write_to_ioda_file(self, obsspace):
        self.write_preqc(obsspace, self.ioda_vars.T_name)
        self.write_preqc(obsspace, self.ioda_vars.S_name)
        self.write_obs_errorT(obsspace)
        self.write_obs_errorS(obsspace)
        self.write_ocean_basin(obsspace)

    def log(self, logger):
        self.log_preqc(logger)
        self.log_obs_error_temp(logger)
        self.log_obs_error_saln(logger)
        self.log_ocean_basin(logger)


class TrkobConfig(Bufr2iodaConfig):
    def ioda_filename(self):
        return f"{self.cycle_type}.t{self.hh}z.insitu_surface_{self.data_format}.{self.cycle_datetime}.nc"


if __name__ == '__main__':

    script_name, config_file, log_file, test_file = parse_arguments()

    bufr2ioda_config = TrkobConfig(
        script_name,
        config_file,
        platform_description)

    ioda_vars = TrkobIODAVariables()
    ioda_vars.set_temperature_var_name("seaSurfaceTemperature")
    ioda_vars.set_temperature_error(0.3)
    ioda_vars.set_salinity_var_name("seaSurfaceSalinity")
    ioda_vars.set_salinity_error(1.0)

    trkob = Bufr2ioda_Converter(bufr2ioda_config, ioda_vars, log_file)
    trkob.run()

    if test_file:
        result = trkob.test(test_file)
        sys.exit(result)
