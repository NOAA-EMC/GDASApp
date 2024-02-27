import json
import os
import re
import yaml

from pyioda.ioda.Engines import bufr
from utils import timing_decorator
from wxflow import Logger

GROUPS = ['MetaData', 'ObsValue']

logger = Logger(os.path.basename(__file__), level='INFO')


class Bufr2IodaBase:
    def __init__(self, file_name):
        with open(file_name, "r") as json_file:
            config = json.load(json_file)
        self.config = config
        yaml_config = self.get_yaml_config()
        self.yaml_config = yaml_config
        self.ioda_files = yaml_config['observations'][0]['ioda'].get('obsdataout')
        self.obs_data_in = yaml_config['observations'][0]['obs space'].get('obsdatain')
        logger.info(f'Ioda output files are: {self.ioda_files}')
        self.splits = yaml_config['observations'][0]['obs space']['exports'].get('splits')
        self.sat_ids = None
        if self.splits:
            self.sat_ids = [x for x in self.splits['satId']['category']['map'].values()]
        logger.info(self.splits)
        self.split_files = {}
        self.yaml_path = None

    def get_container(self):
        self.yaml_path = self.get_yaml_file()
        container = bufr.Parser(self.obs_data_in, self.yaml_path).parse()
        return container

    @staticmethod
    def get_container_variable(container, group, variable, sat_id):
        ret = container.get(group + '/' + variable, sat_id)
        return ret

    @staticmethod
    def replace_container_variable(container, group, variable, var, sat_id):
        container.replace(group + '/' + variable, var, sat_id)

    def get_yaml_file(self):
        return self.config['yaml_file']

    def get_yaml_config(self):
        yaml_file = self.get_yaml_file()
        with open(yaml_file, 'r') as file:
            yaml_config = yaml.load(file, Loader=yaml.FullLoader)
            return yaml_config

    def make_split_files(self, sat_ids):
        # sat_id a list of ids
        pattern = r'{(.*?)}'
        for sat_id in sat_ids:
            self.split_files[sat_id] = re.sub(pattern, sat_id, self.ioda_files)

    def re_map_variable(self, container):
        # Make any changes and return for your specific case in the sub-class
        pass

    def ioda_encode(self, container):
        bufr.IodaEncoder(self.yaml_path).encode(container)

    @timing_decorator
    def execute(self):
        if self.splits:
            self.make_split_files(self.sat_ids)
        container = self.get_container()
        self.re_map_variable(container)
        self.ioda_encode(container)

    def get_info(self):
        if not self.split_files:
            self.make_split_files(self.splits)
        sat_info = {'ioda_files': self.ioda_files,
                    'split': self.splits,
                    'split_files': self.split_files
                    }
        return sat_info
