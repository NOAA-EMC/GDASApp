import json
import yaml
import os


class Bufr2iodaConfig:
    def __init__(self, script_name, config_file, platform_description):
        self.script_name = script_name
        self.platform_description = platform_description

        _, file_extension = os.path.splitext(config_file)

        if file_extension == ".json":
            with open(config_file, "r") as file:
                config = json.load(file)
            self.ReadConfig(config)
        elif file_extension == ".yaml":
            with open(config_file, "r") as file:
                config = yaml.safe_load(file)
            self.ReadConfig(config)
        else:
            print("Unknown file extension = ", file_extension)

    def ReadConfig(self, config):
        subsets = config["subsets"]

        # Get parameters from configuration
        self.data_format = config["data_format"]
        self.source = config["source"]
        self.data_type = config["data_type"]
        self.data_description = config["data_description"]
        self.data_provider = config["data_provider"]
        self.cycle_type = config["cycle_type"]
        self.cycle_datetime = config["cycle_datetime"]
        self.dump_dir = config["dump_directory"]
        self.ioda_dir = config["ioda_directory"]

        self.yyyymmdd = self.cycle_datetime[0:8]
        self.hh = self.cycle_datetime[8:10]

        # General Information
        self.converter = 'BUFR to IODA Converter'

    def BufrFilename(self):
        return f"{self.cycle_datetime}-{self.cycle_type}.t{self.hh}z.{self.data_format}.tm00.bufr_d"

    def BufrFilepath(self):
        return os.path.join(self.dump_dir, self.BufrFilename())

    def IODAFilename(self):
        return f"{self.cycle_type}.t{self.hh}z.insitu_profile_{self.data_format}.{self.cycle_datetime}.nc4"

    def IODAFilepath(self):
        return os.path.join(self.ioda_dir, self.IODAFilename())

    def CreateIODAAttributes(self, obsspace, date_range):
        obsspace.write_attr('Converter', self.converter)
        obsspace.write_attr('source', self.source)
        obsspace.write_attr('sourceFiles', self.BufrFilename())
        obsspace.write_attr('dataProviderOrigin', self.data_provider)
        obsspace.write_attr('description', self.data_description)
        obsspace.write_attr('datetimeRange', date_range)
        obsspace.write_attr('platformLongDescription', self.platform_description)
