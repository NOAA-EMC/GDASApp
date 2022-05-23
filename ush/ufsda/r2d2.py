import r2d2
import re
from solo.configuration import Configuration
from solo.date import date_sequence, Hour, DateIncrement
import yaml
import os

possible_args = [
    'provider', 'experiment', 'database', 'type', 'file_type',
    'resolution', 'model', 'user_date_format', 'fc_date_rendering', 'tile',
]


def setup(shared_root='', r2d2_config_yaml='r2d2_config.yaml'):
    """
    setup(shared_root)

    prepares the R2D2 configuration yaml file and exports the R2D2_CONFIG
    environement variable

    TODO (Guillaume): We need the flexibility to change all key values in the
                      below dictionary ...
    """

    # TODO: Should it be in a template instead?
    r2d2_config = {'databases': {'archive': {'bucket': 'archive.jcsda',
                                             'cache_fetch': True,
                                             'class': 'S3DB'},
                                 'local': {'cache_fetch': False,
                                           'class': 'LocalDB',
                                           'root': './r2d2-local/'},
                                 'shared': {'cache_fetch': False,
                                            'class': 'LocalDB',
                                            'root': shared_root}},
                   'fetch_order': ['shared'],
                   'store_order': ['local']}

    f = open(r2d2_config_yaml, 'w')
    yaml.dump(r2d2_config, f, sort_keys=False, default_flow_style=False)
    os.environ['R2D2_CONFIG'] = r2d2_config_yaml


def store(config):
    inputs = {}
    inputs['ignore_missing'] = True
    for arg in config.keys():
        if arg in possible_args:
            inputs[arg] = config[arg]
    r2d2_type = config.type
    times = date_sequence(config.start, config.end, config.step)
    dump = config.get('dump', 'gdas')
    source_dir = config['source_dir']
    source_file_fmt = config['source_file_fmt']
    obs_types = config.get('obs_types', None)
    for time in times:
        year = Hour(time).format('%Y')
        month = Hour(time).format('%m')
        day = Hour(time).format('%d')
        hour = Hour(time).format('%H')
        inputs['date'] = time
        if r2d2_type in ['bc', 'ob']:
            if r2d2_type == 'ob':
                inputs['date'] = time
                inputs['time_window'] = config['step']
            for obs_type in obs_types:
                inputs['source_file'] = eval(f"f'{source_file_fmt}'"),
                inputs['obs_type'] = obs_type
                r2d2.store(**inputs)
        if r2d2_type in ['fc']:
            inputs['model'] = config['model']
            if config['model'] == 'mom6_cice6_UFS':
                inputs['step'] = config['forecast_steps']
                inputs['experiment'] = config['experiment']
                inputs['database'] = config['database']
                inputs['resolution'] = config['resolution']
                file_type = config['file_type']
                inputs['source_file'] = eval(f"f'{source_file_fmt}'"),
                r2d2.store(**inputs)
            else:
                inputs['file_type'] = config.file_type_list
                inputs['step'] = config['forecast_steps']
                inputs['source_file'] = eval(f"f'{source_file_fmt}'"),
                r2d2.store(**inputs)


def fetch(config):
    inputs = {}
    inputs['ignore_missing'] = False
    for arg in config.keys():
        if arg in possible_args:
            inputs[arg] = config[arg]
    r2d2_type = config.type
    times = date_sequence(config.start, config.end, config.step)
    dump = config.get('dump', 'gdas')
    obs_types = config.get('obs_types', None)
    target_dir = config['target_dir']
    target_file_fmt = config['target_file_fmt']
    for time in times:
        year = Hour(time).format('%Y')
        month = Hour(time).format('%m')
        day = Hour(time).format('%d')
        hour = Hour(time).format('%H')
        inputs['date'] = time
        if r2d2_type in ['bc', 'ob']:
            if r2d2_type == 'ob':
                inputs['time_window'] = config['step']
            for obs_type in obs_types:
                inputs['target_file'] = eval(f"f'{target_file_fmt}'"),
                inputs['obs_type'] = obs_type
                r2d2.fetch(**inputs)
        else:
            inputs['file_type'] = config.file_type_list
            inputs['step'] = config['forecast_steps']
            inputs['target_file'] = eval(f"f'{target_file_fmt}'"),
            r2d2.fetch(**inputs)
