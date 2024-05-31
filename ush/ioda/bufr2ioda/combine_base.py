import json
import os
import re
import yaml

import bufr
from bufr.encoders import netcdf
from utils import timing_decorator
from wxflow import Logger, Jinja,  save_as_yaml
from pprint import pprint

GROUPS = ['MetaData', 'ObsValue']

logger = Logger(os.path.basename(__file__), level='INFO')

json_template_base = {
    "data_format": "bufr_d",
    "cycle_type": "{{ RUN }}",
    "cycle_datetime": "20220810",  #'"{{ current_cycle | to_YMDH }}",
    "dump_directory": "{{ DMPDIR }}",
    "ioda_directory": "{{ COM_OBS }}",
}

bufr_base = {
    'variables': {
        'timestamp': {'datetime': {'day': '*/DAYS',
                                       'hour': '*/HOUR',
                                       'minute': '*/MINU',
                                       'month': '*/MNTH',
                                       'second': '*/SECO',
                                       'year': '*/YEAR'}}}
}

encoder_base = {
    'backend': 'netcdf',
    'variables': [{'longName': 'Datetime',
                   'name': 'MetaData/dateTime',
                   'source': 'variables/timestamp',
                   'units': 'seconds since 1970-01-01T00:00:00Z'},
                  {'longName': 'Latitude',
                   'name': 'MetaData/latitude',
                   'range': [-90, 90],
                   'source': 'variables/latitude',
                   'units': 'degree_north'},
                  {'longName': 'Longitude',
                   'name': 'MetaData/longitude',
                   'source': 'variables/longitude',
                   'units': 'degree_east'},
}

class Bufr2IodaBase:
    def __init__(self, config_para):
        json_object = json.dumps(json_template_base, indent=4)
        self.config = json.loads(Jinja(json_object, config_para).render)  # make it a method if the base is not unique
        self.yaml_config = None
        self.yaml_path = None
        self.ioda_files = None
        self.obs_data_in = None
        self.container = None

    def initialization(self):
        self.yaml_path = self.get_yaml_file()
        pprint(self.yaml_config)
        self.ioda_files = self.yaml_config['encoder'].get('obsdataout')
        self.obs_data_in = self.yaml_config['bufr'].get('obsdatain')
        logger.info(f'Ioda output files are: {self.ioda_files}')

    def update_config(self, config_json):
        self.config.update(config_json)

    def set_yaml(self):
        save_as_yaml(ssmis_yaml, yaml_file)

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
        logger.info(f'Parser: input-{self.obs_data_in}, yaml_path- {self.yaml_path}')
        self.container = bufr.Parser(self.obs_data_in, self.yaml_path).parse()
        logger.info('finished parsing')
        self.re_map_variable()

    @timing_decorator
    def encode(self):
        print(f'Output ioda file: {self.ioda_files}')
        netcdf.Encoder(self.yaml_path).encode(self.container, self.ioda_files)

    def execute(self):
        self.initialization()
        self.set_container()
        self.encode()

    def get_info(self):
        if not self.split_files:
            self.make_split_files(self.splits)
        sat_info = {'ioda_files': self.ioda_files,
                    'split': self.splits,
                    'split_files': self.split_files
                    }
        return sat_info
