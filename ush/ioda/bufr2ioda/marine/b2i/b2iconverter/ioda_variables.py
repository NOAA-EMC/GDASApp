import numpy as np
from pyiodaconv import bufr
from .ocean import OceanBasin
from .util import *
from .ioda_metadata import IODAMetadata
from .ioda_addl_vars import IODAAdditionalVariables


class IODAVariables:
    def __init__(self):
        self.construct()
        # derived classes add their own additional_vars:
        self.additional_vars = IODAAdditionalVariables(self)

    def construct(self):
        self.n_obs = 0
        # default values can be oerridden using methods of this class:
        self.set_temperature_range(-10.0, 50.0)
        self.T_error = 0.0
        self.set_salinity_range(0.0, 45.0)
        self.S_error = 0.0
        self.metadata = IODAMetadata()

    def set_ocean_basin_nc_file(self, nc_file_path):
        self.additional_vars.set_ocean_basin_nc_file(nc_file_path)

    def set_temperature_var_name(self, name):
        self.T_name = name

    def set_temperature_error(self, e):
        self.T_error = e

    def set_temperature_range(self, tmin, tmax):
        self.T_min = tmin
        self.T_max = tmax

    def set_salinity_var_name(self, name):
        self.S_name = name

    def set_salinity_error(self, e):
        self.S_error = e

    def set_salinity_range(self, smin, smax):
        self.S_min = smin
        self.S_max = smax

    def number_of_temp_obs(self):
        try:
            if isinstance(self.temp, np.ma.MaskedArray):
                return self.temp.count()
            else:
                return 0
        # except NameError:
        except AttributeError:
            return 0

    def number_of_saln_obs(self):
        try:
            if isinstance(self.saln, np.ma.MaskedArray):
                return self.saln.count()
            else:
                return 0
        # except NameError:
        except AttributeError:
            return 0

    def number_of_obs(self):
        return max(self.number_of_temp_obs(), self.number_of_saln_obs())

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
        return q

    def set_from_query_result(self, r):
        self.metadata.set_from_query_result(r)
        self.set_obs_from_query_result(r)

###########################################################################

    def TemperatureFilter(self):
        return (self.temp > self.T_min) & (self.temp <= self.T_max)

    def SalinityFilter(self):
        return (self.saln >= self.S_min) & (self.saln <= self.S_max)

    def filter(self):
        pass

###########################################################################

    def write_to_ioda_file(self, obsspace):
        self.metadata.write_to_ioda_file(obsspace)
        self.additional_vars.write_to_ioda_file(obsspace)
        self.write_obs_value_t(obsspace)
        self.write_obs_value_s(obsspace)

##########################################################################

    def set_obs_from_query_result(self, r):
        self.temp = r.get('temp', group_by='depth')
        self.temp -= 273.15
        self.saln = r.get('saln', group_by='depth')

###########################################################################

    def write_obs_value_t(self, obsspace):
        obsspace.create_var('ObsValue/' + self.T_name, dtype=self.temp.dtype, fillval=self.temp.fill_value) \
            .write_attr('units', 'degC') \
            .write_attr('valid_range', np.array([self.T_min, self.T_max], dtype=np.float32)) \
            .write_attr('long_name', self.T_name) \
            .write_data(self.temp)

    def write_obs_value_s(self, obsspace):
        obsspace.create_var(
            'ObsValue/' + self.S_name,
            dtype=self.saln.dtype,
            fillval=self.saln.fill_value
        ) \
            .write_attr('units', 'psu') \
            .write_attr('valid_range', np.array([self.S_min, self.S_max], dtype=np.float32)) \
            .write_attr('long_name', self.S_name) \
            .write_data(self.saln)

##############################################################################

    def log(self, logger):
        self.metadata.log(logger)
        self.log_obs(logger)
        self.additional_vars.log(logger)

    def log_obs(self, logger):
        self.log_temperature(logger)
        self.log_salinity(logger)

    def log_temperature(self, logger):
        log_variable(logger, "temp", self.temp)
        logger.debug(f"temp hash = {compute_hash(self.temp)}")

    def log_salinity(self, logger):
        log_variable(logger, "saln", self.saln)
        logger.debug(f"saln hash = {compute_hash(self.saln)}")
