import numpy as np
import bufr
from b2iconverter.ioda_variables import IODAVariables
from b2iconverter.ioda_metadata import IODAMetadata
from b2iconverter.ioda_addl_vars import IODAAdditionalVariables
from b2iconverter.util import log_variable, compute_hash
from wmo_codes import *


class MbuoybTropicalIODAVariables(IODAVariables):

    def build_query(self):
        q = super().build_query()
        q.add('latitude', '*/CLATH')
        q.add('longitude', '*/CLONH')
        q.add('stationID', '*/RPID')
        q.add('depth', '*/IDMSMDBS/BBYSTSL/DBSS')
        q.add('temp', '*/IDMSMDBS/BBYSTSL/SST1')
        q.add('saln', '*/IDMSMDBS/BBYSTSL/SALN')
        return q

    def filter(self):
        super().filter()
        mask = self.TemperatureFilter() & self.SalinityFilter()
        self.metadata.filter(mask)
        self.temp = self.temp[mask]
        self.saln = self.saln[mask]
