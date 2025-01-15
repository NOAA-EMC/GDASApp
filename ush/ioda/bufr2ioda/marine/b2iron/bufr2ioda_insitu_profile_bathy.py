#!/usr/bin/env python3

import sys
from b2ibase.util import parse_arguments
from b2ibase.config import Config
from b2ibase.data_container import DataContainer
from b2ibase.b2i import B2I
from b2ibase.log import B2ILogger


class BathyData(DataContainer):
    def process_data(self):
        self.convert_temp_to_celsius("waterTemperature")

        temp = self.container.get("variables/waterTemperature")
        temp_min = -10.0
        temp_max = 50.0
        mask = (temp > temp_min) & (temp < temp_max)

        self.filter(mask)

        temp_error = 0.24

        self.add_preqc_var("waterTemperature")
        self.add_error_var("waterTemperature", temp_error)
        self.add_seq_num()


if __name__ == '__main__':

    script_name, config_file, log_file, test_file = parse_arguments()
    log_to_console = True
    logger = B2ILogger(script_name, log_to_console, log_file)

    config = Config(config_file, logger)
    data = BathyData(logger)
    b2i = B2I(config, data, logger)
    b2i.run()
    if test_file:
        result = b2i.test(test_file)
        sys.exit(result)
