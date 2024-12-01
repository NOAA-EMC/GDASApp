import tempfile
from .util import run_diff


class B2I:
    def __init__(self, config, data, logger):
        self.config = config
        self.data = data
        self.logger = logger
        var_yaml_file = self.config.data_description_filepath()
        self.logger.debug(f"reading data description file {var_yaml_file}")
        self.data.read_from_yaml(var_yaml_file)

    def read_from_bufr(self):
        bufr_file_path = self.config.bufr_filepath()
        self.logger.debug(f"reading bufr file {bufr_file_path}")
        self.data.read_from_bufr(bufr_file_path)
        self.logger.debug(f"filtered from bufr: data size = {self.data.get_data_size()}")

    def process_data(self):
        self.data.add_preqc_vars()
        self.data.add_error_vars()
        self.data.add_seq_num()
        ocean_file_path = self.config.ocean_basin_nc_file_path()
        self.data.add_ocean_basin(ocean_file_path)
        # self.data.describe()

    def write_to_ioda_file(self):
        self.logger.debug(f"writing ioda file {self.config.ioda_filepath()}")
        self.data.write_to_ioda_file(self.config)

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

            self.logger.debug(f"TEST: running diff with reference file {test_file}")  

            result = run_diff(temp_log_file_name, test_file, self.logger)
            if result:
                self.logger.error(f"TEST ERROR: files are different")
            else:
                self.logger.info(f"TEST passed: files are identical")

            return result
