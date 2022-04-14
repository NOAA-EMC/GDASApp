from r2d2 import fetch
from solo.basic_files import mkdir
from solo.date import Hour, DateIncrement
from solo.logger import Logger
from solo.stage import Stage
from solo.configuration import Configuration
from solo.nice_dict import NiceDict
import os
import shutil
import datetime as dt
import ufsda

__all__ = ['atm_background', 'atm_obs', 'gdas_fix', 'gdas_single_cycle']


def gdas_fix(input_fix_dir, working_dir, config):
    """
    gdas_fix(input_fix_dir, working_dir, config):
        Stage fix files needed by FV3-JEDI for GDAS analyses
        input_fix_dir - path to root fix file directory
        working_dir - path to where files should be linked to
        config - dict containing configuration
    """
    # create output directories
    ufsda.disk_utils.mkdir(config['fv3jedi_fieldset_dir'])
    ufsda.disk_utils.mkdir(config['fv3jedi_fix_dir'])
    # figure out analysis resolution
    if config['DOHYBVAR']:
        case_anl = config['CASE_ENKF']
    else:
        case_anl = config['CASE']
    layers = int(config['LEVS'])-1
    # link static B files
    ufsda.disk_utils.symlink(os.path.join(input_fix_dir, 'bump', case_anl),
                             config['fv3jedi_staticb_dir'])
    # link akbk file
    ufsda.disk_utils.symlink(os.path.join(input_fix_dir, 'fv3jedi',
                                          'fv3files', f"akbk{layers}.nc4"),
                             os.path.join(config['fv3jedi_fix_dir'], 'akbk.nc4'))
    # link other fv3files
    ufsda.disk_utils.symlink(os.path.join(input_fix_dir, 'fv3jedi',
                                          'fv3files', 'fmsmpp.nml'),
                             os.path.join(config['fv3jedi_fix_dir'], 'fmsmpp.nml'))
    ufsda.disk_utils.symlink(os.path.join(input_fix_dir, 'fv3jedi',
                                          'fv3files', 'field_table_gfdl'),
                             os.path.join(config['fv3jedi_fix_dir'], 'field_table'))
    # link fieldsets
    fieldsets = ['dynamics.yaml', 'ufo.yaml']
    for fieldset in fieldsets:
        ufsda.disk_utils.symlink(os.path.join(input_fix_dir, 'fv3jedi',
                                              'fieldsets', fieldset),
                                 os.path.join(config['fv3jedi_fieldset_dir'], fieldset))
    # link CRTM coeff dir
    ufsda.disk_utils.symlink(os.path.join(input_fix_dir, 'crtm', '2.3.0_jedi'),
                             config['CRTM_COEFF_DIR'])


def atm_background(config):
    # stage FV3 backgrounds
    r2d2_config = {
        'start': config['prev_valid_time'],
        'end': config['prev_valid_time'],
        'step': config['atm_window_length'],
        'forecast_steps': ['PT6H'],  # 3DVar no FGAT for now
        'file_type_list': ['fv_core.res', 'fv_srf_wnd.res', 'fv_tracer.res', 'phy_data', 'sfc_data'],
        'target_dir': config.get('target_dir', config.get('BKG_DIR', './')),
        'target_file_fmt': '{target_dir}/$(valid_date).$(file_type).tile$(tile).nc',
        'type': 'fc',
        'model': 'gfs',
        'resolution': config['CASE'].lower(),
        'database': 'shared',
        'dump': 'gdas',
        'experiment': 'oper_gdas',  # change this here and other places to be oper_{dump}
        'tile': [1, 2, 3, 4, 5, 6],
        'user_date_format': '%Y%m%d.%H%M%S',
        'fc_date_rendering': 'analysis',
    }
    r2d2_config = NiceDict(r2d2_config)
    ufsda.r2d2.fetch(r2d2_config)
    # get gfs metadata
    r2d2_config['model'] = 'gfs_metadata'
    r2d2_config['target_file_fmt'] = '{target_dir}/$(valid_date).$(file_type)'
    r2d2_config['file_type_list'] = ['coupler.res', 'fv_core.res.nc']
    del r2d2_config['tile']
    ufsda.r2d2.fetch(r2d2_config)


def atm_obs(config):
    # fetch atm analysis obs
    r2d2_config = {
        'start': config['prev_valid_time'],
        'end': config['prev_valid_time'],
        'step': config['atm_window_length'],
        'database': 'shared',
        'dump': 'gdas',
        'experiment': 'oper_gdas',  # change this here and other places to be oper_{dump}
        'target_dir': config.get('target_dir', config.get('BKG_DIR', './')),
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
        target_file = ob['obs space']['obsdatain']['obsfile']
        r2d2_config['target_file_fmt'] = target_file
        r2d2_config['obs_types'] = [ob['obs space']['name']]
        ufsda.r2d2.fetch(r2d2_config)
        # get bias files if needed
        if 'obs bias' in ob.keys():
            r2d2_config['type'] = 'bc'
            r2d2_config['provider'] = 'gsi'
            r2d2_config['start'] = config['prev_valid_time']
            r2d2_config['end'] = r2d2_config['start']
            r2d2_config['file_type'] = 'satbias'
            target_file = ob['obs bias']['input file']
            r2d2_config['target_file_fmt'] = target_file
            ufsda.r2d2.fetch(r2d2_config)
            r2d2_config['file_type'] = 'tlapse'
            target_file = target_file.replace('satbias', 'tlapse')
            target_file = target_file.replace('nc4', 'txt')
            r2d2_config['target_file_fmt'] = target_file
            ufsda.r2d2.fetch(r2d2_config)


def gdas_single_cycle(config):
    # grab backgrounds first
    atm_background(config)

    # grab observations and bias correction files
    atm_obs(config)
