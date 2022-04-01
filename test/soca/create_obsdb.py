#!/usr/bin/env python3
import argparse
import os
import shutil
from r2d2 import store
from solo.configuration import Configuration
from solo.date import date_sequence
import yaml
import ufsda.store


def store_obs(yaml_file):
    config = Configuration(yaml_file)
    config['component'] = 'soca'
    ufsda.store.obs(config)


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
    obsdir = os.getenv('OBS_DIR')
    shutil.copyfile(os.path.join(obsdir, 'adt.nc'), 'adt_j3_20180415.nc4', follow_symlinks=True)
    shutil.copyfile(os.path.join(obsdir, 'sst.nc'), 'sst_noaa19_l3u_20180415.nc4', follow_symlinks=True)
    shutil.copyfile(os.path.join(obsdir, 'sss.nc'), 'sss_smap_20180415.nc4', follow_symlinks=True)
    shutil.copyfile(os.path.join(obsdir, 'prof.nc'), 'temp_profile_fnmoc_20180415.nc4', follow_symlinks=True)
    shutil.copyfile(os.path.join(obsdir, 'prof.nc'), 'salt_profile_fnmoc_20180415.nc4', follow_symlinks=True)
    shutil.copyfile(os.path.join(obsdir, 'icec.nc'), 'icec_EMC_20180415.nc4', follow_symlinks=True)
    shutil.copyfile(os.path.join(obsdir, 'icefb.nc'), 'icefb_GDR_20180415.nc4', follow_symlinks=True)

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
