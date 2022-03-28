#!/usr/bin/env python3
import argparse
import os
import shutil
from r2d2 import store
from solo.configuration import Configuration
from solo.date import date_sequence
import yaml


def store_obs(yaml_file):
    config = Configuration(yaml_file)
    dates = date_sequence(config.start, config.end, config.step)
    obs_types = config.obs_types
    provider = config.provider
    experiment = config.experiment
    database = config.database
    type = config.type
    source_dir = config.source_dir
    step = config.step

    for date in dates:
        day = str(date).split('T')[0]
        year = day[0:4]
        month = day[4:6]
        day = day[6:8]
        for obs_type in obs_types:
            obs_prefix = obs_type.split('_')[0]
            store(
                provider=provider,
                type=type,
                experiment=experiment,
                database=database,
                date=date,
                obs_type=obs_type,
                time_window=step,
                source_file=f'{source_dir}/{obs_type}_{year}{month}{day}.nc4',
                ignore_missing=True,
            )


if __name__ == "__main__":

    # Set the R2D2_CONFIG environement variable
    r2d2_config = {'databases': {'archive': {'bucket': 'archive.jcsda',
                                             'cache_fetch': True,
                                             'class': 'S3DB'},
                                 'local': {'cache_fetch': False,
                                           'class': 'LocalDB',
                                           'root': './r2d2-local/'},
                                 'shared': {'cache_fetch': False,
                                            'class': 'LocalDB',
                                            'root': './r2d2-shared/'}},
                   'fetch_order': ['local'],
                   'store_order': ['shared', 'local', 'archive']}
    f = open('r2d2_config_test.yaml', 'w')
    yaml.dump(r2d2_config, f, sort_keys=False, default_flow_style=False)
    os.environ['R2D2_CONFIG'] = 'r2d2_config_test.yaml'

    # Change the obs file format
    wrk = os.getenv('WRK_DIR')
    shutil.copyfile(os.path.join(wrk, 'adt.nc'), 'adt_j3_20180415.nc4', follow_symlinks=True)
    shutil.copyfile(os.path.join(wrk, 'sst.nc'), 'sst_noaa19_l3u_20180415.nc4', follow_symlinks=True)
    shutil.copyfile(os.path.join(wrk, 'sss.nc'), 'sss_smap_20180415.nc4', follow_symlinks=True)
    shutil.copyfile(os.path.join(wrk, 'prof.nc'), 'temp_profile_fnmoc_20180415.nc4', follow_symlinks=True)
    shutil.copyfile(os.path.join(wrk, 'prof.nc'), 'salt_profile_fnmoc_20180415.nc4', follow_symlinks=True)
    shutil.copyfile(os.path.join(wrk, 'icec.nc'), 'icec_EMC_20180415.nc4', follow_symlinks=True)
    shutil.copyfile(os.path.join(wrk, 'icefb.nc'), 'icefb_GDR_20180415.nc4', follow_symlinks=True)

    # Create the test R2D2 database
    obsstore = {'start': '20180415',
                'end': '20180415',
                'step': 'P1D',
                'source_dir': '.',
                'type': 'ob',
                'database': 'shared',
                'provider': 'gdasapp',
                'experiment': 'soca',
                'obs_types': ['adt_j3',
                              'sst_noaa19_l3u',
                              'sss_smap',
                              'temp_profile_fnmoc',
                              'salt_profile_fnmoc',
                              'icec_EMC',
                              'icefb_GDR']}
    f = open('store_obs.yaml', 'w')
    yaml.dump(obsstore, f, sort_keys=False, default_flow_style=False)
    store_obs('store_obs.yaml')
