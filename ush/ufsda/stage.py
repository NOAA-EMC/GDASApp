from r2d2 import fetch
from solo.basic_files import mkdir
from solo.date import Hour, DateIncrement, date_sequence
from solo.logger import Logger
from solo.stage import Stage
from solo.configuration import Configuration
from solo.nice_dict import NiceDict
from datetime import datetime, timedelta
import os
import shutil
from dateutil import parser
import ufsda
import logging
import glob
import xarray

__all__ = ['atm_background', 'atm_obs', 'bias_obs', 'background', 'fv3jedi', 'obs', 'berror', 'gdas_fix', 'gdas_single_cycle']


def concatenate_ioda(iodafname):
    flist = glob.glob(iodafname+'*')
    flist.sort()
    if len(flist) == 1:
        # No need to concatenate, exit early
        shutil.move(flist[0], iodafname)
        return

    if len(flist) > 1:
        groups = ["ObsError", "ObsValue", "PreQC", "MetaData"]
        mode = 'w'
        for group in groups:
            if group == "MetaData":
                encoding = {'datetime': {'dtype': 'S1'}}
            else:
                encoding = None
            ds = xarray.concat([xarray.open_dataset(f, group=group) for f in flist],
                               dim='nlocs')

            ds.to_netcdf('test.nc4', group=group, mode=mode, encoding=encoding)
            mode = 'a'

    return


def gdas_fix(input_fix_dir, working_dir, config):
    """
    gdas_fix(input_fix_dir, working_dir, config):
        Stage fix files needed by FV3-JEDI for GDAS analyses
        input_fix_dir - path to root fix file directory
        working_dir - path to where files should be linked to
        config - dict containing configuration
    """
    # create output directories
    ufsda.disk_utils.mkdir(config['fv3jedi_fieldmetadata_dir'])
    ufsda.disk_utils.mkdir(config['fv3jedi_fix_dir'])
    # figure out analysis resolution
    if config['DOHYBVAR']:
        case_anl = config['CASE_ENKF']
    else:
        case_anl = config['CASE_ANL']
    layers = int(config['LEVS'])-1

    # figure out staticb source
    staticb_source = config.get('STATICB_TYPE', 'gsibec')

    # link staticb
    if staticb_source in ['bump', 'gsibec']:
        ufsda.disk_utils.symlink(os.path.join(input_fix_dir, staticb_source, case_anl),
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
    # link fieldmetadata
    # Note that the required data will be dependent on input file type (restart vs history, etc.)
    ufsda.disk_utils.symlink(os.path.join(input_fix_dir, 'fv3jedi',
                                          'fieldmetadata', 'gfs-restart.yaml'),
                             os.path.join(config['fv3jedi_fieldmetadata_dir'], 'gfs-restart.yaml'))
    # link CRTM coeff dir
    ufsda.disk_utils.symlink(os.path.join(input_fix_dir, 'crtm', '2.3.0'),
                             config['CRTM_COEFF_DIR'])


def soca_fix(config):
    """
    soca_fix(input_fix_dir, config):
        Stage fix files needed by SOCA for GDAS analyses
        input_fix_dir - path to root fix file directory
        working_dir - path to where files should be linked to
        config - dict containing configuration
    """

    # link static B bump files
    bump_archive = os.path.join(config['soca_input_fix_dir'], 'bump')
    bump_scratch = os.path.join(config['stage_dir'], 'bump')
    if os.path.isdir(bump_archive):
        # link archived bump files
        ufsda.disk_utils.symlink(bump_archive, bump_scratch)
    else:
        # create an empty bump directory
        ufsda.disk_utils.mkdir(bump_scratch)

    # link static sst B
    ufsda.disk_utils.symlink(os.path.join(config['soca_input_fix_dir'], 'godas_sst_bgerr.nc'),
                             os.path.join(config['stage_dir'], 'godas_sst_bgerr.nc'))

    # link Rossby Radius file
    ufsda.disk_utils.symlink(os.path.join(config['soca_input_fix_dir'], 'rossrad.dat'),
                             os.path.join(config['stage_dir'], 'rossrad.dat'))
    # link name lists
    ufsda.disk_utils.symlink(os.path.join(config['soca_input_fix_dir'], 'field_table'),
                             os.path.join(config['stage_dir'], 'field_table'))
    ufsda.disk_utils.symlink(os.path.join(config['soca_input_fix_dir'], 'diag_table'),
                             os.path.join(config['stage_dir'], 'diag_table'))
    ufsda.disk_utils.symlink(os.path.join(config['soca_input_fix_dir'], 'MOM_input'),
                             os.path.join(config['stage_dir'], 'MOM_input'))
    # link field metadata
    ufsda.disk_utils.symlink(os.path.join(config['soca_input_fix_dir'], 'fields_metadata.yaml'),
                             os.path.join(config['stage_dir'], 'fields_metadata.yaml'))

    # INPUT
    ufsda.disk_utils.copytree(os.path.join(config['soca_input_fix_dir'], 'INPUT'),
                              os.path.join(config['stage_dir'], 'INPUT'))


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
        'dump': 'gdas',
        'experiment': 'oper_gdas',  # change this here and other places to be oper_{dump}
        'target_dir': config.get('target_dir', config.get('BKG_DIR', './')),
    }
    r2d2_config = NiceDict(r2d2_config)
    # get list of obs to process and their output files
    obs_list_yaml = config['OBS_LIST']
    obs_list_config = Configuration(obs_list_yaml)
    obs_list_config = ufsda.yamltools.iter_config(config, obs_list_config)
    for ob in obs_list_config['observers']:
        # first get obs
        r2d2_config.pop('file_type', None)
        r2d2_config['type'] = 'ob'
        r2d2_config['provider'] = 'ncdiag'
        r2d2_config['start'] = config['window_begin']
        r2d2_config['end'] = r2d2_config['start']
        target_file = ob['obs space']['obsdatain']['engine']['obsfile']
        r2d2_config['target_file_fmt'] = target_file
        r2d2_config['obs_types'] = [ob['obs space']['name']]
        ufsda.r2d2.fetch(r2d2_config)


def bias_obs(config):
    # fetch bias files
    r2d2_config = {
        'start': config['prev_valid_time'],
        'end': config['prev_valid_time'],
        'step': config['atm_window_length'],
        'dump': 'gdas',
        'experiment': 'oper_gdas',  # change this here and other places to be oper_{dump}
        'target_dir': config.get('target_dir', config.get('BKG_DIR', './')),
    }
    r2d2_config = NiceDict(r2d2_config)
    # get list of obs to process and their output files
    obs_list_yaml = config['OBS_LIST']
    obs_list_config = Configuration(obs_list_yaml)
    obs_list_config = ufsda.yamltools.iter_config(config, obs_list_config)
    for ob in obs_list_config['observers']:
        r2d2_config.pop('file_type', None)
        r2d2_config['obs_types'] = [ob['obs space']['name']]
        # get bias files if needed
        if 'obs bias' in ob.keys():
            r2d2_config['type'] = 'bc'
            r2d2_config['provider'] = 'gsi'
            r2d2_config['start'] = config['prev_valid_time']
            r2d2_config['end'] = r2d2_config['start']

            # fetch satbias
            r2d2_config['file_type'] = 'satbias'
            target_file = ob['obs bias']['input file']
            r2d2_config['target_file_fmt'] = target_file
            r2d2_config['experiment'] = config.get('experiment', 'oper_gdas')
            ufsda.r2d2.fetch(r2d2_config)

            # fetch satbias_cov    # note:  non-standard R2D2 added for cycling
            r2d2_config['file_type'] = 'satbias_cov'
            target_file = target_file.replace('satbias', 'satbias_cov')
            r2d2_config['target_file_fmt'] = target_file
            r2d2_config['experiment'] = config.get('experiment', 'oper_gdas')
            ufsda.r2d2.fetch(r2d2_config)

            # fetch tlapse
            r2d2_config['file_type'] = 'tlapse'
            target_file = target_file.replace('satbias_cov', 'tlapse')
            target_file = target_file.replace('nc4', 'txt')
            r2d2_config['target_file_fmt'] = target_file
            r2d2_config['experiment'] = 'oper_gdas'
            ufsda.r2d2.fetch(r2d2_config)


def gdas_single_cycle(config):
    # grab backgrounds first
    r2d2_config = {
        'start': config['prev_valid_time'],
        'end': config['prev_valid_time'],
        'step': config['atm_window_length'],
        'forecast_steps': config['forecast_steps'],
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
    for ob in obs_list_config['observers']:
        # first get obs
        r2d2_config.pop('file_type', None)
        r2d2_config['type'] = 'ob'
        r2d2_config['provider'] = 'ncdiag'
        r2d2_config['start'] = config['window_begin']
        r2d2_config['end'] = r2d2_config['start']
        target_file = ob['obs space']['obsdatain']['engine']['obsfile']
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
            r2d2_config['file_type'] = 'satbias_cov'
            target_file2 = target_file.replace('satbias', 'satbias_cov')
            r2d2_config['target_file_fmt'] = target_file2
            try:
                ufsda.r2d2.fetch(r2d2_config)
            except FileNotFoundError:
                logging.error("Warning: satbias_cov file cannot be fetched from R2D2!")
                # temp hack to copy satbias as satbias_cov
                # if satbias_cov does not exists in R2D2
                if os.path.isfile(target_file) and not os.path.isfile(target_file2):
                    shutil.copy(target_file, target_file2)
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
    for ob in config['observers']:
        obname = ob['obs space']['name'].lower()
        outfile = ob['obs space']['obsdatain']['engine']['obsfile']
        # the above path is what 'FV3-JEDI' expects, need to modify it
        outpath = outfile.split('/')
        outpath[0] = 'analysis'
        outpath = '/'.join(outpath)
        # grab obs using R2D2
        window_begin = config['window begin']

        print("----------------------------------------------")
        print("----------------------------------------------")
        window_begin = parser.parse(window_begin, fuzzy=True)
        window_end = window_begin + timedelta(hours=6)
        steps = ['P1D', 'PT10M']
        for step in steps:
            if step == 'P1D':
                dates = date_sequence(window_begin.strftime('%Y%m%d'), window_end.strftime('%Y%m%d'), step)
            if step == "PT10M":
                dates = date_sequence(window_begin.strftime('%Y%m%d%H'), window_end.strftime('%Y%m%d%H'), step)
            for count, date in enumerate(dates):
                print("----------   ", count, date, outfile+'.'+str(count))
                fetch(
                    type='ob',
                    provider=config['r2d2_obs_src'],
                    experiment=config['r2d2_obs_dump'],
                    date=date,
                    obs_type=obname,
                    time_window=step,
                    target_file=outfile+'.'+str(count),
                    ignore_missing=True,
                    database=config['r2d2_obs_db']
                )
            # Concatenate ioda files
            concatenate_ioda(outfile)
        print("----------------------------------------------")
        print("----------------------------------------------")


def fv3jedi(config):
    """
    fv3jedi(config)
    stage fix files needed for FV3-JEDI
    such as akbk, fieldmetadata, fms namelist, etc.
    uses input config dictionary for paths
    """
    # create output directory
    mkdir(config['stage_dir'])
    # call solo.Stage
    path = os.path.dirname(config['fv3jedi_stage'])
    stage = Stage(path, config['stage_dir'], config['fv3jedi_stage_files'])


def static(stage_dir, static_source_dir, static_source_files):
    """
    stage_dir: dir destination to copy files in
    static_source_dir: source dir
    static_source_files: list of files to copy
    """

    # create output directory
    mkdir(stage_dir)
    # call solo.Stage
    path = os.path.dirname(static_source_dir)
    stage = Stage(path, stage_dir, static_source_files)


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
