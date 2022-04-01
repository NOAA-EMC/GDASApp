#!/usr/bin/env python3
import os
from r2d2 import store
from solo.configuration import Configuration
from solo.date import date_sequence
import yaml

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
