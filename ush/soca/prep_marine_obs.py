#!/usr/bin/env python3

from wxflow import FileHandler
import os
import fnmatch


DMPDIR = os.getenv('DMPDIR')
cyc = os.getenv('cyc')
PDY = os.getenv('PDY')
CDUMP = os.getenv('CDUMP')
COMIN_OBS = os.getenv('COMIN_OBS')

cycdir = os.path.join(DMPDIR, CDUMP + '.' + str(PDY), str(cyc))

# TODO: this looks good for a yaml
obs_dict = {
    #                  '20210630210000-STAR-L3C_GHRSST-SSTsubskin-ABI_G16-ACSPO_V2.70-v02.0-fv01.0.nc'
    'ABI_G16': ('sst', '??????????????-STAR-L3C_GHRSST-SSTsubskin-ABI_G16-ACSPO_V2.70-v02.0-fv01.0.nc '),

    #                  '20210630210000-STAR-L3C_GHRSST-SSTsubskin-ABI_G17-ACSPO_V2.71-v02.0-fv01.0.nc'
    'ABI_G17': ('sst', '??????????????-STAR-L3C_GHRSST-SSTsubskin-ABI_G17-ACSPO_V2.71-v02.0-fv01.0.nc '),

    #                  '20210630210000-STAR-L3C_GHRSST-SSTsubskin-ABI_G18-ACSPO_V2.71-v02.0-fv01.0.nc'
    'ABI_G18': ('sst', '??????????????-STAR-L3C_GHRSST-SSTsubskin-ABI_G18-ACSPO_V2.71-v02.0-fv01.0.nc '),

    #                  '20210630210000-STAR-L3C_GHRSST-SSTsubskin-AHI_H09-ACSPO_V2.70-v02.0-fv01.0.nc'
    'AHI_H09': ('sst', '??????????????-STAR-L3C_GHRSST-SSTsubskin-AHI_H09-ACSPO_V2.70-v02.0-fv01.0.nc '),

    #                   'rads_adt_3b_2021182.nc'
    'adt_3b_egm2008': ('ADT', 'rads_adt_3b_???????.nc'),

    #                   'rads_adt_c2_2021182.nc'
    'adt_c2_egm2008': ('ADT', 'rads_adt_c2_???????.nc'),

    #                   'rads_adt_sa_2021182.nc'
    'adt_sa_egm2008': ('ADT', 'rads_adt_sa_???????.nc'),

    #                            'AMSR2-SEAICE-NH_v2r2_GW1_s202107011426180_e202107011605170_c202107011642250.nc'
    'icec_amsr2_north': ('icec', 'AMSR2-SEAICE-NH_v2r2_GW1_s???????????????_e???????????????_c???????????????.nc'),

    #                            'AMSR2-SEAICE-SH_v2r2_GW1_s202107011426180_e202107011605170_c202107011642250.nc'
    'icec_amsr2_south': ('icec', 'AMSR2-SEAICE-SH_v2r2_GW1_s???????????????_e???????????????_c???????????????.nc'),

    #                   'SM_OPER_MIR_OSUDP2_20210701T093946_20210701T103256_700_001_1.nc'
    'sss_smos': ('SSS', 'SM_OPER_MIR_OSUDP2_????????T??????_????????T??????_700_001_1.nc'),

    #                   'SMAP_L2B_SSS_NRT_34268_A_20210701T153914.h5'
    'sss_smap': ('SSS', 'SMAP_L2B_SSS_NRT_?????_[AD]_????????T??????.h5'),

    #                               '20210701145000-OSPO-L3U_GHRSST-SSTsubskin-AVHRRF_MA-ACSPO_V2.70-v02.0-fv01.0.nc'
    'sst_metopa_l3u_so025': ('sst', '??????????????-OSPO-L3U_GHRSST-SSTsubskin-AVHRRF_MA-ACSPO_V2.70-v02.0-fv01.0.nc'),

    #                               '20210701145000-OSPO-L3U_GHRSST-SSTsubskin-AVHRRF_MB-ACSPO_V2.70-v02.0-fv01.0.nc'
    'sst_metopb_l3u_so025': ('sst', '??????????????-OSPO-L3U_GHRSST-SSTsubskin-AVHRRF_MB-ACSPO_V2.70-v02.0-fv01.0.nc'),

    #                     '20210701150000-OSPO-L3U_GHRSST-SSTsubskin-VIIRS_N20-ACSPO_V2.61-v02.0-fv01.0.nc'
    'sst_viirs_n20_l3u_so025': ('sst', '??????????????-OSPO-L3U_GHRSST-SSTsubskin-VIIRS_N20-ACSPO_V2.61-v02.0-fv01.0.nc'),

    #                     '20210701150000-OSPO-L3U_GHRSST-SSTsubskin-VIIRS_NPP-ACSPO_V2.61-v02.0-fv01.0.nc'
    'sst_viirs_npp_l3u_so025': ('sst', '??????????????-OSPO-L3U_GHRSST-SSTsubskin-VIIRS_NPP-ACSPO_V2.61-v02.0-fv01.0.nc'),

}


def obs_fetch(obsprocSpace):

    subdir = obsprocSpace['obsproc subdir']
    filepattern = obsprocSpace['obsproc regex']

    datadir = os.path.join(cycdir, subdir)
    # TODO: check the existence of this
    print('datadir:', datadir)
    matchingFiles = []

    for root, _, files in os.walk(datadir):
        for filename in fnmatch.filter(files, filepattern):
            matchingFiles.append(filename)

    obs_cpy = []
    for obs_src in matchingFiles:
        obs_path = os.path.join(datadir, obs_src)
        obs_dst = os.path.join(COMIN_OBS, obs_src)
        obs_cpy.append([obs_path, obs_dst])

    print(f"obs_cpy: {obs_cpy}")
    print(f"matchingFiles: {matchingFiles}")

    FileHandler({'copy': obs_cpy}).sync()
    
    return matchingFiles
