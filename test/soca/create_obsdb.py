#!/usr/bin/env python3
import os
import shutil
from solo.configuration import Configuration
from solo.nice_dict import NiceDict
import ufsda.r2d2

if __name__ == "__main__":

    # Setup the shared R2D2 databases
    ufsda.r2d2.setup(r2d2_config_yaml='r2d2_config.yaml', shared_root='./r2d2-shared')

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
