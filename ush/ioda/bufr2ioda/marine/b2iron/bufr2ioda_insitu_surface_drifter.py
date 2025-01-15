#!/usr/bin/env python3

import sys
import numpy as np
from b2ibase.util import parse_arguments
from b2ibase.config import Config
from b2ibase.data_container import DataContainer
from b2ibase.b2i import B2I
from b2ibase.log import B2ILogger


class DrifterConfig(Config):
    def ioda_filename(self):
        return f"{self.cycle_type}.t{self.hh}z.insitu_surface_drifter..{self.cycle_datetime}.nc4"


class DrifterData(DataContainer):
    def process_data(self):
        self.convert_temp_to_celsius("seaSurfaceTemperature")

        temp = self.container.get("variables/seaSurfaceTemperature")
        temp_min = -10.0
        temp_max = 50.0
        temp_mask = (temp > temp_min) & (temp < temp_max)

        buoy_type = self.container.get("variables/buoyType")
        # Separate Drifter profiles from dbuoy tank
        # buoy_type:
        # 1 - Standard Lagrangian drifter (Global Drifter Programme)
        # 4 - Ice drifter
        # 5 - SVPG Standard Lagrangian drifter with GPS
        values_to_select = [1, 4, 5]
        buoy_mask = np.isin(buoy_type, values_to_select)

        mask = buoy_mask & temp_mask
        self.filter(mask)

        saln_error = 0.01
        temp_error = 0.24

        self.add_preqc_var("seaSurfaceTemperature")
        self.add_preqc_var("salinity")
        self.add_error_var("seaSurfaceTemperature", temp_error)
        self.add_error_var("salinity", saln_error)


if __name__ == '__main__':
    script_name, config_file, log_file, test_file = parse_arguments()
    log_to_console = True
    logger = B2ILogger(script_name, log_to_console, log_file)

    config = DrifterConfig(config_file, logger)
    data = DrifterData(logger)
    b2i = B2I(config, data, logger)
    b2i.run()
    if test_file:
        result = b2i.test(test_file)
        sys.exit(result)
