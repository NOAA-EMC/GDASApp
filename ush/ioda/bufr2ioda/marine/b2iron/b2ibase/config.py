import json
import yaml
import os
import sys


# configuration file can be either json or yaml
# this config class provides the functions that determine
# the names and the paths of the bufr input and the ioda output files
# these functions can be overridden in the converter

class Config:
    def __init__(self, config_file, logger):
        self.logger = logger
        self.logger.debug(f"Reading configuration file {config_file}")
        _, file_extension = os.path.splitext(config_file)
        if file_extension == ".json":
            with open(config_file, "r") as file:
                config = json.load(file)
            self.read_config(config)
        elif file_extension == ".yaml":
            with open(config_file, "r") as file:
                config = yaml.safe_load(file)
            self.read_config(config)
        else:
            self.logger.critical(f"Unknown file extension = {file_extension}")
            sys.exit(1)

    def read_config(self, config):
        # Get parameters from configuration
        self.data_format = config["data_format"]
        self.source = config["source"]
        self.data_type = config["data_type"]
        self.data_provider = config["data_provider"]
        self.cycle_type = config["cycle_type"]
        self.cycle_datetime = config["cycle_datetime"]
        self.dump_dir = config["dump_directory"]
        self.ioda_dir = config["ioda_directory"]
        self.ocean_basin = config["ocean_basin"]
        self.data_description = config["data_description"]
        self.data_description_file = config["data_description_file"]
        self.platform_description = config["platform_description"]

        self.yyyymmdd = self.cycle_datetime[0:8]
        self.hh = self.cycle_datetime[8:10]

        # General Information
        self.converter = 'BUFR to IODA Converter'

    def data_description_filepath(self):
        return self.data_description_file

    def ocean_basin_nc_file_path(self):
        return self.ocean_basin

    def bufr_filename(self):
        return f"{self.cycle_datetime}-{self.cycle_type}.t{self.hh}z.{self.data_format}.tm00.bufr_d"

    def bufr_filepath(self):
        return os.path.join(self.dump_dir, self.bufr_filename())

    def ioda_filename(self):
        return f"{self.cycle_type}.t{self.hh}z.insitu_profile_{self.data_format}.{self.cycle_datetime}.nc4"

    def ioda_filepath(self):
        return os.path.join(self.ioda_dir, self.ioda_filename())

    # def create_ioda_attributes(self, description, date_range):
        # date_range_str = date_range[0] + ", " + date_range[1]
        # description.add_global(name='datetimeRange', value=date_range_str)
        # self.logger.debug("Created ioda global attributes")
