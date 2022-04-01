#!/usr/bin/env python3
import os
from r2d2 import store
from solo.configuration import Configuration
from solo.date import date_sequence
import yaml
import ufsda.r2d2


def store_satbias(yaml_file):
    config = Configuration(yaml_file)
    ufsda.r2d2.store(config)


if __name__ == "__main__":
    # create a dummy R2D2 config YAML
    r2d2_config = {
        'databases':
            {'test': {'cache_fetch': False,
                      'class': 'LocalDB',
                      'root': os.path.join(os.getcwd(), 'r2d2-test')}, },
        'fetch_order': ['test'],
        'store_order': ['test'],
    }
    with open(os.path.join(os.getcwd(), 'testinput', 'r2d2_config_test.yaml'), 'w') as f:
        yaml.dump(r2d2_config, f, sort_keys=False, default_flow_style=False)
    os.environ['R2D2_CONFIG'] = os.path.join(os.getcwd(), 'testinput', 'r2d2_config_test.yaml')
    # create YAML for satbias
    satbias = {
        'start': '2022-04-01T00:00:00Z',
        'end': '2022-04-01T00:00:00Z',
        'step': 'PT6H',
        'source_dir': os.path.join(os.getcwd(), 'testoutput', 'satbias'),
        'source_file_fmt': '{source_dir}/{dump}.{year}{month}{day}/{hour}/atmos/{obs_type}_satbias.nc4',
        'type': 'bc',
        'database': 'test',
        'provider': 'gsi',
        'experiment': 'gdasapp',
        'obs_types': [
            'amsua_metop-b',
            'atms_npp',
            'cris-fsr_npp',
            'iasi_metop-c',
        ],
    }
    satbias_yaml = os.path.join(os.getcwd(), 'testinput', 'r2d2_store_satbias.yaml')
    with open(satbias_yaml, 'w') as f:
        yaml.dump(satbias, f, sort_keys=False, default_flow_style=False)
    # create YAML for tlapse
    tlapse = {
        'start': '2022-04-01T00:00:00Z',
        'end': '2022-04-01T00:00:00Z',
        'step': 'PT6H',
        'source_dir': os.path.join(os.getcwd(), 'testoutput', 'satbias'),
        'source_file_fmt': '{source_dir}/{dump}.{year}{month}{day}/{hour}/atmos/{obs_type}_tlapmean.txt',
        'type': 'tlapse',
        'database': 'test',
        'provider': 'gsi',
        'experiment': 'gdasapp',
        'obs_types': [
            'amsua_metop-b',
            'atms_npp',
            'cris-fsr_npp',
            'iasi_metop-c',
        ],
    }
    tlapse_yaml = os.path.join(os.getcwd(), 'testinput', 'r2d2_store_tlapse.yaml')
    with open(tlapse_yaml, 'w') as f:
        yaml.dump(tlapse, f, sort_keys=False, default_flow_style=False)
    # call the store commands
    store_satbias(satbias_yaml)
    store_satbias(tlapse_yaml)
