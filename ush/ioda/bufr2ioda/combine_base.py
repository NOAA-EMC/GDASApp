import json
import os
import re
import yaml

import bufr
from bufr.encoders import netcdf
from utils import timing_decorator
from wxflow import Logger, Jinja
from pprint import pprint

GROUPS = ['MetaData', 'ObsValue']

logger = Logger(os.path.basename(__file__), level='INFO')

json_template_base = {
    "data_format": "bufr_d",
    "data_type": ["esamua", "1bamua_td"],
    "cycle_type": "{{ RUN }}",
    "cycle_datetime": "{{ current_cycle | to_YMDH }}",
    "dump_directory": "{{ DMPDIR }}",
    "ioda_directory": "{{ COM_OBS }}",
}


class Bufr2IodaBase:
    def __init__(self, config_para):
        json_object = json.dumps(json_template_base, indent=4)
        self.config = {}  # json.loads(Jinja(json_object, config_para).render)  # make it a method if the base is not unique
        self.yaml_config = {}
        self.yaml_path = None
        self.ioda_files = None
        self.obs_data_in = None
        self.splits = None
        self.sat_ids = None
        self.container = None

    def initialization(self):
        self.yaml_path = self.get_yaml_file()
        pprint(self.yaml_config)
        self.ioda_files = self.yaml_config['encoder'].get('obsdataout')
        self.obs_data_in = self.yaml_config['bufr'].get('obsdatain')
        logger.info(f'Ioda output files are: {self.ioda_files}')
        self.splits = self.yaml_config['bufr'].get('splits')
        self.sat_ids = None
        if self.splits:
            self.sat_ids = [x for x in self.splits['satId']['category']['map'].values()]
            logger.info(self.splits)


    @staticmethod
    def get_config_json(file_name):
        with open(file_name, "r") as json_file:
            config = json.load(json_file)
        if config:
            return config
        else:
            return None  # TODO, raise an file error Exception

    def get_container_variable(self, group, variable, sat_id):
        return self.container.get(group + '/' + variable, [sat_id, ])

    def replace_container_variable(self, group, variable, var, sat_id):
        self.container.replace(group + '/' + variable, var, [sat_id, ])

    def get_yaml_file(self):
        return self.config['yaml_file']

    def get_yaml_config(self):
        with open(self.yaml_path, 'r') as yaml_file:
            yaml_config = yaml.load(yaml_file, Loader=yaml.FullLoader)
            return yaml_config

    def make_split_files(self, sat_ids):
        # sat_id a list of ids
        pattern = r'{(.*?)}'
        for sat_id in sat_ids:
            self.split_files[sat_id] = re.sub(pattern, sat_id, self.ioda_files)

    def re_map_variable(self):
        # Make any changes and return for your specific case in the sub-class
        pass

    @timing_decorator
    def set_container(self):
        self.container = bufr.Parser(self.obs_data_in, self.yaml_path).parse()
        self.re_map_variable()

    @timing_decorator
    def encode(self):
        print(f'Output ioda file: {self.ioda_files}')
        netcdf.Encoder(self.yaml_path).encode(self.container, self.ioda_files)

    def execute(self):
        self.initialization()
        self.set_container
        self.encode()

    def get_info(self):
        if not self.split_files:
            self.make_split_files(self.splits)
        sat_info = {'ioda_files': self.ioda_files,
                    'split': self.splits,
                    'split_files': self.split_files
                    }
        return sat_info
