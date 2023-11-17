import json
import re
import yaml

from pyiodaconv import bufr

#from wxflow import Logger
from logging import Logger

from utils import timing_decorator

logger = Logger('BUFR2IODA_satwind_amv_goes.py', level='DEBUG')


class Bufr2IodaBase:

    def __init__(self, file_name):
        with open(file_name, "r") as json_file:
            config = json.load(json_file)
        self.config = config
        yaml_config = self.get_yaml_config(config)
        self.yaml_config = yaml_config
        self.ioda_files = yaml_config['observations'][0]['ioda'].get('obsdataout')
        logger.info(f'Ioda output files are: {self.ioda_files}')
        self.splits = yaml_config['observations'][0]['obs space']['exports'].get('splits')
        self.split_files = None

    def check_yaml_config(yaml_config):
        # TODO make some consistency check?
        pass

    def get_attr(self, config):
        # TODO add more attr into the ioda file from config
        obs_attr = {}
        return obs_attr

    def get_data_container(self):
        pass
    
    def get_yaml_file(self):
        return self.config['yaml_file']
        
    def get_yaml_config(self, config):
        # TODO  add and/or modify ymal contents from config json file. e.g. file names, etc.
        # What does en_bufr2ioda_yaml.py do?   connection to this?
        yaml_file = self.get_yaml_file()
        with open(yaml_file, 'r') as file:
            yaml_config = yaml.load(file, Loader=yaml.FullLoader)
            return yaml_config

    def make_split_files(self, sat_ids):
        # sat_id a list of ids
        pattern = r'{(.*?)}'
        self. split_files = [re.sub(pattern, sat_id[0], self.ioda_files) for sat_id in sat_ids]

    def re_map_variable(self, container, ioda_description):
        # Make any changes and return for your specific case in the sub-class
        pass

    @timing_decorator
    def execute(self):
        yaml_path = self.get_yaml_file()
        container = bufr.Parser(yaml_path).parse()
        ioda_description = bufr.IodaDescription(yaml_path)
        if self.splits:
            self.make_split_files(container.allSubCategories())
        self.re_map_variable(container, ioda_description)
        bufr.IodaEncoder(ioda_description).encode(container)

