import json
import netCDF4 as nc
import re
import yaml

from pyiodaconv import bufr

from wxflow import Logger

from utils import timing_decorator

CPP = 1
PYTHON = 2

logger = Logger('BUFR2IODA_satwind_amv_goes.py', level='DEBUG')


class Bufr2IodaBase:

    def __init__(self, file_name, backend=PYTHON):
        with open(file_name, "r") as json_file:
            config = json.load(json_file)
        self.config = config
        yaml_config = self.get_yaml_config()
        self.yaml_config = yaml_config
        self.ioda_files = yaml_config['observations'][0]['ioda'].get('obsdataout')
        logger.info(f'Ioda output files are: {self.ioda_files}')
        self.splits = yaml_config['observations'][0]['obs space']['exports'].get('splits')
        self.sat_ids = None
        if self.splits:
            self.sat_ids = self.splits['satId']['category']['map'].values()
        logger.info(self.splits)
        self.split_files = {}
        self.yaml_path = None
        self.backend = backend

    def check_yaml_config(yaml_config):
        # TODO make some consistency check?
        pass

    def get_attr(self, config):
        # TODO add more attr into the ioda file from config
        obs_attr = {}
        return obs_attr

    def get_container(self):
        container = {}
        if self.backend == PYTHON:
            self.yaml_path = self.get_yaml_file()
            container = bufr.Parser(self.yaml_path).parse()
        elif self.backend == CPP:
            container = {}
            for sat_id in self.sat_ids:
                try:
                    container[sat_id] = nc.Dataset(self.split_files[sat_id], 'r+')
                except FileNotFoundError as e:
                    logger.info(e)
        return container

    def get_container_variable(self, container, variable, sat_id):
        ret = None
        if self.backend == PYTHON:
            ret = container.get(variable, sat_id)
        elif self.backend == CPP:
            ret = container[sat_id][variable][:]
        return ret

    def replace_container_variable(self, container, variable, var, sat_id):
        if self.backend == PYTHON:
            container.replace(variable, sat_id)
        elif self.backend == CPP:
            container[sat_id][variable][:] = var

    def get_yaml_file(self):
        return self.config['yaml_file']

    def get_yaml_config(self):
        # TODO  add and/or modify ymal contents from config json file. e.g. file names, etc.
        # What does en_bufr2ioda_yaml.py do?   connection to this?
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
        if self.backend == PYTHON:
            ioda_description = bufr.IodaDescription(self.yaml_path)
            bufr.IodaEncoder(ioda_description).encode(container)
        elif self.backend == CPP:
            for item in container:
                container[item].close()

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
