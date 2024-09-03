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
        self.SetTemperatureRange(-10.0, 50.0)
        self.T_error = 0.0
        self.SetSalinityRange(0.0, 45.0)
        self.S_error = 0.0
        self.metadata = IODAMetadata()

    def SetOceanBasinNCFilePath(self, nc_file_path):
        self.additional_vars.SetOceanBasinNCFilePath(nc_file_path)

    def SetTemperatureVarName(self, name):
        self.T_name = name

    def SetTemperatureError(self, e):
        self.T_error = e

    def SetTemperatureRange(self, tmin, tmax):
        self.T_min = tmin
        self.T_max = tmax

    def SetSalinityVarName(self, name):
        self.S_name = name

    def SetSalinityError(self, e):
        self.S_error = e

    def SetSalinityRange(self, smin, smax):
        self.S_min = smin
        self.S_max = smax

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

    def SetFromQueryResult(self, r):
        self.metadata.SetFromQueryResult(r)
        self.SetObsFromQueryResult(r)

###########################################################################

    def TemperatureFilter(self):
        return (self.temp > self.T_min) & (self.temp <= self.T_max)

    def SalinityFilter(self):
        return (self.saln >= self.S_min) & (self.saln <= self.S_max)

    def filter(self):
        pass

###########################################################################

    def WriteToIodaFile(self, obsspace):
        self.metadata.WriteToIodaFile(obsspace)
        self.additional_vars.WriteToIodaFile(obsspace)
        self.WriteObsValueT(obsspace)
        self.WriteObsValueS(obsspace)

##########################################################################

    def SetObsFromQueryResult(self, r):
        self.temp = r.get('temp', group_by='depth')
        self.temp -= 273.15
        self.saln = r.get('saln', group_by='depth')

###########################################################################

    def WriteObsValueT(self, obsspace):
        obsspace.create_var('ObsValue/' + self.T_name, dtype=self.temp.dtype, fillval=self.temp.fill_value) \
            .write_attr('units', 'degC') \
            .write_attr('valid_range', np.array([self.T_min, self.T_max], dtype=np.float32)) \
            .write_attr('long_name', self.T_name) \
            .write_data(self.temp)

    def WriteObsValueS(self, obsspace):
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
        self.logObs(logger)
        self.additional_vars.log(logger)

    def logObs(self, logger):
        self.logTemperature(logger)
        self.logSalinity(logger)

    def logTemperature(self, logger):
        LogVariable(logger, "temp", self.temp)
        logger.debug(f"temp hash = {compute_hash(self.temp)}")

    def logSalinity(self, logger):
        LogVariable(logger, "saln", self.saln)
        logger.debug(f"saln hash = {compute_hash(self.saln)}")
