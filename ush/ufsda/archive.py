from r2d2 import store
from solo.configuration import Configuration
from solo.nice_dict import NiceDict
import os
import shutil
import datetime as dt
import ufsda
from pygw.yaml_file import YAMLFile

__all__ = ['atm_diags']


def atm_diags(config):
    # fetch atm analysis obs
    r2d2_config = {
        'start': config['prev_valid_time'],
        'end': config['prev_valid_time'],
        'step': config['atm_window_length'],
        'dump': 'gdas',                      # note:  should move dump to config
        'experiment': config['experiment'],
    }
    r2d2_config = NiceDict(r2d2_config)
    # get list of obs to process and their output files
    obs_list_yaml = config['OBS_LIST']
    obs_list_config = YAMLFile(path=obs_list_yaml)
    for ob in obs_list_config['observers']:
        # first get obs
        r2d2_config.pop('file_type', None)
        r2d2_config['type'] = 'ob'
        r2d2_config['provider'] = config['provider']
        r2d2_config['start'] = config['window_begin']
        r2d2_config['end'] = r2d2_config['start']
        print(ob)
        input_file = ob['obs space']['obsdataout']['engine']['obsfile']
        r2d2_config['source_dir'] = config['OBS_DIR']
        r2d2_config['source_file_fmt'] = input_file.replace('.nc4', '_0000.nc4')
        r2d2_config['obs_types'] = [ob['obs space']['name']]
        ufsda.r2d2.store(r2d2_config)
        # store bias files
        if 'obs bias' in ob.keys():
            r2d2_config['type'] = 'bc'
            r2d2_config['provider'] = 'gsi'
            r2d2_config['start'] = config['valid_time']
            r2d2_config['end'] = config['valid_time']

            # store satbias
            r2d2_config['file_type'] = 'satbias'
            target_file = ob['obs bias']['output file']
            r2d2_config['source_file_fmt'] = target_file
            ufsda.r2d2.store(r2d2_config)

            # store satbias_cov    # note:  non-standard R2D2 added for cycling
            r2d2_config['file_type'] = 'satbias_cov'
            target_file = target_file.replace('satbias', 'satbias_cov')
            r2d2_config['source_file_fmt'] = target_file
            ufsda.r2d2.store(r2d2_config)

            # store tlapse
            r2d2_config['file_type'] = 'tlapse'
            target_file = target_file.replace('satbias', 'tlapse')
            target_file = target_file.replace('nc4', 'txt')
            r2d2_config['source_file_fmt'] = target_file
            ufsda.r2d2.store(r2d2_config)
