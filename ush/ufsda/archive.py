from r2d2 import store
from solo.configuration import Configuration
from solo.nice_dict import NiceDict
import os
import shutil
import datetime as dt
import ufsda

__all__ = ['atm_diags']


def atm_diags(config):
    # fetch atm analysis obs
    r2d2_config = {
        'start': config['prev_valid_time'],
        'end': config['prev_valid_time'],
        'step': config['atm_window_length'],
        'dump': 'gdas',
        'experiment': config['experiment'],  # change this here and other places to be oper_{dump}
    }
    r2d2_config = NiceDict(r2d2_config)
    # get list of obs to process and their output files
    obs_list_yaml = config['OBS_LIST']
    obs_list_config = Configuration(obs_list_yaml)
    obs_list_config = ufsda.yamltools.iter_config(config, obs_list_config)
    for ob in obs_list_config['observations']:
        # first get obs
        r2d2_config.pop('file_type', None)
        r2d2_config['type'] = 'ob'
        r2d2_config['provider'] = 'ncdiag'
        r2d2_config['start'] = config['window_begin']
        r2d2_config['end'] = r2d2_config['start']
        input_file = ob['obs space']['obsdataout']['obsfile']
        r2d2_config['source_dir'] = config['OBS_DIR']
        r2d2_config['source_file_fmt'] = input_file.replace('.nc4', '_0000.nc4')
        r2d2_config['obs_types'] = [ob['obs space']['name']]
        ufsda.r2d2.store(r2d2_config)
        # get bias files if needed
        if 'obs bias' in ob.keys():
            r2d2_config['type'] = 'bc'
            r2d2_config['provider'] = 'gsi'
            r2d2_config['start'] = config['valid_time']
            r2d2_config['end'] = config['valid_time']
            r2d2_config['file_type'] = 'satbias'
            target_file = ob['obs bias']['output file']
            r2d2_config['source_file_fmt'] = target_file
            ufsda.r2d2.store(r2d2_config)
            r2d2_config['file_type'] = 'tlapse'
            target_file = target_file.replace('satbias', 'tlapse')
            target_file = target_file.replace('nc4', 'txt')
            r2d2_config['source_file_fmt'] = target_file
            ufsda.r2d2.store(r2d2_config)
