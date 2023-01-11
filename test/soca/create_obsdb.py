#!/usr/bin/env python3
import os
import shutil
from solo.configuration import Configuration
from solo.nice_dict import NiceDict
import ufsda.r2d2

if __name__ == "__main__":

    shared_root = './r2d2-shared'
    r2d2_config_yaml = 'r2d2_config.yaml'

    # clean output before running - if nothing found, assume first run
    try:
        shutil.rmtree(shared_root)
        os.remove(r2d2_config_yaml)
        os.remove('*20180415.nc4')
    except FileNotFoundError:
        pass

    # Setup the shared R2D2 databases
    ufsda.r2d2.setup(r2d2_config_yaml=r2d2_config_yaml, shared_root=shared_root)

    # Change the obs file name format
    obsdir = os.getenv('OBS_DIR')
    shutil.copyfile(os.path.join(obsdir, 'adt.nc'), 'adt_j3_20180415.nc4', follow_symlinks=True)
    shutil.copyfile(os.path.join(obsdir, 'sst.nc'), 'sst_noaa19_l3u_20180415.nc4', follow_symlinks=True)
    shutil.copyfile(os.path.join(obsdir, 'sss.nc'), 'sss_smap_20180415.nc4', follow_symlinks=True)
    shutil.copyfile(os.path.join(obsdir, 'prof.nc'), 'temp_profile_fnmoc_20180415.nc4', follow_symlinks=True)
    shutil.copyfile(os.path.join(obsdir, 'prof.nc'), 'salt_profile_fnmoc_20180415.nc4', follow_symlinks=True)
    shutil.copyfile(os.path.join(obsdir, 'icec.nc'), 'icec_EMC_20180415.nc4', follow_symlinks=True)
    shutil.copyfile(os.path.join(obsdir, 'icefb.nc'), 'icefb_GDR_20180415.nc4', follow_symlinks=True)

    # Create the test R2D2 database
    obsstore = NiceDict({'start': '2018-04-15T00:00:00Z',
                         'end': '2018-04-15T00:00:00Z',
                         'step': 'PT24H',
                         'source_dir': '.',
                         'source_file_fmt': '{source_dir}/{obs_type}_{year}{month}{day}.nc4',
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
                                       'icefb_GDR']})
    ufsda.r2d2.store(obsstore)

# Create the test R2D2 database for output from bufr2ioda tests
    obsstore['source_dir'] = '../../testoutput/'
    obsstore['source_file_fmt'] = '{source_dir}/{obs_type}_{year}{month}{day}.nc'
    obsstore['obs_types'] = ['temp_bufr_dbuoyprof',
                             'salt_bufr_dbuoyprof',
                             'temp_bufr_mbuoybprof',
                             'salt_bufr_mbuoybprof',
                             'bufr_sfcships',
                             'bufr_sfcshipsu']
    ufsda.r2d2.store(obsstore)

    obsstore['start'] = '2018-04-01T00:00:00Z'
    obsstore['end'] = '2018-04-01T00:00:00Z'
    obsstore['source_file_fmt'] = '{source_dir}/{obs_type}_{year}{month}.nc'
    obsstore['obs_types'] = ['bufr_tesacprof',
                             'bufr_trkobprof']
    ufsda.r2d2.store(obsstore)
