import json
import os
import xarray as xr
import re
import yaml

from pyiodaconv import bufr

from wxflow import Logger

from utils import timing_decorator

CPP = 1
PYTHON = 2
GROUPS = ['MetaData', 'ObsValue']

logger = Logger(os.path.basename(__file__), level='DEBUG')


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
            self.sat_ids = [x for x in self.splits['satId']['category']['map'].values()]
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
                logger.info(f'Processing sat_id: {sat_id}')
                try:
                    container[sat_id] = {}
                    file_name = self.split_files[sat_id]
                    container[sat_id]['dset'] = xr.open_dataset(file_name)
                    for group in GROUPS:
                        container[sat_id][group] = xr.open_dataset(file_name, group=group)
                except FileNotFoundError as e:
                    logger.info(f'File not existed exception for sat id: {sat_id} with error msg: {e}')
                    container.pop(sat_id)
            self.sat_ids = container.keys()
            logger.info(f'sat_ids included in the container: {container.keys()}')
        return container

    def get_container_variable(self, container, group, variable, sat_id):
        ret = None
        if self.backend == PYTHON:
            ret = container.get(group + '/' + variable, sat_id)
        elif self.backend == CPP:
            ret = container[sat_id][group][variable]
        return ret

    def replace_container_variable(self, container, group, variable, var, sat_id):
        if self.backend == PYTHON:
            container.replace(group + '/' + variable, sat_id)
        elif self.backend == CPP:
            container[sat_id][group][variable] = var

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
        if self.backend == PYTHON:
            ioda_description = bufr.IodaDescription(self.yaml_path)
            bufr.IodaEncoder(ioda_description).encode(container)
        elif self.backend == CPP:
            for sat_id in container:
                logger.info(f'Encode for {sat_id}')
                container[sat_id]['dset'].close()
                file_name = self.split_files[sat_id] + 'c'
                container[sat_id]['dset'].to_netcdf(file_name)
                for group in GROUPS:
                    container[sat_id][group].to_netcdf(file_name, mode='a', group=group)

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
