import sys
import os
import tempfile
from .util import run_diff


class B2I:
    def __init__(self, config, data, logger):
        self.config = config
        self.data = data
        self.logger = logger

    def read_from_bufr(self):
        map_yaml_file = self.config.data_description_filepath()
        self.logger.debug(f"read_from_bufr: using mapping file {map_yaml_file}")
        bufr_file_path = self.config.bufr_filepath()
        self.logger.debug(f"reading bufr file {bufr_file_path}")
        self.data.read_from_bufr(bufr_file_path, map_yaml_file)
        self.logger.debug(f"read from bufr: data size = {self.data.get_data_size()}")
        if self.data.get_data_size() == 0:
            self.logger.warning("No data read -- exiting")
            sys.exit()

    def process_data(self):
        self.data.process_data()
        self.logger.debug(f"processed data: data size = {self.data.get_data_size()}")
        if self.data.get_data_size() == 0:
            self.logger.warning("No data read -- exiting")
            sys.exit()
        ocean_file_path = self.config.ocean_basin_nc_file_path()
        self.data.add_ocean_basin(ocean_file_path)
        # print("process_data: variables:")
        # self.data.print_var_names()

    def write_to_ioda_file(self):
        map_yaml_file = self.config.data_description_filepath()
        self.logger.debug(f"write_to_ioda_file: using mapping file {map_yaml_file}")
        iodafile_path = self.config.ioda_filepath()
        path, fname = os.path.split(iodafile_path)
        os.makedirs(path, exist_ok=True)
        self.logger.debug(f"writing ioda file {iodafile_path}")
        self.data.write_to_ioda_file(iodafile_path, map_yaml_file, self.config)

    def run(self):
        self.read_from_bufr()
        self.process_data()
        self.write_to_ioda_file()
        self.data.log(self.logger)

    def test(self, test_file):
        with tempfile.NamedTemporaryFile(delete=False, suffix='.log') as temp_log_file:
            temp_log_file_name = temp_log_file.name
            self.logger.debug(f"TEST: created a temporary log file {temp_log_file_name}")

            self.logger.disable_logging()
            self.logger.enable_test_file_logging(temp_log_file_name)
            self.data.log(self.logger)
            self.logger.disable_test_file_logging()
            self.logger.enable_logging()

            if os.path.exists(test_file):
                self.logger.debug(f"TEST: running diff with reference file {test_file}")
            else:
                self.logger.error(f"TEST: reference file not found: {test_file}")
                return 1    # failure

            result = run_diff(temp_log_file_name, test_file, self.logger)
            if result:
                self.logger.error(f"TEST ERROR: files are different")
            else:
                self.logger.info(f"TEST passed: files are identical")

            return result
