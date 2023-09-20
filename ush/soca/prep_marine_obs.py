#!/usr/bin/env python3

from wxflow import FileHandler
from datetime import datetime, timedelta
import os
import fnmatch



DMPDIR = os.getenv('DMPDIR')
cyc = os.getenv('cyc')
PDY = os.getenv('PDY')
CDUMP = os.getenv('CDUMP')
COMIN_OBS = os.getenv('COMIN_OBS')

cycdir = os.path.join( DMPDIR, CDUMP + '.' + str(PDY), str(cyc))

obs_dict = {
    #                   'rads_adt_3a_2021182.nc'
    'adt_3a_egm2008': ('ADT', 'rads_adt_3a_???????.nc'),

    #                   'rads_adt_3b_2021182.nc'
    'adt_3b_egm2008': ('ADT', 'rads_adt_3b_???????.nc'),

    #                   'rads_adt_c2_2021182.nc'
    'adt_c2_egm2008': ('ADT', 'rads_adt_c2_???????.nc'),

    #                   'rads_adt_j2_2021182.nc'
    'adt_j2': ('ADT', 'rads_adt_j2_???????.nc'),

    #                   'rads_adt_j3_2021182.nc'
    'adt_j3': ('ADT', 'rads_adt_j3_???????.nc'),

    #                   'rads_adt_sa_2021182.nc'
    'adt_sa_egm2008': ('ADT', 'rads_adt_sa_???????.nc'),

    #       'AMSR2-SEAICE-NH_v2r2_GW1_s202107011426180_e202107011605170_c202107011642250.nc'
    'icec_amsr2_north': ('icec', 'AMSR2-SEAICE-NH_v2r2_GW1_s???????????????_e???????????????_c???????????????.nc'),

    #                   'AMSR2-SEAICE-SH_v2r2_GW1_s202107011426180_e202107011605170_c202107011642250.nc'
    'icec_amsr2_south': ('icec', 'AMSR2-SEAICE-SH_v2r2_GW1_s???????????????_e???????????????_c???????????????.nc'),

    #                   'SMAP_L2B_SSS_NRT_34268_A_20210701T153914.h5'
    'sss_smap': ('SSS', 'SMAP_L2B_SSS_NRT_?????_[AD]_????????T??????.h5'),

    #                     '20210701150000-OSPO-L3U_GHRSST-SSTsubskin-VIIRS_N20-ACSPO_V2.61-v02.0-fv01.0.nc'
    'sst_viirs_n20_l3u_so025': ('sst', '??????????????-OSPO-L3U_GHRSST-SSTsubskin-VIIRS_N20-ACSPO_V2.61-v02.0-fv01.0.nc'),

}


def obs_fetch(obs_source_name):

    try:
        obs_source = obs_dict[obs_source_name]
    except KeyError:
        print(f'WARNING: no obs source {obs_source_name} defined, skipping')
        return

    subdir = obs_source[0]
    filepattern = obs_source[1]  

    datadir = os.path.join(cycdir, subdir)
    # TODO: check the existence of this
    print('datadir:', datadir)
    matching_files = []

    for root, _, files in os.walk(datadir):
        for filename in fnmatch.filter(files, filepattern):
            matching_files.append((root, filename))

    obs_cpy = []
    for obs_src in matching_files:
        obs_path = os.path.join(obs_src[0], obs_src[1])
        obs_dst = os.path.join(COMIN_OBS, obs_src[1])
        obs_cpy.append([obs_path, obs_dst])

    print(obs_cpy)

    FileHandler({'copy': obs_cpy}).sync()


