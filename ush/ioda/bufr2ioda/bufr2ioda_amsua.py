#!/usr/bin/env python3

import bufr
import os
from pyioda.ioda.Engines.Bufr import Encoder
#from wxflow import Logger
import logging
#from bufr2ioda_ncep_1bmusa import Bufr2IodaAmusa
#from bufr2ioda_ncep_esamua import Bufr2IodaEsamusa

# logger = Logger(os.path.basename(__file__), level='INFO', colored_log=True)
logger = logging.getLogger(__name__)
YAML_PATH_ES = './bufr2ioda_esamua_mapping.yaml'
YAML_PATH_1B = './bufr2ioda_1bamua_mapping.yaml'


def get_description(yaml_path):

    description = bufr.encoders.Description(yaml_path)

    return description


def get_one_data(input_path, yaml_path, category):
    cache = bufr.DataCache.has(input_path, yaml_path)
    if cache:
        logger.info(f'The cache existed get data container from it')
        C = bufr.DataCache.get(input_path, YAML_PATH_ES)
        #data = Encoder(get_description(yaml_path)).encode(container)[(category,)]
        #bufr.DataCache.mark_finished(input_path, yaml_path, [category])
    else:
        # If cacache does not exist, get data into cache
        # Get data info container first
        logger.info(f'The cache is not existed')
        container = bufr.Parser(input_path, yaml_path).parse()
        logger.info(f'add original container list into a cache = {container.list()}')
        bufr.DataCache.add(input_path, yaml_path, container.all_sub_categories(), container)
        #data = Encoder(get_description(yaml_path)).encode(container)[(category,)]
        #bufr.DataCache.mark_finished(input_path, yaml_path, [category])
    return container


def create_obs_group(input_path1, input_path2, category):
    logger.info(f'imput_path: {input_path1}, {input_path2}, and category: {category}')
    logger.info(f'Entering function to create obs group for {category} with yaml path {YAML_PATH_ES} and {YAML_PATH_1B}')
    container_1 = get_one_data(input_path1, YAML_PATH_ES, category)
    container_2 = get_one_data(input_path2, YAML_PATH_1B, category)

    print(f'emily checking - Original container list = ', container_1.list())
    print(f'emily checking - Original container list = ', container_2.list())
    container = container_1
    container.append(container_2)

    print('Done')
    data = Encoder(get_description(YAML_PATH_ES)).encode(container)[(category,)]
    return data

