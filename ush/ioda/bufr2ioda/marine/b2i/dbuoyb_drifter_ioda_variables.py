import numpy as np
from pyiodaconv import bufr
from b2iconverter.ioda_variables import IODAVariables
from b2iconverter.ioda_metadata import IODAMetadata
from b2iconverter.ioda_addl_vars import IODAAdditionalVariables, compute_seq_num
from b2iconverter.util import *
from dbuoyb_surface_ioda_variables import DbuoybIODAVariables, DbuoybMetadata, DbuoybAdditionalVariables


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
