from r2d2 import fetch
from solo.basic_files import mkdir
from solo.date import Hour, DateIncrement
from solo.logger import Logger
from solo.stage import Stage
import os
import shutil
import datetime as dt

__all__ = ['background', 'fv3jedi', 'obs', 'berror']


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
