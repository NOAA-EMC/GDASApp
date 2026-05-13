import numpy as np
import bufr
from b2iconverter.ioda_variables import IODAVariables
from b2iconverter.ioda_metadata import IODAMetadata
from b2iconverter.ioda_addl_vars import IODAAdditionalVariables
from b2iconverter.util import log_variable, compute_hash


class TropicalIODAVariables(IODAVariables):

    def __init__(self):
        self.construct()
        self.metadata = TropicalMetadata()
        self.additional_vars = IODAAdditionalVariables(self)

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
        q.add('saln', '*/DTSCUR/SALN')
        q.add('buoy_type', '*/RPSEC4/BUYT')
        return q

    def filter(self):
        super().filter()
        TS_mask = self.TemperatureFilter() & self.SalinityFilter()

        # Separate tropical mooring profiles from dbuoy tank
        # buoy_type: ATLAS is 21, TRITON is 22
        buoy_mask = [True if x == 21 or x == 22 else False for x in self.metadata.buoy_type]

        mask = TS_mask & buoy_mask

        self.metadata.filter(mask)
        self.temp = self.temp[mask]
        self.saln = self.saln[mask]


class TropicalMetadata(IODAMetadata):
    def set_from_query_result(self, r):
        super().set_from_query_result(r)
        self.buoy_type = r.get('buoy_type', group_by='depth')
        # self.ldds = r.get('ldds')

    def set_rcpt_date_time_from_query_result(self, r):
        self.rcptdateTime = r.get_datetime('ryear', 'rmonth', 'rday', 'rhour', 'rminute')
        self.rcptdateTime = self.rcptdateTime[:, 0]
        self.rcptdateTime = self.rcptdateTime.astype(np.int64)
        k = int(len(self.dateTime) / len(self.rcptdateTime))
        self.rcptdateTime = np.tile(self.rcptdateTime, k)

    def filter(self, mask):
        super().filter(mask)
        self.buoy_type = self.buoy_type[mask]

    def write_to_ioda_file(self, obsspace):
        super().write_to_ioda_file(obsspace)
        obsspace.create_var(
            'MetaData/BuoyType',
            dtype=self.buoy_type.dtype, fillval=self.buoy_type.fill_value
        ) \
            .write_attr('long_name', 'Buoy Type') \
            .write_data(self.buoy_type)

    def log(self, logger):
        super().log(logger)
        log_variable(logger, "buoy type", self.buoy_type)
        logger.debug(f"buoy type hash = {compute_hash(self.buoy_type)}")
