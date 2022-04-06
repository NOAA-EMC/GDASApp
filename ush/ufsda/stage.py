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

__all__ = ['background', 'fv3jedi', 'obs', 'berror', 'gdas_fix', 'gdas_single_cycle']


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


def gdas_single_cycle(config):
    # grab backgrounds first
    r2d2_config = {
        'start': config['prev_valid_time'],
        'end': config['prev_valid_time'],
        'step': config['atm_window_length'],
        'forecast_steps': ['PT6H'],  # 3DVar no FGAT for now
        'file_type_list': ['fv_core.res', 'fv_srf_wnd.res', 'fv_tracer.res', 'phy_data', 'sfc_data'],
        'target_dir': config['BKG_DIR'],
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

    # remove things from dict and add/change for obs
    delvars = ['forecast_steps', 'model', 'resolution', 'fc_date_rendering', 'user_date_format']
    for d in delvars:
        del r2d2_config[d]
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




def background(config):
    """
    Stage backgrounds and create links for analysis
    This involves:
    - cp RESTART to RESTART_GES
    - ln RESTART_GES to analysis/bkg
    - mkdir analysis/anl
    """
    rst_dir = os.path.join(config['background_dir'], 'RESTART')
    ges_dir = os.path.join(config['background_dir'], 'RESTART_GES')
    jedi_bkg_dir = os.path.join(config['COMOUT'], 'analysis', 'bkg')
    jedi_anl_dir = os.path.join(config['COMOUT'], 'analysis', 'anl')

    # copy RESTART to RESTART_GES
    try:
        shutil.copytree(rst_dir, ges_dir)
    except FileExistsError:
        shutil.rmtree(ges_dir)
        shutil.copytree(rst_dir, ges_dir)
    try:
        os.symlink(ges_dir, jedi_bkg_dir)
    except FileExistsError:
        os.remove(jedi_bkg_dir)
        os.symlink(ges_dir, jedi_bkg_dir)
    mkdir(jedi_anl_dir)


def obs(config):
    """
    Stage observations using R2D2
    based on input `config` dict
    """
    # create directory
    obs_dir = os.path.join(config['COMOUT'], 'analysis', 'obs')
    mkdir(obs_dir)
    for ob in config['observations']:
        obname = ob['obs space']['name'].lower()
        outfile = ob['obs space']['obsdatain']['obsfile']
        # the above path is what 'FV3-JEDI' expects, need to modify it
        outpath = outfile.split('/')
        outpath[0] = 'analysis'
        outpath = '/'.join(outpath)
        outfile = os.path.join(config['COMOUT'], outpath)
        # grab obs using R2D2
        fetch(
            type='ob',
            provider=config['r2d2_obs_src'],
            experiment=config['r2d2_obs_dump'],
            date=config['window begin'],
            obs_type=obname,
            time_window=config['window length'],
            target_file=outfile,
            ignore_missing=True,
            database=config['r2d2_obs_db'],
        )
        # if the ob type has them specified in YAML
        # try to grab bias correction files too
        if 'obs bias' in ob:
            bkg_time = config['background_time']
            satbias = ob['obs bias']['input file']
            # the above path is what 'FV3-JEDI' expects, need to modify it
            satbias = satbias.split('/')
            satbias[0] = 'analysis'
            satbias = '/'.join(satbias)
            satbias = os.path.join(config['COMOUT'], satbias)
            # try to grab bc files using R2D2
            fetch(
                type='bc',
                provider=config['r2d2_bc_src'],
                experiment=config['r2d2_bc_dump'],
                date=bkg_time,
                obs_type=obname,
                target_file=satbias,
                file_type='satbias',
                ignore_missing=True,
                database=config['r2d2_obs_db'],
            )
            # below is lazy but good for now...
            tlapse = satbias.replace('satbias.nc4', 'tlapse.txt')
            fetch(
                type='bc',
                provider=config['r2d2_bc_src'],
                experiment=config['r2d2_bc_dump'],
                date=bkg_time,
                obs_type=obname,
                target_file=tlapse,
                file_type='tlapse',
                ignore_missing=True,
                database=config['r2d2_obs_db'],
            )


def fv3jedi(config):
    """
    fv3jedi(config)
    stage fix files needed for FV3-JEDI
    such as akbk, fieldsets, fms namelist, etc.
    uses input config dictionary for paths
    """
    # create output directory
    mkdir(config['stage_dir'])
    # call solo.Stage
    path = os.path.dirname(config['fv3jedi_stage'])
    stage = Stage(path, config['stage_dir'], config['fv3jedi_stage_files'])


def berror(config):
    """
    Stage background error
    This involves:
    - ln StaticB to analysis/staticb
    """
    jedi_staticb_dir = os.path.join(config['COMOUT'], 'analysis', 'staticb')

    # ln StaticB to analysis/staticb
    try:
        os.symlink(config['staticb_dir'], jedi_staticb_dir)
    except FileExistsError:
        os.remove(jedi_staticb_dir)
        os.symlink(config['staticb_dir'], jedi_staticb_dir)
